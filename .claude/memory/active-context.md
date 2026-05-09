# Active Context - Current Task State

## Current Focus
Manyfold experiment fully removed. OneDrive is now the sole copy of all 3D print files.

## Recent Changes
- Reorganized Objects into 15 clean-named categories ✓
- Manyfold server experiment decommissioned ✓
  - Stopped and removed all containers (manyfold, redis, postgres)
  - Removed Docker images
  - Removed `/volume1/Cloud_Jeff/docker/manyfold/` (config, pgdata, compose)
  - Removed `/volume1/Cloud_Jeff/3-D Printing/` (full library from NAS)

## Upcoming Changes
- Audit OneDrive contents for duplicates and outdated files

## Active Decisions and Considerations
- Config/firmware/CAD files bundled with downloaded projects should stay in Objects (contextual)
- Folder 5 (Designer Files) is for user's OWN designs; downloaded project CAD files stay in Objects
- Video file in Napier Deltic Engine project left in place (project reference, not a timelapse)
