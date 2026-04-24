; ZenClean 安装包打包脚本 (Inno Setup)
; 此脚本将打包 PyInstaller 生成的 dist/ZenClean 目录

#define MyAppName "ZenClean 禅清"
#define MyAppVersion "0.1.7-beta"
#define MyAppPublisher "HW-DEM Team"
#define MyAppURL "https://github.com/hwdem"
#define MyAppExeName "ZenClean.exe"
#define MyIconName "icon.ico"

[Setup]
; 注：AppId 的值用于唯一标识此应用程序。
; 不要在其他应用程序中使用相同的 AppId 值。
; (你可以通过在 IDE 中点击工具 -> 生成 GUID 来生成新的 GUID。)
AppId={{D1A2B3C4-E5F6-7890-A1B2-C3D4E5F67890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
; 默认安装到 Program Files (x86) 或 Program Files
DefaultDirName={autopf}\ZenClean
; 默认开始菜单组名
DefaultGroupName={#MyAppName}
; 安装包输出目录
OutputDir=installer
; 安装包文件名
OutputBaseFilename=ZenClean_Setup_v{#MyAppVersion}
; 安装程序图标
SetupIconFile=assets\{#MyIconName}
; 压缩算法
Compression=lzma2/ultra64
SolidCompression=yes
; 最小支持系统 (Windows 10)
MinVersion=10.0
; 提示需要管理员权限安装 (UAC 标记)
PrivilegesRequired=admin
; 卸载程序图标
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; 注意：Source 路径需要根据你实际 PyInstaller 的输出路径调整
; 这里假设运行 Inno Setup 时，当前目录是项目根目录
Source: "dist\ZenClean\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\ZenClean\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; 开始菜单快捷方式
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
; 桌面快捷方式
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; 安装完成后提供运行选项
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; 卸载前确保程序已关闭 (尝试通过命令行终止)
Filename: "{cmd}"; Parameters: "/C taskkill /IM {#MyAppExeName} /F /T"; Flags: runhidden
