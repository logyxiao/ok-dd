param(
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $Root

python -m pip install --upgrade pyinstaller

$addDataData = "data;data"
$addDataAssets = "assets;assets"
$addDataWeb = "web;web"
$addIconPng = "icon.png;."

python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name OK-DingTalk `
    --icon icon.ico `
    --add-data $addDataData `
    --add-data $addDataAssets `
    --add-data $addIconPng `
    main.py

python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name OK-DingTalk-Panel `
    --icon icon.ico `
    --add-data $addDataData `
    --add-data $addDataWeb `
    --add-data $addIconPng `
    scripts\dingtalk_gui.py

python -m PyInstaller `
    --noconfirm `
    --clean `
    --console `
    --name OK-DingTalk-Auto `
    --icon icon.ico `
    --add-data $addDataData `
    --add-data $addIconPng `
    scripts\dingtalk_offwork_sequence.py

Write-Host "已构建可执行程序目录："
Write-Host "  $Root\dist\OK-DingTalk"
Write-Host "  $Root\dist\OK-DingTalk-Panel"
Write-Host "  $Root\dist\OK-DingTalk-Auto"

if ($SkipInstaller) {
    exit 0
}

$iscc = Get-Command iscc -ErrorAction SilentlyContinue
if (-not $iscc) {
    Write-Warning "未检测到 Inno Setup 或 iscc.exe 不在 PATH。请安装 Inno Setup 6 后重新运行。"
    exit 0
}

& $iscc.Source "$Root\installer\OK-DingTalk.iss"
Write-Host "安装包输出：$Root\release\OK-DingTalk-setup.exe"
