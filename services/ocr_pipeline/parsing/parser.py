"""
parser.py - 영수증 텍스트 파싱

담당: OCR
설명: OCR 추출 텍스트에서 구조화된 영수증 데이터 추출
    - 가게명: 브랜드 사전 + 휴리스틱 점수 기반 탐색
    - 날짜: 정규식 패턴 매칭
    - 합계금액: 우선순위 키워드 + fallback 후보 수집
    - 결제수단: 하단 15줄 기반 탐색 (페이/현금/카드)
    - 카테고리: 가게명 → 품목 순서 사전 분류
    - 품목: 단일 라인 및 분리된 라인 탐색 후 중복 제거
"""

import re
from datetime import datetime

from .dict.store_dict import BRAND_KEYWORDS
from .dict.store_dict import STORE_GENERIC
from .dict.store_dict import STORE_CATEGORY_RULES
from .dict.item_dict import ITEM_CATEGORY_RULES

# --------------------------------------------------
# 1️⃣ Store Name
# --------------------------------------------------

def normalize_text(t):
    return re.sub(r"[^A-Z0-9가-힣]", "", t.upper())


def extract_store_name(lines):

    # 🔹 VAN / 결제사 차단
    VAN_BLOCK = [
        "KOCES","KICC","한국신용카드","신용카드","신용매출"
    ]

    # --------------------------------------------------
    # 1️⃣ 브랜드 사전 탐색
    # --------------------------------------------------
    for text in lines[:10]:

        if any(v in text for v in VAN_BLOCK):
            continue

        text_norm = normalize_text(text)

        for brand in BRAND_KEYWORDS:

            brand_norm = normalize_text(brand)

            if brand_norm in text_norm:
                return text.strip()

    BLOCK_KEYWORDS = [
        "사업자","TEL","전화","합계","총액",
        "카드","단가","수량","금액","상품",
        "고객용","주문","요청","주소",
        "대한민국","고객","APP","메뉴"
    ]

    candidates = lines[:10]

    best_score = -999
    best_text = ""

    # --------------------------------------------------
    # 2️⃣ 휴리스틱 점수 기반 탐색
    # --------------------------------------------------
    for text in candidates:

        if "가맹점주소" in text:
            continue

        if "신고안내" in text:
            continue

        if any(v in text for v in VAN_BLOCK):
            continue

        score = 0

        if re.search(r"[가-힣A-Za-z]", text):
            score += 2

        if not re.search(r"\d", text):
            score += 2

        if 2 <= len(text) <= 25:
            score += 1

        if re.match(r"^[A-Za-z&\-\s]+$", text):
            score += 3

        if re.search(r"\d{2,}", text):
            score -= 3

        if any(k in text for k in BLOCK_KEYWORDS):
            score -= 5

        if any(g in text.lower() for g in STORE_GENERIC):
            score += 2

        if score > best_score:
            best_score = score
            best_text = text

    if best_text:
        return best_text.strip()

    # --------------------------------------------------
    # 3️⃣ 매장 필드 regex (마지막 fallback)
    # --------------------------------------------------
    store_patterns = [
        r"주문\s*매장\s*[:：]\s*(.+)",
        r"상호\s*[:：]\s*(.+)",
        r"매장명\s*[:：]\s*(.+)",
        r"가맹점명\s*[:：]\s*(.+)",
    ]

    for text in lines:

        for p in store_patterns:

            m = re.search(p, text)

            if m:

                name = m.group(1).strip()

                if "가맹점주소" in name:
                    continue

                if 2 <= len(name) <= 30:
                    return name

    return ""


# --------------------------------------------------
# 2️⃣ Date
# --------------------------------------------------
def extract_date(lines):

    full_text = "\n".join(lines)

    patterns = [
        r"(\d{4}|\d{2})[-./년\s]+(\d{1,2})[-./월\s]+(\d{1,2})",
        r"(\d{4})(\d{2})(\d{2})"
    ]

    for pattern in patterns:
        for m in re.finditer(pattern, full_text):
            y, mth, d = m.groups()

            if len(y) == 2:
                y = "20" + y

            try:
                dt = datetime(int(y), int(mth), int(d))
                if 2010 <= dt.year <= 2030:
                    return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

    return ""

