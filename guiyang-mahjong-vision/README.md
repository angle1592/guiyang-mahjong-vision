# 贵阳捉鸡麻将识牌助手

本程序只识别当前电脑上的“多乐贵阳捉鸡麻将”固定窗口，并在置顶小窗显示弃牌建议；它不会自动点击或代打。

## 安装

```powershell
uv sync --extra test
```

也可以使用 pip：

```powershell
python -m pip install -e ".[test]"
```

## 启动

1. 打开微信小程序并保持窗口可见。
2. 保持 Windows 显示缩放和小程序窗口尺寸不变。
3. 运行：

```powershell
mahjong-vision
```

如果使用 uv 环境：

```powershell
uv run mahjong-vision
```

## 配置坐标

`config.json` 中的 `hand.x` 和 `hand.y` 是第一张手牌左上角相对小程序窗口的位置；`slot_width`、`slot_height` 和 `stride` 定义固定牌槽。

第一版只支持固定窗口尺寸和固定牌槽。窗口缩放、遮挡、动画中间帧或坐标不匹配时，助手会拒绝给出建议。

## 模板

模板按 `templates/1m/`、`templates/2m/`、`templates/1p/`、`templates/1s/` 等目录保存。万、筒、条分别使用 `m`、`p`、`s`。每种牌可以保存多个普通、选中和高亮状态样本。

低置信度时助手不会给出建议。使用标注窗口保存正确标签后，下一帧即可使用新模板。

## 验证

```powershell
uv run python -m pytest -q --basetemp .pytest-local
```

## 回放数据格式

`samples/manifest.json`：

```json
[
  {
    "image": "hand-001.png",
    "labels": [
      "5m", "6m", "6m", "9m", "2s", "2s", "3s",
      "8s", "1p", "1p", "1p", "6p", "6p", "8s"
    ]
  }
]
```

加入标注截图后运行 `uv run python -m pytest tests/test_replay.py -v`，测试会检查单牌准确率与第 95 百分位延迟。
