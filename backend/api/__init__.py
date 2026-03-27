# =============================================================================
# backend/api/ - API 모듈 패키지
# =============================================================================
# 담당: 백엔드
# 설명: 테이블별 CRUD API를 분리하여 관리
#       - categories.py      : 카테고리 관련 API
#       - receipts.py        : 영수증 관련 API
#       - receipt_items.py   : 영수증 품목 관련 API
#       - receipt_embeddings.py : RAG 임베딩 관련 API
#       - storage.py         : Supabase Storage API
# =============================================================================

from backend.api.categories import (
    create_category,
    get_category_by_id,
    get_all_categories,
    update_category,
    delete_category,
)
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
from backend.api.receipt_items import (
    create_receipt_items,
    get_items_by_receipt,
    get_items_by_activity_tag,
    delete_items_by_receipt,
)
from backend.api.receipt_embeddings import (
    save_embedding,
    search_similar,
)
from backend.api.storage import (
    upload_image,
    get_public_url,
    list_files,
    delete_image,
)
