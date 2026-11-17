# Startet Label Studio lokal (nur auf diesem Rechner erreichbar: http://localhost:8080).
# Aufruf im Projektordner:  .\tools\start_labelstudio.ps1
# Beenden: Strg+C im Terminal.
param([int]$Port = 8080)

$projekt = Split-Path -Parent $PSScriptRoot
$env:LABEL_STUDIO_BASE_DATA_DIR = Join-Path $projekt "data\labelstudio"  # Datenbank und Uploads, nicht im Git
$env:COLLECT_ANALYTICS = "false"                                          # keine Nutzungsdaten senden
Remove-Item Env:HOST -ErrorAction SilentlyContinue                        # eine HOST-Variable stört Label Studio
Remove-Item Env:LABEL_STUDIO_DISABLE_SIGNUP_WITHOUT_LINK -ErrorAction SilentlyContinue  # sperrt sonst die Registrierung (403)

New-Item -ItemType Directory -Force $env:LABEL_STUDIO_BASE_DATA_DIR | Out-Null
# --internal-host legt fest, auf welcher Adresse der Server lauscht: 127.0.0.1 = nur dieser Rechner.
& (Join-Path $projekt ".venv-labelstudio\Scripts\label-studio.exe") start --internal-host 127.0.0.1 --port $Port --no-browser
