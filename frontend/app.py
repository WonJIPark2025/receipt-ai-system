"""
app.py - Streamlit 메인 진입점 (디바이스 분기)

담당: 프론트엔드
실행: streamlit run frontend/app.py
설명: 접속 기기를 감지하여 적절한 UI로 분기
    - 데스크톱/노트북 → OCR_front.py (wide 레이아웃)
    - 모바일 기기     → OCR_mobile.py (centered 레이아웃)
동작 원리:
    1. streamlit_js_eval로 브라우저 화면 너비를 가져옴
    2. 화면 너비 768px 이하 → 모바일로 판단
    3. 판단 결과에 따라 해당 파일을 load_page()로 실행
의존성:
    pip install streamlit-js-eval
"""
import sys
import streamlit as st
from streamlit_js_eval import streamlit_js_eval
from pathlib import Path

# ↓ 이 두 줄 추가 (exec 실행 전에 path 잡아줌)
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# =============================================================================
# 1. 페이지 기본 설정
# =============================================================================
st.set_page_config(
    page_title="영수증 OCR 장부",
    page_icon="🧾",
    layout="centered"
)

# =============================================================================
# 2. 브라우저 화면 너비 감지
# =============================================================================
# streamlit_js_eval로 JavaScript를 실행하여 디바이스 화면 너비를 가져옴
# window.screen.width → 디바이스 물리 해상도 (레이아웃에 영향받지 않음)
# 768px 이하 → 모바일 / 초과 → 데스크톱
# 결과가 올 때까지 None이므로, None인 동안 로딩 표시
# =============================================================================

# 디바이스 실제 화면 너비 가져오기 (JavaScript 실행)
screen_width = streamlit_js_eval(js_expressions="window.screen.width", key="screen_width")

if screen_width is None:
    # JS 결과가 아직 도착하지 않은 상태 → 잠시 로딩
    st.markdown(
        "<div style='text-align:center; padding-top:100px;'>"
        "<h3>🔄 로딩 중...</h3>"
        "</div>",
        unsafe_allow_html=True
    )
    st.stop()

# 디바이스 판별 (768px 기준)
is_mobile = screen_width <= 768

# =============================================================================
# 3. 디바이스별 분기 실행
# =============================================================================
# 감지된 디바이스 타입에 따라 해당 UI 파일을 로드
# - 모바일 (768px 이하) → OCR_mobile.py 실행
# - 데스크톱 (768px 초과) → OCR_front.py 실행
#
# load_page():
#   OCR_front.py / OCR_mobile.py 안에 있는 st.set_page_config() 호출을
#   건너뛰어 중복 호출 에러를 방지함 (app.py에서 이미 호출했으므로)
# =============================================================================

frontend_dir = Path(__file__).parent


def load_page(file_path: Path):
    """
    파일을 읽어서 실행하되, st.set_page_config() 줄은 건너뜀
    (app.py에서 이미 호출했으므로 중복 호출 방지)
    """
    code = open(file_path, encoding="utf-8").read()
    code = code.replace(
        "st.set_page_config(",
        "# [app.py에서 이미 설정됨] st.set_page_config("
    )
    exec(code, globals())


if is_mobile:
    # --- 모바일 UI 로드 ---
    load_page(frontend_dir / "OCR_mobile.py")
else:
    # --- 데스크톱 UI 로드 ---
    load_page(frontend_dir / "OCR_front.py")