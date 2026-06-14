"""
HyperCLOVA X SEED Think-14B → AWQ 4-bit 양자화 스크립트

전략:
  transformers 5.x에 hyperclovax 내장 지원 (trust_remote_code 불필요).
  AutoAWQ에 hyperclovax → LlamaAWQForCausalLM 패치 후 from_pretrained 직접 호출.

실행:
  .venv/bin/python3 tools/awq_quantize.py
"""
import warnings, os, sys
warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

MODEL_PATH  = "naver-hyperclovax/HyperCLOVAX-SEED-Think-14B"
QUANT_PATH  = "/home/machine/Hello-Clova-Agent/models/HyperCLOVAX-Think-14B-AWQ"

CALIB_DATA = [
    "인공지능 기술은 최근 급격히 발전하였습니다. 특히 대규모 언어 모델의 등장으로 많은 분야에서 혁신이 일어나고 있습니다.",
    "프레젠테이션 자동 생성 시스템은 사용자의 입력을 받아 슬라이드를 자동으로 작성합니다. 이를 통해 업무 효율성을 높일 수 있습니다.",
    "LangGraph는 에이전트 파이프라인을 구성하는 프레임워크입니다. 각 노드가 독립적으로 작동하며 상태를 공유합니다.",
    "HyperCLOVA X는 네이버에서 개발한 대규모 한국어 언어 모델입니다. 한국어 이해와 생성 능력이 뛰어납니다.",
    "vLLM은 GPU에서 LLM 추론을 효율적으로 수행하는 라이브러리입니다. PagedAttention 기술을 활용하여 메모리를 최적화합니다.",
    "양자화 기술은 모델의 가중치를 낮은 비트로 표현하여 메모리 사용량과 추론 속도를 개선합니다.",
    "슬라이드 덱 생성 에이전트는 사용자의 메모를 분석하여 구조화된 프레젠테이션을 자동으로 만들어냅니다.",
    "기업 환경에서 AI 기술의 도입은 생산성 향상과 비용 절감에 크게 기여하고 있습니다.",
]

import torch
print(f"[AWQ] PyTorch {torch.__version__} | CUDA {torch.cuda.is_available()}")
print(f"[AWQ] GPU: {torch.cuda.get_device_name(0)} | VRAM: {torch.cuda.mem_get_info()[0]/1e9:.1f}GB free")

# ─── AutoAWQ에 hyperclovax 아키텍처 패치 ──────────────────────────────────────
from awq.models import auto as awq_auto
from awq.models.llama import LlamaAWQForCausalLM
from awq.models import base as awq_base

# AWQ_CAUSAL_LM_MODEL_MAP: 어떤 AWQ 래퍼 클래스를 쓸지
awq_auto.AWQ_CAUSAL_LM_MODEL_MAP["hyperclovax"] = LlamaAWQForCausalLM
# TRANSFORMERS_AUTO_MAPPING_DICT: 어떤 transformers AutoClass를 쓸지
awq_base.TRANSFORMERS_AUTO_MAPPING_DICT["hyperclovax"] = "AutoModelForCausalLM"
print("[AWQ] 패치 완료: hyperclovax → LlamaAWQForCausalLM + AutoModelForCausalLM")

# ─── transformers 내장 hyperclovax 지원으로 직접 로드 ─────────────────────────
from awq import AutoAWQForCausalLM
from transformers import AutoTokenizer

print(f"\n[AWQ] 토크나이저 로드...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)  # trust_remote_code 불필요

print(f"[AWQ] 모델 로드 (FP16, device_map=auto)...")
# trust_remote_code=False (기본값) — transformers 5.x에 hyperclovax 내장
model = AutoAWQForCausalLM.from_pretrained(
    MODEL_PATH,
    device_map="auto",
    low_cpu_mem_usage=True,
)
print("[AWQ] 모델 로드 완료")

# ─── AWQ 양자화 실행 ─────────────────────────────────────────────────────────
quant_config = {"zero_point": True, "q_group_size": 128, "w_bit": 4, "version": "GEMM"}
print(f"\n[AWQ] 양자화 설정: {quant_config}")
print(f"[AWQ] 캘리브레이션: {len(CALIB_DATA)}개 샘플")
print("[AWQ] 양자화 시작...")

model.quantize(tokenizer, quant_config=quant_config, calib_data=CALIB_DATA)

# ─── 저장 ───────────────────────────────────────────────────────────────────
print(f"\n[AWQ] 저장: {QUANT_PATH}")
os.makedirs(QUANT_PATH, exist_ok=True)
model.save_quantized(QUANT_PATH)
tokenizer.save_pretrained(QUANT_PATH)
print("[AWQ] ✅ 완료!")
print(f"\n[사용법]")
print(f"  vllm serve {QUANT_PATH} --quantization awq --dtype auto")
