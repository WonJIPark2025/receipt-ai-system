"""
OCR_front.py - 데스크톱 전용 UI

담당: 프론트엔드
설명: 데스크톱/노트북에 최적화된 영수증 OCR 시스템 UI
    - app.py에서 데스크톱 감지 시 이 파일로 분기
    - wide 레이아웃, 사이드바 메뉴 구성
포함 기능:
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

# 프로젝트 루트를 path에 추가 (backend 모듈 import를 위해)
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.api.categories import get_all_categories
from backend.api.receipts import create_receipt, get_receipts_by_user, delete_receipt
from backend.api.receipt_items import create_receipt_items
from backend.api.storage import upload_image, get_public_url, delete_image
from services.ocr_pipeline.pipeline.run_pipeline import run_pipeline
from services.ocr_pipeline.persistence.db_mapper import _resolve_activity_tag
from utils.config import DEFAULT_USER_ID

# purchase_type UI 레이블 → DB 값 매핑
PURCHASE_TYPE_OPTIONS = {
    "간편": "general",
    "배달": "delivery",
    "포장": "takeout",
    "매장": "dine_in",
    "직접 요리": "cooking",
}

# --- 1. 페이지 설정 및 세션 상태 초기화 ---
st.set_page_config(page_title="영수증 OCR 장부", layout="wide")

if 'history' not in st.session_state:
    st.session_state['history'] = []


# --- 2. 메인 앱 화면 (main_app) - 사이드바 페이지 전환 허브 ---
def main_app():
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


# --- 3. 영수증 업로드 페이지 ---
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

            # OCR 날짜+시간 문자열 파싱
            from datetime import date as _date, time as _time, datetime as _datetime
            try:
                parsed_dt = _datetime.fromisoformat(parsed_date_str)
                parsed_date = parsed_dt.date()
                parsed_time = parsed_dt.time()
            except (ValueError, TypeError):
                parsed_date = _date.today()
                parsed_time = _time(0, 0)
            parsed_category = ocr_data.get("category", "기타")
            validation_status = ocr_data.get("validation_status", "error")

            # LLM 통합 추론 — 1회 호출로 식사 방식 + 품목 동시 추출 (캐싱)
            raw_text_for_llm = ocr_data.get("raw_text", "")
            infer_cache_key = f"inferred_{file.name}"
            if infer_cache_key not in st.session_state:
                from services.ai.receipt_inferrer import infer_receipt_fields
                st.session_state[infer_cache_key] = infer_receipt_fields(raw_text_for_llm)
            inferred = st.session_state[infer_cache_key]

            PT_DB_TO_LABEL = {v: k for k, v in PURCHASE_TYPE_OPTIONS.items()}
            inferred_label = PT_DB_TO_LABEL.get(inferred["purchase_type"], "간편")
            inferred_items = inferred["items"]

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

                    c1b, c2b = st.columns(2)
                    time_val = c1b.time_input("결제 시간", value=parsed_time, key=f"time_{idx}", step=60)

                    c3, c4 = st.columns(2)
                    amount = c3.number_input("금액", value=parsed_total, step=100, key=f"amt_{idx}")

                    cat_index = 0
                    if parsed_category in category_names:
                        cat_index = category_names.index(parsed_category)
                    category = c4.selectbox(
                        "카테고리", category_names, index=cat_index, key=f"cat_{idx}"
                    ) if category_names else c4.text_input("카테고리", value=parsed_category, key=f"cat_{idx}")

                    selected_cat_id = st.session_state['categories'].get(category)

                    pt_options = list(PURCHASE_TYPE_OPTIONS.keys())
                    pt_default_idx = pt_options.index(inferred_label) if inferred_label in pt_options else 0
                    purchase_type_label = st.selectbox(
                        "식사 방식",
                        pt_options,
                        index=pt_default_idx,
                        key=f"pt_{idx}"
                    )

                    memo = st.text_input("메모 (일기)", key=f"memo_{idx}")

                    # 품목 확인 및 수정 (항상 LLM 추출 — 사전 캐싱된 결과 사용)
                    raw_items = inferred_items
                    st.caption(f"품목 출처: LLM ({len(raw_items)}건)")

                    items_df = pd.DataFrame(
                        [{"품목명": i.get("name", ""), "수량": i.get("quantity", 1), "단가": i.get("price", 0)}
                         for i in raw_items]
                        if raw_items else
                        [{"품목명": "", "수량": 1, "단가": 0}]
                    )
                    edited_df = st.data_editor(
                        items_df, key=f"items_{idx}",
                        num_rows="dynamic", use_container_width=True
                    )
                    edited_items = [
                        {
                            "name":     row["품목명"],
                            "quantity": int(row["수량"]) if pd.notna(row["수량"]) else 1,
                            "price":    int(row["단가"]) if pd.notna(row["단가"]) else 0,
                        }
                        for _, row in edited_df.iterrows()
                        if row["품목명"] and pd.notna(row["품목명"])
                    ]

                    # 스토리지 업로드를 위해 파일 바이너리와 content_type도 함께 저장
                    file_suffix = Path(file.name).suffix.lower()
                    content_type = "image/png" if file_suffix == ".png" else "image/jpeg"

                    temp_data_list.append({
                        "store_name": store_name,
                        "paid_at": f"{date_val.strftime('%Y-%m-%d')}T{time_val.strftime('%H:%M:%S')}+09:00",
                        "total_amount": amount,
                        "category": category,
                        "category_id": selected_cat_id,
                        "purchase_type": PURCHASE_TYPE_OPTIONS[purchase_type_label],
                        "memo": memo or None,
                        "raw_text": ocr_data.get("raw_text", ""),
                        "items": edited_items,
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
                    name_part, ext_part = os.path.splitext(data['file_name'])
                    storage_path = f"user_{DEFAULT_USER_ID}/{name_part}_{int(_time.time())}{ext_part}"
                    upload_result = upload_image(
                        file_path=storage_path,
                        file_bytes=data["file_bytes"],
                        content_type=data["content_type"]
                    )

                    # 2. DB에 영수증 정보 저장 (image_path = 스토리지 경로)
                    receipt_result = create_receipt(
                        user_id=DEFAULT_USER_ID,
                        category_id=data["category_id"],
                        paid_at=data["paid_at"],
                        total_amount=data["total_amount"],
                        store_name=data["store_name"],
                        purchase_type=data["purchase_type"],
                        memo=data["memo"],
                        image_path=upload_result["path"],
                        raw_text=data["raw_text"],
                    )

                    # 3. 임베딩 생성 및 저장 (RAG 기반)
                    if receipt_result and data["raw_text"]:
                        from services.ai.embedder import embed_text
                        from backend.api.receipt_embeddings import save_embedding
                        embedding = embed_text(data["raw_text"])
                        if embedding:
                            save_embedding(receipt_result["id"], data["raw_text"], embedding)

                    # 4. 품목 저장 (activity_tag 자동 태깅)
                    if receipt_result and data["items"]:
                        items_payload = [
                            {
                                "name":         item.get("name", ""),
                                "quantity":     item.get("quantity", 1),
                                "price":        item.get("price"),
                                "activity_tag": _resolve_activity_tag(item.get("name", "")),
                            }
                            for item in data["items"]
                            if item.get("name")
                        ]
                        create_receipt_items(receipt_result["id"], items_payload)
                    # 3. OCR 캐시의 image_path와 이벤트 로그도 스토리지 경로로 갱신
                    ocr_cache = st.session_state['ocr_results'].get(data["file_name"])
                    if ocr_cache:
                        ocr_cache["image_path"] = upload_result["path"]
                        for event in ocr_cache.get("events", []):
                            if event.get("meta") and "image_path" in event["meta"]:
                                event["meta"]["image_path"] = upload_result["path"]

                    success_count += 1
                    st.session_state['history'].append({
                        "날짜": data["paid_at"][:10],
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
            for key in list(st.session_state.keys()):
                if key.startswith("inferred_"):
                    del st.session_state[key]
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


# --- 4. 지출 분석 페이지 ---
def page_analytics():
    import plotly.graph_objects as go
    from datetime import datetime

    st.title("📊 지출 분석 통계")

    # DB에서 영수증 데이터 조회
    try:
        receipts = get_receipts_by_user(DEFAULT_USER_ID)
    except Exception as e:
        st.error(f"데이터 조회 실패: {e}")
        return

    if not receipts:
        st.info("저장된 영수증 데이터가 없습니다. 영수증을 업로드하고 저장해 주세요.")
        return

    # --- [데이터 준비] ---
    cat_id_to_name = {v: k for k, v in st.session_state['categories'].items()}

    df = pd.DataFrame(receipts)
    df['날짜'] = pd.to_datetime(df['paid_at'])
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
        # 선택된 연월의 구매방식 비중 파이 차트
        PURCHASE_TYPE_KO = {
            "general":  "간편",
            "delivery": "배달",
            "takeout":  "포장",
            "dine_in":  "매장",
            "cooking":  "직접 요리",
        }
        df_filtered_pt = df_filtered.copy()
        df_filtered_pt['구매방식'] = df_filtered_pt['purchase_type'].map(PURCHASE_TYPE_KO).fillna("간편")
        pt_sum = df_filtered_pt.groupby('구매방식')['금액'].sum().reset_index()
        fig_pie = px.pie(
            pt_sum, values='금액', names='구매방식',
            title=f"{selected_month} 식사방식별 지출 비중", hole=0.4
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
                    from services.ai.analyzer import analyze
                    result_text = analyze(selected_month)
                    st.session_state['ai_advice'] = result_text
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
        file_name="장부.xlsx",
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


# --- 5. 실행 로직 ---
main_app()