# --------------------------------------------------
# 2️⃣ Date
# --------------------------------------------------
def extract_date(lines):

    full_text = "\n".join(lines)

    patterns = [
        r"(\d{4}|\d{2})[-./년\s]+(\d{1,2})[-./월\s]+(\d{1,2})",
        r"(\d{4})(\d{2})(\d{2})"
    ]

    for pattern in patterns:
        for m in re.finditer(pattern, full_text):
            y, mth, d = m.groups()

            if len(y) == 2:
                y = "20" + y

            try:
                dt = datetime(int(y), int(mth), int(d))
                if 2010 <= dt.year <= 2030:
                    return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

    return ""


# --------------------------------------------------
# 3️⃣ Total 계층형 구조로 교체
# --------------------------------------------------
def extract_total(lines):

    EXCLUDE_KEYWORDS = [
        "받은금액", "상품권", "거스름", "내신금액", "면세", "과세", "부가세", "세액",
        "단가", "수량", "상품코드", "상품명", "품목", "가격", "할인", "할인액", "총할인*", "적립", "포인트", "쿠폰", "잔액",
        "예금", "계좌", "카드번호", "승인번호", "사업자등록번호", "전화번호", "주소", "대표자", "사업자", 
        "상호", "매장", "가맹점", "주문", "요청", "APP", "고객", "고객용", "대한민국", "영수증", "영수증용",
        "세금계산서", "계산서", "청구서", "명세서"
        ]

    PRIORITY_KEYWORDS = [
        "카드청구액", "결제대상금액", "결제금액", "결제액", "결제금", "합계", "총액", "총합계", "총금액", "총",
        "총합", "계", "총계", "금액", "청구금액", "청구액", "지불금액", "지불액", "실결제금액", "실결제액"
        "실제결제금액", "실제결제액"
    ]    

    # 1️⃣ 우선순위 기반 탐색
    for keyword in PRIORITY_KEYWORDS:
        for i, text in enumerate(lines):
            if keyword in text:

                # 같은 줄 숫자
                nums = re.findall(r"\d{1,3}(?:,\d{3})+", text)
                if nums:
                    return int(nums[-1].replace(",", ""))

                # 다음 줄 탐색
                if i + 1 < len(lines):
                    nums = re.findall(r"\d{1,3}(?:,\d{3})+", lines[i+1])
                    if nums:
                        return int(nums[-1].replace(",", ""))

    # 2️⃣ fallback 후보 수집
    candidates = []

    for text in lines:
        clean = text.replace(" ", "")

        # 할인(-) 제외
        if "-" in text:
            continue

        # 세금/단가 제외
        if any(k in clean for k in EXCLUDE_KEYWORDS):
            continue

        nums = re.findall(r"\d{1,3}(?:,\d{3})+", text)

        for n in nums:
            val = int(n.replace(",", ""))
            if val >= 500:
                candidates.append(val)

    return max(candidates) if candidates else 0


# --------------------------------------------------
# 2️⃣ Date
# --------------------------------------------------
def extract_date(lines):

    full_text = "\n".join(lines)

    patterns = [
        r"(\d{4}|\d{2})[-./년\s]+(\d{1,2})[-./월\s]+(\d{1,2})",
        r"(\d{4})(\d{2})(\d{2})"
    ]

    for pattern in patterns:
        for m in re.finditer(pattern, full_text):
            y, mth, d = m.groups()

            if len(y) == 2:
                y = "20" + y

            try:
                dt = datetime(int(y), int(mth), int(d))
                if 2010 <= dt.year <= 2030:
                    return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

    return ""


# --------------------------------------------------
# 4️⃣ Payment
# --------------------------------------------------
def extract_payment(lines):

    # 하단 15줄만 탐색 (결제 영역)
    target_lines = lines[-15:]

    PAYMENT_PRIORITY = [
        ("페이", "app"),
        ("현금", "cash"),
        ("카드", "card"),
    ]

    for keyword, label in PAYMENT_PRIORITY:
        for text in target_lines:

            # 환불 안내 문구 제외
            if "환불" in text or "지참" in text or "영수증" in text:
                continue

            if keyword in text:
                return label

    return ""


# --------------------------------------------------
# 5️⃣ Category
# --------------------------------------------------
def classify_category(store_name, full_text):

    store_upper = store_name.upper()
    text_upper = full_text.upper()

    # 1️⃣ store 기반 분류
    for category, keywords in STORE_CATEGORY_RULES.items():
        for kw in keywords:
            if kw.upper() in store_upper:
                return category

    # 2️⃣ 품목 기반 분류
    for category, keywords in ITEM_CATEGORY_RULES.items():
        for kw in keywords:
            if kw.upper() in text_upper:
                return category

    return "기타"


