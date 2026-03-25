# =============================================================================
# receipts.py - 영수증 API
# =============================================================================
# 담당: 백엔드
# 설명: receipts 테이블 CRUD 함수
#       v2 스키마 기준:
#         - payment_method_id 제거
#         - date → paid_at (TIMESTAMPTZ)
#         - purchase_type, memo 필드 추가
#         - details(JSONB) 제거 → receipt_items 테이블로 분리
# =============================================================================

from backend.database import get_client
from backend.models import TABLE_RECEIPTS


# =============================================================================
# CREATE - 영수증 생성
# =============================================================================
def create_receipt(
    user_id: int,
    category_id: int,
    paid_at: str,
    total_amount: int,
    store_name: str,
    purchase_type: str = None,
    memo: str = None,
    image_path: str = None,
) -> dict:
    """
    새 영수증 생성

    Args:
        user_id       : 사용자 식별자
        category_id   : 카테고리 FK (1=식비 / 2=기타)
        paid_at       : 결제 일시 ISO 문자열 (예: "2024-01-15T21:30:00+09:00")
        total_amount  : 총 금액
        store_name    : 상호명
        purchase_type : 'delivery' | 'takeout' | 'dine_in' | 'cooking' | None
        memo          : 감정·상황 메모 (선택)
        image_path    : 영수증 이미지 경로 (선택)

    Returns:
        dict: 생성된 영수증 데이터 (receipt_id 포함)

    사용 예시:
        receipt = create_receipt(
            user_id=1,
            category_id=1,
            paid_at="2024-01-15T21:30:00+09:00",
            total_amount=15000,
            store_name="스타벅스",
            purchase_type="dine_in",
        )
    """
    client = get_client()
    data = {
        "user_id":       user_id,
        "category_id":   category_id,
        "paid_at":       paid_at,
        "total_amount":  total_amount,
        "store_name":    store_name,
        "purchase_type": purchase_type,
        "memo":          memo,
        "image_path":    image_path,
    }
    result = client.table(TABLE_RECEIPTS).insert(data).execute()
    return result.data[0] if result.data else None


# =============================================================================
# READ - 영수증 조회
# =============================================================================
def get_receipt_by_id(id: int) -> dict:
    """
    ID로 영수증 단건 조회

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
    특정 사용자의 영수증 목록 조회 (최신순)

    Args:
        user_id: 사용자 식별자

    Returns:
        list: 영수증 데이터 리스트
    """
    client = get_client()
    result = (
        client.table(TABLE_RECEIPTS)
        .select("*")
        .eq("user_id", user_id)
        .order("paid_at", desc=True)
        .execute()
    )
    return result.data


def get_receipts_by_date_range(user_id: int, start: str, end: str) -> list:
    """
    특정 기간의 영수증 목록 조회

    Args:
        user_id : 사용자 식별자
        start   : 시작 일시 (예: "2024-01-01T00:00:00+09:00")
        end     : 종료 일시 (예: "2024-01-31T23:59:59+09:00")

    Returns:
        list: 영수증 데이터 리스트
    """
    client = get_client()
    result = (
        client.table(TABLE_RECEIPTS)
        .select("*")
        .eq("user_id", user_id)
        .gte("paid_at", start)
        .lte("paid_at", end)
        .order("paid_at", desc=True)
        .execute()
    )
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
    result = (
        client.table(TABLE_RECEIPTS)
        .select("*")
        .eq("category_id", category_id)
        .execute()
    )
    return result.data


def get_all_receipts() -> list:
    """
    전체 영수증 목록 조회 (최신순)

    Returns:
        list: 영수증 데이터 리스트
    """
    client = get_client()
    result = (
        client.table(TABLE_RECEIPTS)
        .select("*")
        .order("paid_at", desc=True)
        .execute()
    )
    return result.data


# =============================================================================
# UPDATE - 영수증 수정
# =============================================================================
def update_receipt(id: int, **kwargs) -> dict:
    """
    영수증 정보 수정

    Args:
        id      : 영수증 PK
        **kwargs: 수정할 필드
                  (category_id, paid_at, total_amount, store_name,
                   purchase_type, memo, image_path)

    Returns:
        dict: 수정된 영수증 데이터

    사용 예시:
        update_receipt(1, memo="스트레스 받아서 야식", purchase_type="delivery")
    """
    client = get_client()
    result = client.table(TABLE_RECEIPTS).update(kwargs).eq("id", id).execute()
    return result.data[0] if result.data else None


# =============================================================================
# DELETE - 영수증 삭제
# =============================================================================
def delete_receipt(id: int) -> bool:
    """
    영수증 삭제 (receipt_items 는 CASCADE 로 자동 삭제)

    Args:
        id: 영수증 PK

    Returns:
        bool: 삭제 성공 여부
    """
    client = get_client()
    result = client.table(TABLE_RECEIPTS).delete().eq("id", id).execute()
    return len(result.data) > 0
