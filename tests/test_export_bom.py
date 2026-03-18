"""
Tests for ExportCommands.export_bom and _load_schematic_lcsc_map.
pcbnew is mocked via conftest.py.
"""
import csv
import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from commands.export import ExportCommands


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_footprint(ref: str, value: str, footprint: str = "Device:R_0402", layer: str = "F.Cu"):
    """Build a mock pcbnew footprint."""
    fp = MagicMock()
    fp.GetReference.return_value = ref
    fp.GetValue.return_value = value
    fp.GetFPID.return_value.GetUniStringLibId.return_value = footprint
    fp.GetLayer.return_value = 0
    return fp


def _make_board(footprints: list, board_file: str = "") -> MagicMock:
    """Build a mock pcbnew BOARD."""
    board = MagicMock()
    board.GetFootprints.return_value = footprints
    board.GetLayerName.return_value = "F.Cu"
    board.GetFileName.return_value = board_file
    return board


class _SymbolProperty:
    """Minimal kicad-skip property mock supporting 'in' and [] access."""

    def __init__(self, fields: dict):
        # kicad-skip normalizes field names: spaces → underscores.
        # Store both original and normalized forms so tests can use either.
        self._fields = {}
        for k, v in fields.items():
            mock = MagicMock(value=v)
            self._fields[k] = mock
            normalized = k.replace(" ", "_")
            if normalized != k:
                self._fields[normalized] = mock
            setattr(self, normalized, mock)
        if "Reference" in self._fields:
            self.Reference = self._fields["Reference"]
        if "Value" in self._fields:
            self.Value = self._fields["Value"]

    def __contains__(self, key):
        return key in self._fields

    def __getitem__(self, key):
        return self._fields[key]


def _make_symbol(ref: str, fields: dict) -> MagicMock:
    """Build a mock kicad-skip symbol."""
    sym = MagicMock()
    sym.property = _SymbolProperty({"Reference": ref, **fields})
    return sym


def _make_schematic(symbols: list) -> MagicMock:
    sch = MagicMock()
    sch.symbol = symbols
    return sch


# ---------------------------------------------------------------------------
# _load_schematic_lcsc_map
# ---------------------------------------------------------------------------

