# =============================================================================
# receipts.py - 영수증 API
# =============================================================================
# 담당: 백엔드
# 설명: receipts 테이블 CRUD 함수 (핵심 테이블)
#       - users, categories, payment_methods를 FK로 참조
# =============================================================================

from backend.database import get_client
from backend.models import TABLE_RECEIPTS


# =============================================================================
# CREATE - 영수증 생성
# =============================================================================
def create_receipt(
    user_id: int,
    category_id: int,
    payment_method_id: int,
    date: str,
    total_amount: int,
    store_name: str,
    image_path: str = None,
    details: list = None
) -> dict:
    """
    새 영수증 생성

    Args:
        user_id: 사용자 FK (users.id)
        category_id: 카테고리 FK (categories.id)
        payment_method_id: 결제수단 FK (payment_methods.id)
        date: 결제 날짜 (예: "2024-01-15")
        total_amount: 총 금액
        store_name: 상호명
        image_path: 영수증 이미지 경로 (선택)
        details: 상세 항목 리스트 (선택)
                 예: [{"name": "아메리카노", "quantity": 2, "price": 4500}]

    Returns:
        dict: 생성된 영수증 데이터

    사용 예시:
        receipt = create_receipt(
            user_id=1,
            category_id=1,
            payment_method_id=1,
            date="2024-01-15",
            total_amount=15000,
            store_name="스타벅스",
            details=[{"name": "아메리카노", "quantity": 2, "price": 4500}]
        )
    """
    client = get_client()
    data = {
        "user_id": user_id,
        "category_id": category_id,
        "payment_method_id": payment_method_id,
        "date": date,
        "total_amount": total_amount,
        "store_name": store_name,
        "image_path": image_path,
        "details": details
    }
    result = client.table(TABLE_RECEIPTS).insert(data).execute()
    return result.data[0] if result.data else None


# =============================================================================
# READ - 영수증 조회
# =============================================================================
def get_receipt_by_id(id: int) -> dict:
    """
    ID로 영수증 조회

    Args:
        id: 영수증 PK

    Returns:
        dict: 영수증 데이터 또는 None
    """
    client = get_client()
    result = client.table(TABLE_RECEIPTS).select("*").eq("id", id).execute()
    return result.data[0] if result.data else None


def get_receipts_by_user(user_id: int) -> list:
    """
    특정 사용자의 영수증 목록 조회

    Args:
        user_id: 사용자 FK

    Returns:
        list: 영수증 데이터 리스트
    """
    client = get_client()
    result = client.table(TABLE_RECEIPTS).select("*").eq("user_id", user_id).execute()
    return result.data


def get_receipts_by_category(category_id: int) -> list:
    """
    특정 카테고리의 영수증 목록 조회

    Args:
        category_id: 카테고리 FK

    Returns:
        list: 영수증 데이터 리스트
    """
    client = get_client()
    result = client.table(TABLE_RECEIPTS).select("*").eq("category_id", category_id).execute()
    return result.data


def get_receipts_by_date_range(user_id: int, start_date: str, end_date: str) -> list:
    """
    특정 기간의 영수증 목록 조회

    Args:
        user_id: 사용자 FK
        start_date: 시작 날짜 (예: "2024-01-01")
        end_date: 종료 날짜 (예: "2024-01-31")

    Returns:
        list: 영수증 데이터 리스트
    """
    client = get_client()
    result = (
        client.table(TABLE_RECEIPTS)
        .select("*")
        .eq("user_id", user_id)
        .gte("date", start_date)
        .lte("date", end_date)
        .execute()
    )
    return result.data


def get_all_receipts() -> list:
    """
    전체 영수증 목록 조회

    Returns:
        list: 영수증 데이터 리스트
    """
    client = get_client()
    result = client.table(TABLE_RECEIPTS).select("*").execute()
    return result.data


# =============================================================================
# UPDATE - 영수증 수정
# =============================================================================
def update_receipt(id: int, **kwargs) -> dict:
    """
    영수증 정보 수정

    Args:
        id: 영수증 PK
        **kwargs: 수정할 필드
                  (category_id, payment_method_id, date, total_amount,
                   store_name, image_path, details)

    Returns:
        dict: 수정된 영수증 데이터

    사용 예시:
        update_receipt(1, total_amount=20000, store_name="이디야")
    """
    client = get_client()
    result = client.table(TABLE_RECEIPTS).update(kwargs).eq("id", id).execute()
    return result.data[0] if result.data else None


# =============================================================================
# DELETE - 영수증 삭제
# =============================================================================
def delete_receipt(id: int) -> bool:
    """
    영수증 삭제

    Args:
        id: 영수증 PK

    Returns:
        bool: 삭제 성공 여부
    """
    client = get_client()
    result = client.table(TABLE_RECEIPTS).delete().eq("id", id).execute()
    return len(result.data) > 0