# Python 개발 환경 설정

이 문서는 Integrated Care Platform의 Python 개발 환경을 로컬에 구축하는 방법을 설명합니다.

## 0. Python 설치 (미설치 시)

### Windows

- **winget (권장)** — 관리자 권한 불필요, 터미널에서 한 줄로 설치:
  ```powershell
  winget install Python.Python.3.12
  ```
  설치 후 **새 터미널**을 열어 주세요.

- **공식 설치 프로그램**: [python.org/downloads](https://www.python.org/downloads/) 에서 다운로드 후 설치. 설치 시 **"Add Python to PATH"** 체크.

- **Microsoft Store**: "Python 3.12" 검색 후 설치.

### macOS / Linux

- macOS: `brew install python@3.12`
- Ubuntu/Debian: `sudo apt update && sudo apt install python3.12 python3.12-venv`

설치 확인: `python --version` 또는 `py -3.12 --version` (Windows) → `Python 3.11` 이상이면 됩니다.

## 1. 가상 환경 자동 설정 (권장)

**Windows (PowerShell)** — 프로젝트 루트에서 한 번만 실행:

```powershell
cd c:\Users\Wyatt\Desktop\Integrated-Care-Platform
.\scripts\setup-venv.ps1
```

스크립트가 `.venv` 생성, `pip` 업그레이드, `requirements.txt` 설치까지 수행합니다. 완료 후:

```powershell
.\.venv\Scripts\Activate.ps1
pytest
```

## 2. 가상 환경 수동 설정

**Windows (PowerShell):**

```powershell
cd c:\Users\Wyatt\Desktop\Integrated-Care-Platform
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**macOS / Linux:**

```bash
cd /path/to/Integrated-Care-Platform
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

pip 업그레이드 후 설치하려면: `pip install --upgrade pip` 후 `pip install -r requirements.txt`

## 3. 개발용 도구 설치 (선택)

린트/포맷터(ruff), 타입 체크(mypy)를 사용하려면:

```bash
pip install -e ".[dev]"
```

또는 개별 설치:

```bash
pip install ruff mypy
```

## 4. 테스트 실행

프로젝트 루트에서:

```bash
pytest
```

특정 앱/패키지만 실행:

```bash
pytest apps/api/tests
pytest packages/data-pipeline/tests
```

## 5. 린트 및 포맷

- **Ruff (린트 + 포맷):**
  ```bash
  ruff check apps/api packages/data-pipeline
  ruff format apps/api packages/data-pipeline
  ```

- **Mypy (타입 체크):**
  ```bash
  mypy apps/api/src packages/data-pipeline/src
  ```

## 6. 프로젝트 구조 (Python 관련)

- `apps/api/` — BFF/API 서버 코드 및 테스트
- `packages/data-pipeline/` — ETL 파이프라인 및 프로바이더 어댑터
- `pytest.ini` — pytest 기본 설정 (pythonpath 등)
- `pyproject.toml` — 프로젝트 메타데이터, 의존성, ruff/mypy 설정

`pytest.ini`의 `pythonpath` 덕분에 `api`, `data_pipeline` 패키지를 별도 설치 없이 import 할 수 있습니다.

## 7. 문제 해결

- **ModuleNotFoundError**: 터미널을 **프로젝트 루트**에서 열고 `pytest`를 실행했는지 확인하세요. `pytest.ini`의 pythonpath는 루트 기준입니다.
- **가상 환경이 활성화되지 않음**: `which python`(또는 Windows에서는 `where python`)으로 `.venv` 내의 Python이 사용되는지 확인하세요.
