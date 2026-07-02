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
