"""
draft_builder.py - 파이프라인 결과 초안 생성

담당: OCR
설명: 파싱 결과로부터 파이프라인 결과 초안(draft) 딕셔너리 생성
    - OCR / Parsing / Backend 간 도메인 경계 역할
    - image_path, 파싱 필드, items, events 포함
"""

def build_draft(image_path: str, parsed: dict) -> dict:
    """
    파싱 결과로 부터 결과 초안(draft)을 만들기.

    도메인 경계:
    - OCR
    - Parsing
    - Downstream API / Backend

    Validation 층은 제거 v01.5
    """

    draft = {
        "image_path": image_path,

        # 파싱된 정보들
        "store_name": parsed.get("store_name"),
        "transaction_date": parsed.get("transaction_date"),
        "total": parsed.get("total"),
        "category": parsed.get("category"),

        # Items (현재 비활성 또는 빈 리스트 유지)
        "items": parsed.get("items", []),

        # 이벤트 로그 기록
        "events": []
    }

    return draft