"""
evaluate_pipeline.py - OCR 파이프라인 평가 스크립트

담당: OCR
설명: data/receipts/v01_eval/ 내 영수증 이미지로 파이프라인 일괄 평가
    - 각 이미지별 추출 결과(가게명/paid_at/합계/카테고리/purchase_type/items) 수집
    - v2 스키마 정합 여부 함께 검증
    - 결과를 tests/test_pipeline/results/v02_summary.csv로 저장
실행: python -m tests.test_pipeline.scripts.evaluate_pipeline
"""

import csv
import sys
from pathlib import Path

# 프로젝트 루트 설정
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data" / "receipts" / "v01_eval"
RESULT_DIR = PROJECT_ROOT / "tests" / "test_pipeline" / "results"
RESULT_DIR.mkdir(parents=True, exist_ok=True)

sys.path.append(str(PROJECT_ROOT))
from services.ocr_pipeline.pipeline.run_pipeline import run_pipeline
from services.ocr_pipeline.persistence.db_mapper import map_to_db_schema

# v2 스키마 기준
V2_RECEIPT_FIELDS = {
    "user_id", "category_id", "paid_at", "total_amount",
    "store_name", "purchase_type", "memo", "image_path",
}
V1_REMOVED_FIELDS = {"payment_method_id", "date", "details"}


def check_v2(receipt: dict) -> str:
    """v2 정합 여부 반환: OK / 누락필드 / v1잔존"""
    missing = V2_RECEIPT_FIELDS - set(receipt.keys())
    if missing:
        return f"누락:{','.join(missing)}"
    leaked = V1_REMOVED_FIELDS & set(receipt.keys())
    if leaked:
        return f"v1잔존:{','.join(leaked)}"
    return "OK"


def evaluate():
    output_csv = RESULT_DIR / "v02_summary.csv"

    summary_rows = []

    images = sorted(DATA_DIR.glob("*.jpg"))

    if not images:
        print(f"⚠️  이미지 없음: {DATA_DIR}")
        print("data/receipts/v01_eval/ 에 영수증 이미지(.jpg)를 넣고 실행하세요.")
        return

    for image_path in images:
        result = run_pipeline(str(image_path), verbose=False)

        # 파이프라인 출력
        store             = result.get("store_name", "")
        paid_at           = result.get("transaction_date", "")
        total             = result.get("total", 0)
        category          = result.get("category", "")
        validation_status = result.get("validation_status", "")
        issues            = result.get("issues", [])

        # db_mapper 통과 후 v2 payload 생성
        payload = map_to_db_schema(
            image_path=str(image_path),
            parsed=result,
            user_id=1,
            purchase_type=None,     # UI 입력값 — 평가 시 None
        )
        receipt = payload["receipt"]
        items   = payload["items"]

        # items 요약
        items_count    = len(items)
        activity_tags  = ",".join(
            i["activity_tag"] for i in items if i.get("activity_tag")
        )
        item_names = ",".join(i["name"] for i in items)

        # v2 정합 검증
        v2_check = check_v2(receipt)

        summary_rows.append([
            image_path.stem,
            store,
            paid_at,
            total,
            category,
            receipt.get("category_id", ""),
            validation_status,
            ",".join(issues) if isinstance(issues, list) else "",
            items_count,
            activity_tags,
            item_names,
            v2_check,
        ])

    # CSV 저장
    with open(output_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "image",
            "store_name",
            "paid_at",
            "total",
            "category",
            "category_id",
            "validation_status",
            "issues",
            "items_count",
            "activity_tags",
            "item_names",
            "v2_schema",
        ])
        writer.writerows(summary_rows)

    ok_count = sum(1 for r in summary_rows if r[-1] == "OK")
    print("===== Evaluation Completed =====")
    print(f"총 이미지   : {len(images)}")
    print(f"v2 정합     : {ok_count}/{len(images)}")
    print(f"CSV 저장    : {output_csv}")


if __name__ == "__main__":
    evaluate()
