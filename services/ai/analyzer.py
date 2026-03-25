"""
analyzer.py - AI 지출 분석 서비스

담당: AI
설명: Gemini LLM을 사용한 소비 데이터 분석 서비스
    - Supabase에서 로드한 영수증 데이터를 LLM으로 분석
    - 전체 소비 패턴, 과소비 카테고리, 월별 변화, 절약 조언 제공
    - 향후 services/ai/chatbot.py 및 RAG와 통합 예정
"""

# 분석 데이터 로드 (Supabase 연동 예정)
import json

# TODO: Supabase에서 영수증 데이터 로드
data = []

# Gemini 연결
import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=api_key)

model = genai.GenerativeModel("gemini-2.5-flash")

# 프롬프트 생성
prompt = f"""
다음은 사용자의 소비 데이터이다.

{json.dumps(data, ensure_ascii=False, indent=2)}

다음 내용을 분석해라.

1. 전체 소비 패턴
2. 과소비 카테고리
3. 월별 소비 변화
4. 절약을 위한 조언
"""

# Gemini 분석 실행
response = model.generate_content(prompt)

print(response.text)
