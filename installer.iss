; Inno Setup 6 script for 3D Print Sync
; Build with: ISCC.exe installer.iss
; Requires the PyInstaller bundle at dist\3DPrintSync\ to exist first.

[Setup]
AppName=3D Print Sync
AppVersion=1.1.0
AppPublisher=dorfmandesign
AppPublisherURL=https://github.com/dorfman2/3d-print-library
DefaultDirName={localappdata}\3DPrintSync
DisableProgramGroupPage=no
OutputDir=dist
OutputBaseFilename=3DPrintSync-Setup
SetupIconFile=app-icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; No UAC prompt — installs per-user into %LOCALAPPDATA%
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "Create a &Desktop shortcut";  GroupDescription: "Additional shortcuts:"; Flags: unchecked
Name: "startmenu";  Description: "Create a &Start Menu entry";   GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "dist\3DPrintSync\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs
; PyInstaller 6.x stashes bundled data under _internal\, so place a copy of the
; .ico at the install root for shortcut IconFilename references.
Source: "app-icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{userdesktop}\3D Print Sync";                Filename: "{app}\3DPrintSync.exe"; IconFilename: "{app}\app-icon.ico"; Tasks: desktopicon
Name: "{userprograms}\3D Print Sync\3D Print Sync"; Filename: "{app}\3DPrintSync.exe"; IconFilename: "{app}\app-icon.ico"; Tasks: startmenu
; Uninstall shortcut is always created so users have a discoverable entry
; even when the optional Start Menu task is left unchecked.
Name: "{userprograms}\3D Print Sync\Uninstall";     Filename: "{uninstallexe}"

[UninstallDelete]
; Remove runtime-generated files that the uninstaller won't know about
Type: files;          Name: "{app}\sort_downloads_config.json"
Type: files;          Name: "{app}\sort_downloads.log"
Type: files;          Name: "{app}\categories.json"
Type: filesandordirs; Name: "{app}"

[Run]
Filename: "{app}\3DPrintSync.exe"; Description: "&Launch 3D Print Sync now"; Flags: nowait postinstall skipifsilent
