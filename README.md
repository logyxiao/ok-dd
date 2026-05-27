# OK-DingTalk

基于 ADB、scrcpy、OpenCV 模板识别和 Web 面板的钉钉打卡自动化工具。

当前主入口是 Web 面板。macOS 上通过 ADB 直接截图和点击手机屏幕；Windows 上保留 scrcpy 窗口截图、计划任务和 ok-script 相关兼容入口。

请确保你了解并遵守所在组织关于考勤、自动化工具和设备使用的规则。使用本工具产生的后果由使用者自行承担。

## 功能

- 打开钉钉并执行上班或下班打卡流程。
- 执行前检查手机是否息屏或锁屏，必要时唤醒并尝试普通上滑解锁。
- 使用 OpenCV 模板识别等待目标出现后再点击，避免页面未加载完成时提前点击。
- 支持多尺度模板匹配，适配 Windows/scrcpy 截图和 macOS/ADB 原始截图之间的分辨率差异。
- Web 面板提供仪表盘、执行控制、测试步骤、自动计划、模板识别和操作日志。
- 支持中国工作日判断，跳过普通周末和节假日，覆盖调休上班日。
- macOS 自动计划使用 `launchd`，Windows 自动计划使用计划任务。

## 环境要求

- Python 3.12
- ADB 可在命令行执行：`adb devices`
- scrcpy 可在命令行执行：`scrcpy`
- Android 手机已开启 USB 调试，并允许当前电脑调试

macOS 推荐使用 Homebrew。第一次放到一台新的 Mac 上时，优先运行项目内置初始化脚本：

```bash
./scripts/bootstrap_macos.sh
```

它会检查并安装/配置：

- `python@3.12`
- `android-platform-tools`
- `scrcpy`
- 项目虚拟环境 `.venv`
- Python 依赖
- 启动脚本执行权限

也可以手动安装：

```bash
brew install python@3.12 android-platform-tools scrcpy
/opt/homebrew/bin/python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
```

`ok-script` 和 `pywin32` 只在 Windows 安装。macOS 默认使用 Web 面板和 ADB 自动化路径。

## 启动面板

macOS：

```bash
./start-panel.command
```

`start-panel.command` 会自动使用项目内 `.venv`。如果 `.venv` 不存在或依赖缺失，会尝试调用 `scripts/bootstrap_macos.sh` 修复。

也可以直接运行：

```bash
.venv/bin/python scripts/dingtalk_gui.py
```

如果终端或启动器对中文文件名编码异常，使用 `start-panel.command` 或 `start-panel.sh`，不要使用中文 `.command` 文件名。

Windows：

```powershell
python scripts\dingtalk_gui.py
```

或双击：

```text
启动钉钉打卡面板.cmd
```

启动后打开：

```text
http://127.0.0.1:8765/
```

## 发给别人 Mac 使用

### 从 Git 克隆后启动

如果对方的 Mac 已经配置过 GitHub SSH key，可以用 SSH 克隆：

```bash
git clone git@github.com:logyxiao/ok-dd.git
cd ok-dd
./scripts/bootstrap_macos.sh
./start-panel.command
```

如果没有配置 SSH key，使用 HTTPS 克隆：

```bash
git clone https://github.com/logyxiao/ok-dd.git
cd ok-dd
./scripts/bootstrap_macos.sh
./start-panel.command
```

第一次运行时，`bootstrap_macos.sh` 会检查 Homebrew、Python 3.12、ADB、scrcpy，并创建 `.venv` 安装依赖。初始化完成后，连接 Android 手机，开启 USB 调试，并在手机弹窗中允许当前电脑调试。

如果 macOS 提示脚本没有执行权限，运行：

```bash
chmod +x scripts/bootstrap_macos.sh scripts/doctor_macos.py start-panel.command start-panel.sh
```

如果启动失败，先运行诊断：

```bash
./scripts/doctor_macos.py
```

