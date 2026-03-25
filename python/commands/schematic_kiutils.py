"""
KiCAD Schematic Editor using kiutils

Provides structured, in-memory manipulation of .kicad_sch files.
All operations load from disk, modify the object model, then save back —
no raw text or S-expression manipulation.
"""

import copy
import math
import re
import uuid
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

from kiutils.schematic import Schematic
from kiutils.symbol import SymbolLib
from kiutils.items.schitems import (
    SchematicSymbol,
    SymbolProjectInstance,
    SymbolProjectPath,
    Connection,
    LocalLabel,
    GlobalLabel,
    Junction,
    NoConnect,
    Property,
)
from kiutils.items.common import Position

logger = logging.getLogger("kicad_interface")

# Standard KiCAD symbol library search paths (platform-aware)
_SYMBOL_LIB_SEARCH_PATHS: List[str] = [
    "/usr/share/kicad/symbols",
    "/usr/local/share/kicad/symbols",
    os.path.expanduser("~/kicad/symbols"),
    # macOS
    "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols",
    # Windows (common)
    r"C:\Program Files\KiCad\9.0\share\kicad\symbols",
    r"C:\Program Files\KiCad\8.0\share\kicad\symbols",
]


def _find_symbol_lib_file(library: str, extra_paths: Optional[List[str]] = None) -> Optional[Path]:
    """Find a .kicad_sym file for the given library name."""
    filename = f"{library}.kicad_sym"
    search = list(extra_paths or []) + _SYMBOL_LIB_SEARCH_PATHS
    for base in search:
        p = Path(base) / filename
        if p.exists():
            return p
    return None


def _collect_pins(sym_def) -> List:
    """
    Recursively collect pin definitions from a kiutils Symbol object.

    Pins live inside sub-symbols (units).  We deduplicate by pin number so that
    DeMorgan alternates (styleId=2) do not produce duplicate entries.
    """
    pins_by_number: dict = {}

    def _walk(sym):
        for pin in (getattr(sym, "pins", None) or []):
            if pin.number not in pins_by_number:
                pins_by_number[pin.number] = pin
        for unit in (getattr(sym, "units", None) or []):
            _walk(unit)

    _walk(sym_def)
    return list(pins_by_number.values())


