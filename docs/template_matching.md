# 模板识别点击

坐标点击容易在页面未加载完成时提前点击。更稳的方式是：

1. 先截取按钮或入口的一小块图片作为模板。
2. 脚本运行时循环截取 scrcpy 画面。
3. 只有当模板出现在画面中，并达到相似度阈值，才点击模板中心。

## 制作模板

先打开目标页面，保存完整截图：

```powershell
python scripts\capture_scrcpy_once.py --no-start --output screenshots\step.png
```

然后用系统图片工具或截图工具，从 `screenshots\step.png` 里裁剪目标按钮的小区域，保存到：

```text
assets\templates\
```

主流程默认会识别这些文件名：

```text
assets\templates\work_notice.png
assets\templates\offwork_button.png
assets\templates\field_offwork_button.png
assets\templates\field_confirm_button.png
```

如果某个模板不存在，该步骤会自动回退到原来的相对坐标点击。

## 测试模板是否能识别

```powershell
python scripts\find_scrcpy_template.py assets\templates\work_notice.png
```

识别成功会输出：

```text
找到模板：相似度=0.923
模板区域：x=..., y=..., width=..., height=...
中心相对坐标：0.6500,0.1500
```

## 等待模板并点击

```powershell
python scripts\click_scrcpy_template.py assets\templates\work_notice.png
```

可以调低或调高阈值：

```powershell
python scripts\click_scrcpy_template.py assets\templates\work_notice.png --threshold 0.82
```

## 主流程使用模板

默认启用模板识别：

```powershell
python scripts\dingtalk_offwork_sequence.py
```

每一步最多等待 25 秒。可以调整：

```powershell
python scripts\dingtalk_offwork_sequence.py --step-timeout 40 --template-threshold 0.84
```

临时关闭模板识别，回到纯坐标点击：

```powershell
python scripts\dingtalk_offwork_sequence.py --no-template
```

## 模板裁剪建议

- 尽量裁剪按钮文字、按钮图标或稳定的卡片区域。
- 不要把大面积空白、时间、红点数字、动态头像裁进去。
- 模板越稳定越好，尺寸不要太大。
- 如果识别不到，先用 `--threshold 0.80` 测试。
- 如果误识别，调高到 `0.90` 左右，或重新裁剪更独特的区域。