诊断里最常见的问题是 `adb devices` 没有设备或显示 `unauthorized`。这通常需要重新插拔手机、打开 USB 调试，或在手机上重新允许当前电脑。

建议交付前确认项目目录里包含这些内容：

```text
assets/templates/
data/china_workdays_2026.json
scripts/bootstrap_macos.sh
scripts/doctor_macos.py
start-panel.command
requirements.txt
web/
src/
```

对方拿到项目后：

1. 解压或克隆项目到任意目录。
2. 双击 `start-panel.command`，或在终端运行 `./start-panel.command`。
3. 如果是第一次运行，脚本会初始化 `.venv` 并安装依赖。
4. 连接 Android 手机，开启 USB 调试，并在手机弹窗中允许当前电脑。
5. 打开 `http://127.0.0.1:8765/`。

如果启动失败，运行诊断：

```bash
./scripts/doctor_macos.py
```

常见迁移问题：

- 没有 Homebrew：先安装 <https://brew.sh/>。
- `adb devices` 无设备：检查 USB 线、USB 调试和手机授权弹窗。
- 显示 `unauthorized`：在手机上重新允许当前电脑调试。
- 模板相似度低：在新手机/新分辨率下重新截图并裁剪模板。
- 自动计划不触发：在 Web 面板“自动计划”页重新保存一次计划，让 launchd 生成当前 Mac 的 plist。

## 推荐测试顺序

进入 Web 面板左侧的“测试步骤”。

1. 选择 `下班打卡` 或 `上班打卡`。
2. 点击 `0. 检查 / 解锁屏幕`。
3. 点击 `1. 打开钉钉`。
4. 点击 `截图当前页面`，确认面板显示的是手机当前画面。
5. 对第一个流程步骤点击 `只识别`。
6. 相似度正常后，再点击 `识别并点击`。
7. 逐步测试后续步骤。

`只识别` 不会点击手机。`识别并点击` 会真实点击手机。

如果手机有密码、人脸或指纹锁，脚本不会绕过安全锁。它只会尝试普通亮屏和上滑解锁；如果仍然锁屏，需要手动解锁后再继续。

## 当前流程

执行脚本会先做通用准备：

1. 保持电脑唤醒。
2. 检查手机屏幕状态。
3. 如果息屏，发送 `WAKEUP`。
4. 如果是普通滑动锁屏，尝试上滑解锁。
5. 如果仍然锁屏，停止并提示手动解锁。
6. 打开钉钉。
7. 根据模板识别逐步点击。
8. 成功后关闭钉钉并锁定手机屏幕。

上班打卡步骤：

```text
1. 打开上班打卡入口
2. 点击打卡上班（如果进入提醒详情页，也会识别“立即打卡”）
3. 点击外勤打卡上班
4. 确认上班打卡成功
```

下班打卡步骤：

```text
1. 打开下班打卡入口
2. 点击打卡下班
3. 点击外勤打卡下班
4. 确认下班打卡成功
```

最近钉钉页面有两个变化已经兼容：

- 上班提醒可能先进入“打卡提醒”详情页，脚本会额外识别 `立即打卡` 按钮。
- 下班成功页新版文案样式与旧模板有差异，脚本会同时识别两套成功页模板。

如果运行中遇到短暂断连、黑屏或 `adb: no devices/emulators found`，脚本会先自动重试并尝试重新唤醒设备、拉起钉钉，再继续执行。

## 命令行执行

只检查今天是否会执行，不打开钉钉、不点击：

```bash
.venv/bin/python scripts/dingtalk_offwork_sequence.py --dry-run --mode evening
```

按中国工作日判断执行下班流程：

```bash
.venv/bin/python scripts/dingtalk_offwork_sequence.py --workday-only --mode evening
```

执行上班流程：

```bash
.venv/bin/python scripts/dingtalk_offwork_sequence.py --workday-only --mode morning
```

如果钉钉已经打开：

```bash
.venv/bin/python scripts/dingtalk_offwork_sequence.py --mode evening --no-open-dingtalk
```

