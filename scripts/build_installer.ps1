# ZenClean 自动化打包流水线脚本 (PowerShell)

$ProjectRoot = Resolve-Path "$PSScriptRoot\.." | Select-Object -ExpandProperty Path
$ISCCPath = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
$ISSFile = Join-Path $ProjectRoot "zenclean.iss"
$SpecFile = Join-Path $ProjectRoot "zenclean.spec"

Write-Host "===========================" -ForegroundColor Cyan
Write-Host " 🚀 启动 ZenClean 打包流水线 " -ForegroundColor Cyan
Write-Host "===========================" -ForegroundColor Cyan

Write-Host "`n[1/3] 清理旧的构建文件..." -ForegroundColor Yellow
$OldDist = Join-Path $ProjectRoot "dist"
$OldBuild = Join-Path $ProjectRoot "build"
$OldInstaller = Join-Path $ProjectRoot "installer"

if (Test-Path $OldDist) { Remove-Item -Recurse -Force $OldDist }
if (Test-Path $OldBuild) { Remove-Item -Recurse -Force $OldBuild }
if (Test-Path $OldInstaller) { Remove-Item -Recurse -Force $OldInstaller }
Write-Host "清理完毕。" -ForegroundColor Green

Write-Host "`n[2/3] 执行 PyInstaller 生成独立程序集..." -ForegroundColor Yellow
Set-Location -Path $ProjectRoot
pyinstaller --clean $SpecFile

if ($LASTEXITCODE -ne 0) {
    Write-Host "X PyInstaller 打包失败！" -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host "PyInstaller 成功生成 dist/ZenClean。" -ForegroundColor Green

Write-Host "`n[3/3] 正在挂载 Inno Setup 编译器..." -ForegroundColor Yellow
$ISCCExists = Test-Path $ISCCPath
if (-Not $ISCCExists) {
    Write-Host "X 未检测到 Inno Setup 安装目录 ($ISCCPath)。请确保已安装 Inno Setup 6。" -ForegroundColor Red
    Write-Host "跳过最后一步安装包生成。您可以在 dist/ZenClean 找到绿色免安装版。" -ForegroundColor Yellow
    exit 0
}

& $ISCCPath $ISSFile

if ($LASTEXITCODE -ne 0) {
    Write-Host "X Inno Setup 编译失败！" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "`n🎉 打包流水线全部完成！" -ForegroundColor Green
$OutDir = Join-Path $ProjectRoot 'installer'
Write-Host "成品安装包已输出至: $OutDir" -ForegroundColor Cyan
