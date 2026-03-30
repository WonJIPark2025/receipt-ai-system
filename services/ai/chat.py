"""
chat.py - 최근 12개월 지출 데이터 기반 챗봇

담당: AI
설명: 최근 12개월 영수증 데이터를 컨텍스트로 Gemini와 대화
    - 대화 히스토리 유지 (messages 리스트)
    - 컨텍스트는 매 호출 시 최신 12개월 데이터로 갱신
"""

import json
from datetime import datetime
from utils.config import GEMINI_API_KEY, DEFAULT_USER_ID
from backend.api.receipts import get_receipts_by_date_range
from backend.api.receipt_items import get_items_by_receipt


PURCHASE_TYPE_KO = {
    "general":  "간편",
    "delivery": "배달",
    "takeout":  "포장",
    "dine_in":  "매장",
    "cooking":  "직접 요리",
}

ACTIVITY_TAG_KO = {
    "caffeine":   "카페인",
    "alcohol":    "음주",
    "late_snack": "야식",
}


def _load_12month_context() -> str:
    """최근 12개월 지출 데이터를 로드해 프롬프트용 컨텍스트 문자열로 변환"""
    now = datetime.now()
    cutoff_month = now.month - 11
    cutoff_year  = now.year
    if cutoff_month <= 0:
        cutoff_month += 12
        cutoff_year  -= 1
    start = f"{cutoff_year}-{cutoff_month:02d}-01T00:00:00+09:00"
    end   = now.strftime("%Y-%m-%dT23:59:59+09:00")

    receipts = get_receipts_by_date_range(DEFAULT_USER_ID, start, end)
    if not receipts:
        return ""

    data = []
    for r in receipts:
        items = get_items_by_receipt(r["id"])
        tags = [
            ACTIVITY_TAG_KO[i["activity_tag"]]
            for i in items
            if i.get("activity_tag") in ACTIVITY_TAG_KO
        ]
        entry = {
            "날짜":     r["paid_at"][:10],
            "상호명":   r.get("store_name", ""),
            "금액":     r.get("total_amount", 0),
            "구매방식": PURCHASE_TYPE_KO.get(r.get("purchase_type"), "미분류"),
        }
        if tags:
            entry["태그"] = tags
        if r.get("memo"):
            entry["메모"] = r["memo"]
        data.append(entry)

    total = sum(r.get("total_amount", 0) for r in receipts)
    return (
        f"최근 12개월 지출 데이터 (총 {len(receipts)}건, 합계 {total:,}원)\n"
        + json.dumps(data, ensure_ascii=False, indent=2)
    )


def chat(messages: list[dict]) -> str:
    """
    최근 12개월 지출 데이터를 컨텍스트로 Gemini와 대화

    Args:
        messages : [{"role": "user"|"assistant", "content": str}, ...]
                   마지막 항목이 현재 사용자 질문

    Returns:
        str: Gemini 답변
    """
    if not GEMINI_API_KEY:
        return "GEMINI_API_KEY가 설정되지 않았습니다."

    from google import genai
    from google.genai import types

    context = _load_12month_context()
    if not context:
        return "지출 데이터가 없습니다."

    system_prompt = (
        "당신은 사용자의 지출 데이터를 분석하는 가계부 AI 어시스턴트입니다. "
        "아래 최근 12개월 데이터를 바탕으로 질문에 간결하고 구체적으로 답하세요. "
        "불필요한 서론 없이 핵심만 답하세요.\n\n"
        f"[데이터]\n{context}"
    )

    history = []
    for msg in messages[:-1]:
        role = "user" if msg["role"] == "user" else "model"
        history.append(types.Content(role=role, parts=[types.Part(text=msg["content"])]))

    client = genai.Client(api_key=GEMINI_API_KEY)
    chat_session = client.chats.create(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(system_instruction=system_prompt),
        history=history,
    )

    response = chat_session.send_message(messages[-1]["content"])
    return response.text
