"""
categories.py - 카테고리 API

담당: 백엔드
설명: categories 테이블 CRUD 함수
    - create_category, get_category_by_id
    - get_all_categories, update_category, delete_category
"""

from backend.database import get_client
from backend.models import TABLE_CATEGORIES


# =============================================================================
# CREATE - 카테고리 생성
# =============================================================================
def create_category(name: str, icon: str = None) -> dict:
    """
    새 카테고리 생성

    Args:
        name: 카테고리명 (유니크)
        icon: 아이콘 (선택, 예: "🍔", "🚗")

    Returns:
        dict: 생성된 카테고리 데이터

    사용 예시:
        category = create_category("식비", "🍔")
    """
    client = get_client()
    data = {"name": name, "icon": icon}
    result = client.table(TABLE_CATEGORIES).insert(data).execute()
    return result.data[0] if result.data else None


# =============================================================================
# READ - 카테고리 조회
# =============================================================================
def get_category_by_id(id: int) -> dict:
    """
    ID로 카테고리 조회

    Args:
        id: 카테고리 PK

    Returns:
        dict: 카테고리 데이터 또는 None
    """
    client = get_client()
    result = client.table(TABLE_CATEGORIES).select("*").eq("id", id).execute()
    return result.data[0] if result.data else None


def get_all_categories() -> list:
    """
    전체 카테고리 목록 조회

    Returns:
        list: 카테고리 데이터 리스트
    """
    client = get_client()
    result = client.table(TABLE_CATEGORIES).select("*").execute()
    return result.data


# =============================================================================
# UPDATE - 카테고리 수정
# =============================================================================
def update_category(id: int, **kwargs) -> dict:
    """
    카테고리 정보 수정

    Args:
        id: 카테고리 PK
        **kwargs: 수정할 필드 (name, icon)

    Returns:
        dict: 수정된 카테고리 데이터

    사용 예시:
        update_category(1, name="음식", icon="🍕")
    """
    client = get_client()
    result = client.table(TABLE_CATEGORIES).update(kwargs).eq("id", id).execute()
    return result.data[0] if result.data else None


# =============================================================================
# DELETE - 카테고리 삭제
# =============================================================================
def delete_category(id: int) -> bool:
    """
    카테고리 삭제

    Args:
        id: 카테고리 PK

    Returns:
        bool: 삭제 성공 여부
    """
    client = get_client()
    result = client.table(TABLE_CATEGORIES).delete().eq("id", id).execute()
    return len(result.data) > 0