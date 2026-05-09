param(
    [string]$TaskName = "DingTalk Offwork Clock",
    [string]$Time = "18:05"
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = (Get-Command python).Source
$Script = Join-Path $Root "scripts\dingtalk_offwork_sequence.py"
$Arguments = "`"$Script`" --workday-only"

$Action = New-ScheduledTaskAction -Execute $Python -Argument $Arguments -WorkingDirectory $Root
$Trigger = New-ScheduledTaskTrigger -Daily -At $Time
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "在中国工作日运行钉钉下班打卡点击序列。" `
    -Force

Write-Host "已注册计划任务：$TaskName"
Write-Host "执行时间：$Time"
Write-Host "工作目录：$Root"
Write-Host "执行命令：$Python $Arguments"
