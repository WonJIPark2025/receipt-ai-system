"""
test_storage.py - Supabase Storage 업로드 테스트

담당: 백엔드
설명: OcrReceipts 버킷에 이미지 업로드/조회/삭제 테스트
실행: python -m tests.test_storage
사용법:
    1. data/receipts/ 폴더에 테스트용 이미지를 넣거나,
    2. 아래 코드가 자동으로 더미 이미지를 생성함
"""

import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import check_env
from backend.api.storage import upload_image, get_public_url, list_files, delete_image


def create_test_image() -> bytes:
    """
    테스트용 1x1 PNG 이미지 바이트 생성
    (별도 라이브러리 없이 최소 PNG 바이너리)
    """
    # 1x1 빨간 픽셀 PNG
    import struct, zlib
    raw_data = b'\x00\xff\x00\x00'  # filter byte + RGB
    compressed = zlib.compress(raw_data)

    def chunk(chunk_type, data):
        c = chunk_type + data
        crc = struct.pack('>I', zlib.crc32(c) & 0xffffffff)
        return struct.pack('>I', len(data)) + c + crc

    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', compressed)
    png += chunk(b'IEND', b'')
    return png


def main():
    print("=" * 60)
    print("Supabase Storage 테스트 (버킷: OcrReceipts)")
    print("=" * 60)

    # 1. 환경변수 확인
    print("\n[1] 환경변수 확인...")
    if not check_env():
        print("❌ .env 파일을 확인하세요.")
        return
    print("✅ 환경변수 OK")

    # 2. 테스트 이미지 준비
    print("\n[2] 테스트 이미지 준비...")

    # data/receipts/ 에 이미지가 있으면 사용, 없으면 더미 생성
    test_dir = Path(__file__).parent.parent / "data" / "receipts"
    existing_images = list(test_dir.glob("*.jpg")) + list(test_dir.glob("*.png"))

    if existing_images:
        test_file = existing_images[0]
        with open(test_file, "rb") as f:
            file_bytes = f.read()
        file_name = test_file.name
        content_type = "image/png" if test_file.suffix == ".png" else "image/jpeg"
        print(f"   기존 이미지 사용: {file_name}")
    else:
        file_bytes = create_test_image()
        file_name = "test_dummy.png"
        content_type = "image/png"
        print(f"   더미 이미지 생성: {file_name}")

    # 3. 업로드 테스트
    upload_path = f"test/{file_name}"
    print(f"\n[3] 업로드 테스트... (경로: {upload_path})")
    try:
        result = upload_image(upload_path, file_bytes, content_type)
        print(f"   ✅ 업로드 성공!")
        print(f"   📁 경로: {result['path']}")
        print(f"   🔗 URL: {result['url']}")
    except Exception as e:
        print(f"   ❌ 업로드 실패: {e}")
        return

    # 4. 공개 URL 조회 테스트
    print(f"\n[4] 공개 URL 조회 테스트...")
    try:
        url = get_public_url(upload_path)
        print(f"   ✅ URL: {url}")
    except Exception as e:
        print(f"   ❌ URL 조회 실패: {e}")

    # 5. 파일 목록 조회 테스트
    print(f"\n[5] 파일 목록 조회 테스트... (폴더: test)")
    try:
        files = list_files("test")
        print(f"   ✅ {len(files)}개 파일 발견")
        for f in files:
            print(f"      - {f.get('name', 'unknown')}")
    except Exception as e:
        print(f"   ❌ 목록 조회 실패: {e}")

    # 6. 삭제 테스트
    print(f"\n[6] 삭제 테스트... (경로: {upload_path})")
    try:
        deleted = delete_image(upload_path)
        if deleted:
            print(f"   ✅ 삭제 성공!")
        else:
            print(f"   ⚠️ 삭제 결과 확인 필요")
    except Exception as e:
        print(f"   ❌ 삭제 실패: {e}")

    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()