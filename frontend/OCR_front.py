"""
OCR_front.py - 데스크톱 전용 UI

담당: 프론트엔드
설명: 데스크톱/노트북에 최적화된 영수증 OCR 시스템 UI
    - app.py에서 데스크톱 감지 시 이 파일로 분기
    - wide 레이아웃, 사이드바 메뉴 구성
포함 기능:
    - Supabase 로그인/회원가입 + localStorage 로그인 유지
    - OCR 파이프라인 영수증 인식 + DB/Storage 저장
    - 지출 분석 (연월 선택, 막대/선 그래프, 파이 차트)
    - AI 월별 조언 (Gemini)
    - 장부 다운로드 (Excel)
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import time
import tempfile
import os
import sys
from pathlib import Path
from streamlit_js_eval import streamlit_js_eval

# 프로젝트 루트를 path에 추가 (backend 모듈 import를 위해) - app.py에 추가됨
#sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.api.users import get_user_by_user_id, create_user
from backend.api.categories import get_all_categories
from backend.api.receipts import create_receipt, get_receipts_by_user, delete_receipt
from backend.api.storage import upload_image, get_public_url, delete_image
from services.ocr_pipeline.pipeline.run_pipeline import run_pipeline
from services.ocr_pipeline.persistence.db_mapper import CATEGORY_MAP, PAYMENT_MAP

# --- 1. Supabase 연동 로그인/회원가입 함수 ---

def check_login(user_id: str, password: str) -> dict:
    """
    로그인 확인 - Supabase users 테이블 조회

    Args:
        user_id: 로그인 ID
        password: 비밀번호

    Returns:
        dict: 로그인 성공 시 사용자 정보, 실패 시 None
    """
    try:
        user = get_user_by_user_id(user_id)
        if user and user.get("password") == password:
            return user
        return None
    except Exception as e:
        st.error(f"DB 연결 오류: {e}")
        return None


def register_user(user_id: str, password: str, name: str = None) -> bool:
    """
    회원가입 - Supabase users 테이블에 추가

    Args:
        user_id: 로그인 ID
        password: 비밀번호
        name: 사용자 이름 (선택, 없으면 user_id 사용)

    Returns:
        bool: 성공 여부
    """
    try:
        # 이미 존재하는지 확인
        existing = get_user_by_user_id(user_id)
        if existing:
            return False

        # 새 사용자 생성
        result = create_user(
            name=name or user_id,
            user_id=user_id,
            password=password
        )
        return result is not None
    except Exception as e:
        st.error(f"회원가입 오류: {e}")
        return False

# --- 2. 페이지 설정 및 세션 상태 초기화 ---
st.set_page_config(page_title="영수증 OCR 장부", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None
if 'user_pk' not in st.session_state:
    st.session_state['user_pk'] = None  # DB의 users.id (FK로 사용)
if 'history' not in st.session_state:
    st.session_state['history'] = []

# --- [로그아웃 처리 - localStorage 삭제] ---
# 로그아웃 버튼 클릭 시 pending_logout 플래그가 설정되며,
# 다음 렌더링에서 JS removeItem이 실행된 뒤 플래그를 해제한다.
# (st.rerun() 직전에 JS를 호출하면 실행되기 전에 페이지가 리렌더링되어 무시되는 문제 방지)
if st.session_state.get('pending_logout'):
    streamlit_js_eval(js_expressions="localStorage.removeItem('ocr_user_id')", key="del_uid")
    streamlit_js_eval(js_expressions="localStorage.removeItem('ocr_user_pk')", key="del_upk")
    st.session_state['pending_logout'] = False

# --- [localStorage에서 로그인 복원] ---
# 새로고침 시 session_state는 초기화되지만 localStorage는 브라우저에 남아있으므로 자동 복원
if not st.session_state['logged_in'] and not st.session_state.get('pending_logout'):
    saved_user_id = streamlit_js_eval(js_expressions="localStorage.getItem('ocr_user_id')", key="restore_uid")
    saved_user_pk = streamlit_js_eval(js_expressions="localStorage.getItem('ocr_user_pk')", key="restore_upk")
    if saved_user_id and saved_user_pk and saved_user_id != "null":
        st.session_state['logged_in'] = True
        st.session_state['user_id'] = saved_user_id
        st.session_state['user_pk'] = int(saved_user_pk)

# --- 3. 로그인 / 회원가입 화면 (auth_page) ---
def auth_page():
    st.title("🔐 OCR 장부 시스템")
    tab1, tab2 = st.tabs(["로그인", "회원가입"])
    
    with tab1:
        st.subheader("로그인")
        login_id = st.text_input("아이디", key="login_id")
        login_pw = st.text_input("비밀번호", type="password", key="login_pw")
        if st.button("로그인", use_container_width=True):
            # Supabase users 테이블에서 확인
            user = check_login(login_id, login_pw)
            if user:
                st.session_state['logged_in'] = True
                st.session_state['user_id'] = login_id
                st.session_state['user_pk'] = user.get("id")  # DB의 PK 저장 (영수증 저장 시 필요)
                # localStorage에 로그인 정보 저장 (새로고침 시 유지)
                streamlit_js_eval(js_expressions=f"localStorage.setItem('ocr_user_id', '{login_id}')", key="save_uid")
                streamlit_js_eval(js_expressions=f"localStorage.setItem('ocr_user_pk', '{user.get('id')}')", key="save_upk")
                st.success(f"{login_id}님 환영합니다!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 잘못되었습니다.")
                
    with tab2:
        st.subheader("새 계정 만들기")
        new_id = st.text_input("사용할 아이디", key="new_id")
        new_pw = st.text_input("사용할 비밀번호", type="password", key="new_pw")
        confirm_pw = st.text_input("비밀번호 확인", type="password", key="confirm_pw")
        
        if st.button("회원가입 완료", use_container_width=True):
            if not new_id or not new_pw:
                st.warning("아이디와 비밀번호를 모두 입력해주세요.")
            elif new_pw != confirm_pw:
                st.error("비밀번호가 일치하지 않습니다.")
            else:
                # Supabase users 테이블에 추가
                if register_user(new_id, new_pw):
                    st.success("회원가입 성공! 로그인 탭에서 로그인해주세요.")
                else:
                    st.error("이미 존재하는 아이디입니다.")

# --- 4. 메인 앱 화면 (main_app) - 사이드바 페이지 전환 허브 ---
def main_app():
    # --- [사용자 정보 및 로그아웃] ---
    st.sidebar.write(f"👤 **{st.session_state['user_id']}**님 접속 중")
    if st.sidebar.button("로그아웃"):
        st.session_state['logged_in'] = False
        st.session_state['user_id'] = None
        st.session_state['user_pk'] = None
        # 다음 렌더링에서 localStorage 삭제가 실행되도록 플래그 설정
        st.session_state['pending_logout'] = True
        st.rerun()

    # --- [사이드바 페이지 선택] ---
    st.sidebar.divider()
    page = st.sidebar.radio(
        "메뉴",
        ["🧾 영수증 업로드", "📊 지출 분석"],
        key="page_select"
    )

    # --- [카테고리 목록을 DB에서 로드 (공통)] ---
    if 'categories' not in st.session_state:
        try:
            cat_list = get_all_categories()
            st.session_state['categories'] = {c["name"]: c["id"] for c in cat_list}
        except Exception as e:
            st.warning(f"카테고리 로드 실패: {e}")
            st.session_state['categories'] = {}

    # 선택된 페이지 렌더링
    if page == "🧾 영수증 업로드":
        page_upload()
    else:
        page_analytics()


# --- 4-1. 영수증 업로드 페이지 ---
def page_upload():
    category_names = list(st.session_state['categories'].keys())

    st.title("🧾 영수증 OCR 자동 장부 시스템")
    st.info("여러 장의 영수증을 한 번에 업로드하고 내용을 확인한 뒤 저장하세요.")

    # --- [1. 파일 업로드 섹션] ---
    uploaded_files = st.file_uploader(
        "영수증 사진들을 선택하세요 (JPG, PNG)",
        type=['jpg', 'jpeg', 'png'],
        accept_multiple_files=True
    )

    # --- [OCR 파이프라인 실행 - 업로드된 파일별로 결과를 세션에 캐싱] ---
    if 'ocr_results' not in st.session_state:
        st.session_state['ocr_results'] = {}

    if uploaded_files:
        for file in uploaded_files:
            if file.name not in st.session_state['ocr_results']:
                with st.spinner(f"🔍 {file.name} OCR 처리 중..."):
                    try:
                        suffix = Path(file.name).suffix
                        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                        tmp.write(file.getbuffer())
                        tmp.close()

                        result = run_pipeline(tmp.name, verbose=False)
                        st.session_state['ocr_results'][file.name] = result

                        os.unlink(tmp.name)
                    except Exception as e:
                        st.session_state['ocr_results'][file.name] = {
                            "validation_status": "error",
                            "error_msg": str(e)
                        }

        st.divider()
        st.subheader(f"🔍 추출 결과 확인 (총 {len(uploaded_files)}건)")

        temp_data_list = []

        for idx, file in enumerate(uploaded_files):
            ocr_data = st.session_state['ocr_results'].get(file.name, {})

            parsed_store = ocr_data.get("store_name", "")
            parsed_date_str = ocr_data.get("transaction_date", "")
            parsed_total = ocr_data.get("total", 0)

            # OCR 날짜 문자열 → date 객체 변환 (실패 시 오늘 날짜)
            from datetime import date as _date
            try:
                parsed_date = _date.fromisoformat(parsed_date_str)
            except (ValueError, TypeError):
                parsed_date = _date.today()
            parsed_category = ocr_data.get("category", "기타")
            parsed_payment = ocr_data.get("payment", "")
            validation_status = ocr_data.get("validation_status", "error")

            with st.expander(f"📄 영수증 #{idx+1} : {file.name}", expanded=True):
                col_img, col_form = st.columns([1, 2])

                with col_img:
                    st.image(file, use_column_width=True)
                    if validation_status == "success":
                        st.success("✅ OCR 인식 성공")
                    elif validation_status == "review_required":
                        st.warning("⚠️ 검토 필요")
                    else:
                        st.error("❌ OCR 인식 실패")

                with col_form:
                    c1, c2 = st.columns(2)
                    store_name = c1.text_input("상호명", value=parsed_store, key=f"store_{idx}")
                    date_val = c2.date_input("날짜", value=parsed_date, key=f"date_{idx}")

                    c3, c4 = st.columns(2)
                    amount = c3.number_input("금액", value=parsed_total, step=100, key=f"amt_{idx}")

                    cat_index = 0
                    if parsed_category in category_names:
                        cat_index = category_names.index(parsed_category)
                    category = c4.selectbox(
                        "카테고리", category_names, index=cat_index, key=f"cat_{idx}"
                    ) if category_names else c4.text_input("카테고리", value=parsed_category, key=f"cat_{idx}")

                    selected_cat_id = st.session_state['categories'].get(category)

                    # 스토리지 업로드를 위해 파일 바이너리와 content_type도 함께 저장
                    file_suffix = Path(file.name).suffix.lower()
                    content_type = "image/png" if file_suffix == ".png" else "image/jpeg"

                    temp_data_list.append({
                        "store_name": store_name,
                        "date": date_val.strftime('%Y-%m-%d'),
                        "total_amount": amount,
                        "category": category,
                        "category_id": selected_cat_id,
                        "payment": parsed_payment,
                        "payment_method_id": PAYMENT_MAP.get(parsed_payment),
                        "file_name": file.name,
                        "file_bytes": file.getvalue(),
                        "content_type": content_type,
                    })

        # --- [2. 일괄 저장 버튼 - 클릭 시에만 DB에 저장] ---
        st.write("")
        if st.button(
            "💾 위 {0}건의 내역을 모두 장부에 저장".format(len(uploaded_files)),
            use_container_width=True, type="primary"
        ):
            success_count = 0
            fail_count = 0

            for data in temp_data_list:
                try:
                    # 1. Supabase Storage에 영수증 이미지 업로드
                    import time as _time
                    user_pk = st.session_state['user_pk']
                    name_part, ext_part = os.path.splitext(data['file_name'])
                    storage_path = f"user_{user_pk}/{name_part}_{int(_time.time())}{ext_part}"
                    upload_result = upload_image(
                        file_path=storage_path,
                        file_bytes=data["file_bytes"],
                        content_type=data["content_type"]
                    )

                    # 2. DB에 영수증 정보 저장 (image_path = 스토리지 경로)
                    create_receipt(
                        user_id=user_pk,
                        category_id=data["category_id"],
                        payment_method_id=data["payment_method_id"],
                        date=data["date"],
                        total_amount=data["total_amount"],
                        store_name=data["store_name"],
                        image_path=upload_result["path"],
                    )
                    # 3. OCR 캐시의 image_path와 이벤트 로그도 스토리지 경로로 갱신
                    ocr_cache = st.session_state['ocr_results'].get(data["file_name"])
                    if ocr_cache:
                        ocr_cache["image_path"] = upload_result["path"]
                        for event in ocr_cache.get("events", []):
                            if event.get("meta") and "image_path" in event["meta"]:
                                event["meta"]["image_path"] = upload_result["path"]

                    success_count += 1
                    st.session_state['history'].append({
                        "날짜": data["date"],
                        "상호명": data["store_name"],
                        "금액": data["total_amount"],
                        "카테고리": data["category"],
                    })
                except Exception as e:
                    fail_count += 1
                    st.error(f"❌ {data['store_name']} 저장 실패: {e}")

            if success_count > 0:
                st.balloons()
                st.success(f"✅ {success_count}건 저장 완료!" + (f" ({fail_count}건 실패)" if fail_count else ""))
            st.session_state['ocr_results'] = {}
            time.sleep(1)
            st.rerun()

    # --- [3. 장부 내역 테이블 표시] ---
    st.divider()
    st.subheader("📅 최근 기록된 장부 내역")

    if st.session_state['history']:
        df = pd.DataFrame(st.session_state['history'])
        st.dataframe(df.iloc[::-1], use_container_width=True)

        if st.sidebar.button("🗑️ 전체 데이터 초기화"):
            st.session_state['history'] = []
            st.rerun()
    else:
        st.write("아직 저장된 내역이 없습니다. 영수증을 업로드해 보세요!")


# --- 4-2. 지출 분석 페이지 ---
def page_analytics():
    import plotly.graph_objects as go
    from datetime import datetime

    st.title("📊 지출 분석 통계")

    # DB에서 현재 로그인한 사용자의 영수증 데이터 조회
    user_pk = st.session_state.get('user_pk')
    if not user_pk:
        st.warning("사용자 정보를 불러올 수 없습니다.")
        return

    try:
        receipts = get_receipts_by_user(user_pk)
    except Exception as e:
        st.error(f"데이터 조회 실패: {e}")
        return

    if not receipts:
        st.info("저장된 영수증 데이터가 없습니다. 영수증을 업로드하고 저장해 주세요.")
        return

    # --- [데이터 준비] ---
    cat_id_to_name = {v: k for k, v in st.session_state['categories'].items()}

    df = pd.DataFrame(receipts)
    df['날짜'] = pd.to_datetime(df['date'])
    df['연월'] = df['날짜'].dt.strftime('%Y-%m')
    df['금액'] = df['total_amount']
    df['상호명'] = df['store_name']
    df['카테고리'] = df['category_id'].map(cat_id_to_name).fillna("기타")

    # --- [요구사항 1] 연월 선택 (default: 오늘 날짜 기준) ---
    all_months = sorted(df['연월'].unique().tolist())
    current_month = datetime.now().strftime('%Y-%m')
    # 현재 연월이 데이터에 있으면 해당 인덱스, 없으면 가장 마지막 연월
    if current_month in all_months:
        default_idx = all_months.index(current_month)
    else:
        default_idx = len(all_months) - 1

    selected_month = st.selectbox(
        "조회할 연월 선택", all_months, index=default_idx, key="month_select"
    )

    # 선택된 연월로 필터링
    df_filtered = df[df['연월'] == selected_month]

    # --- [요약 지표] - 선택된 연월 기준 ---
    st.subheader(f"💰 {selected_month} 요약")
    m1, m2, m3 = st.columns(3)
    m1.metric("총 지출", f"{df_filtered['금액'].sum():,.0f}원")
    m2.metric("영수증 수", f"{len(df_filtered)}건")
    avg_val = df_filtered['금액'].mean() if len(df_filtered) > 0 else 0
    m3.metric("건당 평균", f"{avg_val:,.0f}원")

    st.divider()

    # --- [시각화 레이아웃] ---
    v_col1, v_col2 = st.columns([3, 2])

    with v_col1:
        # --- [요구사항 2] 막대/선 그래프 전환 ---
        chart_type = st.radio(
            "그래프 유형", ["막대 그래프", "선 그래프"],
            horizontal=True, key="chart_type"
        )

        # 전체 데이터 기준으로 월별 추이 표시 (선택 연월은 강조)
        monthly_sum = df.groupby(['연월', '카테고리'])['금액'].sum().reset_index()
        fig = go.Figure()

        if chart_type == "막대 그래프":
            for cat_name in monthly_sum['카테고리'].unique():
                subset = monthly_sum[monthly_sum['카테고리'] == cat_name]
                fig.add_trace(go.Bar(
                    x=subset['연월'].tolist(),
                    y=subset['금액'].tolist(),
                    name=cat_name,
                    text=subset['금액'].tolist(),
                    textposition='auto'
                ))
            fig.update_layout(barmode='group')
        else:
            for cat_name in monthly_sum['카테고리'].unique():
                subset = monthly_sum[monthly_sum['카테고리'] == cat_name]
                fig.add_trace(go.Scatter(
                    x=subset['연월'].tolist(),
                    y=subset['금액'].tolist(),
                    name=cat_name,
                    mode='lines+markers+text',
                    text=subset['금액'].tolist(),
                    textposition='top center'
                ))

        fig.update_layout(
            title="월별 지출 추이",
            height=400,
            xaxis_title="연월",
            yaxis_title="금액",
            xaxis_type='category'
        )
        st.plotly_chart(fig, use_container_width=True)

    with v_col2:
        # 선택된 연월의 카테고리 비중 파이 차트
        cat_sum = df_filtered.groupby('카테고리')['금액'].sum().reset_index()
        fig_pie = px.pie(
            cat_sum, values='금액', names='카테고리',
            title=f"{selected_month} 카테고리별 지출 비중", hole=0.4
        )
        fig_pie.update_layout(height=400)
        st.plotly_chart(fig_pie, use_container_width=True)

    # --- [AI 월별 조언 섹션] - 그래프와 영수증 내역 사이 ---
    st.divider()
    st.subheader("🤖 AI 월별 지출 조언")

    df_advice_month = df[df['연월'] == selected_month]

    if len(df_advice_month) == 0:
        st.info(f"📭 {selected_month} 지출 내역이 없습니다.")
    else:
        if st.button(f"🔍 {selected_month} AI 조언 받기", key="ai_advice_btn", type="primary"):
            with st.spinner("AI가 지출 내역을 분석하고 있습니다..."):
                try:
                    import google.generativeai as genai
                    from utils.config import GEMINI_API_KEY
                    import json as _json

                    if not GEMINI_API_KEY:
                        st.error("GEMINI_API_KEY가 .env에 설정되지 않았습니다.")
                    else:
                        genai.configure(api_key=GEMINI_API_KEY)
                        model = genai.GenerativeModel("gemini-2.5-flash")

                        advice_data = []
                        for _, r in df_advice_month.iterrows():
                            advice_data.append({
                                "date": r['날짜'].strftime('%Y-%m-%d'),
                                "store_name": r['상호명'],
                                "total_amount": int(r['금액']),
                                "category": r['카테고리']
                            })

                        prompt = f"""다음은 사용자의 {selected_month} 월 소비 데이터입니다.