# --------------------------------------------------
# 6️⃣ Items 추출 추가
# --------------------------------------------------
def extract_items(lines):

    EXCLUDE_KEYWORDS = [
        "%", "APP", "P", "가격", "가맹점", "거스름", "고객", "고객용",
        "과세", "계산서", "계좌", "대한민국", "단가", "대표", "대표자",
        "매장", "면세", "명세서", "부가세", "사업자", "사업자등록번호",
        "상호", "세금", "세금계산서", "세액", "수량", "승인", "승인번호",
        "영수증", "영수증용", "예금", "요청", "주소", "점", "주문", "전화",
        "전화번호", "총액", "총합", "총할인*", "카드", "카드번호",
        "쿠폰", "내신금액", "상품권", "상품코드", "적립", "포인트",
        "판매", "합계", "현금",

        # 🔹 추가 노이즈 필터
        "결제", "지불", "청구", "금액", "잔액", "번호", "CATID",
        "POS", "KOCES", "KICC", "NO", "소계", "총계"
    ]

    items = []

    # 전체 total 한번 계산
    total_value = extract_total(lines)

    # --------------------------------------------------
    # 1️⃣ single line item 탐색
    # --------------------------------------------------
    for text in lines:

        price_match = re.search(r"\d{1,3}(?:,\d{3})+", text)

        if not price_match:
            continue

        if any(k in text for k in EXCLUDE_KEYWORDS):
            continue

        price = int(price_match.group().replace(",", ""))

        if price < 500:
            continue

        # total과 동일한 값 제거
        if price == total_value:
            continue

        # 가격이 줄 끝에 있는 경우만
        if not text.strip().endswith(price_match.group()):
            continue

        name = text.replace(price_match.group(), "").strip()

        if len(name) < 2:
            continue

        # 1️⃣ 한글 없는 항목 제거 (숫자, 코드 제거)
        if not re.search(r"[가-힣]", name):
            continue

        # 2️⃣ 세금 / 결제 라인 제거
        if re.search(r"(세|부가세|결제|합계|총액|금액)", name):
            continue

        # 3️⃣ 너무 긴 텍스트 제거 (영수증 설명문 방지)
        if len(name) > 25:
            continue

        normalized = normalize_item(name)

        items.append({
            "name": name,          
            "normalized": normalized, 
            "price": price,
            "qty": 1,
            "line_text": text
        })

    # --------------------------------------------------
    # 2️⃣ item + price 분리된 경우
    # --------------------------------------------------
    for i in range(len(lines)-1):

        item_line = lines[i]
        price_line = lines[i+1]

        if len(item_line) > 40:
            continue

        if any(k in item_line for k in EXCLUDE_KEYWORDS):
            continue

        price = extract_price(price_line)

        if not price:
            continue

        if price == total_value:
            continue

        name = item_line.strip()

        if len(name) < 2:
            continue

        if re.fullmatch(r"[0-9\-* ]+", name):
            continue

        name = normalize_item(name)

        items.append({
            "name": name,
            "price": price,
            "qty": 1,
            "line_text": item_line + " | " + price_line
        })

    # --------------------------------------------------
    # 3️⃣ dedupe
    # --------------------------------------------------
    unique = []
    seen = set()

    for item in items:
        key = (item["name"], item["price"])

        if key not in seen:
            unique.append(item)
            seen.add(key)

    return unique


def extract_price(text):

    match = re.search(r"\d{1,3}(?:,\d{3})+", text)

    if not match:
        return None

    value = int(match.group().replace(",", ""))

    if value < 500:
        return None

    return value


# --------------------------------------------------
# item normalization
# --------------------------------------------------
def normalize_item(name):

    name_upper = name.upper()

    for _, keywords in ITEM_CATEGORY_RULES.items():
        for kw in keywords:
            if kw.upper() in name_upper:
                return kw

    return name


# --------------------------------------------------
# 최종 파이프라인 entry
# --------------------------------------------------
def parse_text(ocr_result: dict) -> dict:

    lines = [l.strip() for l in ocr_result["full_text"].split("\n") if l.strip()]

    store = extract_store_name(lines)
    date = extract_date(lines)
    total = extract_total(lines)
    payment = extract_payment(lines)
    category = classify_category(store, ocr_result["full_text"])
    items = extract_items(lines)
    full_text = ocr_result["full_text"]

    # 배달/포장 fallback
    if (not store or len(store) < 2) and (
        "배달" in full_text or
        "포장" in full_text or
        "픽업" in full_text
    ):
        store = "배달/포장"
        category = "식비"

    return {
        "store_name": store,
        "transaction_date": date,
        "total": total,
        "payment": payment,
        "category": category,
        "items": items
    }