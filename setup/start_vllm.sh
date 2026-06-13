#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# vLLM API 서버 시작 스크립트
#
# [개념] API 서버(API Server)란?
# 이 스크립트는 HyperCLOVA X 모델을 HTTP REST API로 제공하는 서버를 실행합니다.
# OpenAI의 Chat Completions API와 동일한 형식을 사용하므로
# openai 파이썬 라이브러리로 바로 호출 가능합니다.
#
# 엔드포인트: http://localhost:8000/v1/chat/completions
# ─────────────────────────────────────────────────────────────────────────────

set -e

MODEL=${LLM_MODEL:-"naver-hyperclovax/HyperCLOVA-X-SEED-Instruct-3B"}
PORT=${LLM_PORT:-8000}
DTYPE=${LLM_DTYPE:-"half"}             # fp16 기본값
MAX_LEN=${LLM_MAX_LEN:-4096}
GPU_MEM=${LLM_GPU_MEM:-0.90}
QUANTIZATION=${LLM_QUANTIZATION:-""}  # 14B 이상: bitsandbytes 권장

echo "========================================"
echo " vLLM API 서버 시작"
echo " 모델  : $MODEL"
echo " 포트  : $PORT"
echo " dtype : $DTYPE"
if [ -n "$QUANTIZATION" ]; then
  echo " 양자화: $QUANTIZATION (4-bit)"
fi
echo "========================================"
echo ""
echo " VRAM 가이드:"
echo "   Instruct-3B  → fp16  ~8GB    (T4 15GB OK)"
echo "   Think-14B    → 4-bit ~8-10GB (T4 15GB OK, LLM_QUANTIZATION=bitsandbytes)"
echo "   Think-32B    → 4-bit ~18GB   (A100 40GB 권장)"
echo "========================================"

pip install vllm -q 2>/dev/null || true

# 양자화 옵션 구성
QUANT_ARGS=""
if [ -n "$QUANTIZATION" ]; then
    QUANT_ARGS="--quantization $QUANTIZATION --load-format bitsandbytes"
fi

python -m vllm.entrypoints.openai.api_server \
    --model "$MODEL" \
    --host "0.0.0.0" \
    --port "$PORT" \
    --dtype "$DTYPE" \
    --max-model-len "$MAX_LEN" \
    --gpu-memory-utilization "$GPU_MEM" \
    --trust-remote-code \
    --served-model-name "$MODEL" \
    $QUANT_ARGS
