# KiCAD MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io/) server that lets AI assistants control KiCAD for PCB design automation. Describe what you want in plain language — the server handles the rest.

> **Fork of [mixelpixx/KiCAD-MCP-Server](https://github.com/mixelpixx/KiCAD-MCP-Server)** — Python-only rewrite with expanded schematic support, kiutils integration, and improved tool schemas.

---

## What it does

- **64 tools** covering the full PCB design workflow: projects, board layout, component placement, routing, schematics, DRC, and exports
- **Dynamic symbol loading** — access all ~10,000 KiCAD symbols from standard libraries, no manual import needed
- **Intelligent schematic wiring** — automatic pin location, rotation-aware routing, power symbol support
- **BOM export** with LCSC part number extraction from schematic fields
- **IPC backend** (experimental) — real-time sync with a running KiCAD instance via the KiCAD 9.0 IPC API
- **Tool router** — organises 64 tools into discoverable categories so the AI only loads what it needs (~70% less context)

---

## Requirements

- **KiCAD 9.0+** — [kicad.org/download](https://www.kicad.org/download/)
- **Python 3.11+** (the `pcbnew` module ships with KiCAD)
- **[uv](https://docs.astral.sh/uv/)** package manager

Verify your KiCAD Python install:
```bash
python3 -c "import pcbnew; print(pcbnew.GetBuildVersion())"
```

---

## Installation

```bash
git clone https://github.com/mageoch/KiCAD-MCP-Server.git
cd KiCAD-MCP-Server
uv sync
```

---

## Configuration

### Claude Code

Add to your project's `.mcp.json` or `~/.claude.json`:

```json
{
  "mcpServers": {
    "kicad": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/KiCAD-MCP-Server",
        "run", "python", "python/kicad_interface.py"
      ],
      "env": {
        "PYTHONPATH": "/usr/lib/python3/dist-packages"
      }
    }
  }
}
```

### Claude Desktop

Edit `~/.config/Claude/claude_desktop_config.json` (Linux/macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "kicad": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/KiCAD-MCP-Server",
        "run", "python", "python/kicad_interface.py"
      ],
      "env": {
        "PYTHONPATH": "/usr/lib/python3/dist-packages"
      }
    }
  }
}
```

### Platform-specific `PYTHONPATH`

| Platform | Path |
|----------|------|
| Linux | `/usr/lib/kicad/lib/python3/dist-packages` or `/usr/lib/python3/dist-packages` |
| macOS | `/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/lib/python3.11/site-packages` |
| Windows | `C:\Program Files\KiCad\9.0\lib\python3\dist-packages` |

If the server can't find Python, set `KICAD_PYTHON` to the full path:
```json
"env": { "KICAD_PYTHON": "/usr/bin/python3", "PYTHONPATH": "..." }
```

### IPC API (optional)

For real-time sync with the KiCAD UI, enable the IPC server in KiCAD:
**Preferences → Plugins → Enable IPC API Server**

No extra configuration needed — the server detects IPC automatically and falls back to the file-based API when unavailable.

---

## Tools

### Project (4)
`create_project` · `open_project` · `save_project` · `get_project_info`

### Board (9)
`set_board_size` · `add_board_outline` · `add_layer` · `set_active_layer` · `get_layer_list` · `get_board_info` · `get_board_2d_view` · `add_mounting_hole` · `add_board_text`

### Component placement (10)
`place_component` · `move_component` · `rotate_component` · `delete_component` · `edit_component` · `get_component_properties` · `get_component_list` · `place_component_array` · `align_components` · `duplicate_component`

### Routing & nets (8)
`add_net` · `route_trace` · `add_via` · `delete_trace` · `get_nets_list` · `create_netclass` · `add_copper_pour` · `route_differential_pair`

### Schematic (9)
`create_schematic` · `load_schematic` · `add_schematic_component` · `add_schematic_wire` · `add_schematic_connection` · `add_schematic_net_label` · `add_schematic_junction` · `add_schematic_no_connect` · `list_schematic_libraries`

### Library (6)
`list_libraries` · `search_footprints` · `list_library_footprints` · `get_footprint_info` · `list_symbol_libraries` · `search_symbols`

### Design rules (4)
`set_design_rules` · `get_design_rules` · `run_drc` · `get_drc_violations`

### Export (6)
`export_gerber` · `export_pdf` · `export_svg` · `export_3d` · `export_bom` · `export_schematic_pdf`

### UI (2)
`check_kicad_ui` · `launch_kicad_ui`

### Tool discovery (4)
`list_tool_categories` · `get_category_tools` · `search_tools` · `execute_tool`

---

## LCSC/JLCPCB component search

Component search and catalog access have been moved to the companion [LCSC-MCP-Server](https://github.com/mageoch/LCSC-MCP-Server), which provides parametric search across 2.5M+ JLCPCB parts, live pricing, stock data, and KiCAD file downloads.

This server handles the PCB/schematic side — `export_bom` includes LCSC part numbers extracted from schematic component properties, ready to use with JLCPCB's assembly service.

---

## Resources

Read-only access to project state without running tools:

| URI | Description |
|-----|-------------|
| `kicad://project/current/info` | Project metadata |
| `kicad://project/current/board` | Board properties |
| `kicad://project/current/components` | Component list (JSON) |
| `kicad://project/current/nets` | Electrical nets |
| `kicad://project/current/layers` | Layer stack |
| `kicad://project/current/design-rules` | DRC settings |
| `kicad://project/current/drc-report` | DRC violations |
| `kicad://board/preview.png` | Board visualisation (PNG) |

---

## Architecture

```
python/
├── kicad_interface.py       # MCP entry point — message routing
├── kicad_api/
│   ├── swig_backend.py      # pcbnew file-based API
│   ├── ipc_backend.py       # KiCAD 9.0 IPC API (real-time)
│   └── factory.py           # Backend auto-detection
├── commands/                # One module per tool category
├── schemas/tool_schemas.py  # JSON Schema for all tools
└── resources/               # MCP resource handlers
```

The server runs as a Python process over stdio. It uses `pcbnew` (KiCAD's SWIG bindings) for file operations and `kipy` for the IPC backend when KiCAD is running. Schematic manipulation uses `kicad-skip` and `kiutils`.

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'pcbnew'`**
Check that `PYTHONPATH` points to the directory containing `pcbnew.so` for your KiCAD installation (see platform table above).

**Server not listed in MCP client**
Ensure the `--directory` path is absolute and `uv sync` completed without errors.

**Tool errors**
Check logs at `~/.kicad-mcp/logs/kicad_interface.log`. Most errors are caused by a missing open project or relative file paths — always use absolute paths.

For more, see [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md) and [GitHub Issues](https://github.com/mageoch/KiCAD-MCP-Server/issues).

---

## Contributing

Bug reports, feature requests, and pull requests are welcome.

1. Open an issue describing the bug or feature
2. Fork the repo and create a branch
3. Submit a PR with a clear description

See [GitHub Issues](https://github.com/mageoch/KiCAD-MCP-Server/issues) to report bugs or request features.

---

## License

MIT — see [LICENSE](LICENSE).

Originally created by [mixelpixx](https://github.com/mixelpixx/KiCAD-MCP-Server). Maintained by [@mageo](https://github.com/mageo) / [mageoch](https://github.com/mageoch).
