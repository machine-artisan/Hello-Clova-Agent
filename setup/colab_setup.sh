#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# Colab 초기 환경 설정 스크립트
# Colab 터미널에서 아래 명령어로 실행:
#   bash setup/colab_setup.sh
# ─────────────────────────────────────────────────────────────────────────────

echo "========================================="
echo " Local Deck Gen Agent — Colab 환경 설정"
echo "========================================="

# 1. 의존성 설치
echo "[1/4] Python 패키지 설치 중..."
pip install -r requirements.txt -q

# 2. vLLM 설치 (GPU 환경)
echo "[2/4] vLLM 설치 중..."
pip install vllm -q

# 3. 환경변수 파일 생성
echo "[3/4] 환경변수 설정..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "  → .env 파일 생성 완료 (필요시 수정하세요)"
fi

# 4. 출력 디렉토리 확인
mkdir -p output

echo ""
echo "========================================="
echo " 설정 완료!"
echo ""
echo " 다음 단계:"
echo " 1) vLLM 서버 시작 (백그라운드):"
echo "    bash setup/start_vllm.sh &"
echo ""
echo " 2) 서버 준비 대기 (약 1~2분):"
echo "    sleep 60"
echo ""
echo " 3) Gradio 앱 실행:"
echo "    python ui/app.py"
echo ""
echo " → 출력된 공개 URL로 브라우저 접속"
echo "========================================="