如果不想强制停止并重开钉钉：

```bash
.venv/bin/python scripts/dingtalk_offwork_sequence.py --mode evening --no-fresh
```

## 模板识别

模板目录：

```text
assets/templates/
```

当前模板文件：

```text
morning_work_notice.png
morning_clock_button.png
morning_field_clock_button.png
morning_success_text.png
work_notice.png
offwork_button.png
field_offwork_button.png
offwork_success_text.png
```

Web 面板的“模板识别”页可以上传、测试和点击模板。

Web 面板的“测试步骤”页更适合按正式流程调试。每一步都会显示：

- 是否识别成功
- 相似度
- 命中的缩放倍数
- 相对坐标
- 实际屏幕坐标

如果从 Windows 换到 macOS，旧模板可能因为截图分辨率变化而相似度降低。项目已启用多尺度匹配，会在 `0.40x` 到 `2.00x` 之间寻找最佳缩放。若最佳相似度仍很低，通常说明当前手机页面不对，或需要用当前截图重新裁剪模板。

建议重新制作模板的流程：

1. 在“测试步骤”中点击 `截图当前页面`。
2. 确认截图里包含目标按钮或成功文字。
3. 到截图目录找到当前截图。
4. 裁剪目标区域，保存为对应模板文件。
5. 回到面板点击 `只识别` 测试相似度。

## 自动计划

Web 面板“自动计划”页可以设置早上和晚上两个目标时间。

macOS 使用 `launchd`，面板会写入：

```text
~/Library/LaunchAgents/com.ok-dingtalk.morning.plist
~/Library/LaunchAgents/com.ok-dingtalk.evening.plist
```

Windows 使用计划任务。

项目内置 `data/china_workdays_2026.json`，用于判断 2026 年中国工作日、法定节假日和调休上班日。自动计划可以每天触发，但实际点击由脚本内的 `--workday-only` 决定。

## 日志和截图

执行状态：

```text
logs/dingtalk_state.json
logs/dingtalk_actions.jsonl
```

运行日志：

```text
logs/
```

截图：

```text
screenshots/
```

模板：

```text
assets/templates/
```

Web 面板左侧工具区可以直接打开这些目录。

## macOS 和 Windows 差异

macOS：

- 截图：`adb exec-out screencap -p`
- 点击：`adb shell input tap`
- 保持唤醒：`caffeinate`
- 自动计划：`launchd`
- 推荐入口：Web 面板

Windows：

- 截图：scrcpy 窗口捕获
- 点击：Windows 鼠标事件
- 保持唤醒：Windows execution state
- 自动计划：Windows 计划任务
- 可继续使用 ok-script / PyInstaller 打包链路

## ok-script 和打包

项目仍保留 ok-script 相关入口：

```text
main.py
main_debug.py
config.py
pyappify.yml
```

Windows 主 GUI：

```powershell
python main.py
```

Windows 本地构建：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_installer.ps1 -SkipInstaller
```

生成安装包需要 Inno Setup 6，并确保 `iscc.exe` 在 `PATH`：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_installer.ps1
```

macOS 当前不建议使用 `main.py` 作为主入口，因为 ok-script 依赖链包含 Windows 专用组件。macOS 请使用 Web 面板。

## 常见问题

### `adb devices` 没有设备

检查 USB 调试是否开启，手机上是否弹出并允许了当前电脑调试。

```bash
adb devices
```

如果显示 `unauthorized`，在手机上重新确认调试授权。

### 模板相似度很低

先在“测试步骤”中截图当前页面，确认手机真的停在目标页面。如果页面正确但相似度仍低，重新裁剪当前截图里的按钮或文字作为模板。

### 点击位置不对

优先使用模板识别，不建议长期依赖固定坐标。测试步骤会显示相对坐标和实际屏幕坐标，可以用它判断命中区域是否正确。

### 手机仍然锁屏

脚本只尝试普通亮屏和上滑解锁。存在密码、人脸或指纹锁时，需要手动解锁。
