# SWA-06: 환경 설정 가이드 (Environment & Operations Guide)

> 이 패턴(Colab + LangGraph + vLLM)을 새 환경에서 처음 구축할 때 참고하는 가이드.  
> 의존성 충돌 해결, 가상환경 관리, GPU 설정을 다룹니다.

---

## 1. 필수 환경 요건

| 항목 | 최소 사양 | 권장 사양 |
|------|---------|---------|
| GPU VRAM | 15GB (T4, 4-bit 기준) | 24GB+ (RTX A5000, A100) |
| CUDA Driver | 12.4+ | 12.8+ |
| Python | 3.10+ | 3.12 |
| RAM | 32GB | 64GB |
| 디스크 | 100GB (모델 캐시) | 200GB+ |

---

## 2. 의존성 패키지

### 2-1. 핵심 패키지 (requirements.txt)

```txt
# LangGraph 에이전트
langgraph>=0.2.0
langchain-core>=0.3.0

# LLM API 클라이언트 (OpenAI 호환)
openai>=1.0.0

# Gradio 웹 UI
gradio>=4.44.0

# 환경변수 관리
python-dotenv>=1.0.0
```

### 2-2. vLLM 및 ML 패키지 (별도 설치, 버전 고정 필수)

```bash
# HyperCLOVA X 지원 + CUDA 12.8 호환 버전
pip install vllm==0.19.1

# transformers (5.x에 HyperCLOVA X 내장)
pip install transformers==5.12.0 "huggingface-hub>=1.2.0,<2.0"

# BitsAndBytes 4-bit 양자화
pip install bitsandbytes
```

### 2-3. 버전 충돌 매트릭스 (HyperCLOVA X 기준)

| 패키지 | 안전 버전 | 위험 버전 | 이유 |
|--------|---------|---------|------|
| vLLM | **0.19.1** | 0.8.x (HCX 미지원), 0.23+ (CUDA 13.0 요구) | HCX 아키텍처 내장 여부 |
| transformers | **5.12.0** | 4.x (HCX 미지원) | hyperclovax 모델 타입 지원 |
| huggingface-hub | **>=1.2.0,<2.0** | 0.36.x (Gradio 6.x 미호환) | Gradio 요구사항 |
| llmcompressor | ❌ 설치 금지 | - | transformers 강제 다운그레이드 |
| autoawq | ❌ 실효 없음 | - | HCX hook 미호환 |

---

## 3. 가상환경 구성

```bash
# Python 3.12 venv 생성
python3.12 -m venv .venv

# 활성화
source .venv/bin/activate          # Linux/macOS/WSL2
.venv\Scripts\activate             # Windows (PowerShell)

# 기본 패키지 설치
pip install -r requirements.txt

# vLLM 별도 설치 (용량 크므로 후순위)
pip install vllm==0.19.1
pip install transformers==5.12.0 "huggingface-hub>=1.2.0,<2.0"
pip install bitsandbytes
```

---

## 4. HuggingFace 인증

```bash
# CLI 로그인 (캐시에 토큰 저장)
.venv/bin/huggingface-cli login --token $HF_TOKEN

# 또는 환경변수로 직접 (Colab Secrets, .env 파일 등)
export HF_TOKEN="hf_..."
```

**Claude Code CLI에서 환경변수 주입:**

```json
// .claude/settings.local.json (gitignore 처리 필수)
{
  "env": {
    "HF_TOKEN": "hf_..."
  }
}
```

---

## 5. CUDA 환경 진단

```bash
# CUDA 드라이버 버전 확인
nvidia-smi | head -5

# Python에서 CUDA 확인
.venv/bin/python3 -c "
import torch
print('PyTorch:', torch.__version__)
print('CUDA available:', torch.cuda.is_available())
print('CUDA version:', torch.version.cuda)
print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')
print('VRAM free:', f'{torch.cuda.mem_get_info()[0]/1e9:.1f}GB')
"
```

**CUDA 버전 호환표 (PyTorch 내장 기준):**

