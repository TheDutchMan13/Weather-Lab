; Inno Setup script for Weather Lab. Build it with build_installer.py after build_exe.py.
; Installs for the current user only (no admin prompt). Settings and data stay in AppData
; and are not removed by the uninstaller.

#define AppName "Weather Lab"
#define AppVersion "0.19.0"

[Setup]
AppId={{6F2D8A1E-4B7C-4E0A-9C3D-2A7B5E1F8D42}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Weather Lab contributors
DefaultDirName={localappdata}\Programs\Weather Lab
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=installer
OutputBaseFilename=WeatherLabSetup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\WeatherLab.exe
SetupIconFile=assets\installer\weatherlab.ico
WizardImageFile=assets\installer\wizard-large.bmp
WizardSmallImageFile=assets\installer\wizard-small.bmp
CloseApplications=yes
RestartApplications=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "dist\WeatherLab\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\WeatherLab.exe"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\WeatherLab.exe"; Tasks: desktopicon

[Registry]
; Removes the start-on-login entry when the app is uninstalled
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "WeatherLab"; Flags: uninsdeletevalue

[Run]
Filename: "{app}\WeatherLab.exe"; Description: "Start {#AppName}"; Flags: nowait postinstall skipifsilent
