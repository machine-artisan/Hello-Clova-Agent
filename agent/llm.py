"""
LLM 클라이언트 모듈

[개념] API 서버란?
vLLM이 OpenAI 호환 REST API를 로컬에서 제공합니다.
이 모듈은 그 API 서버에 요청을 보내는 클라이언트 역할을 합니다.

                 ┌────────────┐  HTTP 요청   ┌─────────────────┐
  이 모듈 ───►  │  openai    │ ──────────► │  vLLM API 서버  │
                 │  라이브러리 │             │  localhost:8000  │
                 └────────────┘             └─────────────────┘
"""
import os
from openai import OpenAI


def get_client() -> OpenAI:
    """환경변수 기반 OpenAI 호환 클라이언트 반환"""
    return OpenAI(
        api_key=os.getenv("LLM_API_KEY", "EMPTY"),        # vLLM은 키 불필요
        base_url=os.getenv("LLM_API_BASE", "http://localhost:8000/v1"),
    )


def get_model_name() -> str:
    return os.getenv(
        "LLM_MODEL",
        "naver-hyperclovax/HyperCLOVA-X-SEED-Instruct-3B",
    )


def chat(messages: list[dict], temperature: float = 0.7, max_tokens: int = 2048) -> str:
    """LLM 채팅 완성 호출 — 모든 노드가 이 함수를 통해 LLM을 호출합니다."""
    client = get_client()
    response = client.chat.completions.create(
        model=get_model_name(),
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()
