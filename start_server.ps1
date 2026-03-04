# FLUX.1 OpenVINO 画像生成 API サーバー起動
# 使い方: .\start_server.ps1

$env:PYTHONIOENCODING = "utf-8"
Set-Location $PSScriptRoot
.\venv\Scripts\Activate.ps1
Write-Host "Starting FLUX.1 OpenVINO Generator API on http://127.0.0.1:8188"
Write-Host "First startup takes ~2 min for model loading."
Write-Host ""
python api_server.py
