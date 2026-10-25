Set-Location $PSScriptRoot

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    $py = (Get-Command py -ErrorAction SilentlyContinue)
    if ($py) {
        py -3.10 -m venv .venv
    } else {
        python -m venv .venv
    }
    & .\.venv\Scripts\python.exe -m pip install --upgrade pip
    & .\.venv\Scripts\python.exe -m pip install -r requirements.txt
}

& .\.venv\Scripts\python.exe gestures.py
& .\.venv\Scripts\python.exe main.py
