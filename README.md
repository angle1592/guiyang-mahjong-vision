# 贵阳捉鸡麻将识牌助手

面向 Windows 的本地麻将识牌与弃牌建议工具。程序捕获当前电脑上的“多乐贵阳捉鸡麻将”微信小程序窗口，识别手牌，并通过置顶小窗显示建议。

> 本工具只提供识别和建议，不会自动点击、代打、发送消息或执行任何账号操作。

## 功能

- 固定窗口区域实时截图与 14 张手牌定位
- 基于本地模板的万、筒、条识别
- 多帧稳定与低置信度拒绝，减少动画和误识别干扰
- 贵阳捉鸡麻将弃牌建议
- Tkinter 置顶提示窗口
- 支持运行时补充牌面模板
- 支持打包为免安装的 Windows 便携版

## 使用便携版

便携版位于本地构建产物：

```text
guiyang-mahjong-vision/dist/贵阳麻将识牌助手/
```

1. 打开微信小程序“多乐贵阳捉鸡麻将”，保持游戏窗口可见。
2. 保持 Windows 显示缩放和小程序窗口尺寸与采集模板时一致。
3. 双击 `贵阳麻将识牌助手.exe`。

复制到其他电脑时必须复制整个 `贵阳麻将识牌助手` 文件夹。不要单独移动 EXE，也不要删除 `_internal/`、`config.json`、`templates/` 或 `启动说明.txt`。

仓库默认不提交 `dist/`，需要在本机按下文重新构建。

## 从源码启动

要求：

- Windows 10/11
- Python 3.11 或更高版本
- [uv](https://docs.astral.sh/uv/)

在仓库根目录运行：

```powershell
cd .\guiyang-mahjong-vision
uv sync --extra test --extra build
uv run mahjong-vision
```

也可以使用 pip：

```powershell
cd .\guiyang-mahjong-vision
python -m pip install -e ".[test]"
mahjong-vision
```

## 构建 EXE

```powershell
cd .\guiyang-mahjong-vision
.\build-exe.ps1
```

构建脚本会安装构建依赖、调用 PyInstaller，并把运行所需配置与模板复制到：

```text
dist/贵阳麻将识牌助手/
```

## 配置与模板

`guiyang-mahjong-vision/config.json` 保存：

- 目标窗口标题
- 手牌区域坐标、牌槽尺寸和间距
- 模板匹配阈值
- 识别帧率与稳定帧数
- 弃牌建议权重

公开牌区域的裁剪与调试流程见 [公开牌区域校准流程](guiyang-mahjong-vision/docs/visible-region-calibration.md)。

模板位于 `guiyang-mahjong-vision/templates/`，按 `1m`、`2p`、`3s` 等牌面标签分目录保存。其中 `m`、`p`、`s` 分别表示万、筒、条。

当前参数针对固定的微信小程序布局调优。窗口缩放、显示缩放、遮挡、动画中间帧或坐标变化都可能导致拒绝识别，需要重新校准或补充模板。

## 测试

```powershell
cd .\guiyang-mahjong-vision
$base = Join-Path $env:TEMP ("guiyang-mahjong-tests-" + [guid]::NewGuid().ToString("N"))
uv run python -m pytest -q --basetemp $base
```

回放测试数据使用 `samples/manifest.json` 描述截图和对应的 14 张牌标签。加入标注截图后可运行：

```powershell
uv run python -m pytest tests/test_replay.py -v
```

## 项目结构

```text
guiyang-mahjong-vision/
├── src/mahjong_vision/
│   ├── app.py          # 应用生命周期与实时识别状态
│   ├── capture.py      # Win32/MSS 截图与牌槽检测
│   ├── templates.py    # 模板持久化与匹配
│   ├── recognizer.py   # 手牌识别与多帧稳定
│   ├── advisor.py      # 弃牌建议逻辑
│   └── overlay.py      # Tkinter 置顶界面
├── templates/          # 已标注牌面模板
├── tests/              # 单元测试与回放测试
├── config.json         # 当前布局配置
└── build-exe.ps1       # Windows 便携版构建脚本
```

## 当前限制

- 仅支持 Windows。
- 第一版针对当前微信小程序窗口标题、尺寸和牌槽布局。
- 模板集主要覆盖万、筒、条；识别效果取决于实际牌面样式与模板完整度。
- 建议逻辑用于辅助判断，不能保证最优结果。
