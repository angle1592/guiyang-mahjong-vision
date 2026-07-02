# 公开牌区域校准流程

本文档用于校准 `config.json` 中的 `visible_regions`，让助手可以从真实麻将窗口截图中裁剪牌河、副露和其他公开牌区域，并把识别结果转换为 `visible_counts` 参与建议计算。

## 当前能力边界

当前流程只做视觉调试和坐标校准：

- 读取当前麻将窗口截图。
- 按 `visible_regions` 裁剪公开牌 slot。
- 使用现有 `TemplateStore.match()` 识别每个 slot。
- 保存调试截图和 `visible-report.json`。

当前流程不做：

- 自动点击。
- 自动出牌。
- 自动控制游戏或账号。
- 自动推断完整桌面布局。
- 提交 `debug/` 目录中的截图或诊断文件。

## 前置条件

在 Windows 上运行，并确保麻将窗口处于可见状态。

从嵌套项目目录执行命令：

```powershell
cd guiyang-mahjong-vision
uv sync --extra test --extra build
```

确认 `config.json` 中的 `window_title` 能匹配目标窗口标题。

## 运行调试脚本

默认输出到 `debug/visible/`：

```powershell
uv run python scripts/debug-visible-regions.py
```

指定输出目录：

```powershell
uv run python scripts/debug-visible-regions.py --output debug/visible
```

脚本会生成类似文件：

```text
debug/visible/frame.png
debug/visible/discards_0_slot_00.png
debug/visible/melds_0_slot_00.png
debug/visible/revealed_0_slot_00.png
debug/visible/visible-report.json
```

`debug/` 已在嵌套项目 `.gitignore` 中忽略，不要手动提交这些截图或报告。

## 调试输出怎么看

### 1. 查看 frame.png

先打开：

```text
debug/visible/frame.png
```

确认它是当前麻将窗口截图。如果截图不对，优先检查：

- 麻将窗口是否打开。
- `window_title` 是否正确。
- 窗口是否被遮挡或最小化。
- 缩放比例是否稳定。

### 2. 查看 slot 裁剪图

打开这些文件：

```text
debug/visible/discards_0_slot_00.png
debug/visible/discards_0_slot_01.png
debug/visible/melds_0_slot_00.png
```

目标是每张裁剪图尽量只包含一张完整公开牌。

常见问题：

| 现象 | 可能原因 | 调整项 |
| --- | --- | --- |
| 裁到牌的左半边 | x 太小或 stride 不准 | 增大 x，或调整 stride |
| 裁到牌的右半边 | x 太大 | 减小 x |
| 牌上下被切掉 | y、slot_height 不准 | 调整 y 或 slot_height |
| 两张牌挤在一个 slot | slot_width 太大或 stride 太小 | 减小 slot_width，增大 stride |
| slot 中没有牌 | x/y 或 count 不准 | 调整 x/y/count |

### 3. 查看 visible-report.json

打开：

```text
debug/visible/visible-report.json
```

每个 slot 会包含：

```json
{
  "region": 0,
  "slot": 0,
  "image": "discards_0_slot_00.png",
  "label": "1m",
  "accepted": true,
  "score": 0.95,
  "runner_up_score": 0.1
}
```

重点看：

- `accepted` 是否为 `true`。
- `label` 是否和裁剪图中的牌一致。
- `score` 是否明显高于 `runner_up_score`。

如果裁剪图正确但识别不准，优先检查模板质量和 `matching.threshold` / `matching.min_margin`，不要先改坐标。

## visible_regions 配置格式

`visible_regions` 分为三类：

```json
"visible_regions": {
  "discards": [],
  "melds": [],
  "revealed": []
}
```

每个 region 的格式：

```json
{
  "x": 100,
  "y": 260,
  "slot_width": 42,
  "slot_height": 58,
  "stride": 44,
  "count": 10
}
```

字段含义：

| 字段 | 含义 |
| --- | --- |
| x | 第一个 slot 左上角 x 坐标 |
| y | 第一个 slot 左上角 y 坐标 |
| slot_width | 每个 slot 的裁剪宽度 |
| slot_height | 每个 slot 的裁剪高度 |
| stride | 相邻 slot 左上角的水平间距 |
| count | 这个 region 中要裁剪的 slot 数量 |

当前 region 是水平排列模型。如果实际区域不是水平排列，先拆成多个 region，不要在一个 region 里硬套。

## 推荐校准顺序

### 第一步：只校准一个最明显的牌河区域

先从自己的牌河或最容易定位的一排公开牌开始：

```json
"visible_regions": {
  "discards": [
    {
      "x": 100,
      "y": 260,
      "slot_width": 42,
      "slot_height": 58,
      "stride": 44,
      "count": 10
    }
  ],
  "melds": [],
  "revealed": []
}
```

运行：

```powershell
uv run python scripts/debug-visible-regions.py
```

查看 `discards_0_slot_*.png`，反复调整 `x/y/slot_width/slot_height/stride/count`。

### 第二步：增加副露区域

`melds` 每个 region 的 `count` 必须是 `3` 或 `4`。

示例：

```json
"visible_regions": {
  "discards": [
    {
      "x": 100,
      "y": 260,
      "slot_width": 42,
      "slot_height": 58,
      "stride": 44,
      "count": 10
    }
  ],
  "melds": [
    {
      "x": 520,
      "y": 180,
      "slot_width": 42,
      "slot_height": 58,
      "stride": 44,
      "count": 3
    }
  ],
  "revealed": []
}
```

如果副露之间间距不一致，用多个 `melds` region：

```json
"melds": [
  {"x": 520, "y": 180, "slot_width": 42, "slot_height": 58, "stride": 44, "count": 3},
  {"x": 680, "y": 180, "slot_width": 42, "slot_height": 58, "stride": 44, "count": 4}
]
```

### 第三步：增加其他 revealed 区域

`revealed` 用于其他公开牌来源。没有稳定用途时保持空数组。

## 什么时候不要改默认 config.json

如果没有稳定的真实窗口截图和多次校准结果，不建议直接修改默认 `config.json`。

更稳的做法是只在文档或本地配置中保留示例：

```json
"visible_regions": {
  "discards": [],
  "melds": [],
  "revealed": []
}
```

等真实坐标稳定后，再单独开 PR 更新默认配置或提供 `config.visible.example.json`。

## 校准检查清单

合并真实坐标前，至少确认：

- `frame.png` 是目标麻将窗口。
- 每个 `*_slot_*.png` 基本只包含一张完整牌。
- `visible-report.json` 中主要 slot 的 `accepted` 为 `true`。
- `label` 和裁剪图一致。
- 多次运行后没有旧 slot 图片残留。
- `debug/` 没有被提交。
- 没有加入自动点击、自动出牌或游戏控制逻辑。

## Codex review request

审查本流程时请重点检查：

1. 文档步骤是否和 `scripts/debug-visible-regions.py` 当前行为一致。
2. `visible_regions` 示例是否符合 `load_config()` 的校验规则。
3. 是否明确提醒不要提交 `debug/` 截图和诊断文件。
4. 是否明确避免自动点击、自动出牌、账号或游戏控制行为。
5. 是否需要补充 Windows 路径、缩放比例、模板匹配阈值相关说明。
