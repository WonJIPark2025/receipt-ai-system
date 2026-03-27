"""
evaluate_gemini.py - Gemini 배치 평가 스크립트

담당: 테스트
설명: data/receipts/v01_eval/ 내 영수증 이미지로 Gemini 일괄 평가
    - 각 이미지별 추출 결과(가게명/date/합계/카테고리/purchase_type/items) 수집
    - v2 스키마 정합 여부 함께 검증
    - 결과를 tests/test_ai/results/v02_summary.csv로 저장
실행: python -m tests.test_ai.scripts.evaluate_gemini
"""

import csv
import sys
from pathlib import Path

# 프로젝트 루트 설정
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data" / "receipts" / "v01_eval"
RESULT_DIR = PROJECT_ROOT / "tests" / "test_ai" / "results"
RESULT_DIR.mkdir(parents=True, exist_ok=True)

sys.path.append(str(PROJECT_ROOT))
from services.ai.gemini import extract_receipt_data
from services.ai.validator import validate_receipt

# 필수 필드 기준
REQUIRED_FIELDS = {"store_name", "date", "total", "category", "purchase_type", "items"}


def check_schema(data: dict) -> str:
    """필수 필드 존재 여부 반환: OK / 누락필드"""
    missing = REQUIRED_FIELDS - set(data.keys())
    if missing:
        return f"누락:{','.join(missing)}"
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
        data = extract_receipt_data(str(image_path))
        validation = validate_receipt(data)
        result = {**data, **validation}

        store             = result.get("store_name", "")
        date              = result.get("date", "")
        total             = result.get("total", 0)
        category          = result.get("category", "")
        purchase_type     = result.get("purchase_type", "")
        validation_status = result.get("validation_status", "")
        issues            = result.get("issues", [])
        items             = result.get("items", [])

        items_count   = len(items)
        item_names    = ",".join(i["name"] for i in items)
        schema_check  = check_schema(data)

        summary_rows.append([
            image_path.stem,
            store,
            date,
            total,
            category,
            purchase_type,
            validation_status,
            ",".join(issues) if isinstance(issues, list) else "",
            items_count,
            item_names,
            schema_check,
        ])

    # CSV 저장
    with open(output_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "image",
            "store_name",
            "date",
            "total",
            "category",
            "purchase_type",
            "validation_status",
            "issues",
            "items_count",
            "item_names",
            "schema_check",
        ])
        writer.writerows(summary_rows)

    ok_count = sum(1 for r in summary_rows if r[-1] == "OK")
    print("===== Evaluation Completed =====")
    print(f"총 이미지   : {len(images)}")
    print(f"스키마 정합 : {ok_count}/{len(images)}")
    print(f"CSV 저장    : {output_csv}")


if __name__ == "__main__":
    evaluate()
