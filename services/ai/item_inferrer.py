"""
item_inferrer.py - 품목 자동 추출 (LLM fallback)

담당: AI
설명: parser.py가 품목을 추출하지 못한 경우 OCR raw text에서 LLM으로 품목 추출
    - 반환값: [{"name": str, "quantity": int, "price": int}, ...]
"""

import json
from utils.config import GEMINI_API_KEY


def infer_items(raw_text: str) -> list:
    """
    OCR raw text에서 품목 목록 추출

    Args:
        raw_text: OCR 추출 전체 텍스트

    Returns:
        list: [{"name": str, "quantity": int, "price": int}, ...]
              추론 실패 시 빈 리스트 반환
    """
    if not GEMINI_API_KEY:
        return []

    from google import genai

    prompt = f"""다음은 영수증 OCR 텍스트입니다.

[영수증 텍스트]
{raw_text[:1000]}

구매한 품목 목록을 JSON 배열로만 반환하세요. 다른 말은 하지 마세요.
합계, 부가세, 할인, 카드 정보는 제외하세요.

형식:
[
  {{"name": "품목명", "quantity": 1, "price": 5000}},
  ...
]

품목이 없으면 [] 를 반환하세요."""

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        text = response.text.strip()

        # 코드블록 제거
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        items = json.loads(text)

        return [
            {
                "name":     str(i.get("name", "")),
                "quantity": int(i.get("quantity", 1)),
                "price":    int(i.get("price", 0)),
            }
            for i in items
            if i.get("name")
        ]

    except Exception:
        return []
