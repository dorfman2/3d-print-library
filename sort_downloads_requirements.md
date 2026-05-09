# sort_downloads.py — Requirements

## Purpose
A single script that ingests new 3D print files from the Downloads folder into the
organised library (`G:\3-D Printing\1 - Objects`), with clean folder names,
no duplicates, and no leftover ZIP files anywhere.

---

## Execution Modes

| Mode | Command | Behaviour |
|------|---------|-----------|
| Dry run (default) | `python sort_downloads.py` | Preview all phases, no changes made |
| Execute | `python sort_downloads.py --move` | Run all phases |

---

## Phases (in order)

### Phase 1 — Pre-process Downloads ZIPs
Collapse ZIP + extracted-folder duplicates in Downloads before anything is moved.

**Rules:**
- Scan the Downloads root for `.zip` files that contain at least one print file.
- If a folder with the same stem already exists alongside the ZIP → the ZIP is
  redundant; delete it.
- If no matching folder exists → extract the ZIP in place (to Downloads root),
  then delete the ZIP.
- After this phase, the Downloads root contains **no ZIP files**.

### Phase 2 — Build library index
Scan `LIBRARY_ROOT/*/*` (category / project) and collect the **cleaned name**
of every existing project folder into a set.  Used for duplicate detection in
Phase 3.

### Phase 3 — Collect and categorise candidates
Identify items in Downloads that should move to the library.

**Item types:**
- **Folder** containing at least one print file anywhere inside it → move the
  whole folder as a project.
- **Loose print file** (STL, 3MF, OBJ, STEP, etc.) at the Downloads root →
  wrap in a new subfolder named after the file stem, then move.

**For each candidate:**
1. Derive the **raw name** (folder name or file stem).
2. Compute the **cleaned name** via the name-cleanup rules (see below).
3. Check if the cleaned name already exists in the library index →
   **skip** and report as duplicate.
4. Assign a **category** via keyword scoring (see below).
5. Compute a unique destination path: `LIBRARY_ROOT / category / cleaned_name`.
   If the path already exists append `_2`, `_3`, … (should only happen for
   genuine near-duplicates after the dedup check).

### Phase 4 — Move to library
- Execute the moves collected in Phase 3.
- Log every move: `source_name -> category / cleaned_name`.
- Log every skip: `source_name  [DUPLICATE — already in library]`.

### Phase 5 — Clean library ZIPs
After all moves, eliminate every ZIP file remaining in the library tree.

**Rules:**
- Recursively find all `.zip` files under `LIBRARY_ROOT`.
- For each ZIP: extract contents into the ZIP's parent directory.
  - Skip individual files that already exist at the destination.
- Delete the ZIP after extraction.
- Log each ZIP processed.

---

## Name Cleanup Rules

Applied to every raw folder/file name before it is used as a destination.

| Step | Rule |
|------|------|
| 1 | Strip trailing noise **before** replacing separators (so `v1_2` still matches). |
| 2 | Noise tokens stripped (multi-pass until stable): version numbers (`v1`, `v2`, `v1_2`, `v1.0`), file-type tags (`stl`, `3mf`, `obj`, `step`, `gcode`), site-naming suffixes (`model_files`, `files`), `final`, `remix`/`remixed`/`remixof`, `by <author>`, `print`/`printed`/`printable`, `updated`/`fixed`, `free`, `paid`. |
| 3 | Replace `_` and `-` with spaces. |
| 4 | Collapse multiple spaces; strip leading/trailing whitespace. |
| 5 | Title-case each fully-lowercase word (first letter uppercased). |
| 6 | Preserve words with internal uppercase (`3DBenchy`, `RPi`) and all-caps (`NERF`, `MMU`). |
| 7 | Downcase small conjunctions/prepositions in non-first position (`and`, `for`, `of`, `the`, `in`, `or`, `to`, `at`, `a`, `an`, `but`, `by`, `as`, `nor`, `on`). |
| 8 | If cleaning produces an empty string, return the original name unchanged. |

**Examples:**

| Raw | Cleaned |
|-----|---------|
| `Ender_3_Fan_Duct_v3_FINAL_STL` | `Ender 3 Fan Duct` |
| `case-for-rak-wisblock-1-watt-starter-kit-model_files` | `Case for Rak Wisblock 1 Watt Starter Kit` |
| `desk_cable_organizer_v1_2_updated` | `Desk Cable Organizer` |
| `Raspberry_Pi_4_Case_by_SomeUser` | `Raspberry Pi 4 Case` |
| `3DBenchy` | `3DBenchy` |
| `NERF_Blaster_Attachment` | `NERF Blaster Attachment` |
| `musubi-press-spam-eggtamago-etc-model_files` | `Musubi Press Spam Eggtamago Etc` |

