[Setup]
AppName=Distord
AppVersion=0.1.0
DefaultDirName={pf}\Distord
DefaultGroupName=Distord
SetupIconFile=icon.ico
UninstallDisplayIcon=icon.ico
OutputDir=Output
OutputBaseFilename=DistordInstallerWindows
Compression=lzma
SolidCompression=yes

[Files]
Source: "Distord.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Distord"; Filename: "{app}\Distord.exe"
Name: "{commondesktop}\Distord"; Filename: "{app}\Distord.exe"; Tasks: desktopicon; IconFilename: "icon.ico"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked