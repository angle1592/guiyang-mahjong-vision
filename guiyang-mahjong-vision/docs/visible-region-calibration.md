# 公开牌区域校准流程

本文档用于校准 `config.json` 中的 `visible_regions`，让助手可以从真实麻将窗口截图中裁剪牌河、副露和其他公开牌区域，并把识别结果转换为 `visible_counts` 参与建议计算。

## 当前能力边界

当前流程只做视觉调试和坐标校准：

- 读取当前麻将窗口截图。
- 按 `visible_regions` 裁剪公开牌 slot。
- 使用现有 `TemplateStore.match()` 识别每个 slot。
- 保存调试截图和 `visible-report.json`。

当前流程不做任何交互控制，只提供识别、裁剪、诊断和建议相关信息。也不要提交 `debug/` 目录中的截图或诊断文件。

## 前置条件

在 Windows 上运行，并确保麻将窗口处于可见状态。

从嵌套项目目录执行命令：

```powershell
cd guiyang-mahjong-vision
uv sync --extra test --extra build
```

确认 `config.json` 中的 `window_title` 与目标窗口标题**精确匹配**。如果窗口标题有多余空格、不同后缀或不同语言，截图捕获可能找不到目标窗口。

## 坐标系说明

`visible_regions` 中的 `x` / `y` 不是桌面坐标。

它们是相对 `debug/visible/frame.png` 左上角的像素坐标，也就是麻将窗口客户区截图内的坐标。一般不包含窗口标题栏、窗口边框，也不包含桌面左上角偏移。

如果发生以下变化，需要重新校准：

- 麻将窗口尺寸变化。
- Windows 显示缩放变化。
- 微信小程序缩放或布局变化。
- 游戏皮肤、牌面样式或窗口 DPI 行为变化。
- 从窗口模式切换到其他显示方式。

校准时以 `frame.png` 为准：先在 `frame.png` 上估算公开牌左上角位置，再把该位置填入 `visible_regions`。

## 运行调试脚本

默认输出到 `debug/visible/`：

```powershell
uv run python scripts/debug-visible-regions.py
```

指定输出目录：

```powershell
uv run python scripts/debug-visible-regions.py --output debug/visible
```

如果路径包含空格，请加引号：

```powershell
uv run python scripts/debug-visible-regions.py --output "debug/visible captures"
```

指定配置文件：

```powershell
uv run python scripts/debug-visible-regions.py --config "config.json" --output "debug/visible"
```

注意：嵌套项目 `.gitignore` 默认只忽略 `debug/` 目录。如果把 `--output` 指向 `debug/` 之外的位置，例如桌面或 `captures/`，这些文件不一定会被 Git 忽略，提交前需要手动检查。

## 第一次运行时会生成什么

默认 `config.json` 中的 `visible_regions` 为空：

```json
"visible_regions": {
  "discards": [],
  "melds": [],
  "revealed": []
}
```

因此第一次运行调试脚本时，通常只会生成：

```text
debug/visible/frame.png
debug/visible/visible-report.json
```

此时不会生成 `discards_0_slot_00.png`、`melds_0_slot_00.png` 或其他 `*_slot_*.png`，因为还没有配置任何要裁剪的 region。

正确流程是：

1. 先运行脚本生成 `frame.png`。
2. 打开 `frame.png`，根据截图估算公开牌区域坐标。
3. 在 `config.json` 中填写至少一个 `visible_regions` region。
4. 重新运行脚本。
5. 第二次运行后才会出现对应的 `*_slot_*.png` 裁剪图。

## 调试输出怎么看

### 1. 查看 frame.png

先打开：

```text
debug/visible/frame.png
```

确认它是当前麻将窗口截图。如果截图不对，优先检查：

- 麻将窗口是否打开。
- `window_title` 是否与目标窗口标题精确匹配。
- 窗口是否被遮挡或最小化。
- 窗口尺寸和 Windows 显示缩放是否稳定。

### 2. 填写至少一个 region

