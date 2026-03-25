"""
evaluate_pipeline.py - OCR 파이프라인 평가 스크립트

담당: OCR
설명: data/receipts/v01_eval/ 내 영수증 이미지로 파이프라인 일괄 평가
    - 각 이미지별 추출 결과(가게명/날짜/합계/결제/카테고리/검증상태) 수집
    - 결과를 tests/test_pipeline/results/v01_summary.csv로 저장
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


def evaluate():
    output_csv = RESULT_DIR / "v01_summary.csv"

    summary_rows = []

    images = sorted(DATA_DIR.glob("*.jpg"))

    for image_path in images:
        result = run_pipeline(str(image_path), verbose=False)

        store = result.get("store_name", "")
        date = result.get("transaction_date", "")
        total = result.get("total", 0)
        payment = result.get("payment", "")
        category = result.get("category", "")

        validation_status = result.get("validation_status", "")
        db_insert_ready = result.get("db_insert_ready", False)
        issues = result.get("issues", [])

        summary_rows.append([
            image_path.stem,
            store,
            date,
            total,
            payment,
            category,
            validation_status,
            db_insert_ready,
            ",".join(issues) if isinstance(issues, list) else ""
        ])

    # CSV 저장
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "image",
            "store_name",
            "transaction_date",
            "total",
            "payment",
            "category",
            "validation_status",
            "db_insert_ready",
            "issues"
        ])
        writer.writerows(summary_rows)

    print("===== Evaluation Completed =====")
    print(f"Total images: {len(images)}")
    print(f"CSV saved to: {output_csv}")


if __name__ == "__main__":
    evaluate()