"""
HyperCLOVA X SEED Think-14B → GPTQ W4A16 양자화 (llm-compressor)

llm-compressor는 vLLM 공식 양자화 도구로, transformers 내장 모델 지원.
HyperCLOVA X는 transformers 5.x에 내장되어 있어 trust_remote_code 불필요.

실행: .venv/bin/python3 tools/gptq_quantize.py
"""
import warnings, os
warnings.filterwarnings("ignore")
os.environ["TOKENIZERS_PARALLELISM"] = "false"

MODEL_PATH = "naver-hyperclovax/HyperCLOVAX-SEED-Think-14B"
QUANT_PATH = "/home/machine/Hello-Clova-Agent/models/HyperCLOVAX-Think-14B-GPTQ"

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
print(f"[GPTQ] PyTorch {torch.__version__} | CUDA {torch.cuda.is_available()}")
print(f"[GPTQ] VRAM: {torch.cuda.mem_get_info()[0]/1e9:.1f}GB free")

from transformers import AutoTokenizer, AutoModelForCausalLM

print(f"\n[GPTQ] 토크나이저 로드...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

print(f"[GPTQ] 모델 로드 (FP16, device_map=auto)...")
model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    device_map="auto",
    torch_dtype=torch.float16,
    low_cpu_mem_usage=True,
)
print(f"[GPTQ] 모델 로드 완료: {type(model).__name__}")

print(f"\n[GPTQ] llm-compressor GPTQ W4A16 양자화 시작...")
from llmcompressor import oneshot
from llmcompressor.modifiers.quantization import GPTQModifier

recipe = GPTQModifier(
    targets="Linear",
    scheme="W4A16",
    ignore=["lm_head"],
    dampening_frac=0.01,
)

oneshot(
    model=model,
    dataset=CALIB_DATA,
    recipe=recipe,
    max_seq_length=512,
    num_calibration_samples=len(CALIB_DATA),
)

print(f"\n[GPTQ] 저장: {QUANT_PATH}")
os.makedirs(QUANT_PATH, exist_ok=True)
model.save_pretrained(QUANT_PATH, save_compressed=True)
tokenizer.save_pretrained(QUANT_PATH)
print("[GPTQ] ✅ 완료!")
print(f"\n[사용법]")
print(f"  vllm serve {QUANT_PATH} --quantization gptq --dtype auto")
