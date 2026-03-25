"""
api.py - API 모듈 통합 진입점

담당: 백엔드
설명: 모든 API 함수를 한 곳에서 import할 수 있도록 제공
    - 실제 구현은 backend/api/ 폴더에 테이블별로 분리
예시:
    from backend.api import create_user, get_all_receipts
    from backend.api.users import create_user
"""

# 사용자 API
from backend.api.users import (
    create_user,
    get_user_by_id,
    get_user_by_user_id,
    get_all_users,
    update_user,
    delete_user,
)

# 카테고리 API
from backend.api.categories import (
    create_category,
    get_category_by_id,
    get_all_categories,
    update_category,
    delete_category,
)

# 결제수단 API
from backend.api.payment_methods import (
    create_payment_method,
    get_payment_method_by_id,
    get_all_payment_methods,
    update_payment_method,
    delete_payment_method,
)

# 영수증 API
from backend.api.receipts import (
    create_receipt,
    get_receipt_by_id,
    get_receipts_by_user,
    get_receipts_by_category,
    get_receipts_by_date_range,
    get_all_receipts,
    update_receipt,
    delete_receipt,
)