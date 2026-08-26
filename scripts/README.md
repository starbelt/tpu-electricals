# Scripts

Standalone helper scripts for managing the KiCad libraries in this project. Not part of the KiCad project itself — run manually as needed.

## Contents

* `extract_footprints.py` — flattens a folder tree of downloaded component libraries (e.g. from a distributor export) into [kicad/footprints.pretty/](../kicad/footprints.pretty/), then rewrites the `Footprint` property of every symbol found alongside a footprint so it points at the flattened library. Paths are currently hardcoded at the bottom of the script (`components_root`, `footprints_target`) — update them for your local layout before running.

## Usage

```bash
python extract_footprints.py
```
