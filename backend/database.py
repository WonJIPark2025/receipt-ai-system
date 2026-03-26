"""
database.py - Supabase 데이터베이스 연결

담당: 백엔드
설명: Supabase 클라이언트 생성 및 연결 관리
    - 싱글톤 패턴으로 앱 전체에서 하나의 클라이언트 공유
    - 연결 상태 확인 함수 제공
예시:
    from backend.database import get_client
    client = get_client()
"""

from supabase import create_client, Client
from utils.config import SUPABASE_URL, SUPABASE_KEY, check_env

# =============================================================================
# Supabase 클라이언트 (싱글톤)
# =============================================================================
# 앱 전체에서 하나의 클라이언트를 공유합니다.
# 사용법: from backend.database import supabase
# =============================================================================

supabase: Client = None


def get_client() -> Client:
    """
    Supabase 클라이언트 반환 (싱글톤 패턴)

    Returns:
        Client: Supabase 클라이언트 객체

    사용 예시:
        from backend.database import get_client
        client = get_client()
        data = client.table("users").select("*").execute()
    """
    global supabase

    if supabase is None:
        if not check_env():
            raise ValueError("Supabase 환경변수가 설정되지 않았습니다.")
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    return supabase


def test_connection() -> bool:
    """
    Supabase 연결 테스트

    Returns:
        bool: 연결 성공 여부

    사용 예시:
        from backend.database import test_connection
        if test_connection():
            print("연결 성공!")
    """
    try:
        client = get_client()
        # 간단한 쿼리로 연결 확인
        client.table("categories").select("id").limit(1).execute()
        return True
    except Exception as e:
        print(f"❌ 연결 실패: {e}")
        return False