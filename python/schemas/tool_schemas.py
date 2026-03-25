"""
Comprehensive tool schema definitions for all KiCAD MCP commands

Following MCP 2025-06-18 specification for tool definitions.
Each tool includes:
- name: Unique identifier
- title: Human-readable display name
- description: Detailed explanation of what the tool does
- inputSchema: JSON Schema for parameters
- outputSchema: Optional JSON Schema for return values (structured content)
"""

from typing import Dict, Any

# =============================================================================
# PROJECT TOOLS
# =============================================================================

PROJECT_TOOLS = [
    {
        "name": "create_project",
        "title": "Create New KiCAD Project",
        "description": "Creates a new KiCAD project with PCB board file and optional project configuration. Automatically creates project directory and initializes board with default settings.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectName": {
                    "type": "string",
                    "description": "Name of the project (used for file naming)",
                    "minLength": 1
                },
                "path": {
                    "type": "string",
                    "description": "Directory path where project will be created (defaults to current working directory)"
                },
                "template": {
                    "type": "string",
                    "description": "Optional path to template board file to copy settings from"
                }
            },
            "required": ["projectName"]
        }
    },
    {
        "name": "open_project",
        "title": "Open Existing KiCAD Project",
        "description": "Opens an existing KiCAD project file (.kicad_pro or .kicad_pcb) and loads the board into memory for manipulation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Path to .kicad_pro or .kicad_pcb file"
                }
            },
            "required": ["filename"]
        }
    },
    {
        "name": "save_project",
        "title": "Save Current Project",
        "description": "Saves the current board to disk. Can optionally save to a new location.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Optional new path to save the board (if not provided, saves to current location)"
                }
            }
        }
    },
    {
        "name": "snapshot_project",
        "title": "Snapshot Project (Checkpoint)",
        "description": "Copies the entire project folder to a new timestamped snapshot directory so you can resume from this checkpoint later without redoing earlier steps. Call this after every successfully completed design step (e.g. after Step 1 schematic, after Step 2 PCB layout) before asking for user confirmation to proceed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "step": {
                    "type": "string",
                    "description": "Step number or name to include in snapshot folder name, e.g. '1' or '2'"
                },
                "label": {
                    "type": "string",
                    "description": "Optional short label, e.g. 'schematic_ok' or 'layout_ok'"
                },
                "projectPath": {
                    "type": "string",
                    "description": "Project directory path. Auto-detected from loaded board if omitted."
                }
            }
        }
    },
    {
        "name": "get_project_info",
        "title": "Get Project Information",
        "description": "Retrieves metadata and properties of the currently open project including name, paths, and board status.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]

# =============================================================================
# BOARD TOOLS
# =============================================================================

BOARD_TOOLS = [
    {
        "name": "set_board_size",
        "title": "Set Board Dimensions",
        "description": "Sets the PCB board dimensions. The board outline must be added separately using add_board_outline.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "width": {
                    "type": "number",
                    "description": "Board width in millimeters",
                    "minimum": 1
                },
                "height": {
                    "type": "number",
                    "description": "Board height in millimeters",
                    "minimum": 1
                }
            },
            "required": ["width", "height"]
        }
    },
    {
        "name": "add_board_outline",
        "title": "Add Board Outline",
        "description": "Adds a board outline shape (rectangle, rounded_rectangle, circle, or polygon) on the Edge.Cuts layer. By default the board top-left corner is placed at (0, 0) so all coordinates are positive. Use x/y to set a different top-left corner position.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "shape": {
                    "type": "string",
                    "enum": ["rectangle", "rounded_rectangle", "circle", "polygon"],
                    "description": "Shape type for the board outline"
                },
                "width": {
                    "type": "number",
                    "description": "Width in mm (for rectangle/rounded_rectangle)",
                    "minimum": 1
                },
                "height": {
                    "type": "number",
                    "description": "Height in mm (for rectangle/rounded_rectangle)",
                    "minimum": 1
                },
                "x": {
                    "type": "number",
                    "description": "X coordinate of the top-left corner in mm (default: 0). Board extends from x to x+width."
                },
                "y": {
                    "type": "number",
                    "description": "Y coordinate of the top-left corner in mm (default: 0). Board extends from y to y+height."
                },
                "radius": {
                    "type": "number",
                    "description": "Corner radius in mm for rounded_rectangle, or radius for circle",
                    "minimum": 0
                },
                "points": {
                    "type": "array",
                    "description": "Array of {x, y} point objects in mm (for polygon shape only)",
                    "items": {
                        "type": "object",
                        "properties": {"x": {"type": "number"}, "y": {"type": "number"}},
                        "required": ["x", "y"]
                    },
                    "minItems": 3
                }
            },
            "required": ["shape"]
        }
    },
    {
        "name": "add_layer",
        "title": "Add Custom Layer",
        "description": "Adds a new custom layer to the board stack (e.g., User.1, User.Comments).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "layerName": {
                    "type": "string",
                    "description": "Name of the layer to add"
                },
                "layerType": {
                    "type": "string",
                    "enum": ["signal", "power", "mixed", "jumper"],
                    "description": "Type of layer (for copper layers)"
                }
            },
            "required": ["layerName"]
        }
    },
    {
        "name": "set_active_layer",
        "title": "Set Active Layer",
        "description": "Sets the currently active layer for drawing operations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "layerName": {
                    "type": "string",
                    "description": "Name of the layer to make active (e.g., F.Cu, B.Cu, Edge.Cuts)"
                }
            },
            "required": ["layerName"]
        }
    },
    {
        "name": "get_layer_list",
        "title": "List Board Layers",
        "description": "Returns a list of all layers in the board with their properties.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_board_info",
        "title": "Get Board Information",
        "description": "Retrieves comprehensive board information including dimensions, layer count, component count, and design rules.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_board_2d_view",
        "title": "Render Board Preview",
        "description": "Generates a 2D visual representation of the current board state as a PNG image.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "width": {
                    "type": "number",
                    "description": "Image width in pixels (default: 800)",
                    "minimum": 100,
                    "default": 800
                },
                "height": {
                    "type": "number",
                    "description": "Image height in pixels (default: 600)",
                    "minimum": 100,
                    "default": 600
                }
            }
        }
    },
    {
        "name": "get_board_extents",
        "title": "Get Board Bounding Box",
        "description": "Returns the bounding box extents of the PCB board including all edge cuts, components, and traces.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "unit": {
                    "type": "string",
                    "enum": ["mm", "inch"],
                    "description": "Unit for returned coordinates (default: mm)",
                    "default": "mm"
                }
            }
        }
    },
    {
        "name": "add_mounting_hole",
        "title": "Add Mounting Hole",
        "description": "Adds a mounting hole (non-plated through hole) at the specified position with given diameter.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "x": {
                    "type": "number",
                    "description": "X coordinate in millimeters"
                },
                "y": {
                    "type": "number",
                    "description": "Y coordinate in millimeters"
                },
                "diameter": {
                    "type": "number",
                    "description": "Hole diameter in millimeters",
                    "minimum": 0.1
                }
            },
            "required": ["x", "y", "diameter"]
        }
    },
    {
        "name": "import_svg_logo",
        "title": "Import SVG Logo to PCB",
        "description": "Imports an SVG file as filled graphic polygons onto a KiCAD PCB layer (default F.SilkS). Curves are linearised automatically. Supports path, rect, circle, ellipse, polygon and group transforms.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "pcbPath": {
                    "type": "string",
                    "description": "Path to the .kicad_pcb file"
                },
                "svgPath": {
                    "type": "string",
                    "description": "Path to the SVG logo file"
                },
                "x": {
                    "type": "number",
                    "description": "X position of the logo top-left corner in mm"
                },
                "y": {
                    "type": "number",
                    "description": "Y position of the logo top-left corner in mm"
                },
                "width": {
                    "type": "number",
                    "description": "Target width of the logo in mm (height scaled to preserve aspect ratio)",
                    "minimum": 0.1
                },
                "layer": {
                    "type": "string",
                    "description": "PCB layer name, e.g. F.SilkS or B.SilkS (default: F.SilkS)",
                    "default": "F.SilkS"
                },
                "strokeWidth": {
                    "type": "number",
                    "description": "Outline stroke width in mm (0 = no outline, default 0)",
                    "default": 0
                },
                "filled": {
                    "type": "boolean",
                    "description": "Fill polygons with solid layer colour (default true)",
                    "default": True
                }
            },
            "required": ["pcbPath", "svgPath", "x", "y", "width"]
        }
    },
    {
        "name": "add_board_text",
        "title": "Add Text to Board",
        "description": "Adds text annotation to the board on a specified layer (e.g., F.SilkS for top silkscreen).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Text content to add",
                    "minLength": 1
                },
                "x": {
                    "type": "number",
                    "description": "X coordinate in millimeters"
                },
                "y": {
                    "type": "number",
                    "description": "Y coordinate in millimeters"
                },
                "layer": {
                    "type": "string",
                    "description": "Layer name (e.g., F.SilkS, B.SilkS, F.Cu)",
                    "default": "F.SilkS"
                },
                "size": {
                    "type": "number",
                    "description": "Text size in millimeters",
                    "minimum": 0.1,
                    "default": 1.0
                },
                "thickness": {
                    "type": "number",
                    "description": "Text thickness in millimeters",
                    "minimum": 0.01,
                    "default": 0.15
                }
            },
            "required": ["text", "x", "y"]
        }
    }
]

