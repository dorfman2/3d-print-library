# Project Context - Big Picture View

## Project Purpose
Overall cleanup and organization of 3D printer files. This includes slicer profiles, 3D object files, firmware/images, timelapses, and designer files.

## Current Directory Structure
- `1 - Objects/` - 3D model/object files (20 GB, 15,189+ files)
- `2 - Configs and Profiles/` - Printer slicer configuration profiles (4.6 MB)
- `3 - Firmware and Images/` - Printer firmware files (13 MB, 3 .bbf files)
- `4 - Timelapses/` - Print timelapse recordings (44 .mpg videos from 2019)
- `5 - Designer Files/` - Source design files (1.6 MB, 9 STEP/OBJ files)

## Objects Folder Organization
Reorganized 15-category structure (clean names, no underscores):
- `0 - Calibration` - Calibration prints and tests
- `Uncategorized` - Items pending categorization (no number prefix)
- `1 - Machines` - Printer parts, upgrades, filters
- `2 - Home and Household` - Kitchen, bathroom, planters, home items
- `3 - Office` - Desk accessories, monitors, webcams, phone stands, speakers
- `4 - Tools and Organization` - Workshop tools, storage systems, peg boards
- `5 - Repairs and Replacements` - Replacement parts for broken items
- `6 - Electronics` - Raspberry Pi, IoT devices, Arduino (merged from old RPi + IOT)
- `7 - Gifts and Toys` - Giftable items, fidget toys, games, novelty (merged from old Gifts + Things to Make)
- `8 - Models and Display` - Display models, sculptures, decorative (merged from old Models + Things to Make)
- `9 - Tabletop` - Tabletop gaming minis and scenery
- `10 - RC Flight` - RC vehicle parts
- `11 - MultiBoard` - MultiBoard wall system
- `12 - MMU` - Multi-material upgrade prints
- `13 - NERF` - NERF modifications
- `14 - Legos` - Lego-related prints
- `15 - Cosplay` - Cosplay props and accessories

## Completed Changes
- Deleted folders 4, 6, 8, and Fusion DUMP (user consolidated)
- Git repository reinitialized (reduced from 1.1 GB, pending first commit)
- Flattened Cura profile structure (removed redundant nesting)
- Renamed all folders to sequential numbering (1-5)
- Renamed `2 - Objects` → `1 - Objects` ✓
- Removed duplicate `PrusaSlicer_config_bundle.ini` from root ✓
- Extracted and removed all 147 zip files (including nested zips) ✓
- Created `.claude/settings.local.json` with Bash always-allowed

## Zip File Policy
- All `.zip` files should be extracted in place, then the zip removed
- Skip extraction if contents already exist alongside the zip (already extracted)
- **ALL 147 zip files processed and removed** (0 remaining)

## Version Control
- **No git repo** — removed as impractical for large binary .stl files on OneDrive

## Next Development Priorities
1. Audit contents for duplicates and outdated files

## Technical Challenges
- **OneDrive sync locks:** Files stored on OneDrive can cause permission issues during rename operations. Close OneDrive before bulk file operations.
- **OneDrive filename restrictions:** MUST NOT use these characters in filenames: `~ # " * : < > ? / \ |` — they are invalid or restricted on OneDrive
- **Windows MAX_PATH:** Resolved — all paths now under 260 chars (max 258). Tightest area is `99 - OLD-Deprecated/1 - Duplicator i3/SWD2_KIT_*`
- **PrusaSlicer file locks:** Objects folder locked when files open in PrusaSlicer

## Storage
- **OneDrive** is the sole copy of all 3D print files — NAS copy fully removed (2026-05-09)
- Manyfold self-hosted server experiment was decommissioned; all related Docker containers, images, config, and library files deleted from NAS
