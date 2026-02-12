# Integrated Care Platform - Python 가상환경 자동 설정
# 프로젝트 루트에서 실행: .\scripts\setup-venv.ps1

$ErrorActionPreference = "Stop"
# 스크립트 위치: scripts/setup-venv.ps1 → 프로젝트 루트 = 상위 디렉터리
$ProjectRoot = (Resolve-Path (Join-Path (Split-Path -Parent $PSScriptRoot) ".")).Path
if (-not (Test-Path (Join-Path $ProjectRoot "requirements.txt"))) {
    Write-Error "requirements.txt를 찾을 수 없습니다. 프로젝트 루트에서 실행하세요: .\scripts\setup-venv.ps1"
}
Push-Location $ProjectRoot
try {

function Find-Python {
    $py = $null
    foreach ($candidate in @("python", "python3", "py")) {
        $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($cmd) {
            if ($candidate -eq "py") {
                # Windows py launcher: use -3.12 or -3
                $py = "py -3.12"
                try {
                    $v = & py -3.12 -c "import sys; print(sys.version_info >= (3,11))" 2>$null
                    if ($LASTEXITCODE -ne 0 -or $v -ne "True") { $py = "py -3" }
                } catch {}
            } else {
                $py = $candidate
            }
            break
        }
    }
    $py
}

$pythonCmd = Find-Python
if (-not $pythonCmd) {
    Write-Host "Python이 PATH에 없습니다." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Windows에서 Python 설치 방법:"
    Write-Host "  1) winget (권장):  winget install Python.Python.3.12"
    Write-Host "  2) 공식 설치:       https://www.python.org/downloads/"
    Write-Host "  3) Microsoft Store: 'Python 3.12' 검색 후 설치"
    Write-Host ""
    Write-Host "설치 후 터미널을 다시 열고 이 스크립트를 다시 실행하세요."
    exit 1
}

$venvPath = Join-Path $ProjectRoot ".venv"
if (Test-Path $venvPath) {
    Write-Host "기존 .venv가 있습니다. 재사용합니다."
} else {
    Write-Host "가상환경 생성 중: .venv"
    Invoke-Expression "$pythonCmd -m venv `"$venvPath`""
    if ($LASTEXITCODE -ne 0) {
        Write-Host "venv 생성 실패. 'py -3' 또는 'python'으로 시도해 보세요." -ForegroundColor Yellow
        exit 1
    }
}

$pip = Join-Path $venvPath "Scripts\pip.exe"
$python = Join-Path $venvPath "Scripts\python.exe"
if (-not (Test-Path $pip)) {
    Write-Error ".venv 안에 pip이 없습니다. Python 설치가 불완전할 수 있습니다."
}

Write-Host "pip 업그레이드 및 requirements.txt 설치 중..."
& $pip install --upgrade pip --quiet
& $pip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host ""
Write-Host "설정이 완료되었습니다." -ForegroundColor Green
Write-Host ""
Write-Host "가상환경 활성화 (PowerShell):"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "테스트 실행:"
Write-Host "  pytest"
Write-Host ""
} finally {
    Pop-Location
}
