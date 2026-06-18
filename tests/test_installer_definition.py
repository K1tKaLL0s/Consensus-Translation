from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_installer_supports_directory_and_desktop_shortcut():
    source = (
        ROOT / "packaging" / "installer" / "ConsensusTranslationAgent.iss"
    ).read_text(encoding="utf-8")

    assert "PrivilegesRequired=lowest" in source
    assert "DefaultDirName={localappdata}\\Programs\\ConsensusTranslationAgent" in source
    assert "DisableDirPage=no" in source
    assert "UsePreviousAppDir=yes" in source
    assert 'Name: "desktopicon"' in source
    assert 'Name: "{autodesktop}\\共识翻译 Agent"' in source
    assert 'Filename: "{app}\\ConsensusTranslationAgent\\ConsensusTranslationAgent.exe"' in source
    assert 'Source: "{#AppPayload}\\*"; DestDir: "{app}\\ConsensusTranslationAgent"' in source
    assert 'Excludes: "data\\*"' in source
    assert 'Source: "{#RuntimePayload}\\*"; DestDir: "{app}\\runtime"' in source
    assert 'Excludes: "downloads\\*,conda-pkgs\\*,conda-envs\\*,pip-cache\\*,pip-cache-comet\\*,python-packages-qt\\*,temp\\*,pyinstaller-cache\\*,runtime-settings.json,runtime-verification.json,comet-env\\Scripts\\*.exe"' in source
    assert "DiskSpanning=yes" in source


def test_installer_records_license_privacy_and_uninstall_metadata():
    source = (
        ROOT / "packaging" / "installer" / "ConsensusTranslationAgent.iss"
    ).read_text(encoding="utf-8")

    assert "LicenseFile={#ProjectRoot}\\LICENSE" in source
    assert "InfoBeforeFile={#ProjectRoot}\\docs\\user_manual_zh.md" in source
    assert "UninstallDisplayName=共识翻译 Agent" in source
    assert "UninstallDisplayIcon={app}\\ConsensusTranslationAgent\\ConsensusTranslationAgent.exe" in source
    assert "ChangesAssociations=no" in source
    assert "ArchitecturesInstallIn64BitMode=x64compatible" in source


def test_build_installer_discovers_inno_setup_c_then_e_and_builds_channels():
    script = (ROOT / "build_installer.ps1").read_text(encoding="utf-8")

    assert "-Channel" in script
    assert "standard" in script
    assert "full" in script
    assert "C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe" in script
    assert "E:\\Antigravity\\resources\\app\\node_modules\\innosetup\\bin\\ISCC.exe" in script
    assert script.index("C:\\Program Files (x86)") < script.index("E:\\Antigravity")
    assert "packaging\\installer\\ConsensusTranslationAgent.iss" in script
    assert "/DAppPayload=" in script
    assert "/DOutputDir=" in script
    assert "/DChannel=" in script
    assert "/DRuntimePayload=" in script
