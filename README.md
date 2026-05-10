# scrcpy daily automation

基于 `ok-script` 的 scrcpy 窗口自动化项目骨架。

当前第一步已经完成：

- 启动 `scrcpy` 并指定稳定窗口标题
- 等待并定位 scrcpy 窗口
- 获取窗口画面并保存到 `screenshots`
- 提供 `ok-script` GUI 入口，后续可以继续加入 OCR、找图、点击和每日任务

## 环境

本项目面向 Windows，并要求：

- Python 3.12
- `scrcpy` 可在命令行直接执行
- Android 设备已通过 USB 或 ADB 连接，且 `adb devices` 能看到设备

安装依赖：

```powershell
python -m pip install -r requirements.txt
```

## 第一步：启动 scrcpy 并截图

```powershell
python scripts\capture_scrcpy_once.py
```

默认窗口标题是 `OK Scrcpy Daily`。脚本会保存：

```text
screenshots\scrcpy_capture.png
```

如果需要自定义 scrcpy 参数：

```powershell
python scripts\capture_scrcpy_once.py --scrcpy-arg "--serial" --scrcpy-arg "DEVICE_SERIAL"
```

如果你已经手动打开了 scrcpy，也可以只按标题找窗口：

```powershell
python scripts\capture_scrcpy_once.py --no-start --title "你的 scrcpy 窗口标题"
```

## 打开钉钉并点击打卡区域

默认钉钉包名：

```text
com.alibaba.android.rimet
```

执行：

```powershell
python scripts\dingtalk_click_clock_region.py
```

脚本会依次执行：

1. 使用 ADB 打开钉钉。
2. 启动或连接标题为 `OK Scrcpy Daily` 的 scrcpy 窗口。
3. 截取完整画面到 `screenshots\dingtalk_full.png`。
4. 裁剪打卡候选区域到 `screenshots\dingtalk_clock_region.png`。
5. 使用 Windows 鼠标点击该区域中心。

默认打卡区域使用相对坐标：

```text
0.05,0.50,0.92,0.11
```

含义是：

```text
x,y,width,height
```

每个值都是相对于 scrcpy 画面的比例。比如要点击更靠下的区域：

```powershell
python scripts\dingtalk_click_clock_region.py --clock-box "0.05,0.62,0.90,0.10"
```

如果 scrcpy 已经打开：

```powershell
python scripts\dingtalk_click_clock_region.py --no-start-scrcpy
```

## 下班打卡单步坐标流程

如果已经确认坐标，可以直接运行下班打卡点击序列：

```powershell
python scripts\dingtalk_offwork_sequence.py
```

脚本会先用 ADB 强制停止并重新打开钉钉，尽量从干净状态进入首页，然后按 4 秒间隔依次点击：

```text
1. 打开打卡入口：0.650,0.150
2. 点击打卡下班：0.500,0.600
3. 点击外勤打卡下班：0.500,0.600
4. 点击外勤打卡：0.500,0.940
```

脚本会自动判断当前是否已经有 scrcpy 窗口：

```text
已有 scrcpy：直接复用已有窗口执行。
没有 scrcpy：自动启动新的 scrcpy 执行。
执行结束：只关闭本次脚本新启动的 scrcpy，不关闭你原本手动开的窗口。
```

如果钉钉已经打开，并且只想执行点击：

```powershell
python scripts\dingtalk_offwork_sequence.py --no-open-dingtalk
```

如果不想强制停止钉钉，只做普通启动：

```powershell
python scripts\dingtalk_offwork_sequence.py --no-fresh
```

## Web GUI 控制面板

启动 Web GUI：

```powershell
python scripts\dingtalk_gui.py
```

也可以直接双击项目根目录的：

```text
启动钉钉打卡面板.cmd
```

如果你的 Windows 已关联 `.pyw` 到 Python，也可以双击：

```text
dingtalk_gui.pyw
```

创建桌面快捷方式：

```powershell
python scripts\create_desktop_shortcut.py
```

GUI 支持：

```text
1. 左侧 Tab 菜单切换仪表盘、执行控制、自动计划、操作日志。
2. 查看今天是否已经成功执行。
3. 查看今天是否是中国工作日，以及今天自动任务会执行还是跳过。
4. 查看 Windows 计划任务的下次自动执行时间、上次运行时间和结果。
5. 点击“立即执行”手动运行下班打卡脚本。
6. 点击“只检查今天”进行 dry-run。
7. 设置早上和晚上两个自动执行时间，并安装/更新计划任务。
8. 删除自动执行计划任务。
9. 打开日志目录和截图目录。
10. 查看最近执行日志和实时命令输出。
```

执行状态和日志保存在：

