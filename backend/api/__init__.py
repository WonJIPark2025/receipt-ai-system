# =============================================================================
# backend/api/ - API 모듈 패키지
# =============================================================================
# 담당: 백엔드
# 설명: 테이블별 CRUD API를 분리하여 관리
#       - users.py: 사용자 관련 API
#       - categories.py: 카테고리 관련 API
#       - payment_methods.py: 결제수단 관련 API
#       - receipts.py: 영수증 관련 API
# =============================================================================

from backend.api.users import *
from backend.api.categories import *
from backend.api.payment_methods import *
from backend.api.receipts import *