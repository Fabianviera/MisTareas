[Setup]
AppName=MisTareas
AppVersion=0.1 Beta
AppPublisher=Fabián Viera
DefaultDirName={autopf}\MisTareas
DefaultGroupName=MisTareas
OutputDir=installer
OutputBaseFilename=SetupMisTareas
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\MisTareas.exe
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
AllowNoIcons=no

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el Escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "dist\MisTareas.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\MisTareas";        Filename: "{app}\MisTareas.exe"; IconFilename: "{app}\MisTareas.exe"
Name: "{group}\Desinstalar MisTareas"; Filename: "{uninstallexe}"
Name: "{autodesktop}\MisTareas";  Filename: "{app}\MisTareas.exe"; IconFilename: "{app}\MisTareas.exe"; Tasks: desktopicon
Name: "{userstartmenu}\MisTareas"; Filename: "{app}\MisTareas.exe"; IconFilename: "{app}\MisTareas.exe"

[Run]
Filename: "{app}\MisTareas.exe"; Description: "Abrir MisTareas ahora"; Flags: nowait postinstall skipifsilent
