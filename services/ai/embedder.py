"""
embedder.py - 텍스트 임베딩 생성

담당: AI
설명: OCR raw_text를 벡터 임베딩으로 변환
    - 모델: text-embedding-004 (768차원)
    - RAG retrieval의 기반 벡터
"""

from utils.config import GEMINI_API_KEY


def embed_text(text: str) -> list[float] | None:
    """
    텍스트를 768차원 임베딩 벡터로 변환

    Args:
        text: 임베딩할 텍스트 (OCR raw_text)

    Returns:
        list[float]: 768차원 벡터 또는 실패 시 None
    """
    if not GEMINI_API_KEY or not text:
        return None

    from google import genai

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.embed_content(
            model="text-embedding-004",
            contents=text,
        )
        return response.embeddings[0].values

    except Exception as e:
        print(f"[embedder] 임베딩 생성 실패: {e}")
        return None
