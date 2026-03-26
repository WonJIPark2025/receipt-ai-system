"""
run_pipeline.py - OCR 파이프라인 오케스트레이터

담당: OCR
설명: 영수증 이미지 → 구조화된 데이터 변환 전체 흐름 실행
    1. OCR       : Google Vision으로 텍스트 추출
    2. Parsing   : 가게명/날짜/합계/결제수단/카테고리/품목 추출
    3. Validation: 필수값 검증 후 success/review_required/error 판정
    4. Draft     : 결과 초안 객체 생성
    5. DB Payload: validation 성공 시 DB insert용 payload 준비
                   (실제 저장은 프론트엔드 저장 버튼 클릭 시 수행)
"""

# [변경] import 경로를 ocr_pipeline 기준으로 변경 (원본 ocr_pipeline 모듈과 분리)
from services.ocr_pipeline.logging.logger import PipelineLogger
from services.ocr_pipeline.ocr.google_vision_adapter import GoogleVisionAdapter
from services.ocr_pipeline.parsing.parser import parse_text
from services.ocr_pipeline.pipeline.draft_builder import build_draft
from services.ocr_pipeline.validation.validator import validate_receipt
from services.ocr_pipeline.persistence.db_mapper import map_to_db_schema
# [변경] create_receipt import 제거 - 프론트엔드에서 저장 버튼 클릭 시 직접 호출하도록 변경
# from backend.api.receipts import create_receipt
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def run_pipeline(image_path: str, verbose: bool = True) -> dict:

    logger = PipelineLogger(verbose=verbose)

    try:
        # OCR
        adapter = GoogleVisionAdapter()
        ocr_result = adapter.run(image_path)
        logger.log_event("OCR", "텍스트 추출 완료")

        # Parsing
        parsed = parse_text(ocr_result)
        logger.log_event("PARSING", "파싱 완료")

        # Validation
        validation = validate_receipt(parsed)
        parsed.update(validation)

        logger.log_event(
            "VALIDATION",
            validation["validation_status"],
            {"issues": validation["issues"]}
        )

        # Draft 생성
        draft = build_draft(image_path, parsed)
        draft["raw_text"] = ocr_result.get("full_text", "")
        draft["events"] = logger.get_events()

        draft["validation_status"] = validation["validation_status"]
        draft["issues"] = validation["issues"]

        # [변경] DB Insert를 파이프라인에서 자동 실행하지 않고, db_payload만 준비
        # 프론트엔드에서 사용자가 "저장" 버튼을 클릭할 때 직접 DB에 저장함
        if validation["validation_status"] == "success":
            db_schema = map_to_db_schema(image_path, parsed)
            draft["db_insert_ready"] = True
            draft["db_payload"] = db_schema

            # [변경] 아래 자동 DB 저장 로직 제거
            # try:
            #     db_result = create_receipt(
            #         user_id=db_schema["user_id"],
            #         category_id=db_schema["category_id"],
            #         payment_method_id=db_schema["payment_method_id"],
            #         date=db_schema["date"],
            #         total_amount=db_schema["total_amount"],
            #         store_name=db_schema["store_name"],
            #         image_path=db_schema["image_path"],
            #         details=db_schema["details"]
            #     )
            #
            #     draft["db_inserted"] = True
            #     draft["db_response"] = db_result
            #
            # except Exception as e:
            #     draft["db_inserted"] = False
            #     draft["db_error"] = str(e)

        return draft

    except Exception as e:
        logger.log_error("PIPELINE", e)
        return {
            "image_path": image_path,
            "validation_status": "error",
            "events": logger.get_events()
        }

if __name__ == "__main__":
    image_path = Path("data/receipts/v01_eval/r1.jpg")
    result = run_pipeline(str(image_path), verbose=True)
    print(result)