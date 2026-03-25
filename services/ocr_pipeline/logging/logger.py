"""
logger.py - 파이프라인 이벤트 로거

담당: OCR
설명: 파이프라인 각 단계의 이벤트 및 에러 로그 관리
    - 단계별 타임스탬프(KST) + 메시지 + 메타정보 기록
    - 콘솔 출력(verbose 모드) 및 이벤트 리스트 누적 저장
    - 파이프라인 결과에 events 필드로 포함되어 반환됨
"""

from datetime import datetime, timezone, timedelta
import sys

KST = timezone(timedelta(hours=9))  # 한국 표준시


class PipelineLogger:
    """
    파이프라인 운영 로그 관리 클래스
    - 콘솔 출력
    - 구조화된 이벤트 저장
    """

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.events = []  # 이벤트 기록 저장

    def log_event(self, stage: str, message: str, meta: dict = None):
        """
        단계별 로그 기록
        stage : 처리 단계 (OCR / PARSING 등)
        message : 간단 설명
        meta : 추가 메타정보
        """

        timestamp = datetime.now(KST).isoformat()

        event = {
            "timestamp": timestamp,
            "stage": stage,
            "message": message,
            "meta": meta or {}
        }

        # 내부 저장
        self.events.append(event)

        # 콘솔 출력
        if self.verbose:
            print(f"[{timestamp}] [{stage}] {message}")
            sys.stdout.flush()

    def log_error(self, stage: str, error: Exception):
        """
        에러 전용 로그
        """

        timestamp = datetime.now(KST).isoformat()

        event = {
            "timestamp": timestamp,
            "stage": stage,
            "message": "에러 발생",
            "meta": {
                "error_type": type(error).__name__,
                "error_message": str(error)
            }
        }

        self.events.append(event)

        if self.verbose:
            print(f"[{timestamp}] [ERROR:{stage}] {error}")
            sys.stdout.flush()

    def get_events(self):
        """
        누적 이벤트 반환
        """
        return self.events