| PyTorch 패키지 | 내장 CUDA runtime | 요구 드라이버 |
|--------------|----------------|-------------|
| cu124        | 12.4           | ≥12.4       |
| **cu128**    | 12.8           | ≥12.8 (드라이버 12.9 OK) |
| cu130        | 13.0           | ≥13.0 ❌ (드라이버 12.9에서 실패) |

---

## 6. 모델 캐시 관리

```bash
# HuggingFace 캐시 위치
ls ~/.cache/huggingface/hub/

# 모델 크기 확인 (14B BF16 기준 ~28GB)
du -sh ~/.cache/huggingface/hub/models--naver-hyperclovax--*/

# 캐시 삭제 (주의: 다시 다운로드 필요)
# huggingface-cli delete-cache
```

**config.json auto_map 수정 (HyperCLOVA X 한정):**

```bash
MODEL_CACHE=$(python3 -c "
from huggingface_hub import snapshot_download
import os
path = snapshot_download('naver-hyperclovax/HyperCLOVAX-SEED-Think-14B', local_files_only=True)
print(path)
")
CONFIG="$MODEL_CACHE/config.json"
cp "$CONFIG" "$CONFIG.bak"
python3 -c "
import json, sys
with open('$CONFIG') as f: c = json.load(f)
c.pop('auto_map', None)
with open('$CONFIG', 'w') as f: json.dump(c, f, indent=2, ensure_ascii=False)
print('auto_map 제거 완료')
"
```

---

## 7. vLLM 프로세스 관리

```bash
# 실행 중인 vLLM 확인
ps aux | grep vllm

# 포트 점유 프로세스 확인
lsof -i :8000

# GPU VRAM 사용량 모니터링
watch -n 2 nvidia-smi --query-gpu=memory.used,memory.free --format=csv

# vLLM 정상 종료
kill $(lsof -t -i :8000)

# vLLM 강제 종료 (자식 프로세스 포함)
pkill -f "vllm.entrypoints"

# 종료 후 VRAM 해제 확인
watch -n 1 "nvidia-smi | grep MiB"  # 3000MiB 미만이면 해제 완료
```

---

## 8. 의존성 충돌 복구

llm-compressor 등 설치 후 환경이 망가졌을 때:

```bash
# 환경 상태 확인
pip show transformers huggingface-hub | grep Version

# 복구
pip install \
  "transformers==5.12.0" \
  "huggingface-hub>=1.2.0,<2.0" \
  "compressed-tensors==0.15.0.1"

# 검증
python3 -c "
import transformers, huggingface_hub, gradio
print('transformers:', transformers.__version__)
print('huggingface_hub:', huggingface_hub.__version__)
print('gradio:', gradio.__version__)
"
```

---

## 9. .gitignore 권장 항목

```gitignore
# 가상환경 (용량 크고 재현 가능)
.venv/

# Python 캐시
__pycache__/
*.pyc

# 생성된 출력물 (선택적으로 제외)
output/deck_*.html
output/qa_*.html

# 비밀 정보
.env
.claude/settings.local.json

# 모델 파일 (경로가 프로젝트 내라면)
models/
*.bin
*.safetensors
```

---

## 10. 환경 검증 스크립트

```bash
# 전체 환경 한 번에 검증
.venv/bin/python3 -c "
import torch, transformers, langgraph, openai, gradio
print('=== 환경 검증 ===')
print(f'Python: ok')
print(f'PyTorch: {torch.__version__} | CUDA: {torch.cuda.is_available()}')
print(f'transformers: {transformers.__version__}')
print(f'langgraph: {langgraph.__version__}')
print(f'openai: {openai.__version__}')
print(f'gradio: {gradio.__version__}')

if torch.cuda.is_available():
    free, total = torch.cuda.mem_get_info()
    print(f'VRAM: {free/1e9:.1f}GB free / {total/1e9:.1f}GB total')

import requests
try:
    r = requests.get('http://localhost:8000/health', timeout=2)
    print(f'vLLM 서버: {r.status_code}')
except:
    print('vLLM 서버: 미실행')
"
```

---

*문서 유형: SWA-06 환경 설정 가이드 | 작성일: 2026-06-14*
