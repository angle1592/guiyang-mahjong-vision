# 贵阳麻将识牌助手便携 EXE 设计

日期：2026-07-02

## 目标

把现有 Windows 桌面程序构建为无需安装 Python、无需命令行即可双击启动的便携文件夹。

## 交付布局

构建产物位于：

```text
guiyang-mahjong-vision/dist/贵阳麻将识牌助手/
  贵阳麻将识牌助手.exe
  config.json
  templates/
  启动说明.txt
  _internal/
```

用户只需保留整个文件夹并双击 `贵阳麻将识牌助手.exe`。`_internal/` 是程序运行依赖，不要求用户操作。

## 技术方案

使用 PyInstaller 6 的 `onedir` 与 `windowed` 模式：

- `onedir` 避免单文件程序每次启动时解压，启动更快，也更少触发安全软件误报。
- `windowed` 隐藏命令行窗口，只显示 Tkinter 置顶悬浮窗。
- Python、OpenCV、NumPy、MSS、pywin32 和 Tkinter 运行依赖由 PyInstaller 收集到 `_internal/`。
- `config.json` 与 `templates/` 不嵌入 `_internal/`，而是由构建脚本复制到 EXE 同目录，方便继续调整坐标和替换模板。

## 运行时路径

源码运行时，程序继续使用 Python 项目根目录。

PyInstaller 冻结运行时，程序通过 `Path(sys.executable).resolve().parent` 得到 EXE 所在目录，并从该目录加载：

- `config.json`
- `templates/`

这保证用户从桌面快捷方式、资源管理器或任意当前目录启动时，资源路径都保持正确。

## 构建入口

新增 `build-exe.ps1`，负责：

1. 安装项目的 `build` 可选依赖；
2. 清理并运行 PyInstaller spec；
3. 将 `config.json`、`templates/` 和 `启动说明.txt` 复制到产物根目录；
4. 检查 EXE 和外部资源是否齐全。

构建过程生成的 `build/`、`dist/` 与 PyInstaller 缓存不提交 Git。

## 验证

- 单元测试覆盖源码模式与冻结模式的运行根目录。
- 现有全量测试必须继续通过。
- 构建后检查 EXE、配置、27 类模板目录和启动说明存在。
- 在 Windows 上双击 EXE，确认没有控制台窗口，悬浮窗可以打开并关闭。

## 边界

- 产物仅面向当前 Windows x64 电脑和当前微信小程序窗口布局。
- 不制作安装器、自动更新、代码签名或桌面快捷方式。
- 不把 debug 图片、运行日志、pytest 缓存或开发虚拟环境放入发行包。