```text
logs\dingtalk_state.json
logs\dingtalk_actions.jsonl
```

## 识别截图后点击

纯坐标点击可能在页面没加载完时提前点击。项目现在支持 OpenCV 模板识别：先等待按钮/入口图片出现在 scrcpy 画面里，再点击模板中心。

详细说明：

[docs/template_matching.md](</C:/Users/to/Documents/New project 3/docs/template_matching.md>)

主流程默认启用模板识别。如果模板不存在，会自动回退到原来的坐标点击。

默认模板文件名：

```text
assets\templates\work_notice.png
assets\templates\offwork_button.png
assets\templates\field_offwork_button.png
assets\templates\field_confirm_button.png
```

测试模板：

```powershell
python scripts\find_scrcpy_template.py assets\templates\work_notice.png
```

等待模板并点击：

```powershell
python scripts\click_scrcpy_template.py assets\templates\work_notice.png
```

## ok-script 主界面和安装包

项目现在按 `ok-wuthering-waves` 的发布形态整理：

```text
main.py              启动 ok-script 主 GUI
main_debug.py        启动调试 GUI
config.py           根目录配置入口，转发到 src.config
pyappify.yml        pyappify / GitHub Actions 发布配置
icon.png / icon.ico 应用图标
```

主 GUI：

```powershell
python main.py
```

在主 GUI 的一次性任务里运行：

```text
下班打卡序列
```

命令行自动执行第一个任务并退出的形态与 OK-WW 类似：

```powershell
python main.py -t 1 -e
```

如果 ok-script 当前版本没有接管这些参数，则使用稳定的自动执行入口：

```powershell
python scripts\dingtalk_offwork_sequence.py --workday-only
```

### 本地构建 exe

构建可运行 exe 目录：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_installer.ps1 -SkipInstaller
```

输出：

```text
dist\OK-DingTalk\OK-DingTalk.exe
dist\OK-DingTalk-Panel\OK-DingTalk-Panel.exe
dist\OK-DingTalk-Auto\OK-DingTalk-Auto.exe
```

生成安装包需要安装 Inno Setup 6，并确保 `iscc.exe` 在 `PATH`：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build_installer.ps1
```

安装包输出：

```text
release\OK-DingTalk-setup.exe
```

### GitHub Actions / pyappify 构建

`pyappify.yml` 参考 OK-WW 的发布配置，包含：

```text
China  -> main.py
Panel  -> scripts\dingtalk_gui.py
Debug  -> main_debug.py
```

`.github\workflows\build.yml` 使用：

```text
ok-oldking/pyappify-action@master
```

如果要正式发布，请先把 `pyappify.yml` 里的 `git_url` 改成你的仓库地址。

## 按中国工作日运行

项目内置了 `data\china_workdays_2026.json`，按国务院办公厅发布的 2026 年节假日和调休上班日判断是否应该运行。

每天都触发脚本，但只在中国工作日执行点击：

```powershell
python scripts\dingtalk_offwork_sequence.py --workday-only
```

测试某一天是否会运行：

```powershell
python scripts\dingtalk_offwork_sequence.py --workday-only --date 2026-05-09 --no-open-dingtalk
python scripts\dingtalk_offwork_sequence.py --workday-only --date 2026-05-10 --no-open-dingtalk
```

注册 Windows 计划任务。默认目标时间是早上 `09:00` 和晚上 `18:30`，脚本会提前 5 分钟触发，再随机等待 0 到 10 分钟，所以实际执行时间落在目标时间前后约 5 分钟：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_offwork_task.ps1
```

自定义时间和随机范围：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_offwork_task.ps1 -MorningTime 09:00 -EveningTime 18:30 -RandomWindowMinutes 5
```

计划任务每天运行两次，是否真正点击由脚本内的 `--workday-only` 判断决定。这样能覆盖普通周末、法定节假日，以及调休上班的周六/周日。

## ok-script 调试入口

```powershell
python main_debug.py
```

进入 GUI 后选择 scrcpy 窗口，运行 `抓取 scrcpy 画面` 任务。这个任务会调用 `ok-script` 的截图链路保存一张截图，后续每日任务可以继续写在 `src/tasks` 里。

也可以运行 `打开钉钉并点击打卡区域` 任务，它和命令行脚本使用同一套 ADB 打开、截图、裁剪、鼠标点击逻辑。

## 后续建议

下一步通常是：

1. 固定目标 App 的首页状态。
2. 为每日入口按钮或文字区域建立模板/OCR 检测。
3. 在任务里用 `wait_ocr`、`find_one`、`click_relative` 或 `click_box` 编排流程。
4. 加一个“只跑一次”的每日任务和必要的失败截图。
