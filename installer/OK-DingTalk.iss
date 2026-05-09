#define MyAppName "OK-DingTalk"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "OK-DingTalk"
#define MyAppExeName "OK-DingTalk.exe"

[Setup]
AppId={{9A4C42DF-7160-4F5B-8F0A-5E9F08F2C8D7}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\release
OutputBaseFilename=OK-DingTalk-setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
SetupIconFile=..\icon.ico

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\OK-DingTalk\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\dist\OK-DingTalk-Panel\*"; DestDir: "{app}\panel"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\dist\OK-DingTalk-Auto\*"; DestDir: "{app}\auto"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\OK-DingTalk"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\OK-DingTalk 管理面板"; Filename: "{app}\panel\OK-DingTalk-Panel.exe"
Name: "{group}\OK-DingTalk 自动执行"; Filename: "{app}\auto\OK-DingTalk-Auto.exe"
Name: "{autodesktop}\OK-DingTalk"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{autodesktop}\OK-DingTalk 管理面板"; Filename: "{app}\panel\OK-DingTalk-Panel.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,OK-DingTalk}"; Flags: nowait postinstall skipifsilent
