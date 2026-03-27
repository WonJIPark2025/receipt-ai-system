"""
receipt_embeddings.py - 영수증 임베딩 API

담당: 백엔드
설명: receipt_embeddings 테이블 CRUD
    - 영수증 저장 시 raw_text 임베딩을 함께 저장
    - RAG retrieval 시 유사도 검색에 사용
"""

from backend.database import get_client


TABLE = "receipt_embeddings"


def save_embedding(receipt_id: int, raw_text: str, embedding: list[float]) -> dict | None:
    """
    영수증 임베딩 저장

    Args:
        receipt_id : receipts 테이블 FK
        raw_text   : 영수증 원문 텍스트
        embedding  : 768차원 벡터

    Returns:
        dict: 저장된 row 또는 None
    """
    client = get_client()
    result = client.table(TABLE).insert({
        "receipt_id": receipt_id,
        "raw_text":   raw_text,
        "embedding":  embedding,
    }).execute()
    return result.data[0] if result.data else None


def search_similar(query_embedding: list[float], match_count: int = 5) -> list:
    """
    쿼리 임베딩과 유사한 영수증 검색 (cosine similarity)

    Args:
        query_embedding : 질문 텍스트의 임베딩 벡터
        match_count     : 반환할 최대 결과 수

    Returns:
        list: 유사도 순 영수증 raw_text 목록
    """
    client = get_client()
    result = client.rpc("match_receipts", {
        "query_embedding": query_embedding,
        "match_count":     match_count,
    }).execute()
    return result.data