# =============================================================================
# COMPONENT TOOLS
# =============================================================================

COMPONENT_TOOLS = [
    {
        "name": "place_component",
        "title": "Place Component",
        "description": "Places a component with specified footprint at given coordinates on the board.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "reference": {
                    "type": "string",
                    "description": "Component reference designator (e.g., R1, C2, U3)"
                },
                "footprint": {
                    "type": "string",
                    "description": "Footprint library:name (e.g., Resistor_SMD:R_0805_2012Metric)"
                },
                "x": {
                    "type": "number",
                    "description": "X coordinate in millimeters"
                },
                "y": {
                    "type": "number",
                    "description": "Y coordinate in millimeters"
                },
                "rotation": {
                    "type": "number",
                    "description": "Rotation angle in degrees (0-360)",
                    "minimum": 0,
                    "maximum": 360,
                    "default": 0
                },
                "layer": {
                    "type": "string",
                    "enum": ["F.Cu", "B.Cu"],
                    "description": "Board layer (top or bottom)",
                    "default": "F.Cu"
                }
            },
            "required": ["reference", "footprint", "x", "y"]
        }
    },
    {
        "name": "move_component",
        "title": "Move Component",
        "description": "Moves an existing component to a new position on the board.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "reference": {
                    "type": "string",
                    "description": "Component reference designator"
                },
                "x": {
                    "type": "number",
                    "description": "New X coordinate in millimeters"
                },
                "y": {
                    "type": "number",
                    "description": "New Y coordinate in millimeters"
                }
            },
            "required": ["reference", "x", "y"]
        }
    },
    {
        "name": "rotate_component",
        "title": "Rotate Component",
        "description": "Rotates a component by specified angle. Rotation is cumulative with existing rotation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "reference": {
                    "type": "string",
                    "description": "Component reference designator"
                },
                "angle": {
                    "type": "number",
                    "description": "Rotation angle in degrees (positive = counterclockwise)"
                }
            },
            "required": ["reference", "angle"]
        }
    },
    {
        "name": "delete_component",
        "title": "Delete Component",
        "description": "Removes a component from the board by reference designator or UUID. Use 'uuid' to target a specific duplicate when multiple footprints share the same reference.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "reference": {
                    "type": "string",
                    "description": "Component reference designator (e.g. R1, U3). Required if uuid is not provided."
                },
                "uuid": {
                    "type": "string",
                    "description": "Footprint UUID (e.g. e1c7fd3a-b5c6-400a-a8e5-6d3e8528e5f4). Use this to delete a specific duplicate without affecting other footprints with the same reference."
                }
            }
        }
    },
    {
        "name": "edit_component",
        "title": "Edit Component Properties",
        "description": "Modifies properties of an existing PCB component (value, footprint, DNP flag, etc.).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "reference": {
                    "type": "string",
                    "description": "Component reference designator"
                },
                "value": {
                    "type": "string",
                    "description": "New component value"
                },
                "footprint": {
                    "type": "string",
                    "description": "New footprint library:name"
                },
                "dnp": {
                    "type": "boolean",
                    "description": "Mark component as Do Not Place (true) or clear the DNP flag (false)"
                }
            },
            "required": ["reference"]
        }
    },
    {
        "name": "get_component_properties",
        "title": "Get Component Properties",
        "description": "Retrieves detailed properties of a specific component.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "reference": {
                    "type": "string",
                    "description": "Component reference designator"
                }
            },
            "required": ["reference"]
        }
    },
    {
        "name": "get_component_list",
        "title": "List All Components",
        "description": "Returns a list of all components on the board with their properties.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "find_component",
        "title": "Find Components",
        "description": "Searches for components matching specified criteria. Supports partial matching on reference, value, or footprint patterns.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "reference": {
                    "type": "string",
                    "description": "Reference designator pattern to match (e.g., 'R1', 'U', 'C2')"
                },
                "value": {
                    "type": "string",
                    "description": "Value pattern to match (e.g., '10k', '100nF')"
                },
                "footprint": {
                    "type": "string",
                    "description": "Footprint pattern to match (e.g., '0805', 'SOIC')"
                }
            }
        }
    },
    {
        "name": "get_component_pads",
        "title": "Get Component Pads",
        "description": "Returns all pads for a component with their positions, net connections, sizes, and shapes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "reference": {
                    "type": "string",
                    "description": "Component reference designator (e.g., U1, R5)"
                }
            },
            "required": ["reference"]
        }
    },
    {
        "name": "get_pad_position",
        "title": "Get Pad Position",
        "description": "Returns the position and properties of a specific pad on a component.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "reference": {
                    "type": "string",
                    "description": "Component reference designator"
                },
                "padName": {
                    "type": "string",
                    "description": "Pad name or number (e.g., '1', '2', 'A1')"
                },
                "padNumber": {
                    "type": "string",
                    "description": "Alternative to padName - pad number"
                }
            },
            "required": ["reference"]
        }
    },
    {
        "name": "place_component_array",
        "title": "Place Component Array",
        "description": "Places multiple copies of a component in a grid or circular pattern.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "referencePrefix": {
                    "type": "string",
                    "description": "Reference prefix (e.g., 'R' for R1, R2, R3...)"
                },
                "startNumber": {
                    "type": "integer",
                    "description": "Starting number for references",
                    "minimum": 1,
                    "default": 1
                },
                "footprint": {
                    "type": "string",
                    "description": "Footprint library:name"
                },
                "pattern": {
                    "type": "string",
                    "enum": ["grid", "circular"],
                    "description": "Array pattern type"
                },
                "count": {
                    "type": "integer",
                    "description": "Total number of components to place",
                    "minimum": 1
                },
                "startX": {
                    "type": "number",
                    "description": "Starting X coordinate in millimeters"
                },
                "startY": {
                    "type": "number",
                    "description": "Starting Y coordinate in millimeters"
                },
                "spacingX": {
                    "type": "number",
                    "description": "Horizontal spacing in mm (for grid pattern)"
                },
                "spacingY": {
                    "type": "number",
                    "description": "Vertical spacing in mm (for grid pattern)"
                },
                "radius": {
                    "type": "number",
                    "description": "Circle radius in mm (for circular pattern)"
                },
                "rows": {
                    "type": "integer",
                    "description": "Number of rows (for grid pattern)",
                    "minimum": 1
                },
                "columns": {
                    "type": "integer",
                    "description": "Number of columns (for grid pattern)",
                    "minimum": 1
                }
            },
            "required": ["referencePrefix", "footprint", "pattern", "count", "startX", "startY"]
        }
    },
    {
        "name": "align_components",
        "title": "Align Components",
        "description": "Aligns multiple components horizontally or vertically.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "references": {
                    "type": "array",
                    "description": "Array of component reference designators to align",
                    "items": {"type": "string"},
                    "minItems": 2
                },
                "direction": {
                    "type": "string",
                    "enum": ["horizontal", "vertical"],
                    "description": "Alignment direction"
                },
                "spacing": {
                    "type": "number",
                    "description": "Spacing between components in mm (optional, for even distribution)"
                }
            },
            "required": ["references", "direction"]
        }
    },
    {
        "name": "duplicate_component",
        "title": "Duplicate Component",
        "description": "Creates a copy of an existing component with new reference designator.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sourceReference": {
                    "type": "string",
                    "description": "Reference of component to duplicate"
                },
                "newReference": {
                    "type": "string",
                    "description": "Reference designator for the new component"
                },
                "offsetX": {
                    "type": "number",
                    "description": "X offset from original position in mm",
                    "default": 0
                },
                "offsetY": {
                    "type": "number",
                    "description": "Y offset from original position in mm",
                    "default": 0
                }
            },
            "required": ["sourceReference", "newReference"]
        }
    }
]