class SchematicEditor:
    """
    Stateless structured editor for KiCAD schematic files using kiutils.

    Every public method follows the pattern:
      1. Load schematic from disk
      2. Modify the in-memory object model
      3. Save back to disk
      4. Return a result dict with at least {"success": bool}

    This keeps the file always in sync with the changes made.
    """

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load(path: str) -> Schematic:
        """Load schematic, normalizing KiCAD 8+ ``(hide yes)`` → kiutils bare ``hide``.

        kiutils (<=1.4.8) uses a bare ``hide`` token inside effects blocks.
        KiCAD 8+ writes ``(hide yes)`` instead.  If we feed kiutils a file with
        ``(hide yes)`` it silently ignores the token, causing every previously-
        hidden property to appear visible after the next save.  We normalize the
        format before parsing so kiutils sees what it expects.
        """
        _p = Path(path)
        text = _p.read_text(encoding="utf-8")
        if "(hide yes)" not in text:
            return Schematic.from_file(str(path))

        import tempfile
        import os as _os

        normalized = text.replace("(hide yes)", "hide")
        fd, tmp = tempfile.mkstemp(suffix=".kicad_sch")
        try:
            _os.write(fd, normalized.encode("utf-8"))
            _os.close(fd)
            return Schematic.from_file(tmp)
        finally:
            try:
                _os.unlink(tmp)
            except Exception:
                pass

    @staticmethod
    def _save(sch: Schematic, path: str) -> None:
        sch.to_file(str(path))
        # kiutils (<=1.4.8) writes bare `hide` token inside effects blocks, but
        # KiCAD 8+ requires `(hide yes)`.  Fix in-place after serialisation.
        _p = Path(path)
        text = _p.read_text(encoding="utf-8")
        fixed = re.sub(r'(\(effects\b[^\n]*?) hide\)', r'\1 (hide yes))', text)
        if fixed != text:
            _p.write_text(fixed, encoding="utf-8")

    @staticmethod
    def _find_symbol(sch: Schematic, reference: str) -> Optional[SchematicSymbol]:
        """Return the first placed symbol whose Reference property matches."""
        for sym in sch.schematicSymbols:
            for prop in sym.properties:
                if prop.key == "Reference" and prop.value == reference:
                    return sym
        return None

    @staticmethod
    def _get_project_name(sch_path: str, sch: Schematic) -> str:
        """Derive the project name for instance blocks.

        Priority:
        1. Name from an existing symbol's instances block (most reliable).
        2. Stem of the nearest .kicad_pro file.
        3. Stem of the schematic file itself.
        """
        for sym in sch.schematicSymbols:
            for inst in sym.instances:
                if inst.name:
                    return inst.name
        p = Path(sch_path)
        for d in [p.parent, p.parent.parent]:
            pros = list(d.glob("*.kicad_pro"))
            if pros:
                return pros[0].stem
        return p.stem

    @staticmethod
    def _build_instance_block(sch: Schematic, sch_path: str, reference: str, unit: int = 1) -> SymbolProjectInstance:
        """Create a SymbolProjectInstance for a newly placed symbol."""
        proj_name = SchematicEditor._get_project_name(sch_path, sch)
        sheet_path = sch.sheetInstances[0].instancePath if sch.sheetInstances else "/"
        sym_path = SymbolProjectPath()
        sym_path.sheetInstancePath = sheet_path
        sym_path.reference = reference
        sym_path.unit = unit
        proj_inst = SymbolProjectInstance()
        proj_inst.name = proj_name
        proj_inst.paths = [sym_path]
        return proj_inst

    @staticmethod
    def _make_property(key: str, value: str, prop_id: int,
                       x: float, y: float, hidden: bool = False) -> Property:
        p = Property()
        p.key = key
        p.value = value
        p.id = prop_id
        p.position = Position(X=x, Y=y, angle=0)  # angle required by kicad-cli parser
        if hidden:
            from kiutils.items.common import Effects, Font
            effects = Effects()
            effects.hide = True
            p.effects = effects
        return p

    @staticmethod
    def _resolve_extends(sym_def, sym_lib):
        """Return a fully self-contained copy of sym_def with any ``extends``
        clause resolved by inlining the parent's geometry.

        KiCAD does NOT support ``(extends ...)`` inside the ``lib_symbols``
        section of a schematic — it expects each embedded symbol to carry all
        its graphical data directly.  We inline the parent's units (renamed to
        the child's entry name) and copy relevant pin-display settings.
        """
        parent_name = getattr(sym_def, "extends", None)
        if not parent_name:
            return copy.deepcopy(sym_def)

        parent = next(
            (s for s in sym_lib.symbols if s.entryName == parent_name), None
        )
        if parent is None:
            return copy.deepcopy(sym_def)

        inlined = copy.deepcopy(sym_def)
        inlined.extends = None  # remove extends clause so KiCAD accepts it

        # Inherit pin-display settings from parent (child usually has none)
        for attr in ("pinNames", "hidePinNumbers", "pinNamesOffset", "pinNamesHide"):
            val = getattr(parent, attr, None)
            if val is not None and getattr(inlined, attr, None) is None:
                setattr(inlined, attr, copy.deepcopy(val))

        # Inline parent's units, renaming entryName to child's name so that
        # KiCAD generates correct sub-symbol names (e.g. "2N7002_0_1").
        for unit in getattr(parent, "units", []):
            unit_copy = copy.deepcopy(unit)
            unit_copy.entryName = inlined.entryName
            inlined.units.append(unit_copy)

        return inlined

    @staticmethod
    def _register_lib_symbol(sch: Schematic, sym_def, library: str, sym_lib) -> None:
        """Register sym_def into sch.libSymbols, fully inlining any ``extends``.

        Skips if already present and clean; replaces only if absent or
        corrupted (sub-unit has libraryNickname set, e.g. "Lib:Sym_0_1").
        """
        def _copy_to_lib(s, nick):
            existing = next(
                (x for x in sch.libSymbols
                 if x.entryName == s.entryName and x.libraryNickname == nick),
                None,
            )
            if existing is not None:
                # Keep if no corrupted sub-units (libraryNickname should be None on units)
                corrupted = any(
                    getattr(u, "libraryNickname", None) is not None
                    for u in getattr(existing, "units", [])
                )
                if not corrupted:
                    return  # already present and clean — do not overwrite
            # Remove stale/corrupted entry (if any) and add resolved copy
            sch.libSymbols[:] = [
                x for x in sch.libSymbols
                if not (x.entryName == s.entryName and x.libraryNickname == nick)
            ]
            sc = SchematicEditor._resolve_extends(s, sym_lib)
            sc.libraryNickname = nick
            sch.libSymbols.append(sc)

        _copy_to_lib(sym_def, library)

    @staticmethod
    def _components_from_sch(sch: Schematic) -> List[Dict]:
        result = []
        for sym in sch.schematicSymbols:
            props = {p.key: p.value for p in sym.properties}
            ref = props.get("Reference", "?")
            result.append({
                "reference": ref,
                "value": props.get("Value", ""),
                "footprint": props.get("Footprint", ""),
                "datasheet": props.get("Datasheet", ""),
                "lib_id": sym.libId,
                "x": sym.position.X,
                "y": sym.position.Y,
                "rotation": sym.position.angle or 0,
                "mirror": sym.mirror or "",
            })
        return result

    # ------------------------------------------------------------------
    # Create / Load
    # ------------------------------------------------------------------

    @staticmethod
    def create(path: str, title: str = "", overwrite: bool = True) -> Dict:
        """Create a new empty schematic file.

        If the file already exists its components are counted and reported in
        the response so the caller is never surprised by a silent overwrite.
        Pass overwrite=False to abort instead of overwriting.
        """
        try:
            # Warn if file exists so the caller knows it will be overwritten
            overwrite_warning = None
            if os.path.exists(path):
                try:
                    existing = SchematicEditor._load(path)
                    existing_count = len(existing.schematicSymbols)
                except Exception:
                    existing_count = None
                if not overwrite:
                    msg = (
                        f"File already exists: {path} "
                        f"({existing_count} components). "
                        "Pass overwrite=true to replace it."
                    )
                    logger.warning(msg)
                    return {"success": False, "message": msg}
                overwrite_warning = (
                    f"Overwrote existing file ({existing_count} components erased)."
                    if existing_count is not None
                    else "Overwrote existing file."
                )
                logger.warning(f"create: overwriting {path} — {overwrite_warning}")

            sch = Schematic.create_new()
            # Use the current KiCAD schematic format version
            sch.version = 20250114
            sch.uuid = str(uuid.uuid4())
            if title and hasattr(sch, "titleBlock") and sch.titleBlock:
                sch.titleBlock.title = title
            sch.to_file(str(path))
            logger.info(f"Created schematic: {path}")
            result: Dict = {"success": True, "file_path": str(path)}
            if overwrite_warning:
                result["warning"] = overwrite_warning
            return result
        except Exception as e:
            logger.error(f"Error creating schematic: {e}", exc_info=True)
            return {"success": False, "message": str(e)}

    @staticmethod
    def load(path: str) -> Dict:
        """Load a schematic and return a summary of its contents."""
        try:
            sch = SchematicEditor._load(path)
            components = SchematicEditor._components_from_sch(sch)
            wires = [item for item in sch.graphicalItems if getattr(item, "type", None) == "wire"]
            return {
                "success": True,
                "file_path": str(path),
                "version": sch.version,
                "component_count": len(components),
                "components": components,
                "wire_count": len(wires),
                "label_count": len(sch.labels),
                "global_label_count": len(sch.globalLabels),
                "junction_count": len(sch.junctions),
                "no_connect_count": len(sch.noConnects),
            }
        except Exception as e:
            logger.error(f"Error loading schematic: {e}", exc_info=True)
            return {"success": False, "message": str(e)}

    # ------------------------------------------------------------------
    # List components
    # ------------------------------------------------------------------

    @staticmethod
    def list_components(path: str) -> Dict:
        """Return all placed symbols with their key properties."""
        try:
            sch = SchematicEditor._load(path)
            return {
                "success": True,
                "components": SchematicEditor._components_from_sch(sch),
            }
        except Exception as e:
            logger.error(f"Error listing components: {e}", exc_info=True)
            return {"success": False, "message": str(e)}

    # ------------------------------------------------------------------
    # Add component
    # ------------------------------------------------------------------

    @staticmethod
    def add_component(
        path: str,
        library: str,
        symbol: str,
        reference: str,
        value: str,
        x: float,
        y: float,
        footprint: str = "",
        rotation: float = 0,
        mirror: str = "",
        datasheet: str = "",
        extra_properties: Optional[Dict[str, str]] = None,
        lib_file: Optional[str] = None,
        hide_reference: bool = False,
        hide_value: bool = False,
        dnp: bool = False,
    ) -> Dict:
        """
        Add a component from a KiCAD symbol library to the schematic.

        Args:
            path:             Path to the .kicad_sch file
            library:          Library name (e.g. "Device")
            symbol:           Symbol name within the library (e.g. "R")
            reference:        Reference designator (e.g. "R1")
            value:            Component value (e.g. "10k")
            x, y:             Position in millimetres
            footprint:        KiCAD footprint reference (e.g. "Resistor_SMD:R_0402")
            rotation:         Rotation angle in degrees (0, 90, 180, 270)
            mirror:           Mirror axis: "x", "y", or "" for none
            datasheet:        Datasheet URL or "~"
            extra_properties: Dict of additional property key/value pairs
            lib_file:         Override the library file path (skips auto-search)
            dnp:              Mark component as Do Not Place (default: False)
        """
        try:
            # 1. Locate the symbol definition
            lib_path = Path(lib_file) if lib_file else _find_symbol_lib_file(library)
            if lib_path is None:
                return {
                    "success": False,
                    "message": (
                        f"Symbol library '{library}' not found. "
                        f"Searched: {_SYMBOL_LIB_SEARCH_PATHS}"
                    ),
                }

            sym_lib = SymbolLib.from_file(str(lib_path))
            sym_def = next((s for s in sym_lib.symbols if s.entryName == symbol), None)
            if sym_def is None:
                available = [s.entryName for s in sym_lib.symbols]
                return {
                    "success": False,
                    "message": (
                        f"Symbol '{symbol}' not found in library '{library}'. "
                        f"Available (first 30): {available[:30]}"
                    ),
                }

            # 2. Load schematic and register lib symbol (if not already present)
            sch = SchematicEditor._load(path)
            lib_id = f"{library}:{symbol}"

            # Guard: reject duplicate reference designators
            for existing_sym in sch.schematicSymbols:
                existing_ref = SchematicEditor._get_ref(existing_sym)
                if existing_ref == reference:
                    return {
                        "success": False,
                        "message": (
                            f"Reference '{reference}' already exists in the schematic. "
                            "Use a different reference or call annotate_schematic with "
                            "onlyUnannotated=true after placing all components as 'X?'."
                        ),
                    }

            SchematicEditor._register_lib_symbol(sch, sym_def, library, sym_lib)

            # 3. Create placed symbol instance
            inst = SchematicSymbol()
            inst.libId = lib_id
            inst.position = Position(X=x, Y=y, angle=rotation)
            inst.unit = 1
            inst.inBom = not dnp
            inst.onBoard = True
            inst.dnp = dnp
            inst.mirror = mirror if mirror in ("x", "y") else None
            inst.uuid = str(uuid.uuid4())

            # 4. Build properties
            # Determine datasheet from symbol definition if not supplied
            if not datasheet:
                ds_prop = next(
                    (p for p in sym_def.properties if p.key == "Datasheet"), None
                )
                datasheet = ds_prop.value if ds_prop else "~"

            # Reference (visible by default)
            inst.properties.append(
                SchematicEditor._make_property("Reference", reference, 0, x + 1.27, y - 1.27, hidden=hide_reference)
            )
            # Value (visible by default)
            inst.properties.append(
                SchematicEditor._make_property("Value", value, 1, x + 1.27, y + 1.27, hidden=hide_value)
            )
            # Footprint (hidden by default)
            inst.properties.append(
                SchematicEditor._make_property("Footprint", footprint, 2, x, y + 2.54, hidden=True)
            )
            # Datasheet (hidden by default)
            inst.properties.append(
                SchematicEditor._make_property("Datasheet", datasheet, 3, x, y + 3.81, hidden=True)
            )

            # Extra / custom properties
            if extra_properties:
                for prop_id, (key, val) in enumerate(extra_properties.items(), start=4):
                    inst.properties.append(
                        SchematicEditor._make_property(
                            key, val, prop_id, x, y + 5.08 + (prop_id - 4) * 1.27, hidden=True
                        )
                    )

            # 5. Build instances block (required for KiCAD v7+ hierarchical ref resolution)
            inst.instances = [SchematicEditor._build_instance_block(sch, path, reference)]

            sch.schematicSymbols.append(inst)
            SchematicEditor._save(sch, path)

            # Collect components within 10 mm to help detect label / pin overlaps
            NEARBY_RADIUS_MM = 10.0
            nearby = []
            for s in sch.schematicSymbols:
                s_ref = SchematicEditor._get_ref(s)
                if s_ref == reference:
                    continue  # skip the symbol we just added
                sx, sy = s.position.X, s.position.Y
                dist = ((sx - x) ** 2 + (sy - y) ** 2) ** 0.5
                if dist <= NEARBY_RADIUS_MM:
                    nearby.append({
                        "reference": s_ref,
                        "lib_id": s.libId,
                        "x": round(sx, 3),
                        "y": round(sy, 3),
                        "distance_mm": round(dist, 2),
                    })
            nearby.sort(key=lambda c: c["distance_mm"])

            logger.info(f"Added {reference} ({lib_id}) at ({x}, {y})")
            result: Dict = {
                "success": True,
                "reference": reference,
                "lib_id": lib_id,
                "position": {"x": x, "y": y},
            }
            if nearby:
                result["nearby_components"] = nearby
                result["hint"] = (
                    f"{len(nearby)} component(s) within {NEARBY_RADIUS_MM} mm — "
                    "check for label or pin overlaps."
                )
            return result

        except Exception as e:
            logger.error(f"Error adding component: {e}", exc_info=True)
            return {"success": False, "message": str(e)}

    # ------------------------------------------------------------------
    # Edit component
    # ------------------------------------------------------------------

    @staticmethod
    def edit_component(
        path: str,
        reference: str,
        changes: Dict[str, Any],
        hide_properties: Optional[List[str]] = None,
        show_properties: Optional[List[str]] = None,
    ) -> Dict:
        """
        Update properties of an existing placed symbol.

        Recognised keys in `changes`:
          value, footprint, datasheet, reference (rename), x, y, rotation, mirror
          Any other key is treated as a custom KiCAD property.

        hide_properties: list of property keys to make hidden (e.g. ["Reference", "Value"])
        show_properties: list of property keys to make visible (e.g. ["Footprint"])
        """
        try:
            sch = SchematicEditor._load(path)
            sym = SchematicEditor._find_symbol(sch, reference)
            if sym is None:
                return {"success": False, "message": f"Component '{reference}' not found"}

            # Position / orientation
            if "x" in changes:
                sym.position.X = float(changes["x"])
            if "y" in changes:
                sym.position.Y = float(changes["y"])
            if "rotation" in changes:
                sym.position.angle = float(changes["rotation"])
            if "mirror" in changes:
                m = changes["mirror"]
                sym.mirror = m if m in ("x", "y") else None

            # DNP flag — direct symbol attribute, not a property
            if "dnp" in changes:
                sym.dnp = bool(changes["dnp"])
                if "inBom" not in changes:
                    sym.inBom = not bool(changes["dnp"])

            if "inBom" in changes:
                sym.inBom = bool(changes["inBom"])

            # Named property fields
            kicad_field_map = {
                "value":     "Value",
                "footprint": "Footprint",
                "datasheet": "Datasheet",
                "reference": "Reference",
            }
            prop_by_key = {p.key: p for p in sym.properties}
            skip_keys = set(kicad_field_map) | {"x", "y", "rotation", "mirror", "dnp", "inBom"}

            for param, kicad_key in kicad_field_map.items():
                if param in changes and kicad_key in prop_by_key:
                    prop_by_key[kicad_key].value = str(changes[param])

            # Keep instances block in sync when the reference designator changes
            if "reference" in changes:
                new_ref = str(changes["reference"])
                if sym.instances:
                    for proj_inst in sym.instances:
                        for sym_path in proj_inst.paths:
                            if sym_path.reference == reference:
                                sym_path.reference = new_ref
                else:
                    # Symbol was added without an instances block (legacy); create one now
                    sym.instances = [SchematicEditor._build_instance_block(sch, path, new_ref)]

            # Custom / arbitrary properties
            for key, val in changes.items():
                if key in skip_keys:
                    continue
                if key in prop_by_key:
                    prop_by_key[key].value = str(val)
                else:
                    new_prop = SchematicEditor._make_property(
                        key, str(val),
                        len(sym.properties),
                        sym.position.X, sym.position.Y + 5.08,
                        hidden=True,
                    )
                    sym.properties.append(new_prop)

            # Visibility toggles
            from kiutils.items.common import Effects
            prop_by_key = {p.key: p for p in sym.properties}  # refresh after possible append
            for key in (hide_properties or []):
                if key in prop_by_key:
                    p = prop_by_key[key]
                    if p.effects is None:
                        p.effects = Effects()
                    p.effects.hide = True
            for key in (show_properties or []):
                if key in prop_by_key:
                    p = prop_by_key[key]
                    if p.effects is not None:
                        p.effects.hide = False

            SchematicEditor._save(sch, path)
            logger.info(f"Edited component '{reference}': {list(changes.keys())}")
            return {
                "success": True,
                "reference": reference,
                "updated": list(changes.keys()),
                "dnp": sym.dnp,
            }

        except Exception as e:
            logger.error(f"Error editing component: {e}", exc_info=True)
            return {"success": False, "message": str(e)}

    # ------------------------------------------------------------------
    # Delete component
    # ------------------------------------------------------------------

    @staticmethod
    def delete_component(path: str, reference: str) -> Dict:
        """Remove a placed symbol from the schematic by reference designator."""
        try:
            sch = SchematicEditor._load(path)
            sym = SchematicEditor._find_symbol(sch, reference)
            if sym is None:
                return {"success": False, "message": f"Component '{reference}' not found"}

            sch.schematicSymbols.remove(sym)
            SchematicEditor._save(sch, path)
            logger.info(f"Deleted component '{reference}'")
            return {"success": True, "reference": reference}

        except Exception as e:
            logger.error(f"Error deleting component: {e}", exc_info=True)
            return {"success": False, "message": str(e)}

    # ------------------------------------------------------------------
    # Wire
    # ------------------------------------------------------------------

    @staticmethod
    def add_wire(path: str, points: List[List[float]]) -> Dict:
        """
        Add wire segment(s) to the schematic.

        `points` is a list of [x, y] waypoints.  Each consecutive pair
        becomes one segment, so [[0,0],[10,0],[10,10]] creates two
        segments: (0,0)→(10,0) and (10,0)→(10,10).
        """
        try:
            if len(points) < 2:
                return {"success": False, "message": "At least 2 points are required"}

            sch = SchematicEditor._load(path)
            for i in range(len(points) - 1):
                w = Connection()
                w.type = "wire"
                w.points = [
                    Position(X=float(points[i][0]),     Y=float(points[i][1])),
                    Position(X=float(points[i + 1][0]), Y=float(points[i + 1][1])),
                ]
                w.uuid = str(uuid.uuid4())
                sch.graphicalItems.append(w)

            SchematicEditor._save(sch, path)
            logger.info(f"Added {len(points) - 1} wire segment(s)")
            return {"success": True, "segments": len(points) - 1}

        except Exception as e:
            logger.error(f"Error adding wire: {e}", exc_info=True)
            return {"success": False, "message": str(e)}

    # ------------------------------------------------------------------
    # Net label
    # ------------------------------------------------------------------

    @staticmethod
    def add_net_label(
        path: str,
        net_name: str,
        x: float,
        y: float,
        angle: float = 0,
        global_label: bool = False,
    ) -> Dict:
        """
        Add a net label (local or global) to the schematic.

        Args:
            path:         Path to the .kicad_sch file
            net_name:     Net name string (e.g. "VCC", "GND", "SDA")
            x, y:         Position in mm — should coincide with a wire endpoint or pin
            angle:        Rotation (0, 90, 180, 270)
            global_label: If True, create a global label (visible across sheets)
        """
        try:
            sch = SchematicEditor._load(path)

            if global_label:
                lbl = GlobalLabel()
                lbl.text = net_name
                lbl.position = Position(X=x, Y=y, angle=angle)
                lbl.uuid = str(uuid.uuid4())
                sch.globalLabels.append(lbl)
            else:
                lbl = LocalLabel()
                lbl.text = net_name
                lbl.position = Position(X=x, Y=y, angle=angle)
                lbl.uuid = str(uuid.uuid4())
                sch.labels.append(lbl)

            SchematicEditor._save(sch, path)
            label_kind = "global" if global_label else "local"
            logger.info(f"Added {label_kind} label '{net_name}' at ({x}, {y})")
            return {
                "success": True,
                "net": net_name,
                "type": label_kind,
                "position": {"x": x, "y": y},
            }

        except Exception as e:
            logger.error(f"Error adding net label: {e}", exc_info=True)
            return {"success": False, "message": str(e)}

    # ------------------------------------------------------------------
    # Junction
    # ------------------------------------------------------------------

    @staticmethod
    def add_junction(path: str, x: float, y: float) -> Dict:
        """Add a junction dot where two wires cross and should be connected."""
        try:
            sch = SchematicEditor._load(path)
            jct = Junction()
            jct.position = Position(X=x, Y=y)
            jct.uuid = str(uuid.uuid4())
            sch.junctions.append(jct)
            SchematicEditor._save(sch, path)
            return {"success": True, "position": {"x": x, "y": y}}

        except Exception as e:
            logger.error(f"Error adding junction: {e}", exc_info=True)
            return {"success": False, "message": str(e)}

    # ------------------------------------------------------------------
    # No-connect
    # ------------------------------------------------------------------

    @staticmethod
    def add_no_connect(path: str, x: float, y: float) -> Dict:
        """Mark an unconnected pin with a no-connect flag (X marker)."""
        try:
            sch = SchematicEditor._load(path)
            nc = NoConnect()
            nc.position = Position(X=x, Y=y)
            nc.uuid = str(uuid.uuid4())
            sch.noConnects.append(nc)
            SchematicEditor._save(sch, path)
            return {"success": True, "position": {"x": x, "y": y}}

        except Exception as e:
            logger.error(f"Error adding no-connect: {e}", exc_info=True)
            return {"success": False, "message": str(e)}

    # ------------------------------------------------------------------
    # Pin locations
    # ------------------------------------------------------------------

    @staticmethod
    def get_pin_locations(path: str, reference: str) -> Dict:
        """
        Return the absolute schematic coordinates for every pin of a component.

        Applies the component's position, rotation, and mirror to transform
        pin coordinates from symbol space to schematic space.
        """
        try:
            sch = SchematicEditor._load(path)
            sym = SchematicEditor._find_symbol(sch, reference)
            if sym is None:
                return {"success": False, "message": f"Component '{reference}' not found"}

            # Locate the symbol definition in libSymbols
            lib_id = sym.libId  # e.g. "Device:R"
            if ":" in lib_id:
                lib_name, sym_name = lib_id.split(":", 1)
            else:
                lib_name, sym_name = "", lib_id

            sym_def = next(
                (
                    s for s in sch.libSymbols
                    if s.entryName == sym_name
                    and (not lib_name or s.libraryNickname == lib_name)
                ),
                None,
            )
            if sym_def is None:
                return {
                    "success": False,
                    "message": (
                        f"Symbol definition '{lib_id}' not found in schematic's lib_symbols. "
                        f"Available: {[s.entryName for s in sch.libSymbols]}"
                    ),
                }

            pins = _collect_pins(sym_def)
            if not pins:
                return {
                    "success": True,
                    "reference": reference,
                    "pins": [],
                    "note": "No pins found in symbol definition",
                }

            # Component transform
            cx, cy    = sym.position.X, sym.position.Y
            angle_deg = sym.position.angle or 0
            mirror    = sym.mirror  # "x", "y", or None

            def transform(px: float, py: float):
                # Mirror (in symbol space, before rotation)
                if mirror == "x":
                    py = -py
                elif mirror == "y":
                    px = -px
                # Rotate
                if angle_deg:
                    rad   = math.radians(angle_deg)
                    cos_a = math.cos(rad)
                    sin_a = math.sin(rad)
                    px, py = (px * cos_a - py * sin_a,
                              px * sin_a + py * cos_a)
                # Translate
                return round(cx + px, 4), round(cy + py, 4)

            result_pins = []
            for pin in pins:
                ax, ay = transform(pin.position.X, pin.position.Y)
                result_pins.append({
                    "number": pin.number,
                    "name":   pin.name,
                    "x":      ax,
                    "y":      ay,
                    "angle":  (pin.position.angle or 0),
                })

            return {"success": True, "reference": reference, "pins": result_pins}

        except Exception as e:
            logger.error(f"Error getting pin locations: {e}", exc_info=True)
            return {"success": False, "message": str(e)}

    # ------------------------------------------------------------------
    # Replace symbol (swap lib_id while preserving position & properties)
    # ------------------------------------------------------------------

    @staticmethod
    def replace_symbol(
        path: str,
        reference: str,
        new_library: str,
        new_symbol: str,
        lib_file: Optional[str] = None,
        extra_changes: Optional[Dict[str, Any]] = None,
        hide_reference: bool = False,
        hide_value: bool = False,
    ) -> Dict:
        """
        Swap the underlying KiCAD symbol for a placed component while
        preserving its position, rotation, mirror, and all existing properties
        (reference, value, footprint, custom fields).

        Use this to replace EasyEDA/imported symbols with standard KiCAD symbols
        (e.g. Device:R, Device:C, Transistor_FET:2N7002).

        Args:
            path:         Path to the .kicad_sch file
            reference:    Reference designator of the component to replace
            new_library:  Target library name (e.g. "Device", "Transistor_FET")
            new_symbol:   Target symbol name (e.g. "R", "C", "2N7002")
            lib_file:     Override library file path (skips auto-search)
            extra_changes: Optional dict of property overrides to apply at the
                           same time (same keys as edit_component)
        """
        try:
            # 1. Load schematic and find old symbol
            sch = SchematicEditor._load(path)
            old_sym = SchematicEditor._find_symbol(sch, reference)
            if old_sym is None:
                return {"success": False, "message": f"Component '{reference}' not found"}

            # 2. Locate new symbol definition in KiCAD library
            lib_path = Path(lib_file) if lib_file else _find_symbol_lib_file(new_library)
            if lib_path is None:
                return {
                    "success": False,
                    "message": f"Symbol library '{new_library}' not found. Searched: {_SYMBOL_LIB_SEARCH_PATHS}",
                }
            sym_lib = SymbolLib.from_file(str(lib_path))
            sym_def = next((s for s in sym_lib.symbols if s.entryName == new_symbol), None)
            if sym_def is None:
                available = [s.entryName for s in sym_lib.symbols]
                return {
                    "success": False,
                    "message": f"Symbol '{new_symbol}' not found in '{new_library}'. Available: {available[:30]}",
                }

            # 3. Harvest existing properties from the old symbol
            old_props = {p.key: p.value for p in old_sym.properties}

            # 4. Register new lib symbol definition (+ parent if extends)
            new_lib_id = f"{new_library}:{new_symbol}"
            SchematicEditor._register_lib_symbol(sch, sym_def, new_library, sym_lib)

            # 5. Build new symbol instance — preserve position/orientation
            new_inst = SchematicSymbol()
            new_inst.libId    = new_lib_id
            new_inst.position = Position(
                X=old_sym.position.X,
                Y=old_sym.position.Y,
                angle=old_sym.position.angle,
            )
            new_inst.unit    = 1
            new_inst.inBom   = True
            new_inst.onBoard = True
            new_inst.mirror  = old_sym.mirror
            new_inst.uuid    = str(uuid.uuid4())

            # 6. Rebuild properties — old values take priority, then extra_changes
            changes = dict(extra_changes or {})
            ref_val  = changes.pop("reference", old_props.get("Reference", reference))
            value    = changes.pop("value",     old_props.get("Value",     new_symbol))
            footprint = changes.pop("footprint", old_props.get("Footprint", ""))
            datasheet = changes.pop("datasheet", old_props.get("Datasheet", "~"))
            x_new = float(changes.pop("x", new_inst.position.X))
            y_new = float(changes.pop("y", new_inst.position.Y))
            rot   = float(changes.pop("rotation", new_inst.position.angle or 0))
            mir   = changes.pop("mirror", new_inst.mirror)

            new_inst.position = Position(X=x_new, Y=y_new, angle=rot)
            new_inst.mirror   = mir if mir in ("x", "y") else None

            new_inst.properties.append(
                SchematicEditor._make_property("Reference", ref_val, 0, x_new + 1.27, y_new - 1.27, hidden=hide_reference)
            )
            new_inst.properties.append(
                SchematicEditor._make_property("Value", value, 1, x_new + 1.27, y_new + 1.27, hidden=hide_value)
            )
            new_inst.properties.append(
                SchematicEditor._make_property("Footprint", footprint, 2, x_new, y_new + 2.54, hidden=True)
            )
            new_inst.properties.append(
                SchematicEditor._make_property("Datasheet", datasheet, 3, x_new, y_new + 3.81, hidden=True)
            )

            # Carry over all other custom properties from old symbol
            standard_keys = {"Reference", "Value", "Footprint", "Datasheet",
                             "ki_keywords", "ki_fp_filters", "Description"}
            prop_id = 4
            for key, val in old_props.items():
                if key in standard_keys:
                    continue
                new_inst.properties.append(
                    SchematicEditor._make_property(key, val, prop_id, x_new, y_new + 5.08 + (prop_id - 4) * 1.27, hidden=True)
                )
                prop_id += 1

            # Apply remaining extra_changes as new/overriding properties
            prop_map = {p.key: p for p in new_inst.properties}
            for key, val in changes.items():
                if key in prop_map:
                    prop_map[key].value = str(val)
                else:
                    new_inst.properties.append(
                        SchematicEditor._make_property(key, str(val), prop_id, x_new, y_new + 5.08 + (prop_id - 4) * 1.27, hidden=True)
                    )
                    prop_id += 1

            # 7. Swap in the new symbol
            idx = sch.schematicSymbols.index(old_sym)
            sch.schematicSymbols[idx] = new_inst

            SchematicEditor._save(sch, path)
            logger.info(f"Replaced '{reference}' symbol: {old_sym.libId} → {new_lib_id}")
            return {
                "success": True,
                "reference": ref_val,
                "old_lib_id": old_sym.libId,
                "new_lib_id": new_lib_id,
            }

        except Exception as e:
            logger.error(f"Error replacing symbol: {e}", exc_info=True)
            return {"success": False, "message": str(e)}

    # ------------------------------------------------------------------
    # Search available symbols
    # ------------------------------------------------------------------

    @staticmethod
    def search_library_symbols(library: str, query: str = "") -> Dict:
        """
        List symbols available in a KiCAD symbol library.

        Args:
            library: Library name (e.g. "Device", "Connector")
            query:   Optional filter string (case-insensitive substring match)
        """
        try:
            lib_path = _find_symbol_lib_file(library)
            if lib_path is None:
                return {
                    "success": False,
                    "message": (
                        f"Library '{library}' not found. "
                        f"Searched: {_SYMBOL_LIB_SEARCH_PATHS}"
                    ),
                }
            sym_lib = SymbolLib.from_file(str(lib_path))
            symbols = [s.entryName for s in sym_lib.symbols]
            if query:
                q = query.lower()
                symbols = [s for s in symbols if q in s.lower()]
            return {"success": True, "library": library, "symbols": symbols, "count": len(symbols)}

        except Exception as e:
            logger.error(f"Error searching library symbols: {e}", exc_info=True)
            return {"success": False, "message": str(e)}

    # ------------------------------------------------------------------
    # Annotation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _ref_prefix(ref: str) -> str:
        """Extract the alphabetic prefix from a reference designator.

        'R1' → 'R', 'U12' → 'U', 'C?' → 'C', '#PWR01' → '#PWR'
        """
        return re.sub(r'[\d?]+$', '', ref)

    @staticmethod
    def _is_power_sym(sym: SchematicSymbol) -> bool:
        """Return True for power/flag symbols that must never be re-annotated."""
        if sym.libId.startswith("power:"):
            return True
        for p in sym.properties:
            if p.key == "Reference" and p.value.startswith("#"):
                return True
        return False

    @staticmethod
    def _get_ref(sym: SchematicSymbol) -> str:
        for p in sym.properties:
            if p.key == "Reference":
                return p.value
        return ""

    @staticmethod
    def _set_ref(sym: SchematicSymbol, sch: "Schematic", sch_path: str, new_ref: str) -> None:
        """Update the Reference property and the instances block in one shot."""
        old_ref = SchematicEditor._get_ref(sym)
        for p in sym.properties:
            if p.key == "Reference":
                p.value = new_ref
                break
        if sym.instances:
            for proj_inst in sym.instances:
                for sym_path in proj_inst.paths:
                    if sym_path.reference == old_ref:
                        sym_path.reference = new_ref
        else:
            sym.instances = [SchematicEditor._build_instance_block(sch, sch_path, new_ref, sym.unit)]

    # ------------------------------------------------------------------
    # annotate_components
    # ------------------------------------------------------------------

    @staticmethod
    def annotate_components(
        path: str,
        sort_by_position: bool = True,
        skip_prefixes: Optional[List[str]] = None,
        start_number: int = 1,
        only_unannotated: bool = False,
        existing_schematic_paths: Optional[List[str]] = None,
    ) -> Dict:
        """Re-annotate schematic components with sequential reference designators.

        Algorithm
        ---------
        1. Skip power/flag symbols (libId starts with 'power:' or ref starts with '#').
        2. For a *full* re-annotation (only_unannotated=False), group symbols by their
           current reference so that all units of the same physical multi-unit component
           receive the same new number.
        3. For *partial* annotation (only_unannotated=True), only process symbols whose
           reference ends with '?'.  Unannotated multi-unit companions (unit > 1, same
           libId, same '?' ref) are matched to the nearest unit-1 symbol via Euclidean
           distance.
        4. Sort each prefix group by (X, Y) position when sort_by_position is True
           (left-to-right, top-to-bottom, matching KiCAD's default behaviour).
        5. Assign consecutive integers, skipping numbers already used by symbols that
           are not being re-annotated (relevant when only_unannotated=True).
        6. If existing_schematic_paths is provided, the reference numbers already used
           in those sheets are pre-loaded into the "taken" set so that the annotated
           sheet never produces duplicates across a multi-sheet project.
        """
        try:
            sch = SchematicEditor._load(path)
            skip = set(skip_prefixes or [])

            # Pre-populate taken numbers from other sheets (multi-sheet dedup)
            cross_sheet_used: Dict[str, set] = {}
            for other_path in (existing_schematic_paths or []):
                if os.path.abspath(other_path) == os.path.abspath(path):
                    continue  # skip self
                try:
                    other_sch = SchematicEditor._load(other_path)
                    for s in other_sch.schematicSymbols:
                        if SchematicEditor._is_power_sym(s):
                            continue
                        ref = SchematicEditor._get_ref(s)
                        if '?' in ref or not re.search(r'\d', ref):
                            continue
                        prefix = SchematicEditor._ref_prefix(ref)
                        m = re.search(r'\d+', ref)
                        if m:
                            cross_sheet_used.setdefault(prefix, set()).add(int(m.group()))
                except Exception as e:
                    logger.warning(f"annotate_components: could not read {other_path}: {e}")

            all_syms = [s for s in sch.schematicSymbols if not SchematicEditor._is_power_sym(s)]

            if skip:
                all_syms = [s for s in all_syms
                            if SchematicEditor._ref_prefix(SchematicEditor._get_ref(s)) not in skip]

            def is_unannotated(sym):
                ref = SchematicEditor._get_ref(sym)
                return '?' in ref or not re.search(r'\d', ref)

            if only_unannotated:
                to_process = [s for s in all_syms if is_unannotated(s)]
                to_keep    = [s for s in all_syms if not is_unannotated(s)]
            else:
                to_process = all_syms
                to_keep    = []

            # Numbers already in use (from to_keep + other sheets) — avoid collisions
            used_numbers: Dict[str, set] = {}
            # Seed from other sheets first so they are never overwritten
            for prefix, nums in cross_sheet_used.items():
                used_numbers.setdefault(prefix, set()).update(nums)
            for sym in to_keep:
                ref = SchematicEditor._get_ref(sym)
                prefix = SchematicEditor._ref_prefix(ref)
                m = re.search(r'\d+', ref)
                if m:
                    used_numbers.setdefault(prefix, set()).add(int(m.group()))

            # Build groups: each group = one physical component (list of SchematicSymbol)
            # key = uuid of the unit-1 representative
            groups: List[List[SchematicSymbol]] = []

            if only_unannotated:
                # Unannotated: every unit-1 symbol starts a new group.
                # Match unit>1 symbols to the nearest unit-1 of the same libId.
                unit1 = [s for s in to_process if s.unit == 1]
                unitN = [s for s in to_process if s.unit > 1]

                def _dist(a: SchematicSymbol, b: SchematicSymbol) -> float:
                    return ((a.position.X - b.position.X) ** 2 +
                            (a.position.Y - b.position.Y) ** 2) ** 0.5

                group_map: Dict[str, List[SchematicSymbol]] = {s.uuid: [s] for s in unit1}
                remaining = list(unitN)
                for companion in sorted(remaining,
                                        key=lambda s: min((_dist(s, u) for u in unit1),
                                                          default=0)):
                    candidates = [u for u in unit1 if u.libId == companion.libId]
                    if candidates:
                        nearest = min(candidates, key=lambda u: _dist(companion, u))
                        group_map[nearest.uuid].append(companion)
                    else:
                        # No matching unit-1 — treat as standalone group
                        group_map[companion.uuid] = [companion]

                groups = list(group_map.values())
            else:
                # Full re-annotation: group by current reference (multi-unit share the same ref)
                by_ref: Dict[str, List[SchematicSymbol]] = {}
                for sym in to_process:
                    ref = SchematicEditor._get_ref(sym)
                    by_ref.setdefault(ref, []).append(sym)
                groups = list(by_ref.values())

            # Sort groups: use the unit-1 symbol's position as the sort key
            def _primary(group: List[SchematicSymbol]) -> SchematicSymbol:
                return next((s for s in group if s.unit == 1), group[0])

            # Bucket groups by prefix
            prefix_buckets: Dict[str, List[List[SchematicSymbol]]] = {}
            for group in groups:
                ref = SchematicEditor._get_ref(_primary(group))
                prefix = SchematicEditor._ref_prefix(ref)
                prefix_buckets.setdefault(prefix, []).append(group)

            if sort_by_position:
                for prefix, bucket in prefix_buckets.items():
                    bucket.sort(key=lambda g: (_primary(g).position.X, _primary(g).position.Y))

            # Assign new references
            renames = 0
            mapping: Dict[str, str] = {}
            for prefix, bucket in prefix_buckets.items():
                taken = used_numbers.get(prefix, set())
                counter = start_number
                for group in bucket:
                    while counter in taken:
                        counter += 1
                    new_ref = f"{prefix}{counter}"
                    taken.add(counter)
                    counter += 1

                    for sym in group:
                        old_ref = SchematicEditor._get_ref(sym)
                        if old_ref != new_ref:
                            mapping[old_ref] = new_ref
                            SchematicEditor._set_ref(sym, sch, path, new_ref)
                            renames += 1

            SchematicEditor._save(sch, path)
            logger.info(f"annotate_components: renamed {renames} symbols in {path}")
            return {
                "success": True,
                "renamed": renames,
                "mapping": mapping,
            }

        except Exception as e:
            logger.error(f"Error annotating components: {e}", exc_info=True)
            return {"success": False, "message": str(e)}

    # ------------------------------------------------------------------
    # clear_annotation
    # ------------------------------------------------------------------

    @staticmethod
    def clear_annotation(
        path: str,
        prefixes: Optional[List[str]] = None,
    ) -> Dict:
        """Reset reference designators back to the 'X?' form.

        Args:
            path:     Path to the .kicad_sch file.
            prefixes: If given, only clear references whose prefix is in this list
                      (e.g. ['R', 'C'] clears resistors and capacitors only).
                      If omitted, all non-power symbols are cleared.
        """
        try:
            sch = SchematicEditor._load(path)
            filter_prefixes = set(prefixes) if prefixes else None
            cleared = 0

            for sym in sch.schematicSymbols:
                if SchematicEditor._is_power_sym(sym):
                    continue
                old_ref = SchematicEditor._get_ref(sym)
                prefix  = SchematicEditor._ref_prefix(old_ref)
                if filter_prefixes and prefix not in filter_prefixes:
                    continue
                new_ref = f"{prefix}?"
                if old_ref == new_ref:
                    continue
                SchematicEditor._set_ref(sym, sch, path, new_ref)
                cleared += 1

            SchematicEditor._save(sch, path)
            logger.info(f"clear_annotation: cleared {cleared} symbols in {path}")
            return {"success": True, "cleared": cleared}

        except Exception as e:
            logger.error(f"Error clearing annotation: {e}", exc_info=True)
            return {"success": False, "message": str(e)}
