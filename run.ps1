$ErrorActionPreference = 'Stop'
if (-not (Test-Path '.venv\Scripts\Activate.ps1')) {
  Write-Host 'Missing .venv. Run: py -3.11 -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt' -ForegroundColor Yellow
  exit 1
}
& .\.venv\Scripts\Activate.ps1
Write-Host 'Fast local mode: answers come directly from the local TAP knowledge base. Ollama is not required.' -ForegroundColor Green
streamlit run app.py
