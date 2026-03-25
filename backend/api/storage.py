"""
storage.py - Supabase Storage 파일 API

담당: 백엔드
설명: Supabase Storage 버킷(OcrReceipts)을 통한 파일 업로드/조회/삭제
    - 영수증 이미지 업로드 후 공개 URL 반환
    - upload_image, get_public_url, list_files, delete_image
"""

from backend.database import get_client
from utils.config import SUPABASE_BUCKET

# 버킷 이름 (.env에서 로드)
BUCKET_NAME = SUPABASE_BUCKET


# =============================================================================
# UPLOAD - 파일 업로드
# =============================================================================
def upload_image(file_path: str, file_bytes: bytes, content_type: str = "image/jpeg") -> dict:
    """
    영수증 이미지를 Supabase Storage에 업로드

    Args:
        file_path: 버킷 내 저장 경로 (예: "user_1/receipt_001.jpg")
        file_bytes: 파일의 바이너리 데이터
        content_type: MIME 타입 (기본값: "image/jpeg")
                      - "image/jpeg" : jpg, jpeg
                      - "image/png"  : png

    Returns:
        dict: 업로드 결과
              성공 시: {"path": "저장경로", "url": "공개URL"}
              실패 시: None

    사용 예시:
        with open("receipt.jpg", "rb") as f:
            result = upload_image("user_1/receipt_001.jpg", f.read())
        print(result["url"])  # 공개 URL
    """
    client = get_client()

    # 업로드 실행
    result = client.storage.from_(BUCKET_NAME).upload(
        path=file_path,
        file=file_bytes,
        file_options={"content-type": content_type}
    )

    # 공개 URL 생성
    public_url = client.storage.from_(BUCKET_NAME).get_public_url(file_path)

    return {
        "path": file_path,
        "url": public_url
    }


# =============================================================================
# READ - 파일 조회
# =============================================================================
def get_public_url(file_path: str) -> str:
    """
    업로드된 파일의 공개 URL 조회

    Args:
        file_path: 버킷 내 파일 경로 (예: "user_1/receipt_001.jpg")

    Returns:
        str: 공개 URL

    사용 예시:
        url = get_public_url("user_1/receipt_001.jpg")
    """
    client = get_client()
    return client.storage.from_(BUCKET_NAME).get_public_url(file_path)


def list_files(folder: str = "") -> list:
    """
    버킷 내 파일 목록 조회

    Args:
        folder: 폴더 경로 (예: "user_1", 빈 문자열이면 루트)

    Returns:
        list: 파일 정보 리스트

    사용 예시:
        files = list_files("user_1")
        for f in files:
            print(f["name"])
    """
    client = get_client()
    return client.storage.from_(BUCKET_NAME).list(folder)


# =============================================================================
# DELETE - 파일 삭제
# =============================================================================
def delete_image(file_path: str) -> bool:
    """
    업로드된 파일 삭제

    Args:
        file_path: 버킷 내 파일 경로 (예: "user_1/receipt_001.jpg")

    Returns:
        bool: 삭제 성공 여부

    사용 예시:
        delete_image("user_1/receipt_001.jpg")
    """
    client = get_client()
    result = client.storage.from_(BUCKET_NAME).remove([file_path])
    return len(result) > 0