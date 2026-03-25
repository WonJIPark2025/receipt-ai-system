"""
base_adapter.py - OCR 어댑터 추상 인터페이스

담당: OCR
설명: 모든 OCR 엔진 구현체가 따라야 할 기본 인터페이스 정의
    - 어댑터 패턴으로 OCR 엔진 교체 가능하게 설계
    - 반환 구조: adapter, image_name, full_text
"""

class OCRAdapter:
    """
    OCR 어댑터 기본 인터페이스
    모든 OCR 구현체는 아래 구조를 반환해야 함
    """

    def run(self, image_path: str) -> dict:
        """
        반환 구조:

        {
            "adapter": str,        # OCR 엔진 이름
            "image_name": str,     # 입력 이미지 경로 또는 파일명
            "full_text": str       # OCR 전체 텍스트
        }

        ※ 구조 정보(words, lines 등)는 현재 파이프라인에서 사용하지 않음.
        ※ 향후 확장 시 별도 계층에서 처리.
        """
        raise NotImplementedError
