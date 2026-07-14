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
Name: "{commondesktop}\Distord"; Filename: "{app}\Distord.exe"; Tasks: desktopicon; IconFilename: "{app}\icon.ico"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Registry]
Root: HKCU; Subkey: "Environment"; \
    ValueType: expandsz; ValueName: "Path"; \
    ValueData: "{olddata};{app}"; \
    Check: NeedsAddPath('{app}')

[Code]

function NeedsAddPath(Dir: string): Boolean;
var
  Path: string;
begin
  if not RegQueryStringValue(HKCU, 'Environment', 'Path', Path) then
    Path := '';

  Result := Pos(';' + UpperCase(Dir) + ';', ';' + UpperCase(Path) + ';') = 0;
end;