---

## Category Keyword Additions

The following keywords are missing from the current implementation and must be added:

| Category | Keywords to add |
|----------|----------------|
| `6 - Electronics` | `rak`, `wisblock`, `heltec`, `seeed`, `meshtastic`, `lora`, `lorawan`, `tracker`, `gateway`, `t1000`, `holster` (for device carriers) |
| `2 - Home and Household` | `musubi`, `sushi`, `press`, `food`, `kitchen press`, `bento` |

---

## Dry-Run Output Format

### Phase 1 — Downloads ZIPs
```
=== Phase 1: Downloads ZIPs ===
  [DELETE-ZIP] devil-girl-no-ams-model_files.zip  (folder already extracted)
  [EXTRACT]    holster-for-seeed-studio-t1000-e.zip  ->  holster-for-seeed-studio-t1000-e/
```

### Phase 3 — Candidates
```
=== Phase 3: Import to Library ===
  [SKIP-DUP]  3DBenchy                                (already in library)
  [DIR]  case-for-rak-wisblock-1-watt-starter-kit-model_files
         -> Case for Rak Wisblock 1 Watt Starter Kit  [6 - Electronics]
  [FILE] heltec_v4_stand-body
         -> Heltec V4 Stand Body                      [6 - Electronics]
```

### Phase 5 — Library ZIPs
```
=== Phase 5: Library ZIP Cleanup ===
  [ZIP] 1 - Objects/0 - Calibration/3DBenchy/source_files.zip
```

---

## File Paths

| Path | Purpose |
|------|---------|
| `C:\Users\dorfm\Downloads` | Source folder scanned for new files |
| `G:\3-D Printing\1 - Objects` | Library root; all 15 category subfolders live here |

---

## Print File Extensions Recognised

`.stl` `.3mf` `.obj` `.step` `.stp` `.f3d` `.f3z` `.amf` `.gcode` `.bgcode` `.gco`

---

## Out of Scope

- Scanning subdirectories of Downloads (only the root level is processed).
- Renaming files inside a project folder (only the project folder itself is renamed).
- Moving files between library categories (re-categorisation of existing library items).
- Handling password-protected ZIPs.

---

## Sync App (`sort_downloads_app.py`)

A lightweight Windows system-tray application that runs `sort_downloads.py --move`
on a configurable schedule and provides basic start/stop/boot controls.

### Dependencies

```
pip install pystray Pillow
```

### Config File

`sort_downloads_config.json` (created alongside the script on first run):

```json
{ "interval_minutes": 60, "autostart": false }
```

### System Tray Icon

Right-click menu:

| Item | Action |
|------|--------|
| Show Window | Raise / un-minimise the control window |
| Run Now | Execute sync immediately (outside schedule) |
| ────── | Separator |
| Exit | Cancel timer, remove tray icon, quit |

Icon colour: green when scheduled/running, grey when stopped.

### Control Window (~300 × 240 px)

```
+--------------------------------+
| 3D Print Library Sync          |
+--------------------------------+
| Status:   Idle                 |
| Last run: Never                |
| Next run: Not scheduled        |
|                                |
| Interval: [60 v] minutes       |
|                                |
| [  Start  ]  [  Stop  ]        |
| [x] Start on Boot              |
|          [ Exit ]              |
+--------------------------------+
```

- **Status** — `Idle` / `Running` / `Scheduled`
- **Last run** — timestamp of most recent completed sync, or `Never`
- **Next run** — timestamp of next scheduled sync, or `Not scheduled`
- **Interval spinbox** — range 1–1440 minutes; saved to config on change
- **Start / Stop** — enable or cancel the recurring timer
- **Start on Boot checkbox** — writes/removes a Windows Registry autostart entry
- **Exit button** — same as tray Exit

### Boot Behaviour

When launched with `--minimized` (used by the registry entry), the window is
hidden on startup; only the tray icon appears.

### Registry Key

```
HKCU\Software\Microsoft\Windows\CurrentVersion\Run
  3DPrintSync = "C:\...\pythonw.exe" "G:\3-D Printing\sort_downloads_app.py" --minimized
```

`pythonw.exe` is used so no console window appears on login.