根据 `frame.png` 估算最明显公开牌区域，例如自己的牌河。先只配置一个 region，不要一次配置所有玩家的区域。

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
  "melds": [],
  "revealed": []
}
```

保存 `config.json` 后重新运行：

```powershell
uv run python scripts/debug-visible-regions.py
```

### 3. 查看 slot 裁剪图

配置 region 并重新运行后，打开这些文件：

```text
debug/visible/discards_0_slot_00.png
debug/visible/discards_0_slot_01.png
debug/visible/melds_0_slot_00.png
```

实际会生成哪些 `*_slot_*.png`，取决于 `visible_regions` 中配置了哪些区域。

目标是每张裁剪图尽量只包含一张完整公开牌。

常见问题：

| 现象 | 可能原因 | 调整项 |
| --- | --- | --- |
| 裁到牌的左半边 | x 太小或 stride 不准 | 增大 x，或调整 stride |
| 裁到牌的右半边 | x 太大 | 减小 x |
| 牌上下被切掉 | y、slot_height 不准 | 调整 y 或 slot_height |
| 两张牌挤在一个 slot | slot_width 太大或 stride 太小 | 减小 slot_width，增大 stride |
| slot 中没有牌 | x/y 或 count 不准 | 调整 x/y/count |

### 4. 查看 visible-report.json

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

如果裁剪图正确但识别不准，优先补充公开牌模板或检查模板质量，不要先大幅降低匹配阈值。

## matching 阈值说明

`config.json` 中的 `matching` 控制模板匹配是否接受结果：

```json
"matching": {
  "threshold": 0.82,
  "min_margin": 0.04
}
```

含义：

| 字段 | 含义 |
| --- | --- |
| threshold | 最高匹配分数至少达到这个值才可能接受 |
| min_margin | 第一名分数必须比第二名至少高出这个差值 |

调试公开牌时，如果 `*_slot_*.png` 裁剪正确但 `accepted` 很少为 `true`，优先补充对应公开牌模板，或确认模板是否来自同一牌面样式。不要为了让结果通过而直接大幅降低 `threshold` 或 `min_margin`，否则会增加误识别风险。

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
| x | 第一个 slot 左上角在 `frame.png` 内的 x 坐标 |
| y | 第一个 slot 左上角在 `frame.png` 内的 y 坐标 |
| slot_width | 每个 slot 的裁剪宽度 |
| slot_height | 每个 slot 的裁剪高度 |
| stride | 相邻 slot 左上角的水平间距 |
| count | 这个 region 中要裁剪的 slot 数量 |

所有坐标和尺寸都使用像素。`x/y` 必须非负，`slot_width`、`slot_height`、`stride`、`count` 必须是正整数。

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

## 实测示例配置

仓库中的 `config.visible.example.json` 包含一次 Windows 实机校准得到的顶部中央第一排弃牌区域：

```json
{
  "x": 485,
  "y": 160,
  "slot_width": 34,
  "slot_height": 48,
  "stride": 34,
  "count": 6
}
```

该示例仅在以下环境中验证过裁剪几何：

- Mahjong 窗口客户区为 `896 × 552`。
- Windows 窗口 DPI 为 `120`，即 125% 显示缩放。
- `frame.png` 实际尺寸为 `1120 × 690`。
- 目标窗口完整可见且未被其他窗口遮挡。
- 区域对应顶部中央玩家牌河的第一排 6 个槽位。

可以用示例配置运行调试脚本：

```powershell
uv run python scripts/debug-visible-regions.py --config config.visible.example.json
```

实测中 6 个槽位均能完整裁出单张牌，没有明显切边或相邻牌串入；但现有手牌模板对这些公开牌的匹配结果为 `0/6 accepted`。因此该文件只用于坐标复现和继续采集公开牌模板，不能视为可直接启用的生产配置。

`WindowCapture` 捕获目标窗口所在的屏幕区域。若麻将窗口被 Chrome 等其他窗口遮挡，`frame.png` 会包含遮挡内容。运行调试脚本和实时识别时必须保持麻将窗口未最小化且不被遮挡。

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
- `x/y` 是相对 `frame.png` 左上角的坐标，不是桌面坐标。
- 每个 `*_slot_*.png` 基本只包含一张完整牌。
- `visible-report.json` 中主要 slot 的 `accepted` 为 `true`。
- `label` 和裁剪图一致。
- 多次运行后没有旧 slot 图片残留。
- 自定义输出目录不会误提交截图或诊断文件。
- `debug/` 没有被提交。
- 没有加入交互控制逻辑。

## Codex review request

审查本流程时请重点检查：

1. 文档步骤是否和 `scripts/debug-visible-regions.py` 当前行为一致。
2. `visible_regions` 示例是否符合 `load_config()` 的校验规则。
3. 是否明确说明默认空 `visible_regions` 第一次只生成 `frame.png` 和 `visible-report.json`。
4. 是否明确说明坐标系相对 `frame.png`，不是桌面坐标。
5. 是否明确提醒不要提交 `debug/` 截图和诊断文件。
6. 是否明确避免交互控制行为。
7. 是否需要补充 Windows 路径、缩放比例、模板匹配阈值相关说明。
