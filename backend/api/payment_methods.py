"""
payment_methods.py - 결제수단 API

담당: 백엔드
설명: payment_methods 테이블 CRUD 함수
    - create_payment_method, get_payment_method_by_id
    - get_all_payment_methods, update_payment_method, delete_payment_method
"""

from backend.database import get_client
from backend.models import TABLE_PAYMENT_METHODS


# =============================================================================
# CREATE - 결제수단 생성
# =============================================================================
def create_payment_method(name: str) -> dict:
    """
    새 결제수단 생성

    Args:
        name: 결제수단명 (유니크, 예: "현금", "카드")

    Returns:
        dict: 생성된 결제수단 데이터

    사용 예시:
        method = create_payment_method("신용카드")
    """
    client = get_client()
    data = {"name": name}
    result = client.table(TABLE_PAYMENT_METHODS).insert(data).execute()
    return result.data[0] if result.data else None


# =============================================================================
# READ - 결제수단 조회
# =============================================================================
def get_payment_method_by_id(id: int) -> dict:
    """
    ID로 결제수단 조회

    Args:
        id: 결제수단 PK

    Returns:
        dict: 결제수단 데이터 또는 None
    """
    client = get_client()
    result = client.table(TABLE_PAYMENT_METHODS).select("*").eq("id", id).execute()
    return result.data[0] if result.data else None


def get_all_payment_methods() -> list:
    """
    전체 결제수단 목록 조회

    Returns:
        list: 결제수단 데이터 리스트
    """
    client = get_client()
    result = client.table(TABLE_PAYMENT_METHODS).select("*").execute()
    return result.data


# =============================================================================
# UPDATE - 결제수단 수정
# =============================================================================
def update_payment_method(id: int, name: str) -> dict:
    """
    결제수단 정보 수정

    Args:
        id: 결제수단 PK
        name: 새 결제수단명

    Returns:
        dict: 수정된 결제수단 데이터

    사용 예시:
        update_payment_method(1, "체크카드")
    """
    client = get_client()
    result = client.table(TABLE_PAYMENT_METHODS).update({"name": name}).eq("id", id).execute()
    return result.data[0] if result.data else None


# =============================================================================
# DELETE - 결제수단 삭제
# =============================================================================
def delete_payment_method(id: int) -> bool:
    """
    결제수단 삭제

    Args:
        id: 결제수단 PK

    Returns:
        bool: 삭제 성공 여부
    """
    client = get_client()
    result = client.table(TABLE_PAYMENT_METHODS).delete().eq("id", id).execute()
    return len(result.data) > 0