{_json.dumps(advice_data, ensure_ascii=False, indent=2)}

다음 내용을 한국어로 간결하게 분석해주세요:

1. 소비 패턴 요약
2. 과소비 카테고리
3. 절약을 위한 구체적 조언
4. 한 줄 요약

마크다운 형식으로 작성해주세요."""

                        response = model.generate_content(prompt)
                        st.session_state['ai_advice'] = response.text
                        st.session_state['ai_advice_month'] = selected_month
                except Exception as e:
                    st.error(f"AI 조언 생성 실패: {e}")

        # 저장된 조언이 있으면 표시 (해당 연월 조언만)
        if st.session_state.get('ai_advice') and st.session_state.get('ai_advice_month') == selected_month:
            st.markdown("---")
            st.markdown(st.session_state['ai_advice'])

    # --- [전체 영수증 내역] (페이지네이션 + 선택 삭제 + 이미지 보기) ---
    st.divider()
    st.subheader("📅 전체 영수증 내역")

    # 최신순 정렬
    display_df = df.sort_values('날짜', ascending=False).reset_index(drop=True)

    # --- [장부 다운로드] ---
    import io
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        # ── 전체 내역 시트 ──
        all_df = display_df[['날짜', '상호명', '금액', '카테고리']].copy()
        all_df['날짜'] = all_df['날짜'].dt.strftime('%Y-%m-%d')

        total_amount = all_df['금액'].sum()
        avg_amount = all_df['금액'].mean() if len(all_df) > 0 else 0
        cat_summary = all_df.groupby('카테고리')['금액'].sum().reset_index()
        cat_summary.columns = ['카테고리', '합계']
        cat_summary = cat_summary.sort_values('합계', ascending=False)

        summary_rows = pd.DataFrame([
            {'날짜': '총 지출', '상호명': '', '금액': total_amount, '카테고리': ''},
            {'날짜': '건당 평균', '상호명': '', '금액': round(avg_amount), '카테고리': ''},
            {'날짜': '', '상호명': '', '금액': '', '카테고리': ''},
            {'날짜': '[카테고리별 합계]', '상호명': '', '금액': '', '카테고리': ''},
        ])
        cat_rows = pd.DataFrame({
            '날짜': cat_summary['카테고리'].values,
            '상호명': '',
            '금액': cat_summary['합계'].values,
            '카테고리': ''
        })
        spacer = pd.DataFrame([{'날짜': '', '상호명': '', '금액': '', '카테고리': ''}])
        header_row = pd.DataFrame([{'날짜': '[전체 내역]', '상호명': '', '금액': '', '카테고리': ''}])

        full_sheet = pd.concat([summary_rows, cat_rows, spacer, header_row, all_df], ignore_index=True)
        full_sheet.to_excel(writer, sheet_name='전체 내역', index=False)

        # ── 월별 시트 ──
        months_sorted = sorted(display_df['연월'].unique().tolist())
        for month in months_sorted:
            month_data = display_df[display_df['연월'] == month][['날짜', '상호명', '금액', '카테고리']].copy()
            month_data['날짜'] = month_data['날짜'].dt.strftime('%Y-%m-%d')
            month_data = month_data.sort_values('날짜', ascending=False).reset_index(drop=True)

            m_total = month_data['금액'].sum()
            m_avg = month_data['금액'].mean() if len(month_data) > 0 else 0
            m_cat = month_data.groupby('카테고리')['금액'].sum().reset_index()
            m_cat.columns = ['카테고리', '합계']
            m_cat = m_cat.sort_values('합계', ascending=False)

            m_summary = pd.DataFrame([
                {'날짜': '총 지출', '상호명': '', '금액': m_total, '카테고리': ''},
                {'날짜': '건당 평균', '상호명': '', '금액': round(m_avg), '카테고리': ''},
                {'날짜': '', '상호명': '', '금액': '', '카테고리': ''},
                {'날짜': '[카테고리별 합계]', '상호명': '', '금액': '', '카테고리': ''},
            ])
            m_cat_rows = pd.DataFrame({
                '날짜': m_cat['카테고리'].values,
                '상호명': '',
                '금액': m_cat['합계'].values,
                '카테고리': ''
            })
            m_header = pd.DataFrame([{'날짜': '', '상호명': '', '금액': '', '카테고리': ''}])
            m_detail_header = pd.DataFrame([{'날짜': '[상세 내역]', '상호명': '', '금액': '', '카테고리': ''}])

            month_sheet = pd.concat([m_summary, m_cat_rows, m_header, m_detail_header, month_data], ignore_index=True)
            month_sheet.to_excel(writer, sheet_name=month, index=False)

    st.download_button(
        "📥 장부 다운로드",
        data=excel_buffer.getvalue(),
        file_name=f"장부_{st.session_state['user_id']}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    # 페이지네이션 설정
    PAGE_SIZE = 10
    total_rows = len(display_df)
    total_pages = max(1, (total_rows + PAGE_SIZE - 1) // PAGE_SIZE)

    if 'receipt_page' not in st.session_state:
        st.session_state['receipt_page'] = 1

    # 현재 페이지 데이터 슬라이스
    current_page = st.session_state['receipt_page']
    start_idx = (current_page - 1) * PAGE_SIZE
    end_idx = min(start_idx + PAGE_SIZE, total_rows)
    page_df = display_df.iloc[start_idx:end_idx]

    # --- [전체 선택 체크박스] ---
    select_all = st.checkbox("전체 선택", key="select_all_receipts")

    # 테이블 표시 (체크박스 + expander)
    for i, row in page_df.iterrows():
        date_str = row['날짜'].strftime('%Y-%m-%d')
        receipt_id = row.get('id')

        chk_col, exp_col = st.columns([0.3, 9.7])

        with chk_col:
            checked = st.checkbox(
                "sel", key=f"chk_{receipt_id}",
                value=select_all, label_visibility="collapsed"
            )

        with exp_col:
            label = f"{date_str}  |  {row['상호명']}  |  {row['금액']:,.0f}원  |  {row['카테고리']}"
            with st.expander(label):
                image_path = row.get('image_path')
                if image_path and str(image_path) != 'None':
                    try:
                        img_url = get_public_url(image_path)
                        img_col, _ = st.columns([1, 2])
                        with img_col:
                            st.image(img_url, caption=f"{row['상호명']} 영수증", use_column_width=True)
                    except Exception as e:
                        st.warning(f"이미지를 불러올 수 없습니다: {e}")
                else:
                    st.info("저장된 영수증 이미지가 없습니다.")

    # --- [선택 삭제 버튼] ---
    # 현재 페이지에서 체크된 영수증 ID 수집
    selected_ids = []
    selected_image_paths = []
    for i, row in page_df.iterrows():
        receipt_id = row.get('id')
        if st.session_state.get(f"chk_{receipt_id}", False):
            selected_ids.append(receipt_id)
            img_path = row.get('image_path')
            if img_path and str(img_path) != 'None':
                selected_image_paths.append(img_path)

    st.write("")
    del_col1, del_col2 = st.columns([3, 7])
    with del_col1:
        if st.button(
            f"🗑️ 선택 영수증 삭제 ({len(selected_ids)}건)",
            disabled=(len(selected_ids) == 0),
            use_container_width=True,
            type="primary"
        ):
            st.session_state['confirm_delete'] = True
            st.session_state['delete_ids'] = selected_ids
            st.session_state['delete_image_paths'] = selected_image_paths

    # --- [삭제 확인 다이얼로그] ---
    if st.session_state.get('confirm_delete'):
        ids_to_delete = st.session_state.get('delete_ids', [])
        imgs_to_delete = st.session_state.get('delete_image_paths', [])

        st.warning(f"⚠️ 정말 {len(ids_to_delete)}건의 영수증을 삭제하시겠습니까? (DB + 이미지 모두 삭제됩니다)")
        conf_col1, conf_col2, _ = st.columns([1, 1, 3])
        with conf_col1:
            if st.button("삭제 확인", type="primary", key="confirm_yes"):
                success = 0
                fail = 0
                for rid in ids_to_delete:
                    try:
                        delete_receipt(rid)
                        success += 1
                    except Exception as e:
                        fail += 1
                        st.error(f"DB 삭제 실패 (id={rid}): {e}")
                for img_path in imgs_to_delete:
                    try:
                        delete_image(img_path)
                    except Exception:
                        pass  # 이미지 삭제 실패는 무시 (DB 삭제가 핵심)
                st.session_state['confirm_delete'] = False
                st.session_state.pop('delete_ids', None)
                st.session_state.pop('delete_image_paths', None)
                if success > 0:
                    st.success(f"✅ {success}건 삭제 완료" + (f" ({fail}건 실패)" if fail else ""))
                time.sleep(1)
                st.rerun()
        with conf_col2:
            if st.button("취소", key="confirm_no"):
                st.session_state['confirm_delete'] = False
                st.session_state.pop('delete_ids', None)
                st.session_state.pop('delete_image_paths', None)
                st.rerun()

    # 페이지 네비게이션
    if total_pages > 1:
        st.write("")
        nav_cols = st.columns([1, 2, 1])
        with nav_cols[0]:
            if st.button("◀ 이전", disabled=(current_page <= 1), key="prev_page"):
                st.session_state['receipt_page'] = current_page - 1
                st.rerun()
        with nav_cols[1]:
            st.markdown(
                f"<div style='text-align:center'>{current_page} / {total_pages} 페이지</div>",
                unsafe_allow_html=True
            )
        with nav_cols[2]:
            if st.button("다음 ▶", disabled=(current_page >= total_pages), key="next_page"):
                st.session_state['receipt_page'] = current_page + 1
                st.rerun()

# --- 5. 실행 로직 (이 부분이 있어야 작동합니다!) ---
if not st.session_state['logged_in']:
    auth_page()
else:
    main_app()
    