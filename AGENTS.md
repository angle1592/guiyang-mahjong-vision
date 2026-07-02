# Project Guidance

## Scope

These instructions apply to the entire repository.

The Git repository root contains planning documents and a nested Python project. Run application, test, and build commands from:

```text
guiyang-mahjong-vision/
```

## Setup and verification

Use PowerShell on Windows:

```powershell
cd guiyang-mahjong-vision
uv sync --extra test --extra build
```

Run the focused test for the area being changed, then the full suite:

```powershell
$base = Join-Path $env:TEMP ("guiyang-mahjong-tests-" + [guid]::NewGuid().ToString("N"))
uv run python -m pytest -q --basetemp $base
```

Build the portable Windows application with:

```powershell
.\build-exe.ps1
```

The distributable folder is:

```text
guiyang-mahjong-vision/dist/贵阳麻将识牌助手/
```

## Architecture

- `src/mahjong_vision/app.py`: application lifecycle and live recognition state.
- `src/mahjong_vision/capture.py`: Win32/MSS capture and hand-slot detection.
- `src/mahjong_vision/templates.py`: template persistence and matching.
- `src/mahjong_vision/recognizer.py`: hand recognition and frame stabilization.
- `src/mahjong_vision/advisor.py`: discard recommendation logic.
- `src/mahjong_vision/overlay.py`: Tkinter always-on-top UI.

## Important project data

- Treat `config.json` and `templates/` as important runtime data.
- Preserve the exact window title, capture geometry, matching thresholds, and labeled template images unless the user requests recalibration.
- Do not delete `.venv/` or `dist/` without explicit user approval.
- `build/`, pytest temporary directories, bytecode, egg-info, debug screenshots, and runtime logs are disposable.

## Development rules

- Use test-driven development for behavior changes and bug fixes.
- Keep capture and matching logic deterministic and independently testable.
- Run the full test suite before committing.
- Preserve unrelated user changes in a dirty worktree.
- Keep the first release Windows-specific and optimized for the current WeChat mini-program layout.
- The assistant provides recommendations only. Do not add automatic clicking, gameplay, messaging, or account actions.
