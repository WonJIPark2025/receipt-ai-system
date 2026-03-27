"""
receipt_mobile.py - 모바일 전용 UI

담당: 프론트엔드
설명: 모바일 기기에 최적화된 영수증 AI 장부 UI
    - app.py에서 모바일 감지 시 이 파일로 분기
    - receipt_front.py와 동일한 기능을 모바일 레이아웃으로 제공
    - 세로 1컬럼 레이아웃, 터치 친화적 구성
    - 사이드바 없음 → 상단 탭 메뉴로 대체
포함 기능:
    - Supabase 로그인/회원가입 + localStorage 로그인 유지
    - Gemini 영수증 분석 + DB/Storage 저장
    - 지출 분석 (연월 선택, 막대/선 그래프, 파이 차트)
    - AI 월별 조언 (Gemini)
#       - 영수증 내역 페이지네이션 + 이미지 보기
# =============================================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import time
import tempfile
import os
import sys
from pathlib import Path
from streamlit_js_eval import streamlit_js_eval

# 프로젝트 루트를 path에 추가
#sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.api.users import get_user_by_user_id, create_user
from backend.api.categories import get_all_categories
from backend.api.receipts import create_receipt, get_receipts_by_user, delete_receipt
from backend.api.storage import upload_image, get_public_url, delete_image
from services.ai.gemini import extract_receipt_data
from services.ai.validator import validate_receipt


# =============================================================================
# 1. 모바일 전용 CSS 스타일
# =============================================================================
def apply_mobile_style():
    st.markdown("""
    <style>
        /* 메인 컨테이너 패딩 축소 */
        .block-container {
            padding-top: 1rem;
            padding-left: 0.8rem;
            padding-right: 0.8rem;
        }
        /* 입력창 터치 친화적 */
        .stTextInput > div > div > input,
        .stSelectbox > div > div > div,
        .stDateInput > div > div > input {
            font-size: 16px;
            padding: 12px;
        }
        /* 버튼 크기 확대 */
        .stButton > button {
            font-size: 16px;
            padding: 12px;
            border-radius: 10px;
        }
        /* 사이드바 숨기기 */
        [data-testid="stSidebar"] { display: none; }
        /* 파일 업로더 확대 */
        [data-testid="stFileUploader"] { padding: 8px; }
        /* 탭 폰트 크기 */
        .stTabs [data-baseweb="tab"] {
            font-size: 15px;
            padding: 10px 14px;
        }
        /* metric 카드 패딩 축소 */
        [data-testid="stMetric"] {
            padding: 8px 4px;
        }
    </style>
    """, unsafe_allow_html=True)


# =============================================================================
# 2. Supabase 로그인/회원가입 함수
# =============================================================================
def check_login(user_id: str, password: str) -> dict:
    try:
        user = get_user_by_user_id(user_id)
        if user and user.get("password") == password:
            return user
        return None
    except Exception as e:
        st.error(f"DB 연결 오류: {e}")
        return None


def register_user(user_id: str, password: str, name: str = None) -> bool:
    try:
        existing = get_user_by_user_id(user_id)
        if existing:
            return False
        result = create_user(name=name or user_id, user_id=user_id, password=password)
        return result is not None
    except Exception as e:
        st.error(f"회원가입 오류: {e}")
        return False


# =============================================================================
# 3. 세션 상태 초기화
# =============================================================================
st.set_page_config(page_title="영수증 AI 장부", layout="centered")

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None
if 'user_pk' not in st.session_state:
    st.session_state['user_pk'] = None
if 'history' not in st.session_state:
    st.session_state['history'] = []

# --- [로그아웃 처리 - localStorage 삭제] ---
if st.session_state.get('pending_logout'):
    streamlit_js_eval(js_expressions="localStorage.removeItem('receipt_user_id')", key="m_del_uid")
    streamlit_js_eval(js_expressions="localStorage.removeItem('receipt_user_pk')", key="m_del_upk")
    st.session_state['pending_logout'] = False

# --- [localStorage에서 로그인 복원] ---
if not st.session_state['logged_in'] and not st.session_state.get('pending_logout'):
    saved_user_id = streamlit_js_eval(js_expressions="localStorage.getItem('receipt_user_id')", key="m_restore_uid")
    saved_user_pk = streamlit_js_eval(js_expressions="localStorage.getItem('receipt_user_pk')", key="m_restore_upk")
    if saved_user_id and saved_user_pk and saved_user_id != "null":
        st.session_state['logged_in'] = True
        st.session_state['user_id'] = saved_user_id
        st.session_state['user_pk'] = int(saved_user_pk)


# =============================================================================
# 4. 모바일 로그인 / 회원가입 화면
# =============================================================================
def auth_page():
    st.markdown("<h2 style='text-align: center;'>🔐 AI 장부</h2>", unsafe_allow_html=True)
    st.markdown("---")

    tab1, tab2 = st.tabs(["로그인", "회원가입"])

    with tab1:
        login_id = st.text_input("아이디", key="m_login_id", placeholder="아이디를 입력하세요")
        login_pw = st.text_input("비밀번호", type="password", key="m_login_pw", placeholder="비밀번호를 입력하세요")
        st.markdown("")
        if st.button("로그인", use_container_width=True, type="primary"):
            user = check_login(login_id, login_pw)
            if user:
                st.session_state['logged_in'] = True
                st.session_state['user_id'] = login_id
                st.session_state['user_pk'] = user.get("id")
                streamlit_js_eval(js_expressions=f"localStorage.setItem('receipt_user_id', '{login_id}')", key="m_save_uid")
                streamlit_js_eval(js_expressions=f"localStorage.setItem('receipt_user_pk', '{user.get('id')}')", key="m_save_upk")
                st.success(f"{login_id}님 환영합니다!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 잘못되었습니다.")

    with tab2:
        new_id = st.text_input("사용할 아이디", key="m_new_id", placeholder="아이디")
        new_pw = st.text_input("사용할 비밀번호", type="password", key="m_new_pw", placeholder="비밀번호")
        confirm_pw = st.text_input("비밀번호 확인", type="password", key="m_confirm_pw", placeholder="비밀번호 확인")
        st.markdown("")
        if st.button("회원가입 완료", use_container_width=True, type="primary"):
            if not new_id or not new_pw:
                st.warning("아이디와 비밀번호를 모두 입력해주세요.")
            elif new_pw != confirm_pw:
                st.error("비밀번호가 일치하지 않습니다.")
            else:
                if register_user(new_id, new_pw):
                    st.success("회원가입 성공! 로그인 탭에서 로그인해주세요.")
                else:
                    st.error("이미 존재하는 아이디입니다.")


# =============================================================================
# 5. 메인 앱 화면 - 상단 탭으로 페이지 전환
# =============================================================================
def main_app():
    # --- 상단 헤더 (사이드바 대체) ---
    h1, h2 = st.columns([3, 1])
    with h1:
        st.markdown(f"👤 **{st.session_state['user_id']}**님")
    with h2:
        if st.button("로그아웃", use_container_width=True):
            st.session_state['logged_in'] = False
            st.session_state['user_id'] = None
            st.session_state['user_pk'] = None
            st.session_state['pending_logout'] = True
            st.rerun()

    # --- 카테고리 목록 DB 로드 ---
    if 'categories' not in st.session_state:
        try:
            cat_list = get_all_categories()
            st.session_state['categories'] = {c["name"]: c["id"] for c in cat_list}
        except Exception as e:
            st.warning(f"카테고리 로드 실패: {e}")
            st.session_state['categories'] = {}

    # --- 탭 메뉴로 페이지 전환 ---
    tab_upload, tab_analytics = st.tabs(["🧾 영수증 업로드", "📊 지출 분석"])

    with tab_upload:
        page_upload()
    with tab_analytics:
        page_analytics()


# =============================================================================
# 5-1. 영수증 업로드 페이지 (모바일 - 세로 1컬럼)
# =============================================================================
def page_upload():
    category_names = list(st.session_state['categories'].keys())

    st.markdown("### 🧾 영수증 AI 장부")
    st.info("영수증 사진을 업로드하면 AI가 자동으로 내용을 인식합니다.")

    # --- 파일 업로드 ---
    uploaded_files = st.file_uploader(
        "영수증 사진 선택 (JPG, PNG)",
        type=['jpg', 'jpeg', 'png'],
        accept_multiple_files=True,
        key="m_uploader"
    )

    # --- Gemini 분석 실행 ---
    if 'ocr_results' not in st.session_state:
        st.session_state['ocr_results'] = {}

    if uploaded_files:
        for file in uploaded_files:
            if file.name not in st.session_state['ocr_results']:
                with st.spinner(f"🔍 {file.name} 분석 중..."):
                    try:
                        suffix = Path(file.name).suffix
                        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                        tmp.write(file.getbuffer())
                        tmp.close()
                        data = extract_receipt_data(tmp.name)
                        validation = validate_receipt(data)
                        result = {**data, **validation}
                        st.session_state['ocr_results'][file.name] = result
                        os.unlink(tmp.name)
                    except Exception as e:
                        st.session_state['ocr_results'][file.name] = {
                            "validation_status": "error",
                            "error_msg": str(e)
                        }

        st.markdown("---")
        st.markdown(f"**🔍 추출 결과 ({len(uploaded_files)}건)**")

        temp_data_list = []

        for idx, file in enumerate(uploaded_files):
            ocr_data = st.session_state['ocr_results'].get(file.name, {})

            parsed_store = ocr_data.get("store_name", "")
            parsed_date_str = ocr_data.get("date", "")
            parsed_total = ocr_data.get("total", 0)

            from datetime import date as _date
            try:
                parsed_date = _date.fromisoformat(parsed_date_str[:10])
            except (ValueError, TypeError):
                parsed_date = _date.today()
            parsed_category = ocr_data.get("category", "기타")
            validation_status = ocr_data.get("validation_status", "error")

            with st.expander(f"📄 #{idx+1} {file.name}", expanded=(idx == 0)):
                # 모바일: 이미지를 위에, 폼을 아래에 세로 배치
                st.image(file, use_column_width=True)

                if validation_status == "success":
                    st.success("✅ AI 분석 성공")
                elif validation_status == "review_required":
                    st.warning("⚠️ 검토 필요")
                else:
                    st.error("❌ AI 분석 실패")

                store_name = st.text_input("상호명", value=parsed_store, key=f"m_store_{idx}")
                date_val = st.date_input("날짜", value=parsed_date, key=f"m_date_{idx}")
                amount = st.number_input("금액", value=parsed_total, step=100, key=f"m_amt_{idx}")

                cat_index = 0
                if parsed_category in category_names:
                    cat_index = category_names.index(parsed_category)
                category = st.selectbox(
                    "카테고리", category_names, index=cat_index, key=f"m_cat_{idx}"
                ) if category_names else st.text_input("카테고리", value=parsed_category, key=f"m_cat_{idx}")

                selected_cat_id = st.session_state['categories'].get(category)

                file_suffix = Path(file.name).suffix.lower()
                content_type = "image/png" if file_suffix == ".png" else "image/jpeg"

                temp_data_list.append({
                    "store_name": store_name,
                    "date": date_val.strftime('%Y-%m-%d'),
                    "total_amount": amount,
                    "category": category,
                    "category_id": selected_cat_id,
                    "file_name": file.name,
                    "file_bytes": file.getvalue(),
                    "content_type": content_type,
                })

        # --- 일괄 저장 버튼 ---
        st.markdown("")
        if st.button(
            f"💾 {len(uploaded_files)}건 장부에 저장",
            use_container_width=True, type="primary"
        ):
            import time as _time
            success_count = 0
            fail_count = 0

            for data in temp_data_list:
                try:
                    user_pk = st.session_state['user_pk']
                    name_part, ext_part = os.path.splitext(data['file_name'])
                    storage_path = f"user_{user_pk}/{name_part}_{int(_time.time())}{ext_part}"
                    upload_result = upload_image(
                        file_path=storage_path,
                        file_bytes=data["file_bytes"],
                        content_type=data["content_type"]
                    )
                    create_receipt(
                        user_id=user_pk,
                        category_id=data["category_id"],
                        date=data["date"],
                        total_amount=data["total_amount"],
                        store_name=data["store_name"],
                        image_path=upload_result["path"],
                    )
                    ocr_cache = st.session_state['ocr_results'].get(data["file_name"])
                    if ocr_cache:
                        ocr_cache["image_path"] = upload_result["path"]

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

    # --- 최근 장부 내역 ---
    st.markdown("---")
    st.markdown("**📅 최근 장부 내역**")
    if st.session_state['history']:
        df = pd.DataFrame(st.session_state['history'])
        st.dataframe(df.iloc[::-1], use_container_width=True)
    else:
        st.caption("아직 저장된 내역이 없습니다.")


# =============================================================================
# 5-2. 지출 분석 페이지 (모바일 - 세로 1컬럼)
# =============================================================================
def page_analytics():
    import plotly.graph_objects as go
    from datetime import datetime

    st.markdown("### 📊 지출 분석")

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
        st.info("저장된 영수증이 없습니다. 영수증을 업로드해 주세요.")
        return

    # --- 데이터 준비 ---
    cat_id_to_name = {v: k for k, v in st.session_state['categories'].items()}

    df = pd.DataFrame(receipts)
    df['날짜'] = pd.to_datetime(df['date'])
    df['연월'] = df['날짜'].dt.strftime('%Y-%m')
    df['금액'] = df['total_amount']
    df['상호명'] = df['store_name']
    df['카테고리'] = df['category_id'].map(cat_id_to_name).fillna("기타")

    # --- 연월 선택 ---
    all_months = sorted(df['연월'].unique().tolist())
    current_month = datetime.now().strftime('%Y-%m')
    if current_month in all_months:
        default_idx = all_months.index(current_month)
    else:
        default_idx = len(all_months) - 1

    selected_month = st.selectbox(
        "조회할 연월", all_months, index=default_idx, key="m_month_select"
    )
    df_filtered = df[df['연월'] == selected_month]

    # --- 요약 지표 ---
    st.markdown(f"**💰 {selected_month} 요약**")
    m1, m2, m3 = st.columns(3)
    m1.metric("총 지출", f"{df_filtered['금액'].sum():,.0f}원")
    m2.metric("영수증", f"{len(df_filtered)}건")
    avg_val = df_filtered['금액'].mean() if len(df_filtered) > 0 else 0
    m3.metric("건당 평균", f"{avg_val:,.0f}원")

    st.markdown("---")

    # --- 월별 추이 그래프 (세로 배치) ---
    chart_type = st.radio(
        "그래프 유형", ["막대 그래프", "선 그래프"],
        horizontal=True, key="m_chart_type"
    )

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
        height=350,
        xaxis_title="연월",
        yaxis_title="금액",
        xaxis_type='category',
        margin=dict(l=10, r=10, t=40, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=-0.3)
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- 카테고리 파이 차트 ---
    cat_sum = df_filtered.groupby('카테고리')['금액'].sum().reset_index()
    fig_pie = px.pie(
        cat_sum, values='금액', names='카테고리',
        title=f"{selected_month} 카테고리별 비중", hole=0.4
    )
    fig_pie.update_layout(
        height=350,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2)
    )
    st.plotly_chart(fig_pie, use_container_width=True)

    # --- AI 월별 조언 ---
    st.markdown("---")
    st.markdown("**🤖 AI 월별 지출 조언**")

    df_advice_month = df[df['연월'] == selected_month]

    if len(df_advice_month) == 0:
        st.info(f"📭 {selected_month} 지출 내역이 없습니다.")
    else:
        if st.button(f"🔍 {selected_month} AI 조언 받기", key="m_ai_advice_btn", type="primary", use_container_width=True):
            with st.spinner("AI가 분석 중..."):
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

        if st.session_state.get('ai_advice') and st.session_state.get('ai_advice_month') == selected_month:
            st.markdown("---")
            st.markdown(st.session_state['ai_advice'])

    # --- 영수증 내역 (페이지네이션 + 선택 삭제 + 이미지) ---
    st.markdown("---")
    st.markdown("**📅 전체 영수증 내역**")

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
        use_container_width=True,
        key="m_dl_excel"
    )

    PAGE_SIZE = 5  # 모바일은 5건씩
    total_rows = len(display_df)
    total_pages = max(1, (total_rows + PAGE_SIZE - 1) // PAGE_SIZE)

    if 'receipt_page' not in st.session_state:
        st.session_state['receipt_page'] = 1

    current_page = st.session_state['receipt_page']
    start_idx = (current_page - 1) * PAGE_SIZE
    end_idx = min(start_idx + PAGE_SIZE, total_rows)
    page_df = display_df.iloc[start_idx:end_idx]

    # --- [전체 선택 체크박스] ---
    select_all = st.checkbox("전체 선택", key="m_select_all_receipts")

    for i, row in page_df.iterrows():
        date_str = row['날짜'].strftime('%Y-%m-%d')
        receipt_id = row.get('id')

        # 모바일: 체크박스를 expander 위에 같은 줄로 배치
        chk_col, exp_col = st.columns([0.5, 9.5])

        with chk_col:
            st.checkbox(
                "sel", key=f"m_chk_{receipt_id}",
                value=select_all, label_visibility="collapsed"
            )

        with exp_col:
            label = f"{date_str} | {row['상호명']} | {row['금액']:,.0f}원"
            with st.expander(label):
                st.caption(f"카테고리: {row['카테고리']}")
                image_path = row.get('image_path')
                if image_path and str(image_path) != 'None':
                    try:
                        img_url = get_public_url(image_path)
                        st.image(img_url, caption=f"{row['상호명']} 영수증", use_column_width=True)
                    except Exception as e:
                        st.warning(f"이미지 로드 실패: {e}")
                else:
                    st.caption("영수증 이미지 없음")

    # --- [선택 삭제 버튼] ---
    selected_ids = []
    selected_image_paths = []
    for i, row in page_df.iterrows():
        receipt_id = row.get('id')
        if st.session_state.get(f"m_chk_{receipt_id}", False):
            selected_ids.append(receipt_id)
            img_path = row.get('image_path')
            if img_path and str(img_path) != 'None':
                selected_image_paths.append(img_path)

    st.markdown("")
    if st.button(
        f"🗑️ 선택 삭제 ({len(selected_ids)}건)",
        disabled=(len(selected_ids) == 0),
        use_container_width=True,
        type="primary"
    ):
        st.session_state['m_confirm_delete'] = True
        st.session_state['m_delete_ids'] = selected_ids
        st.session_state['m_delete_image_paths'] = selected_image_paths

    # --- [삭제 확인] ---
    if st.session_state.get('m_confirm_delete'):
        ids_to_delete = st.session_state.get('m_delete_ids', [])
        imgs_to_delete = st.session_state.get('m_delete_image_paths', [])

        st.warning(f"⚠️ {len(ids_to_delete)}건 삭제하시겠습니까? (DB + 이미지 모두 삭제)")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("삭제 확인", type="primary", key="m_confirm_yes", use_container_width=True):
                success = 0
                fail = 0
                for rid in ids_to_delete:
                    try:
                        delete_receipt(rid)
                        success += 1
                    except Exception as e:
                        fail += 1
                        st.error(f"삭제 실패 (id={rid}): {e}")
                for img_path in imgs_to_delete:
                    try:
                        delete_image(img_path)
                    except Exception:
                        pass
                st.session_state['m_confirm_delete'] = False
                st.session_state.pop('m_delete_ids', None)
                st.session_state.pop('m_delete_image_paths', None)
                if success > 0:
                    st.success(f"✅ {success}건 삭제 완료" + (f" ({fail}건 실패)" if fail else ""))
                time.sleep(1)
                st.rerun()
        with c2:
            if st.button("취소", key="m_confirm_no", use_container_width=True):
                st.session_state['m_confirm_delete'] = False
                st.session_state.pop('m_delete_ids', None)
                st.session_state.pop('m_delete_image_paths', None)
                st.rerun()

    # 페이지 네비게이션
    if total_pages > 1:
        st.markdown("")
        nav1, nav2, nav3 = st.columns([1, 2, 1])
        with nav1:
            if st.button("◀", disabled=(current_page <= 1), key="m_prev", use_container_width=True):
                st.session_state['receipt_page'] = current_page - 1
                st.rerun()
        with nav2:
            st.markdown(
                f"<div style='text-align:center; padding:8px 0;'>{current_page} / {total_pages}</div>",
                unsafe_allow_html=True
            )
        with nav3:
            if st.button("▶", disabled=(current_page >= total_pages), key="m_next", use_container_width=True):
                st.session_state['receipt_page'] = current_page + 1
                st.rerun()


# =============================================================================
# 6. 실행 로직
# =============================================================================
apply_mobile_style()

if not st.session_state['logged_in']:
    auth_page()
else:
    main_app()
