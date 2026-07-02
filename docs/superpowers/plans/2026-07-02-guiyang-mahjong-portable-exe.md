# Guiyang Mahjong Portable EXE Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a portable Windows folder that starts the Mahjong assistant by double-clicking `贵阳麻将识牌助手.exe`.

**Architecture:** PyInstaller builds a windowed `onedir` application. Source runs resolve resources from the project root, while frozen runs resolve editable `config.json` and `templates/` beside `sys.executable`; a PowerShell script builds and assembles the final distribution.

**Tech Stack:** Python 3.11+, PyInstaller 6, PowerShell 7/Windows PowerShell, pytest, Tkinter, OpenCV, MSS, pywin32

---

### Task 1: Resolve resources beside the frozen executable

**Files:**
- Modify: `guiyang-mahjong-vision/src/mahjong_vision/app.py`
- Modify: `guiyang-mahjong-vision/tests/test_app.py`

- [ ] **Step 1: Write failing runtime-root tests**

Add:

```python
from pathlib import Path
import sys

from mahjong_vision import app


def test_runtime_root_uses_project_root_when_not_frozen(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)

    assert app._runtime_root() == Path(app.__file__).resolve().parents[2]


def test_runtime_root_uses_executable_directory_when_frozen(
    monkeypatch,
    tmp_path,
):
    executable = tmp_path / "贵阳麻将识牌助手.exe"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(executable))

    assert app._runtime_root() == tmp_path
```

- [ ] **Step 2: Verify the new tests fail**

Run:

```powershell
$base = Join-Path (Get-Location) (".pytest-portable-red-" + [guid]::NewGuid().ToString("N"))
uv run python -m pytest tests/test_app.py -q --basetemp $base
```

Expected: FAIL because `_runtime_root` does not exist.

- [ ] **Step 3: Implement frozen and source path resolution**

Add to `app.py`:

```python
import sys


def _runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]
```

Change `main()` to:

```python
def main() -> None:
    project_root = _runtime_root()
```

- [ ] **Step 4: Run focused and full tests**

Run:

```powershell
$focused = Join-Path (Get-Location) (".pytest-portable-focused-" + [guid]::NewGuid().ToString("N"))
uv run python -m pytest tests/test_app.py -q --basetemp $focused
$all = Join-Path (Get-Location) (".pytest-portable-all-" + [guid]::NewGuid().ToString("N"))
uv run python -m pytest -q --basetemp $all
```

Expected: focused tests pass; full suite reports no failures.

- [ ] **Step 5: Commit**

```powershell
git add guiyang-mahjong-vision/src/mahjong_vision/app.py guiyang-mahjong-vision/tests/test_app.py
git commit -m "feat: resolve portable runtime resources"
```

### Task 2: Add a reproducible PyInstaller build

**Files:**
- Modify: `guiyang-mahjong-vision/pyproject.toml`
- Create: `guiyang-mahjong-vision/mahjong-vision.spec`
- Create: `guiyang-mahjong-vision/build-exe.ps1`
- Create: `guiyang-mahjong-vision/.gitignore`
- Create: `guiyang-mahjong-vision/启动说明.txt`

- [ ] **Step 1: Add the build dependency**

Extend `pyproject.toml`:

```toml
[project.optional-dependencies]
test = ["pytest>=8,<9"]
build = ["pyinstaller>=6.21,<7"]
```

- [ ] **Step 2: Add the PyInstaller spec**

Create `mahjong-vision.spec`:

```python
from pathlib import Path


root = Path(SPECPATH)
analysis = Analysis(
    [str(root / "src" / "mahjong_vision" / "app.py")],
    pathex=[str(root / "src")],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="贵阳麻将识牌助手",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
bundle = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    name="贵阳麻将识牌助手",
)
```

- [ ] **Step 3: Add the build script**

Create `build-exe.ps1`:

```powershell
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$bundle = Join-Path $root "dist\贵阳麻将识牌助手"

Push-Location $root
try {
    uv sync --extra test --extra build
    uv run pyinstaller --clean --noconfirm mahjong-vision.spec

    Copy-Item -LiteralPath "config.json" -Destination $bundle -Force
    Copy-Item -LiteralPath "templates" -Destination $bundle -Recurse -Force
    Copy-Item -LiteralPath "启动说明.txt" -Destination $bundle -Force

    $required = @(
        (Join-Path $bundle "贵阳麻将识牌助手.exe"),
        (Join-Path $bundle "config.json"),
        (Join-Path $bundle "templates"),
        (Join-Path $bundle "启动说明.txt")
    )
    foreach ($path in $required) {
        if (-not (Test-Path -LiteralPath $path)) {
            throw "Missing build output: $path"
        }
    }
    Write-Host "Portable build ready: $bundle"
}
finally {
    Pop-Location
}
```

- [ ] **Step 4: Add distribution instructions and ignores**

Create `启动说明.txt`:

```text
贵阳麻将识牌助手

1. 打开微信小程序“多乐贵阳捉鸡麻将”，保持窗口可见且尺寸不变。
2. 双击“贵阳麻将识牌助手.exe”。
3. 关闭置顶悬浮窗即可退出。

请勿删除或移动 _internal、config.json、templates 文件夹。
```

Create `.gitignore`:

```gitignore
.venv/
.pytest_cache/
.pytest-*/
__pycache__/
*.py[cod]
*.egg-info/
build/
dist/
runtime-*.log
debug-*.png
```

- [ ] **Step 5: Build the portable folder**

Run:

```powershell
.\build-exe.ps1
```

Expected: `dist/贵阳麻将识牌助手/贵阳麻将识牌助手.exe` and the three external resources exist.

- [ ] **Step 6: Commit**

```powershell
git add guiyang-mahjong-vision/pyproject.toml guiyang-mahjong-vision/uv.lock guiyang-mahjong-vision/mahjong-vision.spec guiyang-mahjong-vision/build-exe.ps1 guiyang-mahjong-vision/.gitignore guiyang-mahjong-vision/启动说明.txt
git commit -m "build: add portable Windows executable"
```

### Task 3: Document and verify the double-click release

**Files:**
- Modify: `guiyang-mahjong-vision/README.md`

- [ ] **Step 1: Document the primary launch path**

Add a first-choice section:

```markdown
## 双击启动

下载或复制整个 `贵阳麻将识牌助手` 文件夹，打开微信小程序后双击：

`贵阳麻将识牌助手.exe`

不要单独移动 EXE，也不要删除 `_internal/`、`config.json` 或 `templates/`。

开发者重新构建：

```powershell
.\build-exe.ps1
```
```

- [ ] **Step 2: Re-run the full test suite**

Run:

```powershell
$base = Join-Path (Get-Location) (".pytest-portable-final-" + [guid]::NewGuid().ToString("N"))
uv run python -m pytest -q --basetemp $base
```

Expected: no failures.

- [ ] **Step 3: Smoke-test the built executable**

Open `dist/贵阳麻将识牌助手/贵阳麻将识牌助手.exe` on Windows.

Expected:

- no console window appears;
- the “贵阳捉鸡识牌助手” overlay appears;
- when the Mahjong window is absent, status shows “等待麻将窗口”;
- closing the overlay ends the process.

- [ ] **Step 4: Commit**

```powershell
git add guiyang-mahjong-vision/README.md
git commit -m "docs: explain portable Windows launch"
```
