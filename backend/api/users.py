"""
users.py - 사용자 API

담당: 백엔드
설명: users 테이블 CRUD 함수
    - create_user, get_user_by_id, get_user_by_user_id
    - get_all_users, update_user, delete_user
"""

from backend.database import get_client
from backend.models import TABLE_USERS


# =============================================================================
# CREATE - 사용자 생성
# =============================================================================
def create_user(name: str, user_id: str, password: str, tel: str = None) -> dict:
    """
    새 사용자 생성

    Args:
        name: 사용자 이름
        user_id: 로그인 ID (유니크)
        password: 비밀번호
        tel: 전화번호 (선택)

    Returns:
        dict: 생성된 사용자 데이터

    사용 예시:
        user = create_user("홍길동", "hong123", "password123", "010-1234-5678")
    """
    client = get_client()
    data = {
        "name": name,
        "user_id": user_id,
        "password": password,  # 실제 서비스에서는 해시 처리 필요
        "tel": tel
    }
    result = client.table(TABLE_USERS).insert(data).execute()
    return result.data[0] if result.data else None


# =============================================================================
# READ - 사용자 조회
# =============================================================================
def get_user_by_id(id: int) -> dict:
    """
    ID로 사용자 조회

    Args:
        id: 사용자 PK

    Returns:
        dict: 사용자 데이터 또는 None
    """
    client = get_client()
    result = client.table(TABLE_USERS).select("*").eq("id", id).execute()
    return result.data[0] if result.data else None


def get_user_by_user_id(user_id: str) -> dict:
    """
    로그인 ID로 사용자 조회

    Args:
        user_id: 로그인 ID

    Returns:
        dict: 사용자 데이터 또는 None
    """
    client = get_client()
    result = client.table(TABLE_USERS).select("*").eq("user_id", user_id).execute()
    return result.data[0] if result.data else None


def get_all_users() -> list:
    """
    전체 사용자 목록 조회

    Returns:
        list: 사용자 데이터 리스트
    """
    client = get_client()
    result = client.table(TABLE_USERS).select("*").execute()
    return result.data


# =============================================================================
# UPDATE - 사용자 수정
# =============================================================================
def update_user(id: int, **kwargs) -> dict:
    """
    사용자 정보 수정

    Args:
        id: 사용자 PK
        **kwargs: 수정할 필드 (name, password, tel)

    Returns:
        dict: 수정된 사용자 데이터

    사용 예시:
        update_user(1, name="김철수", tel="010-9999-8888")
    """
    client = get_client()
    result = client.table(TABLE_USERS).update(kwargs).eq("id", id).execute()
    return result.data[0] if result.data else None


# =============================================================================
# DELETE - 사용자 삭제
# =============================================================================
def delete_user(id: int) -> bool:
    """
    사용자 삭제

    Args:
        id: 사용자 PK

    Returns:
        bool: 삭제 성공 여부
    """
    client = get_client()
    result = client.table(TABLE_USERS).delete().eq("id", id).execute()
    return len(result.data) > 0