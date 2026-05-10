; Inno Setup 6 script for 3D Print Sync
; Build with: ISCC.exe installer.iss
; Requires the PyInstaller bundle at dist\3DPrintSync\ to exist first.

[Setup]
AppName=3D Print Sync
AppVersion=0.5.0
AppPublisher=dorfmandesign
AppPublisherURL=https://github.com/dorfman2/3d-print-library
DefaultDirName={localappdata}\3DPrintSync
DisableProgramGroupPage=no
OutputDir=dist
OutputBaseFilename=3DPrintSync-Setup
SetupIconFile=icons8-3d-printer.ico
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

[Icons]
Name: "{userdesktop}\3D Print Sync";                Filename: "{app}\3DPrintSync.exe"; IconFilename: "{app}\icons8-3d-printer.ico"; Tasks: desktopicon
Name: "{userprograms}\3D Print Sync\3D Print Sync"; Filename: "{app}\3DPrintSync.exe"; IconFilename: "{app}\icons8-3d-printer.ico"; Tasks: startmenu
Name: "{userprograms}\3D Print Sync\Uninstall";     Filename: "{uninstallexe}";                                                     Tasks: startmenu

[UninstallDelete]
; Remove runtime-generated files that the uninstaller won't know about
Type: files;          Name: "{app}\sort_downloads_config.json"
Type: files;          Name: "{app}\sort_downloads.log"
Type: filesandordirs; Name: "{app}"

[Run]
Filename: "{app}\3DPrintSync.exe"; Description: "&Launch 3D Print Sync now"; Flags: nowait postinstall skipifsilent
