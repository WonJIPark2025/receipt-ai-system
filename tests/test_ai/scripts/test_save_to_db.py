"""
test_save_to_db.py - Gemini 우회: 수동 데이터로 embed + DB 저장 테스트

실행: python -m tests.test_ai.scripts.test_save_to_db
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.append(str(PROJECT_ROOT))

# ─── 영수증 이미지에서 수동 추출한 데이터 ─────────────────────────────────────
# 쿠팡이츠 영수증 (호시타코야끼 대지점) 2025-10-05 21:40:57
MOCK_DATA = {
    "store_name":    "호시타코야끼 대지점",
    "date":          "2025-10-05T21:40:57+09:00",
    "total":         14000,
    "category":      "식비",
    "purchase_type": "delivery",
    "memo":          "친구랑 집에서 과제를 함",
    "items": [
        {"name": "네기 타코야끼 8알",             "quantity": 1, "price": 6000},
        {"name": "정통 타코야끼 8알",             "quantity": 1, "price": 5500},
        {"name": "까르보불닭볶음면(비조리컵라면)", "quantity": 1, "price": 2500},
    ],
    "raw_text": (
        "coupang eats [고객용]\n"
        "2B25EX [수저포크X]\n"
        "대메뉴              수량  금액\n"
        "네기 타코야끼 8알    1     6,000\n"
        "+ 초강추:오리지널    1         0\n"
        "정통 타코야끼 8알    1     5,500\n"
        "+ best:오리지널     1         0\n"
        "+ 까르보불닭볶음면(비조리컵라면) 1  2,500\n"
        "주문금액            14,000\n"
        "배달비                   0\n"
        "카드결제            14,000\n"
        "총결제금액          14,000\n"
        "거래일시: 2025-10-05 21:40:57\n"
        "주문매장: 호시타코야끼 대지점\n"
        "결제방식: 쿠페이 선결제 완료\n"
        "쿠팡이츠 고객센터 1670-9827"
    ),
}

USER_ID     = 1
CATEGORY_ID = 1   # 식비


def test():
    from services.ai.embedder import embed_text
    from backend.api import (
        create_receipt,
        create_receipt_items,
        save_embedding,
    )

    print("=" * 50)
    print("1단계: 임베딩 생성 (text-embedding-004)")
    print("=" * 50)

    embedding = embed_text(MOCK_DATA["raw_text"])
    if embedding is None:
        print("❌ 임베딩 생성 실패")
        return

    print(f"✅ 임베딩 생성 완료  차원: {len(embedding)}")

    print()
    print("=" * 50)
    print("2단계: 영수증 저장 (receipts)")
    print("=" * 50)

    receipt = create_receipt(
        user_id       = USER_ID,
        category_id   = CATEGORY_ID,
        paid_at       = MOCK_DATA["date"],
        total_amount  = MOCK_DATA["total"],
        store_name    = MOCK_DATA["store_name"],
        purchase_type = MOCK_DATA["purchase_type"],
        memo          = MOCK_DATA["memo"],
        raw_text      = MOCK_DATA["raw_text"],
    )
    if receipt is None:
        print("❌ 영수증 저장 실패")
        return

    receipt_id = receipt["id"]
    print(f"✅ 영수증 저장 완료  id={receipt_id}")

    print()
    print("=" * 50)
    print("3단계: 품목 저장 (receipt_items)")
    print("=" * 50)

    items = create_receipt_items(receipt_id=receipt_id, items=MOCK_DATA["items"])
    print(f"✅ 품목 저장 완료  {len(items)}건")
    for item in items:
        print(f"   - {item['name']} x{item['quantity']} {item['price']}원")

    print()
    print("=" * 50)
    print("4단계: 임베딩 저장 (receipt_embeddings)")
    print("=" * 50)

    emb_row = save_embedding(
        receipt_id = receipt_id,
        raw_text   = MOCK_DATA["raw_text"],
        embedding  = embedding,
    )
    if emb_row is None:
        print("❌ 임베딩 저장 실패")
        return

    print(f"✅ 임베딩 저장 완료  embedding_id={emb_row['id']}")

    print()
    print("=" * 50)
    print("전체 저장 완료")
    print(f"  receipt_id : {receipt_id}")
    print(f"  store      : {MOCK_DATA['store_name']}")
    print(f"  total      : {MOCK_DATA['total']:,}원")
    print(f"  memo       : {MOCK_DATA['memo']}")
    print("=" * 50)


if __name__ == "__main__":
    test()