# =============================================================================
# ROUTING TOOLS
# =============================================================================

ROUTING_TOOLS = [
    {
        "name": "add_net",
        "title": "Create Electrical Net",
        "description": "Creates a new electrical net for signal routing.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "netName": {
                    "type": "string",
                    "description": "Name of the net (e.g., VCC, GND, SDA)",
                    "minLength": 1
                },
                "netClass": {
                    "type": "string",
                    "description": "Optional net class to assign (must exist first)"
                }
            },
            "required": ["netName"]
        }
    },
    {
        "name": "route_trace",
        "title": "Route PCB Trace",
        "description": "Routes a copper trace between two points or pads on a specified layer.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "netName": {
                    "type": "string",
                    "description": "Net name for this trace"
                },
                "layer": {
                    "type": "string",
                    "description": "Layer to route on (e.g., F.Cu, B.Cu)",
                    "default": "F.Cu"
                },
                "width": {
                    "type": "number",
                    "description": "Trace width in millimeters",
                    "minimum": 0.1
                },
                "points": {
                    "type": "array",
                    "description": "Array of [x, y] waypoints in millimeters",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 2,
                        "maxItems": 2
                    },
                    "minItems": 2
                }
            },
            "required": ["points", "width"]
        }
    },
    {
        "name": "add_via",
        "title": "Add Via",
        "description": "Adds a via (plated through-hole) to connect traces between layers.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "x": {
                    "type": "number",
                    "description": "X coordinate in millimeters"
                },
                "y": {
                    "type": "number",
                    "description": "Y coordinate in millimeters"
                },
                "diameter": {
                    "type": "number",
                    "description": "Via diameter in millimeters",
                    "minimum": 0.1
                },
                "drill": {
                    "type": "number",
                    "description": "Drill diameter in millimeters",
                    "minimum": 0.1
                },
                "netName": {
                    "type": "string",
                    "description": "Net name to assign to this via"
                }
            },
            "required": ["x", "y", "diameter", "drill"]
        }
    },
    {
        "name": "delete_trace",
        "title": "Delete Trace",
        "description": "Removes traces from the board. Can delete by UUID, position, or bulk-delete all traces on a net.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "uuid": {
                    "type": "string",
                    "description": "UUID of a specific trace to delete"
                },
                "position": {
                    "type": "object",
                    "description": "Delete trace nearest to this position",
                    "properties": {
                        "x": {"type": "number", "description": "X coordinate"},
                        "y": {"type": "number", "description": "Y coordinate"},
                        "unit": {"type": "string", "enum": ["mm", "inch"], "default": "mm"}
                    },
                    "required": ["x", "y"]
                },
                "net": {
                    "type": "string",
                    "description": "Delete all traces on this net (bulk delete)"
                },
                "layer": {
                    "type": "string",
                    "description": "Filter by layer when using net-based deletion"
                },
                "includeVias": {
                    "type": "boolean",
                    "description": "Include vias in net-based deletion",
                    "default": False
                }
            }
        }
    },
    {
        "name": "query_traces",
        "title": "Query Traces",
        "description": "Queries traces on the board with optional filters by net, layer, or bounding box. Returns trace details including UUID, positions, width, and length.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "net": {
                    "type": "string",
                    "description": "Filter by net name (e.g., 'GND', 'VCC')"
                },
                "layer": {
                    "type": "string",
                    "description": "Filter by layer name (e.g., 'F.Cu', 'B.Cu')"
                },
                "boundingBox": {
                    "type": "object",
                    "description": "Filter by bounding box region",
                    "properties": {
                        "x1": {"type": "number", "description": "Left X coordinate"},
                        "y1": {"type": "number", "description": "Top Y coordinate"},
                        "x2": {"type": "number", "description": "Right X coordinate"},
                        "y2": {"type": "number", "description": "Bottom Y coordinate"},
                        "unit": {"type": "string", "enum": ["mm", "inch"], "default": "mm"}
                    }
                },
                "includeVias": {
                    "type": "boolean",
                    "description": "Include vias in the result",
                    "default": False
                }
            }
        }
    },
    {
        "name": "modify_trace",
        "title": "Modify Trace",
        "description": "Modifies properties of an existing trace. Find trace by UUID or position, then change width, layer, or net assignment.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "uuid": {
                    "type": "string",
                    "description": "UUID of the trace to modify"
                },
                "position": {
                    "type": "object",
                    "description": "Find trace nearest to this position",
                    "properties": {
                        "x": {"type": "number", "description": "X coordinate"},
                        "y": {"type": "number", "description": "Y coordinate"},
                        "unit": {"type": "string", "enum": ["mm", "inch"], "default": "mm"}
                    },
                    "required": ["x", "y"]
                },
                "width": {
                    "type": "number",
                    "description": "New trace width in mm"
                },
                "layer": {
                    "type": "string",
                    "description": "New layer name (e.g., 'F.Cu', 'B.Cu')"
                },
                "net": {
                    "type": "string",
                    "description": "New net name to assign"
                }
            }
        }
    },
    {
        "name": "copy_routing_pattern",
        "title": "Copy Routing Pattern",
        "description": "Copies routing pattern from source components to target components. Enables routing replication between identical component groups by calculating and applying position offset.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sourceRefs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Source component references (e.g., ['U1', 'U2', 'U3'])"
                },
                "targetRefs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Target component references (e.g., ['U4', 'U5', 'U6'])"
                },
                "includeVias": {
                    "type": "boolean",
                    "description": "Include vias in the pattern copy",
                    "default": True
                },
                "traceWidth": {
                    "type": "number",
                    "description": "Override trace width in mm (uses original if not specified)"
                }
            },
            "required": ["sourceRefs", "targetRefs"]
        }
    },
    {
        "name": "get_nets_list",
        "title": "List All Nets",
        "description": "Returns a list of all electrical nets defined on the board.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "create_netclass",
        "title": "Create Net Class",
        "description": "Defines a net class with specific routing rules (trace width, clearance, etc.).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Net class name",
                    "minLength": 1
                },
                "trackWidth": {
                    "type": "number",
                    "description": "Default track/trace width in millimeters",
                    "minimum": 0.1
                },
                "clearance": {
                    "type": "number",
                    "description": "Clearance in millimeters",
                    "minimum": 0.1
                },
                "viaDiameter": {
                    "type": "number",
                    "description": "Via diameter in millimeters"
                },
                "viaDrill": {
                    "type": "number",
                    "description": "Via drill diameter in millimeters"
                }
            },
            "required": ["name", "trackWidth", "clearance"]
        }
    },
    {
        "name": "assign_net_to_class",
        "title": "Assign Net to Net Class",
        "description": "Assigns one or more existing nets to a net class. The net class must already exist (use create_netclass first).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "nets": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of net names to assign (e.g. [\"+3V3\", \"GND\", \"/PWR/VBUS\"])",
                    "minItems": 1
                },
                "netClass": {
                    "type": "string",
                    "description": "Name of the target net class (must exist)"
                }
            },
            "required": ["nets", "netClass"]
        }
    },
    {
        "name": "add_copper_pour",
        "title": "Add Copper Pour",
        "description": "Creates a copper pour/zone (typically for ground or power planes).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "netName": {
                    "type": "string",
                    "description": "Net to connect this copper pour to (e.g., GND, VCC)"
                },
                "layer": {
                    "type": "string",
                    "description": "Layer for the copper pour (e.g., F.Cu, B.Cu)"
                },
                "priority": {
                    "type": "integer",
                    "description": "Pour priority (higher priorities fill first)",
                    "minimum": 0,
                    "default": 0
                },
                "clearance": {
                    "type": "number",
                    "description": "Clearance from other objects in millimeters",
                    "minimum": 0.1
                },
                "outline": {
                    "type": "array",
                    "description": "Array of [x, y] points defining the pour boundary",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 2,
                        "maxItems": 2
                    },
                    "minItems": 3
                }
            },
            "required": ["netName", "layer", "outline"]
        }
    },
    {
        "name": "route_differential_pair",
        "title": "Route Differential Pair",
        "description": "Routes a differential signal pair with matched lengths and spacing.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "positiveName": {
                    "type": "string",
                    "description": "Positive signal net name"
                },
                "negativeName": {
                    "type": "string",
                    "description": "Negative signal net name"
                },
                "layer": {
                    "type": "string",
                    "description": "Layer to route on"
                },
                "width": {
                    "type": "number",
                    "description": "Trace width in millimeters"
                },
                "gap": {
                    "type": "number",
                    "description": "Gap between traces in millimeters"
                },
                "points": {
                    "type": "array",
                    "description": "Waypoints for the pair routing",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 2,
                        "maxItems": 2
                    },
                    "minItems": 2
                }
            },
            "required": ["positiveName", "negativeName", "width", "gap", "points"]
        }
    }
]

