param(
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --runtime-hook pyi_runtime_hook.py `
    --name Hatirlatici `
    app.py

if ($LASTEXITCODE -ne 0) {
    throw "Hatirlatici.exe üretilemedi."
}

Write-Host "EXE hazır: dist\Hatirlatici.exe"
