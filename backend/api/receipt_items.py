# =============================================================================
# receipt_items.py - 품목 API
# =============================================================================
# 담당: 백엔드
# 설명: receipt_items 테이블 CRUD 함수
#       - receipts.details JSONB 를 정규화한 테이블 (v2 신규)
#       - activity_tag 로 품목별 행동 패턴 분류
#       - 영수증 삭제 시 CASCADE 로 자동 삭제됨
# =============================================================================

from backend.database import get_client
from backend.models import TABLE_RECEIPT_ITEMS


# =============================================================================
# CREATE - 품목 일괄 저장
# =============================================================================
def create_receipt_items(receipt_id: int, items: list) -> list:
    """
    영수증 품목 일괄 저장

    Args:
        receipt_id : 영수증 FK (receipts.id)
        items      : 품목 리스트
                     예: [
                           {"name": "아메리카노", "quantity": 2, "price": 4500,
                            "activity_tag": "caffeine"},
                           {"name": "케이크", "quantity": 1, "price": 6000}
                         ]

    Returns:
        list: 저장된 품목 데이터 리스트

    사용 예시:
        items = create_receipt_items(
            receipt_id=42,
            items=[
                {"name": "맥주", "quantity": 2, "price": 3000, "activity_tag": "alcohol"},
                {"name": "치킨", "quantity": 1, "price": 18000, "activity_tag": "fast_food"},
            ]
        )
    """
    if not items:
        return []

    client = get_client()
    payload = [
        {
            "receipt_id":   receipt_id,
            "name":         item.get("name"),
            "quantity":     item.get("quantity"),
            "price":        item.get("price"),
            "activity_tag": item.get("activity_tag"),   # None 허용
        }
        for item in items
    ]
    result = client.table(TABLE_RECEIPT_ITEMS).insert(payload).execute()
    return result.data


# =============================================================================
# READ - 품목 조회
# =============================================================================
def get_items_by_receipt(receipt_id: int) -> list:
    """
    특정 영수증의 품목 목록 조회

    Args:
        receipt_id: 영수증 FK

    Returns:
        list: 품목 데이터 리스트
    """
    client = get_client()
    result = (
        client.table(TABLE_RECEIPT_ITEMS)
        .select("*")
        .eq("receipt_id", receipt_id)
        .execute()
    )
    return result.data


def get_items_by_activity_tag(tag: str, user_id: int = None) -> list:
    """
    특정 activity_tag 품목 조회 (통계·패턴 분석용)

    Args:
        tag     : activity_tag 값 (예: "caffeine", "alcohol")
        user_id : 사용자 필터 (None이면 전체 조회)

    Returns:
        list: 품목 + 영수증 결합 데이터

    사용 예시:
        # 이번 달 카페인 품목 전체 조회
        caffeine_items = get_items_by_activity_tag("caffeine", user_id=1)
    """
    client = get_client()

    if user_id is not None:
        # receipt_id → receipts.user_id 조인이 필요하므로 select 확장
        result = (
            client.table(TABLE_RECEIPT_ITEMS)
            .select("*, receipts!inner(user_id, paid_at, store_name)")
            .eq("activity_tag", tag)
            .eq("receipts.user_id", user_id)
            .execute()
        )
    else:
        result = (
            client.table(TABLE_RECEIPT_ITEMS)
            .select("*, receipts(paid_at, store_name)")
            .eq("activity_tag", tag)
            .execute()
        )

    return result.data


# =============================================================================
# DELETE - 품목 삭제
# =============================================================================
def delete_items_by_receipt(receipt_id: int) -> bool:
    """
    특정 영수증의 품목 전체 삭제
    (receipts 삭제 시 CASCADE 로 자동 처리되므로 수동 호출은 재처리 시 활용)

    Args:
        receipt_id: 영수증 FK

    Returns:
        bool: 삭제 성공 여부
    """
    client = get_client()
    result = (
        client.table(TABLE_RECEIPT_ITEMS)
        .delete()
        .eq("receipt_id", receipt_id)
        .execute()
    )
    return len(result.data) > 0