# =============================================================================
# LIBRARY TOOLS
# =============================================================================

LIBRARY_TOOLS = [
    {
        "name": "list_libraries",
        "title": "List Footprint Libraries",
        "description": "Lists all available footprint libraries accessible to KiCAD.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "search_footprints",
        "title": "Search Footprints",
        "description": "Searches for footprints matching a query string across all libraries.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (e.g., '0805', 'SOIC', 'QFP')",
                    "minLength": 1
                },
                "library": {
                    "type": "string",
                    "description": "Optional library to restrict search to"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "list_library_footprints",
        "title": "List Footprints in Library",
        "description": "Lists all footprints available in a specific library.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "library": {
                    "type": "string",
                    "description": "Library name (e.g., Resistor_SMD, Connector_PinHeader)",
                    "minLength": 1
                }
            },
            "required": ["library"]
        }
    },
    # ------------------------------------------------------------------
    # Symbol library tools (schematic components)
    # ------------------------------------------------------------------
    {
        "name": "list_symbol_libraries",
        "title": "List Symbol Libraries",
        "description": "Lists all KiCAD symbol libraries registered in the global sym-lib-table (and optionally a project sym-lib-table).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectPath": {
                    "type": "string",
                    "description": "Optional project directory path to also load its sym-lib-table"
                }
            }
        }
    },
    {
        "name": "search_symbols",
        "title": "Search Symbols",
        "description": "Searches for KiCAD schematic symbols by name, description, LCSC ID, manufacturer, or MPN across all registered libraries.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (e.g. 'ESP32', 'C25768', 'resistor', 'MOSFET')",
                    "minLength": 1
                },
                "library": {
                    "type": "string",
                    "description": "Optional library name to restrict the search (e.g. 'Device')"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 20)",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 200
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "list_library_symbols",
        "title": "List Symbols in Library (by nickname)",
        "description": "Lists all symbols available in a specific KiCAD symbol library, looked up by its sym-lib-table nickname.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "library": {
                    "type": "string",
                    "description": "Library nickname as registered in sym-lib-table (e.g. 'Device', 'Connector_Generic')",
                    "minLength": 1
                }
            },
            "required": ["library"]
        }
    },
    {
        "name": "list_symbols_in_library",
        "title": "List Symbols in Library (by name or path)",
        "description": "Lists all symbols in a .kicad_sym library file. Accepts either a library name (auto-resolved from KiCAD symbol directories) or a full file path.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "library": {
                    "type": "string",
                    "description": "Library name to auto-resolve (e.g. 'Device', 'Transistor_FET'). Use this instead of libraryPath when possible."
                },
                "libraryPath": {
                    "type": "string",
                    "description": "Full path to the .kicad_sym file. Use library name instead when possible."
                }
            }
        }
    },
    {
        "name": "get_symbol_info",
        "title": "Get Symbol Details",
        "description": "Retrieves detailed metadata for a specific symbol: description, footprint, datasheet, LCSC ID, MPN, and more.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Symbol specification as 'Library:SymbolName' (e.g. 'Device:R') or just 'SymbolName' to search all libraries",
                    "minLength": 1
                }
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "get_footprint_info",
        "title": "Get Footprint Details",
        "description": "Retrieves detailed information about a specific footprint including pad layout, dimensions, and description.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "library": {
                    "type": "string",
                    "description": "Library name"
                },
                "footprint": {
                    "type": "string",
                    "description": "Footprint name"
                }
            },
            "required": ["library", "footprint"]
        }
    }
]

