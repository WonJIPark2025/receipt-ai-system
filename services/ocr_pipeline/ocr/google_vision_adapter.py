"""
google_vision_adapter.py - Google Vision OCR 어댑터

담당: OCR
설명: Google Cloud Vision API를 사용한 OCR 구현체
    - 로컬 .env의 GOOGLE_APPLICATION_CREDENTIALS 또는
      Streamlit Secrets의 [gcp_service_account] 섹션에서 인증 정보 로드
    - 이미지에서 전체 텍스트(full_text) 추출 후 반환
"""

from .base_adapter import OCRAdapter
import os
import json
import tempfile


class GoogleVisionAdapter(OCRAdapter):

    def __init__(self):
        cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        # 로컬 JSON 파일이 없으면 Streamlit Secrets에서 가져와 임시 파일 생성
        if not cred_path or not os.path.exists(cred_path):
            cred_path = self._load_from_streamlit_secrets()

        if not cred_path:
            raise RuntimeError(
                "GOOGLE_APPLICATION_CREDENTIALS not set. "
                "로컬 .env에 JSON 경로를 지정하거나, "
                "Streamlit Secrets에 [gcp_service_account] 섹션을 추가하세요."
            )

        from google.cloud import vision
        self.vision = vision
        self.client = vision.ImageAnnotatorClient()

    @staticmethod
    def _load_from_streamlit_secrets():
        """Streamlit Secrets의 [gcp_service_account]에서 임시 JSON 파일 생성"""
        try:
            import streamlit as st
            gcp_info = st.secrets.get("gcp_service_account")
            if not gcp_info:
                return None

            # dict로 변환 후 임시 JSON 파일에 저장
            gcp_dict = dict(gcp_info)
            tmp = tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            )
            json.dump(gcp_dict, tmp)
            tmp.close()

            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp.name
            return tmp.name
        except Exception:
            return None

    def run(self, image_path: str) -> dict:

        with open(image_path, "rb") as f:
            content = f.read()

        image = self.vision.Image(content=content)
        response = self.client.text_detection(image=image)

        if response.error.message:
            raise RuntimeError(response.error.message)

        texts = response.text_annotations
        raw_text = texts[0].description if texts else ""

        return {
            "adapter": "google_vision",
            "image_name": image_path,
            "full_text": raw_text
        }