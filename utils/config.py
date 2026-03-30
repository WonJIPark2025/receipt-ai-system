"""
config.py - 설정 관리

담당: 공통
설명: 환경변수 및 설정값 로딩
    - 로컬: .env 파일에서 Supabase URL/Key, Gemini API Key 등 로드
    - 배포: Streamlit Secrets fallback 지원
    - 경로, 상수 등 공통 설정
"""

import os
from dotenv import load_dotenv

# .env 파일 로드 (로컬 환경)
load_dotenv()


def _get_config(key: str, default: str = None) -> str:
    """
    환경변수를 가져오되, 없으면 Streamlit Secrets에서 fallback 조회.
    로컬(.env) → Streamlit Secrets 순서로 우선 적용.
    """
    value = os.getenv(key)
    if value:
        return value
    try:
        import streamlit as st
        return st.secrets.get(key, default)
    except Exception:
        return default


# =============================================================================
# Supabase 설정
# =============================================================================
# 로컬: .env 파일에 설정
# 배포: Streamlit Secrets에 설정
# =============================================================================

SUPABASE_URL = _get_config("SUPABASE_URL")
SUPABASE_KEY = _get_config("SUPABASE_KEY")
SUPABASE_BUCKET = _get_config("SUPABASE_BUCKET", "OcrReceipts")

# =============================================================================
# Gemini AI 설정
# =============================================================================

GEMINI_API_KEY = _get_config("GEMINI_API_KEY")


# =============================================================================
# 앱 설정
# =============================================================================
# 단일 사용자 앱 — auth 없이 고정 user_id 사용

DEFAULT_USER_ID = 1

# =============================================================================
# 데모 모드
# =============================================================================
# DEMO_MODE=true 설정 시 업로드/저장/삭제 기능이 비활성화됩니다.

DEMO_MODE = _get_config("DEMO_MODE", "false").lower() == "true"


def check_env():
    """
    환경변수가 제대로 설정되었는지 확인

    Returns:
        bool: 설정 완료 여부
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("⚠️  .env 파일에 SUPABASE_URL, SUPABASE_KEY를 설정하세요.")
        return False
    return True