class TestLoadSchematicLcscMap:

    def test_no_board_filename_returns_empty(self):
        ec = ExportCommands(_make_board([], board_file=""))
        assert ec._load_schematic_lcsc_map() == {}

    def test_no_kicad_sch_files_returns_empty(self, tmp_path):
        board_file = str(tmp_path / "project.kicad_pcb")
        ec = ExportCommands(_make_board([], board_file=board_file))
        assert ec._load_schematic_lcsc_map() == {}

    def test_reads_lcsc_part_field(self, tmp_path):
        (tmp_path / "project.kicad_sch").write_text("")  # file must exist
        board_file = str(tmp_path / "project.kicad_pcb")
        ec = ExportCommands(_make_board([], board_file=board_file))

        sym = _make_symbol("U1", {"LCSC Part": "C81193"})
        sch = _make_schematic([sym])

        # Schematic is imported inside the method → patch via sys.modules
        with patch.dict("sys.modules", {"skip": MagicMock(Schematic=lambda f: sch)}):
            result = ec._load_schematic_lcsc_map()

        assert result.get("U1") == "C81193"

    def test_fallback_field_order(self, tmp_path):
        """LCSC Part > LCSC > lcsc > Supplier Part"""
        (tmp_path / "project.kicad_sch").write_text("")
        board_file = str(tmp_path / "project.kicad_pcb")
        ec = ExportCommands(_make_board([], board_file=board_file))

        # Only "Supplier Part" available
        sym = _make_symbol("R1", {"Supplier Part": "C99999"})
        sch = _make_schematic([sym])

        with patch.dict("sys.modules", {"skip": MagicMock(Schematic=lambda f: sch)}):
            result = ec._load_schematic_lcsc_map()

        assert result.get("R1") == "C99999"

    def test_lcsc_part_wins_over_supplier_part(self, tmp_path):
        (tmp_path / "project.kicad_sch").write_text("")
        board_file = str(tmp_path / "project.kicad_pcb")
        ec = ExportCommands(_make_board([], board_file=board_file))

        sym = _make_symbol("C1", {"LCSC Part": "C11111", "Supplier Part": "C99999"})
        sch = _make_schematic([sym])

        with patch.dict("sys.modules", {"skip": MagicMock(Schematic=lambda f: sch)}):
            result = ec._load_schematic_lcsc_map()

        assert result.get("C1") == "C11111"

    def test_tilde_value_ignored(self, tmp_path):
        """KiCAD uses "~" as empty placeholder."""
        (tmp_path / "project.kicad_sch").write_text("")
        board_file = str(tmp_path / "project.kicad_pcb")
        ec = ExportCommands(_make_board([], board_file=board_file))

        sym = _make_symbol("D1", {"LCSC Part": "~"})
        sch = _make_schematic([sym])

        with patch.dict("sys.modules", {"skip": MagicMock(Schematic=lambda f: sch)}):
            result = ec._load_schematic_lcsc_map()

        assert "D1" not in result

    def test_reads_lcsc_part_underscore(self, tmp_path):
        """kicad-skip normalizes 'LCSC Part' → 'LCSC_Part' in the property dict."""
        (tmp_path / "project.kicad_sch").write_text("")
        board_file = str(tmp_path / "project.kicad_pcb")
        ec = ExportCommands(_make_board([], board_file=board_file))

        # Simulate kicad-skip's normalized form
        sym = _make_symbol("U5", {"LCSC_Part": "C81193"})
        sch = _make_schematic([sym])

        with patch.dict("sys.modules", {"skip": MagicMock(Schematic=lambda f: sch)}):
            result = ec._load_schematic_lcsc_map()

        assert result.get("U5") == "C81193"

    def test_symbol_without_lcsc_skipped(self, tmp_path):
        (tmp_path / "project.kicad_sch").write_text("")
        board_file = str(tmp_path / "project.kicad_pcb")
        ec = ExportCommands(_make_board([], board_file=board_file))

        sym = _make_symbol("R2", {"Value": "100R"})  # no LCSC field
        sch = _make_schematic([sym])

        with patch.dict("sys.modules", {"skip": MagicMock(Schematic=lambda f: sch)}):
            result = ec._load_schematic_lcsc_map()

        assert result == {}

    def test_multiple_schematics(self, tmp_path):
        (tmp_path / "top.kicad_sch").write_text("")
        (tmp_path / "sub.kicad_sch").write_text("")
        board_file = str(tmp_path / "project.kicad_pcb")
        ec = ExportCommands(_make_board([], board_file=board_file))

        sch1 = _make_schematic([_make_symbol("U1", {"LCSC Part": "C111"})])
        sch2 = _make_schematic([_make_symbol("U2", {"LCSC Part": "C222"})])
        schematics = iter([sch1, sch2])

        with patch.dict("sys.modules", {"skip": MagicMock(Schematic=lambda f: next(schematics))}):
            result = ec._load_schematic_lcsc_map()

        assert result == {"U1": "C111", "U2": "C222"}


# ---------------------------------------------------------------------------
# export_bom — format & structure
# ---------------------------------------------------------------------------

