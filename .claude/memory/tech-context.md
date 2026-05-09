# Tech Context - Target Environment and Stack

## Core Requirements
- Windows 11 Pro (local workstation)
- OneDrive as sole storage for all 3D print files

## Core Dependencies
- **OneDrive** - cloud sync for 3D Printing folder (Windows side)
- **PrusaSlicer / Bambu Studio / Cura** - slicers that may lock files

## Technologies, Libraries, and Protocols
- OneDrive for Windows sync (cloud-only file stubs possible)
- STL, 3MF, OBJ, STEP — primary 3D file formats in library

## Component Relationships and Dependencies
- All files live on OneDrive; no NAS or server component active

## Key Technical Decisions
- No git repo for 3D Printing folder — impractical for large binary STL files on OneDrive
