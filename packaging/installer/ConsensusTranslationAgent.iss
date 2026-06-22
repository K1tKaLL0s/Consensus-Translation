#define AppName "共识翻译 Agent"
#define AppPublisher "Consensus Translation"
#define AppExeName "ConsensusTranslationAgent.exe"
#define AppId "{{9F6C03F8-0D3A-4C42-9CF4-6F61F7A2D9E1}"

#ifndef ProjectRoot
  #define ProjectRoot "..\.."
#endif

#ifndef AppPayload
  #define AppPayload "..\..\dist\ConsensusTranslationAgent"
#endif

#ifndef OutputDir
  #define OutputDir "..\..\release"
#endif

#ifndef Channel
  #define Channel "standard"
#endif

#ifndef AppVersion
  #define AppVersion "2026.06.18"
#endif

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\ConsensusTranslationAgent
DefaultGroupName={#AppName}
DisableDirPage=no
UsePreviousAppDir=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutputDir}
OutputBaseFilename=ConsensusTranslationAgent-Setup-{#Channel}
Compression=lzma2/max
SolidCompression=yes
#ifdef RuntimePayload
DiskSpanning=yes
DiskSliceSize=2000000000
#endif
WizardStyle=modern
ChangesAssociations=no
UninstallDisplayName=共识翻译 Agent
UninstallDisplayIcon={app}\ConsensusTranslationAgent\ConsensusTranslationAgent.exe
LicenseFile={#ProjectRoot}\LICENSE
InfoBeforeFile={#ProjectRoot}\docs\user_manual_zh.md
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#AppPayload}\*"; DestDir: "{app}\ConsensusTranslationAgent"; Excludes: "data\*"; Flags: ignoreversion recursesubdirs createallsubdirs
#ifdef RuntimePayload
Source: "{#RuntimePayload}\*"; DestDir: "{app}\runtime"; Excludes: "downloads\*,conda-pkgs\*,conda-envs\*,pip-cache\*,pip-cache-comet\*,python-packages-qt\*,temp\*,pyinstaller-cache\*,runtime-settings.json,runtime-verification.json,comet-env\Scripts\*.exe"; Flags: ignoreversion recursesubdirs createallsubdirs
#endif

[Icons]
Name: "{autoprograms}\共识翻译 Agent"; Filename: "{app}\ConsensusTranslationAgent\ConsensusTranslationAgent.exe"; WorkingDir: "{app}\ConsensusTranslationAgent"
Name: "{autodesktop}\共识翻译 Agent"; Filename: "{app}\ConsensusTranslationAgent\ConsensusTranslationAgent.exe"; WorkingDir: "{app}\ConsensusTranslationAgent"; Tasks: desktopicon

[Run]
Filename: "{app}\ConsensusTranslationAgent\ConsensusTranslationAgent.exe"; Description: "{cm:LaunchProgram,共识翻译 Agent}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\ConsensusTranslationAgent\data\temp"
