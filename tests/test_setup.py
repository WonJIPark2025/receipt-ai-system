"""
test_setup.py - 초기 환경 검증 스크립트

담당: 테스트
설명: 서비스 실행 전 환경변수 / Supabase DB / Storage 연결을 한 번에 확인
실행: python -m tests.test_setup
"""

import sys
import struct
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import check_env
from backend.database import get_client
from backend.api.storage import upload_image, get_public_url, list_files, delete_image


def _dummy_png() -> bytes:
    """1x1 PNG 바이트 생성 (의존성 없음)"""
    raw = b'\x00\xff\x00\x00'
    compressed = zlib.compress(raw)

    def chunk(t, d):
        c = t + d
        return struct.pack('>I', len(d)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)

    return (
        b'\x89PNG\r\n\x1a\n'
        + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
        + chunk(b'IDAT', compressed)
        + chunk(b'IEND', b'')
    )


def check_db():
    print("\n[DB] Supabase 연결 및 테이블 접근")
    client = get_client()
    for table in ["categories", "receipts", "receipt_items", "receipt_embeddings"]:
        try:
            result = client.table(table).select("*").limit(1).execute()
            print(f"  ✅ {table} ({len(result.data)}행)")
        except Exception as e:
            print(f"  ❌ {table}: {e}")


def check_storage():
    print("\n[Storage] 업로드 / 조회 / 삭제")
    path = "test/test_dummy.png"
    try:
        result = upload_image(path, _dummy_png(), "image/png")
        print(f"  ✅ 업로드: {result['path']}")
    except Exception as e:
        print(f"  ❌ 업로드 실패: {e}")
        return

    try:
        url = get_public_url(path)
        print(f"  ✅ URL: {url}")
    except Exception as e:
        print(f"  ❌ URL 조회 실패: {e}")

    try:
        files = list_files("test")
        print(f"  ✅ 목록: {len(files)}개")
    except Exception as e:
        print(f"  ❌ 목록 조회 실패: {e}")

    try:
        delete_image(path)
        print(f"  ✅ 삭제 완료")
    except Exception as e:
        print(f"  ❌ 삭제 실패: {e}")


def main():
    print("=" * 50)
    print("환경 검증")
    print("=" * 50)

    print("\n[ENV] 환경변수 확인")
    if not check_env():
        print("  ❌ .env 파일을 확인하세요.")
        return
    print("  ✅ 환경변수 OK")

    check_db()
    check_storage()

    print("\n" + "=" * 50)
    print("검증 완료")
    print("=" * 50)


if __name__ == "__main__":
    main()
