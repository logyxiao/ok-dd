param(
    [string]$MorningTaskName = "DingTalk Morning Clock",
    [string]$EveningTaskName = "DingTalk Evening Clock",
    [string]$MorningTime = "09:00",
    [string]$EveningTime = "18:30",
    [int]$RandomWindowMinutes = 5
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Python = (Get-Command python).Source
$Script = Join-Path $Root "scripts\dingtalk_offwork_sequence.py"
$RandomDelayMinutes = $RandomWindowMinutes * 2
$MorningArguments = "`"$Script`" --workday-only --mode morning"
$EveningArguments = "`"$Script`" --workday-only --mode evening"

function Get-TriggerTime([string]$TargetTime, [int]$MinusMinutes) {
    return ([datetime]::ParseExact($TargetTime, "HH:mm", $null).AddMinutes(-$MinusMinutes)).ToString("HH:mm")
}

$MorningAction = New-ScheduledTaskAction -Execute $Python -Argument $MorningArguments -WorkingDirectory $Root
$EveningAction = New-ScheduledTaskAction -Execute $Python -Argument $EveningArguments -WorkingDirectory $Root
$MorningTrigger = New-ScheduledTaskTrigger -Daily -At (Get-TriggerTime $MorningTime $RandomWindowMinutes)
$EveningTrigger = New-ScheduledTaskTrigger -Daily -At (Get-TriggerTime $EveningTime $RandomWindowMinutes)
$MorningTrigger.RandomDelay = "PT$($RandomDelayMinutes)M"
$EveningTrigger.RandomDelay = "PT$($RandomDelayMinutes)M"
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -WakeToRun

Register-ScheduledTask `
    -TaskName $MorningTaskName `
    -Action $MorningAction `
    -Trigger $MorningTrigger `
    -Settings $Settings `
    -Description "在中国工作日早上目标时间前后随机执行钉钉打卡脚本。" `
    -Force

Register-ScheduledTask `
    -TaskName $EveningTaskName `
    -Action $EveningAction `
    -Trigger $EveningTrigger `
    -Settings $Settings `
    -Description "在中国工作日晚上目标时间前后随机执行钉钉打卡脚本。" `
    -Force

Write-Host "已注册计划任务：$MorningTaskName，目标时间：$MorningTime，Windows 随机延迟：PT$($RandomDelayMinutes)M"
Write-Host "已注册计划任务：$EveningTaskName，目标时间：$EveningTime，Windows 随机延迟：PT$($RandomDelayMinutes)M"
Write-Host "工作目录：$Root"
Write-Host "早上执行命令：$Python $MorningArguments"
Write-Host "晚上执行命令：$Python $EveningArguments"
