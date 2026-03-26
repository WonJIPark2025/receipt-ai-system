"""
purchase_type_inferrer.py - 식사 방식 자동 추론

담당: AI
설명: OCR raw text + 품목 목록을 기반으로 식사 방식(purchase_type) 추론
    - Gemini LLM 사용
    - 반환값: "general" | "delivery" | "takeout" | "dine_in" | "cooking"
"""

from utils.config import GEMINI_API_KEY

VALID_TYPES = {"general", "delivery", "takeout", "dine_in", "cooking"}


def infer_purchase_type(raw_text: str, items: list) -> str:
    """
    OCR raw text와 품목 목록으로 식사 방식 추론

    Args:
        raw_text : OCR 추출 전체 텍스트
        items    : 파싱된 품목 리스트 [{"name": ..., "price": ...}, ...]

    Returns:
        str: "general" | "delivery" | "takeout" | "dine_in" | "cooking"
             추론 실패 시 "general" 반환
    """
    if not GEMINI_API_KEY:
        return "general"

    from google import genai

    item_names = ", ".join(i.get("name", "") for i in items if i.get("name"))

    prompt = f"""다음은 영수증 OCR 텍스트입니다.

[영수증 텍스트]
{raw_text[:800]}

[추출된 품목]
{item_names or "없음"}

이 영수증의 식사 방식을 아래 중 하나로만 답하세요. 다른 말은 하지 마세요.

- delivery  : 배달 앱/전화 주문 (배달비, 배달팁, 배달의민족, 쿠팡이츠 등)
- takeout   : 식당/카페에서 포장
- dine_in   : 식당/카페에서 직접 취식
- cooking   : 마트/시장에서 식재료 구매 후 직접 요리
- general   : 편의점, 마트 간식, 기타 일반 구매

답변:"""

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        result = response.text.strip().lower()

        return result if result in VALID_TYPES else "general"

    except Exception:
        return "general"
