[CmdletBinding()]
param([switch]$Gemini)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent $PSScriptRoot
$requirements = Join-Path $repoRoot "apps\api\requirements.lock"
$webPackage = Join-Path $repoRoot "apps\web\package.json"
$voiceVenv = Join-Path $env:LOCALAPPDATA "Temp\super-agent-voice-venv"
$voicePython = Join-Path $voiceVenv "Scripts\python.exe"
$backend = $null
$previousPythonPath = [Environment]::GetEnvironmentVariable("PYTHONPATH", "Process")
$previousLocalToken = [Environment]::GetEnvironmentVariable("SUPER_AGENT_LOCAL_TOKEN", "Process")
$previousGeminiKey = [Environment]::GetEnvironmentVariable("GEMINI_API_KEY", "Process")
$previousAdapter = [Environment]::GetEnvironmentVariable("SUPER_AGENT_ADAPTER", "Process")

if (-not (Test-Path $requirements) -or -not (Test-Path $webPackage)) {
    throw "Run the launcher from a complete super-agent checkout."
}

foreach ($port in 8000, 4200) {
    $listener = [System.Net.Sockets.TcpListener]::new(
        [System.Net.IPAddress]::Loopback, $port
    )
    try {
        $listener.Start()
    } catch [System.Net.Sockets.SocketException] {
        throw "Port $port is already in use. Stop the existing local service and run this launcher again."
    } finally {
        $listener.Stop()
    }
}

Push-Location $repoRoot
try {
    if (-not (Test-Path $voicePython)) {
        $python = (Get-Command python -ErrorAction Stop).Source
        & $python -m venv $voiceVenv
        if ($LASTEXITCODE -ne 0) { throw "Could not create the Python environment." }
    }

    & $voicePython -m pip install --disable-pip-version-check --only-binary=:all: -r $requirements
    if ($LASTEXITCODE -ne 0) { throw "Backend dependency installation failed." }

    $npm = (Get-Command npm.cmd -ErrorAction Stop).Source
    & $npm ci --ignore-scripts --prefix (Join-Path $repoRoot "apps\web")
    if ($LASTEXITCODE -ne 0) { throw "Frontend dependency installation failed." }

    Remove-Item Env:SUPER_AGENT_LOCAL_TOKEN -ErrorAction SilentlyContinue
    Remove-Item Env:GEMINI_API_KEY -ErrorAction SilentlyContinue
    # The launcher only serves the fake or Gemini path, so an inherited adapter (such as local) is dropped.
    Remove-Item Env:SUPER_AGENT_ADAPTER -ErrorAction SilentlyContinue
    if ($Gemini) {
        Write-Host "WARNING: real microphone audio goes to Google's free tier, which may use inputs for training. Speak nothing personal (see docs/approvals/gemini-live-testing-exception.md)."
        $secureKey = Read-Host "Gemini API key" -AsSecureString
        $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
        try {
            $plainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
        } finally {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
        }
        if ([string]::IsNullOrWhiteSpace($plainKey)) { throw "A Gemini API key is required with -Gemini." }
        $env:GEMINI_API_KEY = $plainKey
        $plainKey = $null
        $env:SUPER_AGENT_ADAPTER = "gemini"
    }
    $env:PYTHONPATH = Join-Path $repoRoot "apps\api\src"

    & $voicePython -m super_agent_voice.generate_token
    if ($LASTEXITCODE -ne 0) { throw "Local token generation failed." }

    $backendArguments = @(
        "-m", "uvicorn", "super_agent_voice.app:create_app", "--factory",
        "--host", "127.0.0.1", "--port", "8000",
        "--ws-max-size", "65600", "--ws-max-queue", "4"
    )
    $backend = Start-Process -FilePath $voicePython -ArgumentList $backendArguments `
        -WorkingDirectory $repoRoot -NoNewWindow -PassThru

    $ready = $false
    foreach ($attempt in 1..20) {
        if ($backend.HasExited) { throw "The voice backend exited during startup." }
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" `
                -Headers @{ Host = "127.0.0.1:8000" } -TimeoutSec 1
            if ($health.status -eq "ok") {
                $ready = $true
                break
            }
        } catch {
            Start-Sleep -Milliseconds 250
        }
    }
    if (-not $ready) { throw "The voice backend did not become ready on port 8000." }

    Write-Host ""
    Write-Host "Voice scaffold ready: http://127.0.0.1:4200"
    Write-Host "Adapter: $($health.provider)"
    Write-Host "Token file: $HOME\.super-agent\voice-token"
    Write-Host "Use Ctrl+C to stop both services."
    Write-Host ""

    & $npm start --prefix (Join-Path $repoRoot "apps\web")
    if ($LASTEXITCODE -ne 0) { throw "The frontend exited with an error." }
} finally {
    if ($null -ne $backend -and -not $backend.HasExited) {
        Stop-Process -Id $backend.Id -ErrorAction SilentlyContinue
    }
    [Environment]::SetEnvironmentVariable("PYTHONPATH", $previousPythonPath, "Process")
    [Environment]::SetEnvironmentVariable("SUPER_AGENT_LOCAL_TOKEN", $previousLocalToken, "Process")
    [Environment]::SetEnvironmentVariable("GEMINI_API_KEY", $previousGeminiKey, "Process")
    [Environment]::SetEnvironmentVariable("SUPER_AGENT_ADAPTER", $previousAdapter, "Process")
    Pop-Location
}