class TestExportBomFormats:

    def _make_ec_with_lcsc(self, tmp_path, footprints, lcsc_map):
        """ExportCommands with a patched _load_schematic_lcsc_map."""
        board = _make_board(footprints, board_file=str(tmp_path / "p.kicad_pcb"))
        ec = ExportCommands(board)
        ec._load_schematic_lcsc_map = lambda: lcsc_map
        return ec

    def test_no_board_returns_error(self):
        ec = ExportCommands(None)
        result = ec.export_bom({"outputPath": "/tmp/bom.csv"})
        assert result["success"] is False
        assert "No board" in result["message"]

    def test_missing_output_path_returns_error(self, tmp_path):
        board = _make_board([_make_footprint("R1", "10k")], str(tmp_path / "p.kicad_pcb"))
        ec = ExportCommands(board)
        ec._load_schematic_lcsc_map = lambda: {}
        result = ec.export_bom({})
        assert result["success"] is False
        assert "output path" in result["message"].lower()

    def test_unsupported_format_returns_error(self, tmp_path):
        ec = self._make_ec_with_lcsc(tmp_path, [_make_footprint("R1", "10k")], {})
        result = ec.export_bom({"outputPath": str(tmp_path / "bom.xyz"), "format": "xyz"})
        assert result["success"] is False
        assert "Unsupported" in result["message"]

    def test_format_case_insensitive(self, tmp_path):
        ec = self._make_ec_with_lcsc(tmp_path, [_make_footprint("R1", "10k")], {})
        result = ec.export_bom({"outputPath": str(tmp_path / "bom.csv"), "format": "csv"})
        assert result["success"] is True

    def test_csv_contains_lcsc_column(self, tmp_path):
        fp = _make_footprint("U1", "CAT24C32WI-GT3")
        ec = self._make_ec_with_lcsc(tmp_path, [fp], {"U1": "C81193"})
        out = str(tmp_path / "bom.csv")
        result = ec.export_bom({"outputPath": out, "format": "CSV", "groupByValue": False})

        assert result["success"] is True
        with open(out) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert rows[0]["lcsc"] == "C81193"
        assert rows[0]["reference"] == "U1"

    def test_csv_empty_lcsc_when_not_in_schematic(self, tmp_path):
        fp = _make_footprint("R1", "10k")
        ec = self._make_ec_with_lcsc(tmp_path, [fp], {})
        out = str(tmp_path / "bom.csv")
        ec.export_bom({"outputPath": out, "format": "CSV", "groupByValue": False})

        with open(out) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert rows[0]["lcsc"] == ""

    def test_json_format(self, tmp_path):
        fp = _make_footprint("C1", "100nF")
        ec = self._make_ec_with_lcsc(tmp_path, [fp], {"C1": "C14663"})
        out = str(tmp_path / "bom.json")
        result = ec.export_bom({"outputPath": out, "format": "JSON", "groupByValue": False})

        assert result["success"] is True
        with open(out) as f:
            data = json.load(f)
        assert data["components"][0]["lcsc"] == "C14663"

    def test_html_format(self, tmp_path):
        fp = _make_footprint("R1", "10k")
        ec = self._make_ec_with_lcsc(tmp_path, [fp], {"R1": "C25105"})
        out = str(tmp_path / "bom.html")
        result = ec.export_bom({"outputPath": out, "format": "HTML", "groupByValue": False})

        assert result["success"] is True
        content = open(out).read()
        assert "C25105" in content
        assert "<th>lcsc</th>" in content

    def test_xml_format(self, tmp_path):
        fp = _make_footprint("R1", "10k")
        ec = self._make_ec_with_lcsc(tmp_path, [fp], {"R1": "C25105"})
        out = str(tmp_path / "bom.xml")
        result = ec.export_bom({"outputPath": out, "format": "XML", "groupByValue": False})

        assert result["success"] is True
        content = open(out).read()
        assert "C25105" in content
        assert "<lcsc>" in content


# ---------------------------------------------------------------------------
# export_bom — groupByValue
# ---------------------------------------------------------------------------

class TestExportBomGrouping:

    def _ec(self, tmp_path, footprints, lcsc_map):
        board = _make_board(footprints, str(tmp_path / "p.kicad_pcb"))
        ec = ExportCommands(board)
        ec._load_schematic_lcsc_map = lambda: lcsc_map
        return ec

    def test_group_by_value_merges_same_value(self, tmp_path):
        fps = [
            _make_footprint("R1", "10k"),
            _make_footprint("R2", "10k"),
        ]
        ec = self._ec(tmp_path, fps, {"R1": "C25105", "R2": "C25105"})
        out = str(tmp_path / "bom.json")
        ec.export_bom({"outputPath": out, "format": "JSON", "groupByValue": True})

        with open(out) as f:
            data = json.load(f)
        assert len(data["components"]) == 1
        assert data["components"][0]["quantity"] == 2
        assert set(data["components"][0]["references"]) == {"R1", "R2"}

    def test_group_by_value_separates_different_lcsc(self, tmp_path):
        """Same value/footprint but different LCSC → two groups."""
        fps = [
            _make_footprint("R1", "10k"),
            _make_footprint("R2", "10k"),
        ]
        ec = self._ec(tmp_path, fps, {"R1": "C11111", "R2": "C22222"})
        out = str(tmp_path / "bom.json")
        ec.export_bom({"outputPath": out, "format": "JSON", "groupByValue": True})

        with open(out) as f:
            data = json.load(f)
        assert len(data["components"]) == 2

    def test_no_grouping_one_row_per_component(self, tmp_path):
        fps = [_make_footprint("R1", "10k"), _make_footprint("R2", "10k")]
        ec = self._ec(tmp_path, fps, {})
        out = str(tmp_path / "bom.csv")
        result = ec.export_bom({"outputPath": out, "format": "CSV", "groupByValue": False})

        assert result["file"]["componentCount"] == 2
        with open(out) as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 2

    def test_grouped_component_count_in_result(self, tmp_path):
        fps = [_make_footprint(f"R{i}", "10k") for i in range(4)]
        ec = self._ec(tmp_path, fps, {f"R{i}": "C25105" for i in range(4)})
        out = str(tmp_path / "bom.json")
        result = ec.export_bom({"outputPath": out, "format": "JSON", "groupByValue": True})

        assert result["file"]["componentCount"] == 1
