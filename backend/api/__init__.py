# =============================================================================
# backend/api/ - API 모듈 패키지
# =============================================================================
# 담당: 백엔드
# 설명: 테이블별 CRUD API를 분리하여 관리
#       - categories.py: 카테고리 관련 API
#       - receipts.py: 영수증 관련 API
#       - receipt_items.py: 영수증 품목 관련 API
#       - storage.py: Supabase Storage API
# =============================================================================

from backend.api.categories import *
from backend.api.receipts import *
from backend.api.receipt_items import *
from backend.api.storage import *
