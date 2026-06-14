# SWA-04: Colab .ipynb 콘솔 패턴 (Notebook-as-Console Pattern)

> Google Colab의 `.ipynb`를 실행 환경이자 인터랙티브 콘솔로 활용하는 패턴.  
> Git 저장소의 Python 패키지를 Colab에서 로드하고, 에이전트를 구동하는 방법.

---

## 1. 패턴 개요

```
GitHub 저장소 (Python 패키지)
    │
    │ git clone (Colab 셀)
    ▼
Google Colab 런타임 (GPU T4/A100)
    │
    ├── 셀 1: 환경 설정 (pip install, git clone)
    ├── 셀 2: 설정값 입력 (API 키, 모델 선택)
    ├── 셀 3: 서버 기동 (vLLM background process)
    ├── 셀 4: UI 실행 (Gradio with share=True → 공개 URL)
    └── 셀 5~N: 결과 확인 / 재실행
```

---

## 2. .ipynb 셀 구성 템플릿

### 셀 1: 환경 설치

```python
# @title 📦 환경 설치
import subprocess, os

# GPU 확인
result = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                        capture_output=True, text=True)
print("GPU:", result.stdout.strip())

# 저장소 클론
REPO_URL = "https://github.com/your-org/your-agent-package.git"
REPO_DIR = "/content/your-agent-package"

if not os.path.exists(REPO_DIR):
    subprocess.run(["git", "clone", REPO_URL, REPO_DIR], check=True)
else:
    subprocess.run(["git", "-C", REPO_DIR, "pull"], check=True)

os.chdir(REPO_DIR)
print("작업 디렉토리:", os.getcwd())

# 패키지 설치
subprocess.run(["pip", "install", "-r", "requirements.txt", "-q"], check=True)
print("✅ 설치 완료")
```

### 셀 2: vLLM + 모델 설치

```python
# @title 🚀 vLLM 설치 (최초 1회)
# Colab에서 vLLM 버전 선택 기준:
# - T4 (CUDA 12.x): vllm==0.19.1 권장
# - A100 (CUDA 12.x): vllm==0.19.1 또는 최신 버전

!pip install vllm==0.19.1 -q

import torch
print(f"PyTorch: {torch.__version__}")
print(f"CUDA 사용 가능: {torch.cuda.is_available()}")
print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")
```

### 셀 3: HuggingFace 로그인 + 서버 기동

```python
# @title 🔑 HF 로그인 + vLLM 서버 기동
import subprocess, os, time

# HuggingFace 토큰 (Colab Secrets에서 가져오기)
from google.colab import userdata
HF_TOKEN = userdata.get("HF_TOKEN")

MODEL = "naver-hyperclovax/HyperCLOVAX-SEED-Think-14B"

# vLLM 서버를 백그라운드로 기동
proc = subprocess.Popen(
    [
        "python", "-m", "vllm.entrypoints.openai.api_server",
        "--model", MODEL,
        "--host", "0.0.0.0",
        "--port", "8000",
        "--dtype", "auto",
        "--max-model-len", "4096",
        "--gpu-memory-utilization", "0.90",
        "--quantization", "bitsandbytes",
        "--load-format", "bitsandbytes",
        "--served-model-name", MODEL,
    ],
    env={**os.environ, "HF_TOKEN": HF_TOKEN},
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)

# 서버 준비 대기
import requests
for i in range(60):
    try:
        r = requests.get("http://localhost:8000/health", timeout=2)
        if r.status_code == 200:
            print(f"✅ vLLM 서버 준비 완료 ({i*5}초)")
            break
    except:
        pass
    print(f"  대기 중... ({i*5}초)")
    time.sleep(5)
```

### 셀 4: Gradio UI 기동

```python
# @title 🎨 Gradio UI 기동
import os, sys
sys.path.insert(0, "/content/your-agent-package")

os.environ["LLM_API_BASE"] = "http://localhost:8000/v1"
os.environ["LLM_API_KEY"]  = "EMPTY"
os.environ["LLM_MODEL"]    = "naver-hyperclovax/HyperCLOVAX-SEED-Think-14B"

from ui.app import demo  # Gradio Blocks 인스턴스
demo.launch(share=True)  # share=True → 공개 URL 생성 (Colab에서 필수)
```

---

## 3. Colab Secrets 활용

API 키를 코드에 하드코딩하지 않으려면 Colab Secrets 사용:

```python
from google.colab import userdata

# Colab 좌측 패널 → 🔑 Secrets → 키 추가
HF_TOKEN = userdata.get("HF_TOKEN")         # HuggingFace 토큰
OPENAI_API_KEY = userdata.get("OPENAI_KEY") # 외부 LLM API
```

---

## 4. Google Drive 연동 (영구 저장)

```python
from google.colab import drive
drive.mount("/content/drive")

# 출력물을 Drive에 저장
OUTPUT_DIR = "/content/drive/MyDrive/agent-outputs/"
os.makedirs(OUTPUT_DIR, exist_ok=True)
```

혹은 패키지 내 `OUTPUT_DIR` 환경변수로 제어:

```python
os.environ["OUTPUT_DIR"] = "/content/drive/MyDrive/agent-outputs/"
```

---

## 5. 로컬 WSL2 실행 패턴

Colab 없이 로컬 GPU (WSL2 Ubuntu)에서 실행할 때:

```bash
# 1. venv 활성화
source .venv/bin/activate

# 2. vLLM 서버 (백그라운드)
LLM_QUANTIZATION=bitsandbytes bash setup/start_vllm.sh &

# 3. 서버 준비 대기
until curl -sf http://localhost:8000/health > /dev/null; do sleep 5; done
echo "vLLM 준비 완료"

# 4. Gradio UI
LLM_API_BASE="http://localhost:8000/v1" \
LLM_API_KEY="EMPTY" \
LLM_MODEL="naver-hyperclovax/HyperCLOVAX-SEED-Think-14B" \
GRADIO_SHARE="false" \
python3 ui/app.py
```

---

## 6. .ipynb 설계 원칙

### 해야 할 것
- **각 셀은 독립적으로 재실행 가능**하게 설계 (멱등성)
- **긴 작업은 백그라운드 프로세스로** (vLLM 서버) → 셀이 블로킹되지 않게
- **`# @title` 주석으로 셀 이름 지정** → Colab 목차에서 탐색 편의
- **셀 첫 줄에 목적 설명** → 다음 사람이 바로 이해
- **출력 검증 셀 포함** → `curl http://localhost:8000/health` 등

### 피해야 할 것
- 셀에 비밀 키 하드코딩 (Colab Secrets 또는 환경변수 사용)
- 셀 순서에 강한 의존성 (재실행 시 문제)
- 긴 pip install을 매 실행마다 (설치 여부 체크 후 스킵)

---

## 7. 프로젝트 디렉토리 구조 권장

```
your-agent-package/
├── Hello_Agent_Colab.ipynb     # Colab 실행 전용 (짧게 유지)
├── Hello_Agent_local.ipynb     # 로컬 WSL2 실행 전용
├── agent/                      # 실제 에이전트 패키지
│   ├── __init__.py
│   ├── state.py
│   ├── graph.py
│   ├── llm.py
│   ├── prompts.py
│   └── nodes/
├── ui/
│   └── app.py                  # Gradio UI
├── setup/
│   └── start_vllm.sh
├── output/                     # 생성물 저장 (gitignore)
├── requirements.txt
└── README.md
```

---

*문서 유형: SWA-04 Colab .ipynb 콘솔 패턴 | 작성일: 2026-06-14*