# =============================================================================
# DESIGN RULE TOOLS
# =============================================================================

DESIGN_RULE_TOOLS = [
    {
        "name": "set_design_rules",
        "title": "Set Design Rules",
        "description": "Configures board design rules including clearances, trace widths, and via sizes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "clearance": {
                    "type": "number",
                    "description": "Minimum clearance between copper in millimeters",
                    "minimum": 0.1
                },
                "trackWidth": {
                    "type": "number",
                    "description": "Minimum track width in millimeters",
                    "minimum": 0.1
                },
                "viaDiameter": {
                    "type": "number",
                    "description": "Minimum via diameter in millimeters"
                },
                "viaDrill": {
                    "type": "number",
                    "description": "Minimum via drill diameter in millimeters"
                },
                "microViaDiameter": {
                    "type": "number",
                    "description": "Minimum micro-via diameter in millimeters"
                }
            }
        }
    },
    {
        "name": "get_design_rules",
        "title": "Get Current Design Rules",
        "description": "Retrieves the currently configured design rules from the board.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "run_drc",
        "title": "Run Design Rule Check",
        "description": "Executes a design rule check (DRC) on the current board and reports violations.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "includeWarnings": {
                    "type": "boolean",
                    "description": "Include warnings in addition to errors",
                    "default": True
                }
            }
        }
    },
    {
        "name": "get_drc_violations",
        "title": "Get DRC Violations",
        "description": "Returns a list of design rule violations from the most recent DRC run.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
]

# =============================================================================
# EXPORT TOOLS
# =============================================================================

EXPORT_TOOLS = [
    {
        "name": "export_gerber",
        "title": "Export Gerber Files",
        "description": "Generates Gerber files for PCB fabrication (industry standard format).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "outputPath": {
                    "type": "string",
                    "description": "Directory path for output files"
                },
                "layers": {
                    "type": "array",
                    "description": "List of layers to export (if not provided, exports all copper and mask layers)",
                    "items": {"type": "string"}
                },
                "includeDrillFiles": {
                    "type": "boolean",
                    "description": "Include drill files (Excellon format)",
                    "default": True
                }
            },
            "required": ["outputPath"]
        }
    },
    {
        "name": "export_pdf",
        "title": "Export PDF",
        "description": "Exports the board layout as a PDF document for documentation or review.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "outputPath": {
                    "type": "string",
                    "description": "Path for output PDF file"
                },
                "layers": {
                    "type": "array",
                    "description": "Layers to include in PDF",
                    "items": {"type": "string"}
                },
                "colorMode": {
                    "type": "string",
                    "enum": ["color", "black_white"],
                    "description": "Color mode for output",
                    "default": "color"
                }
            },
            "required": ["outputPath"]
        }
    },
    {
        "name": "export_svg",
        "title": "Export SVG",
        "description": "Exports the board as Scalable Vector Graphics for documentation or web display.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "outputPath": {
                    "type": "string",
                    "description": "Path for output SVG file"
                },
                "layers": {
                    "type": "array",
                    "description": "Layers to include in SVG",
                    "items": {"type": "string"}
                }
            },
            "required": ["outputPath"]
        }
    },
    {
        "name": "export_3d",
        "title": "Export 3D Model",
        "description": "Exports a 3D model of the board in STEP or VRML format for mechanical CAD integration.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "outputPath": {
                    "type": "string",
                    "description": "Path for output 3D file"
                },
                "format": {
                    "type": "string",
                    "enum": ["step", "vrml"],
                    "description": "3D model format",
                    "default": "step"
                },
                "includeComponents": {
                    "type": "boolean",
                    "description": "Include 3D component models",
                    "default": True
                }
            },
            "required": ["outputPath"]
        }
    },
    {
        "name": "export_bom",
        "title": "Export Bill of Materials",
        "description": "Generates a bill of materials (BOM) listing all components with references, values, and footprints.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "outputPath": {
                    "type": "string",
                    "description": "Path for output BOM file"
                },
                "format": {
                    "type": "string",
                    "enum": ["csv", "xml", "html"],
                    "description": "BOM output format",
                    "default": "csv"
                },
                "groupByValue": {
                    "type": "boolean",
                    "description": "Group components with same value together",
                    "default": True
                }
            },
            "required": ["outputPath"]
        }
    }
]

