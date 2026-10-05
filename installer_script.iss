[Setup]
AppName=OBDF Gas Kick Simulator
AppVersion=1.0
AppPublisher=Your Engineering Company
AppPublisherURL=https://www.yourengineering.com
DefaultDirName={autopf}\OBDFGasKickSimulator
DefaultGroupName=OBDF Gas Kick Simulator
; The output file you will send to clients
OutputDir=.\Output
OutputBaseFilename=GasKickSimulator_Setup_v1.0
SetupIconFile=.\assets\app_icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Grab the entire PyInstaller output folder and map it to the installation directory
Source: ".\dist\GasKickSimulator\GasKickSimulator.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: ".\dist\GasKickSimulator\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\OBDF Gas Kick Simulator"; Filename: "{app}\GasKickSimulator.exe"; IconFilename: "{app}\assets\app_icon.ico"
Name: "{autodesktop}\OBDF Gas Kick Simulator"; Filename: "{app}\GasKickSimulator.exe"; Tasks: desktopicon; IconFilename: "{app}\assets\app_icon.ico"

[Run]
Filename: "{app}\GasKickSimulator.exe"; Description: "{cm:LaunchProgram,OBDF Gas Kick Simulator}"; Flags: nowait postinstall skipifsilent