"""
receipt_draft.py - 파이프라인 결과 도메인 모델

담당: OCR
설명: 파이프라인 내부 결과를 외부 제공용 JSON 구조로 변환
    - 내부 구현 변경과 외부 인터페이스를 분리
    - meta(이미지/검증상태), receipt(추출 데이터), audit(이벤트 로그) 구조로 반환
"""

def to_receipt_draft(pipeline_result: dict) -> dict:
    """
    파이프라인 결과를 외부 제공용 JSON 구조로 변환
    내부 구조 변경과 분리
    """

    return {
        "meta": {
            "image_path": pipeline_result.get("image_path"),
            "validation_status": pipeline_result.get("validation_status", "success")
        },

        "receipt": {
            "store_name": pipeline_result.get("store_name"),
            "date": pipeline_result.get("transaction_date"),
            "total": pipeline_result.get("total"),
            "payment": pipeline_result.get("payment"),
            "category": pipeline_result.get("category"),
            "items": pipeline_result.get("items", [])
        },

        "audit": {
            "events": pipeline_result.get("events", [])
        }
    }