# =============================================================================
# SCHEMATIC TOOLS
# =============================================================================

SCHEMATIC_TOOLS = [
    # ------------------------------------------------------------------
    # File management
    # ------------------------------------------------------------------
    {
        "name": "create_schematic",
        "title": "Create New Schematic",
        "description": (
            "Creates a new empty KiCAD schematic file (.kicad_sch). "
            "If the file already exists the response includes a 'warning' field "
            "with the number of components that were erased. "
            "Pass overwrite=false to abort instead of silently overwriting."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Full path for the new schematic file, e.g. /path/to/project/my_board.kicad_sch"
                },
                "title": {
                    "type": "string",
                    "description": "Optional schematic title shown in the title block"
                },
                "overwrite": {
                    "type": "boolean",
                    "description": "Allow overwriting an existing file (default: true). Set to false to abort if the file exists.",
                    "default": True
                }
            },
            "required": ["filename"]
        }
    },
    {
        "name": "load_schematic",
        "title": "Load Schematic",
        "description": "Opens an existing KiCAD schematic file and returns a summary: component list, wire count, label count.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Path to the .kicad_sch file"
                }
            },
            "required": ["filename"]
        }
    },
    # ------------------------------------------------------------------
    # Component CRUD
    # ------------------------------------------------------------------
    {
        "name": "list_schematic_components",
        "title": "List Schematic Components",
        "description": "Returns all placed symbols in a schematic with their reference, value, footprint, position, and lib_id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "schematicPath": {
                    "type": "string",
                    "description": "Path to the .kicad_sch file"
                }
            },
            "required": ["schematicPath"]
        }
    },
    {
        "name": "add_schematic_component",
        "title": "Add Component to Schematic",
        "description": (
            "Places a symbol from a KiCAD symbol library onto the schematic. "
            "The symbol definition is read directly from the installed KiCAD library — "
            "no template system needed. "
            "Use get_schematic_pin_locations afterwards to find exact pin coordinates for wiring."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "schematicPath": {
                    "type": "string",
                    "description": "Path to the .kicad_sch file"
                },
                "library": {
                    "type": "string",
                    "description": "KiCAD symbol library name (e.g. 'Device', 'Connector_Generic', 'MCU_ST_STM32F4')"
                },
                "symbol": {
                    "type": "string",
                    "description": "Symbol name within the library (e.g. 'R', 'C', 'Conn_01x04')"
                },
                "reference": {
                    "type": "string",
                    "description": "Reference designator (e.g. 'R1', 'C3', 'U1')"
                },
                "value": {
                    "type": "string",
                    "description": "Component value shown on schematic (e.g. '10k', '100nF', 'STM32F401')"
                },
                "x": {
                    "type": "number",
                    "description": "X position in millimetres on the schematic sheet"
                },
                "y": {
                    "type": "number",
                    "description": "Y position in millimetres on the schematic sheet"
                },
                "footprint": {
                    "type": "string",
                    "description": "KiCAD footprint reference (e.g. 'Resistor_SMD:R_0402'). Can be set later with edit_schematic_component."
                },
                "rotation": {
                    "type": "number",
                    "description": "Rotation in degrees (0, 90, 180, 270). Default: 0",
                    "default": 0
                },
                "mirror": {
                    "type": "string",
                    "enum": ["", "x", "y"],
                    "description": "Mirror the symbol: 'x' = flip vertically, 'y' = flip horizontally, '' = none",
                    "default": ""
                },
                "datasheet": {
                    "type": "string",
                    "description": "Datasheet URL or '~'. Defaults to the value from the library symbol."
                },
                "properties": {
                    "type": "object",
                    "description": "Additional custom properties (e.g. {\"LCSC Part\": \"C25768\"}). All custom properties are hidden by default.",
                    "additionalProperties": {"type": "string"}
                },
                "hideReference": {
                    "type": "boolean",
                    "description": "Hide the Reference designator text on the schematic. Default: false (visible).",
                    "default": False
                },
                "hideValue": {
                    "type": "boolean",
                    "description": "Hide the Value text on the schematic. Default: false (visible).",
                    "default": False
                },
                "dnp": {
                    "type": "boolean",
                    "description": "Mark component as Do Not Place. Also sets inBom=false. Default: false.",
                    "default": False
                }
            },
            "required": ["schematicPath", "library", "symbol", "reference", "x", "y"]
        }
    },
    {
        "name": "edit_schematic_component",
        "title": "Edit Schematic Component",
        "description": (
            "Updates properties of a placed symbol. Supports: value, footprint, datasheet, "
            "reference (rename), x, y, rotation, mirror, and arbitrary custom properties. "
            "Only the fields you supply are changed."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "schematicPath": {
                    "type": "string",
                    "description": "Path to the .kicad_sch file"
                },
                "reference": {
                    "type": "string",
                    "description": "Reference designator of the component to edit (e.g. 'R1')"
                },
                "value": {
                    "type": "string",
                    "description": "New value (e.g. '22k')"
                },
                "footprint": {
                    "type": "string",
                    "description": "New footprint (e.g. 'Resistor_SMD:R_0603')"
                },
                "datasheet": {
                    "type": "string",
                    "description": "New datasheet URL"
                },
                "newReference": {
                    "type": "string",
                    "description": "Rename the component to a new reference designator"
                },
                "x": {
                    "type": "number",
                    "description": "New X position in mm"
                },
                "y": {
                    "type": "number",
                    "description": "New Y position in mm"
                },
                "rotation": {
                    "type": "number",
                    "description": "New rotation in degrees"
                },
                "mirror": {
                    "type": "string",
                    "enum": ["", "x", "y"],
                    "description": "Mirror axis"
                },
                "properties": {
                    "type": "object",
                    "description": "Custom properties to set/update (e.g. {\"LCSC Part\": \"C25768\"})",
                    "additionalProperties": {"type": "string"}
                },
                "hideProperties": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Property keys to hide (e.g. [\"Reference\", \"Value\", \"Footprint\"])"
                },
                "showProperties": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Property keys to make visible (e.g. [\"Footprint\", \"Datasheet\"])"
                },
                "dnp": {
                    "type": "boolean",
                    "description": "Mark component as Do Not Place (true) or clear the DNP flag (false). Also toggles inBom accordingly."
                }
            },
            "required": ["schematicPath", "reference"]
        }
    },
    {
        "name": "replace_schematic_symbol",
        "title": "Replace Schematic Symbol",
        "description": (
            "Swaps the underlying KiCAD symbol (lib_id) of a placed component while "
            "preserving its position, rotation, mirror, and all existing properties. "
            "Use this to replace EasyEDA/imported symbols with standard KiCAD symbols "
            "(e.g. Device:R, Device:C, Device:SW_Push, Transistor_FET:2N7002). "
            "Optionally override value, footprint, or other properties at the same time."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "schematicPath": {
                    "type": "string",
                    "description": "Path to the .kicad_sch file"
                },
                "reference": {
                    "type": "string",
                    "description": "Reference designator of the component to replace (e.g. 'R1')"
                },
                "newLibrary": {
                    "type": "string",
                    "description": "Target KiCAD symbol library name (e.g. 'Device', 'Transistor_FET')"
                },
                "newSymbol": {
                    "type": "string",
                    "description": "Target symbol name within that library (e.g. 'R', 'C', '2N7002')"
                },
                "value": {
                    "type": "string",
                    "description": "Override the component value (default: keep existing value)"
                },
                "footprint": {
                    "type": "string",
                    "description": "Override the footprint (default: keep existing footprint)"
                },
                "datasheet": {
                    "type": "string",
                    "description": "Override the datasheet URL"
                },
                "x": {"type": "number", "description": "Override X position in mm"},
                "y": {"type": "number", "description": "Override Y position in mm"},
                "rotation": {"type": "number", "description": "Override rotation in degrees"},
                "mirror": {
                    "type": "string",
                    "enum": ["", "x", "y"],
                    "description": "Override mirror axis"
                },
                "properties": {
                    "type": "object",
                    "description": "Additional custom properties to set/override",
                    "additionalProperties": {"type": "string"}
                },
                "libFile": {
                    "type": "string",
                    "description": "Explicit path to the .kicad_sym library file (skips auto-search)"
                },
                "hideReference": {
                    "type": "boolean",
                    "description": "Hide the Reference designator text. Default: false (visible).",
                    "default": False
                },
                "hideValue": {
                    "type": "boolean",
                    "description": "Hide the Value text. Default: false (visible).",
                    "default": False
                }
            },
            "required": ["schematicPath", "reference", "newLibrary", "newSymbol"]
        }
    },
    {
        "name": "delete_schematic_component",
        "title": "Delete Schematic Component",
        "description": "Removes a placed symbol from the schematic by its reference designator.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "schematicPath": {
                    "type": "string",
                    "description": "Path to the .kicad_sch file"
                },
                "reference": {
                    "type": "string",
                    "description": "Reference designator of the component to remove (e.g. 'R1')"
                }
            },
            "required": ["schematicPath", "reference"]
        }
    },
    # ------------------------------------------------------------------
    # Wiring
    # ------------------------------------------------------------------
    {
        "name": "add_schematic_wire",
        "title": "Add Wire",
        "description": (
            "Draws one or more wire segments on the schematic. "
            "Provide a list of [x, y] waypoints; consecutive pairs become individual segments, "
            "so [[0,0],[10,0],[10,10]] creates two right-angle segments. "
            "Coordinates must match pin endpoints or existing wire endpoints exactly (KiCAD snaps to 1.27 mm grid)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "schematicPath": {
                    "type": "string",
                    "description": "Path to the .kicad_sch file"
                },
                "points": {
                    "type": "array",
                    "description": "Ordered list of [x, y] waypoints in mm",
                    "items": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 2,
                        "maxItems": 2
                    },
                    "minItems": 2
                }
            },
            "required": ["schematicPath", "points"]
        }
    },
    {
        "name": "add_schematic_net_label",
        "title": "Add Net Label",
        "description": (
            "Adds a net label at a wire endpoint or pin endpoint. "
            "The x/y coordinates must coincide exactly with a wire end or pin — "
            "use get_schematic_pin_locations to obtain precise pin coordinates. "
            "Set global=true for labels that should be visible across multiple sheets."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "schematicPath": {
                    "type": "string",
                    "description": "Path to the .kicad_sch file"
                },
                "netName": {
                    "type": "string",
                    "description": "Net name (e.g. 'VCC', 'GND', 'SDA')"
                },
                "x": {
                    "type": "number",
                    "description": "X coordinate in mm"
                },
                "y": {
                    "type": "number",
                    "description": "Y coordinate in mm"
                },
                "rotation": {
                    "type": "number",
                    "description": "Label rotation in degrees (0, 90, 180, 270). Default: 0",
                    "default": 0
                },
                "global": {
                    "type": "boolean",
                    "description": "If true, creates a global label (visible across sheets). Default: false",
                    "default": False
                }
            },
            "required": ["schematicPath", "netName", "x", "y"]
        }
    },
    {
        "name": "add_schematic_junction",
        "title": "Add Junction",
        "description": "Adds a filled junction dot where two wires cross and should be electrically connected.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "schematicPath": {
                    "type": "string",
                    "description": "Path to the .kicad_sch file"
                },
                "x": {
                    "type": "number",
                    "description": "X coordinate in mm"
                },
                "y": {
                    "type": "number",
                    "description": "Y coordinate in mm"
                }
            },
            "required": ["schematicPath", "x", "y"]
        }
    },
    {
        "name": "add_schematic_no_connect",
        "title": "Add No-Connect Flag",
        "description": "Marks an unconnected pin with a no-connect flag (X) to suppress ERC warnings.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "schematicPath": {
                    "type": "string",
                    "description": "Path to the .kicad_sch file"
                },
                "x": {
                    "type": "number",
                    "description": "X coordinate of the pin endpoint in mm"
                },
                "y": {
                    "type": "number",
                    "description": "Y coordinate of the pin endpoint in mm"
                }
            },
            "required": ["schematicPath", "x", "y"]
        }
    },
    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------
    {
        "name": "get_schematic_pin_locations",
        "title": "Get Pin Locations",
        "description": (
            "Returns the absolute schematic coordinates of every pin on a placed component. "
            "Always call this before adding wires or net labels, to get the exact x/y endpoint "
            "for each pin. Accounts for the component's position, rotation, and mirror."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "schematicPath": {
                    "type": "string",
                    "description": "Path to the .kicad_sch file"
                },
                "reference": {
                    "type": "string",
                    "description": "Reference designator (e.g. 'R1', 'U3', 'J1')"
                }
            },
            "required": ["schematicPath", "reference"]
        }
    },
    # ------------------------------------------------------------------
    # Annotation tools
    # ------------------------------------------------------------------
    {
        "name": "annotate_schematic",
        "title": "Annotate Schematic Components",
        "description": (
            "Assigns sequential reference designators to schematic components "
            "(e.g. R1, R2, C1, C2 …). "
            "Power and flag symbols (#PWR, #FLG …) are always skipped. "
            "Multi-unit components (e.g. dual op-amps) share the same base number. "
            "Use onlyUnannotated=true to number only components that still show 'R?', "
            "leaving already-annotated references intact. "
            "For multi-sheet projects, pass the paths of already-annotated sheets in "
            "existingSchematicPaths so that this sheet never reuses their numbers — "
            "this replaces the need to manually set startNumber."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "schematicPath": {
                    "type": "string",
                    "description": "Absolute path to the .kicad_sch file to annotate"
                },
                "sortByPosition": {
                    "type": "boolean",
                    "description": "Sort components left-to-right then top-to-bottom before numbering (default: true)",
                    "default": True
                },
                "onlyUnannotated": {
                    "type": "boolean",
                    "description": "When true, only number components whose reference still contains '?' (default: false = full re-annotation)",
                    "default": False
                },
                "startNumber": {
                    "type": "integer",
                    "description": "First number to assign for each prefix group (default: 1). Ignored for any prefix whose numbers are already reserved via existingSchematicPaths.",
                    "default": 1,
                    "minimum": 0
                },
                "skipPrefixes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of reference prefixes to leave unchanged, e.g. ['U', 'J']"
                },
                "existingSchematicPaths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Paths to already-annotated sibling schematic sheets. "
                        "Their reference numbers are pre-reserved so this sheet "
                        "never generates duplicates. Use this instead of startNumber "
                        "for multi-sheet projects."
                    )
                }
            },
            "required": ["schematicPath"]
        }
    },
    {
        "name": "clear_annotation",
        "title": "Clear Schematic Annotation",
        "description": (
            "Resets reference designators back to the unannotated 'X?' form "
            "(e.g. R1 → R?, C12 → C?). "
            "Power and flag symbols are never touched. "
            "Use the prefixes parameter to restrict clearing to specific component types."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "schematicPath": {
                    "type": "string",
                    "description": "Absolute path to the .kicad_sch file"
                },
                "prefixes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "If provided, only clear references with these prefixes, e.g. ['R', 'C']. Omit to clear all components."
                }
            },
            "required": ["schematicPath"]
        }
    },
    # ------------------------------------------------------------------
    # ERC / export / sync  (unchanged from previous implementation)
    # ------------------------------------------------------------------
    {
        "name": "run_erc",
        "title": "Run Electrical Rules Check (ERC)",
        "description": "Runs KiCAD ERC via kicad-cli and returns all violations with type, severity, and location.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "schematicPath": {
                    "type": "string",
                    "description": "Path to the .kicad_sch file"
                }
            },
            "required": ["schematicPath"]
        }
    },
    {
        "name": "sync_schematic_to_board",
        "title": "Sync Schematic to PCB",
        "description": "Reads net connections from the schematic and assigns them to matching footprint pads in the PCB file. Run this after completing the schematic and before routing traces.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "schematicPath": {
                    "type": "string",
                    "description": "Path to .kicad_sch file (auto-detected from board path if omitted)"
                },
                "boardPath": {
                    "type": "string",
                    "description": "Path to .kicad_pcb file (uses currently loaded board if omitted)"
                }
            }
        }
    },
    {
        "name": "generate_netlist",
        "title": "Generate Netlist",
        "description": "Generates a netlist from the schematic showing all components and net connections.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "schematicPath": {
                    "type": "string",
                    "description": "Path to the .kicad_sch file"
                },
                "outputPath": {
                    "type": "string",
                    "description": "Optional path to save the netlist file"
                },
                "format": {
                    "type": "string",
                    "enum": ["kicad", "json", "spice"],
                    "description": "Netlist format (default: json)",
                    "default": "json"
                }
            },
            "required": ["schematicPath"]
        }
    },
    {
        "name": "list_schematic_libraries",
        "title": "List Symbol Libraries",
        "description": "Lists all available KiCAD symbol libraries found in the standard search paths.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "searchPaths": {
                    "type": "array",
                    "description": "Additional paths to search for .kicad_sym files",
                    "items": {"type": "string"}
                }
            }
        }
    },
    {
        "name": "export_schematic_pdf",
        "title": "Export Schematic to PDF",
        "description": "Exports the schematic as a PDF file using kicad-cli.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "schematicPath": {
                    "type": "string",
                    "description": "Path to the .kicad_sch file"
                },
                "outputPath": {
                    "type": "string",
                    "description": "Destination path for the PDF"
                }
            },
            "required": ["schematicPath", "outputPath"]
        }
    }
]

# =============================================================================
# UI/PROCESS TOOLS
# =============================================================================

UI_TOOLS = [
    {
        "name": "check_kicad_ui",
        "title": "Check KiCAD UI Status",
        "description": "Checks if KiCAD user interface is currently running and returns process information.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "launch_kicad_ui",
        "title": "Launch KiCAD Application",
        "description": "Opens the KiCAD graphical user interface, optionally with a specific project loaded.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectPath": {
                    "type": "string",
                    "description": "Optional path to project file to open in UI"
                },
                "autoLaunch": {
                    "type": "boolean",
                    "description": "Whether to automatically launch if not running",
                    "default": True
                }
            }
        }
    }
]

# =============================================================================
# COMBINED TOOL SCHEMAS
# =============================================================================

TOOL_SCHEMAS: Dict[str, Any] = {}

# Combine all tool categories
for tool in (PROJECT_TOOLS + BOARD_TOOLS + COMPONENT_TOOLS + ROUTING_TOOLS +
             LIBRARY_TOOLS + DESIGN_RULE_TOOLS + EXPORT_TOOLS +
             SCHEMATIC_TOOLS + UI_TOOLS):
    TOOL_SCHEMAS[tool["name"]] = tool

# Total: 46 tools with comprehensive schemas
