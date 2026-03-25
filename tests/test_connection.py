"""
test_connection.py - Supabase 연결 테스트

담당: 백엔드
설명: Supabase 연결이 정상인지 확인하는 테스트 스크립트
실행: python -m tests.test_connection
"""

import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import check_env
from backend.database import get_client, test_connection


def main():
    print("=" * 60)
    print("Supabase 연결 테스트")
    print("=" * 60)

    # 1. 환경변수 확인
    print("\n[1] 환경변수 확인...")
    if not check_env():
        print("❌ .env 파일을 확인하세요.")
        return

    print("✅ 환경변수 설정 완료")

    # 2. 연결 테스트
    print("\n[2] Supabase 연결 테스트...")
    if test_connection():
        print("✅ Supabase 연결 성공!")
    else:
        print("❌ Supabase 연결 실패")
        return

    # 3. 테이블 조회 테스트
    print("\n[3] 테이블 조회 테스트...")
    client = get_client()

    tables = ["users", "categories", "payment_methods", "receipts"]
    for table in tables:
        try:
            result = client.table(table).select("*").limit(1).execute()
            count = len(result.data)
            print(f"   ✅ {table}: 접근 가능 (현재 {count}개 행)")
        except Exception as e:
            print(f"   ❌ {table}: 접근 실패 - {e}")

    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()