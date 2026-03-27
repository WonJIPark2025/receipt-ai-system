"""
test_gemini.py - Gemini 단일 이미지 테스트

실행: python -m tests.test_ai.scripts.test_gemini
"""

import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.append(str(PROJECT_ROOT))

from utils.config import GEMINI_API_KEY

IMAGE_PATH = PROJECT_ROOT / "data" / "receipts" / "v01_eval" / "r1.jpg"
MODEL = "gemini-2.0-flash"


def test():
    if not GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY가 설정되지 않았습니다.")
        return

    print(f"모델  : {MODEL}")
    print(f"이미지: {IMAGE_PATH.name}")
    print("-" * 40)

    from services.ai.gemini import PROMPT
    from google import genai
    from google.genai import types

    with open(IMAGE_PATH, "rb") as f:
        image_bytes = f.read()

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            PROMPT,
        ],
    )

    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    result = json.loads(text)

    print(f"store_name   : {result.get('store_name')}")
    print(f"date         : {result.get('date')}")
    print(f"total        : {result.get('total')}")
    print(f"category     : {result.get('category')}")
    print(f"purchase_type: {result.get('purchase_type')}")
    print(f"items ({len(result.get('items', []))}건):")
    for item in result.get("items", []):
        print(f"  - {item.get('name')} x{item.get('quantity')} {item.get('price')}원")
    print("-" * 40)
    print(f"raw_text 길이: {len(result.get('raw_text', ''))}자")


if __name__ == "__main__":
    test()
