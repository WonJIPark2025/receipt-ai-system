"""
receipt_front.py - 데스크톱 전용 UI

담당: 프론트엔드
설명: 데스크톱/노트북에 최적화된 영수증 AI 장부 UI
    - app.py에서 데스크톱 감지 시 이 파일로 분기
    - wide 레이아웃, 사이드바 메뉴 구성
포함 기능:
    - Gemini 영수증 분석 + DB/Storage 저장
    - 지출 분석 (최근 12개월, 버블 차트 3종)
    - AI 챗봇 어시스턴트 (Gemini)
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
from services.ai.gemini import extract_receipt_data, resolve_activity_tag
from services.ai.validator import validate_receipt
from utils.config import DEFAULT_USER_ID, DEMO_MODE


# --- 1. 페이지 설정 및 세션 상태 초기화 ---
st.set_page_config(page_title="영수증 AI 장부", layout="wide")

if 'history' not in st.session_state:
    st.session_state['history'] = []
if 'chat_messages' not in st.session_state:
    st.session_state['chat_messages'] = []
if 'chat_month' not in st.session_state:
    st.session_state['chat_month'] = None


# --- 2. 메인 앱 화면 (main_app) - 사이드바 페이지 전환 허브 ---
def main_app():
    # --- [사이드바 로고] ---
    st.sidebar.image("data/receipt-ai-system_logo.png", use_column_width=True)

    # --- [사이드바 페이지 선택] ---
    st.sidebar.divider()
    page = st.sidebar.radio(
        "메뉴",
        ["🍘🥤🧋영수증을 모아보세요", "📒📝🗂️ 식비 지출 분석하기"],
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
    if page == "🍘🥤🧋영수증을 모아보세요":
        page_upload()
    else:
        page_analytics()


# --- 3. 영수증 업로드 페이지 ---
def page_upload():
    st.title("🧾 영수증 AI 장부 정리")
    if DEMO_MODE:
        st.info("👀 데모 모드 — 읽기 전용입니다. 업로드 및 저장 기능은 비활성화되어 있습니다.")

    import io as _io
    from datetime import datetime as _dt

    # --- [세션 초기화] ---
    if 'uploaded_file_data' not in st.session_state:
        st.session_state['uploaded_file_data'] = []  # [{name, data, type}]
    if 'ocr_results' not in st.session_state:
        st.session_state['ocr_results'] = {}  # {name: {status, ocr_data, error}}

    file_data_list = st.session_state['uploaded_file_data']

    # --- [자동 파싱 (OCR만, DB 저장은 저장 버튼에서)] ---
    for fd in file_data_list:
        if fd['name'] in st.session_state['ocr_results']:
            continue
        with st.spinner(f"🔍 {fd['name']} 분석 중..."):
            try:
                suffix = Path(fd['name']).suffix
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                tmp.write(fd['data'])
                tmp.close()
                ocr_data   = extract_receipt_data(tmp.name)
                validation = validate_receipt(ocr_data)
                os.unlink(tmp.name)
                ocr_data.update(validation)

                st.session_state['ocr_results'][fd['name']] = {
                    "status": "success", "ocr_data": ocr_data,
                }

            except Exception as e:
                st.session_state['ocr_results'][fd['name']] = {
                    "status": "error", "error": str(e)
                }

    # --- [레이아웃] ---
    display_list = file_data_list if file_data_list else [None]
    st.subheader("⬇️ 영수증에서 데이터 추출하기" + (f" (총 {len(file_data_list)}건)" if file_data_list else ""))

    for idx, fd in enumerate(display_list):
        if idx > 0:
            st.divider()

        col_img, col_result = st.columns([1, 2])

        with col_img:
            with st.container(height=420, border=True):
                if fd is None:
                    st.markdown("<div style='height:120px'></div>", unsafe_allow_html=True)
                    if DEMO_MODE:
                        st.markdown("<div style='text-align:center; color:#bbb; font-size:13px; padding-top:20px;'>📷 데모 모드에서는<br>업로드가 비활성화됩니다</div>", unsafe_allow_html=True)
                    else:
                        raw_files = st.file_uploader(
                            "영수증 이미지 업로드",
                            type=['jpg', 'jpeg', 'png'],
                            accept_multiple_files=True,
                            label_visibility="collapsed",
                            key="main_uploader",
                        )
                        if raw_files:
                            st.session_state['uploaded_file_data'] = [
                                {'name': f.name, 'data': f.getvalue(), 'type': f.type}
                                for f in raw_files
                            ]
                            st.rerun()
                else:
                    st.image(_io.BytesIO(fd['data']), use_column_width=True)
                    if idx == 0 and st.button("🔄 새 영수증", use_container_width=True):
                        st.session_state['uploaded_file_data'] = []
                        st.session_state['ocr_results'] = {}
                        st.rerun()

        with col_result:
            # fd가 없으면 빈 상태로 항상 표시
            ocr_data = {}
            result   = {}
            if fd is not None:
                result   = st.session_state['ocr_results'].get(fd['name'], {})
                ocr_data = result.get('ocr_data', {})

            if result.get('status') == 'error':
                st.error(f"오류: {result.get('error', '')}")
            else:
                # 항상 표시되는 추출 결과 영역
                r1a, r1b = st.columns(2)
                r1a.metric("상호명", ocr_data.get("store_name", "—"))
                total_val = ocr_data.get("total", 0)
                r1b.metric("금액", f"{total_val:,}원" if total_val else "—")

                r2a, r2b = st.columns(2)
                date_str = ocr_data.get("date", "")
                try:
                    date_display = _dt.fromisoformat(date_str).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    date_display = "—"
                r2a.metric("날짜", date_display)
                r2b.metric("카테고리", ocr_data.get("category", "—"))

                items = ocr_data.get("items", [])
                st.caption(f"품목 ({len(items)}건)" if items else "품목")
                st.dataframe(
                    pd.DataFrame(
                        [{"품목명": i.get("name",""), "수량": i.get("quantity",1), "단가": i.get("price",0)} for i in items]
                        if items else [{"품목명": "—", "수량": "—", "단가": "—"}]
                    ),
                    use_container_width=True, hide_index=True
                )

    # --- [메모 + 저장 버튼 — 컬럼 아래 전체 너비] ---
    # for 루프 마지막 fd/result/ocr_data 값 재사용
    st.divider()
    memo_key = f"memo_input_{fd['name']}" if fd else "memo_input_empty"
    memo_val = st.text_area("메모 (일기)", key=memo_key, disabled=(fd is None or DEMO_MODE), height=108)

    if st.button("💾 저장", key="save_btn", use_container_width=True,
                 type="primary", disabled=(fd is None or result.get('status') != 'success' or DEMO_MODE)):
        with st.spinner("저장 중..."):
            try:
                date_str2 = ocr_data.get("date", "")
                try:
                    paid_at   = _dt.fromisoformat(date_str2).strftime("%Y-%m-%dT%H:%M:%S+09:00")
                    paid_hour = _dt.fromisoformat(date_str2).hour
                except Exception:
                    paid_at   = _dt.now().strftime("%Y-%m-%dT%H:%M:%S+09:00")
                    paid_hour = _dt.now().hour

                cat_id = st.session_state['categories'].get(ocr_data.get("category", "기타"))
                pt     = ocr_data.get("purchase_type", "takeout")
                if pt not in ["delivery", "takeout", "dine_in", "cooking"]:
                    pt = "takeout"

                name_part, ext_part = os.path.splitext(fd['name'])
                storage_path  = f"user_{DEFAULT_USER_ID}/{name_part}_{int(time.time())}{ext_part}"
                content_type  = "image/png" if ext_part.lower() == ".png" else "image/jpeg"
                upload_result = upload_image(
                    file_path=storage_path, file_bytes=fd['data'], content_type=content_type
                )

                receipt = create_receipt(
                    user_id=DEFAULT_USER_ID,
                    category_id=cat_id,
                    paid_at=paid_at,
                    total_amount=ocr_data.get("total", 0),
                    store_name=ocr_data.get("store_name", ""),
                    purchase_type=pt,
                    memo=memo_val or None,
                    image_path=upload_result["path"],
                    raw_text=ocr_data.get("raw_text", ""),
                )

                if receipt and ocr_data.get("raw_text"):
                    from services.ai.embedder import embed_text
                    from backend.api.receipt_embeddings import save_embedding
                    embedding = embed_text(ocr_data["raw_text"])
                    if embedding:
                        save_embedding(receipt["id"], ocr_data["raw_text"], embedding)

                save_items = ocr_data.get("items", [])
                if receipt and save_items:
                    items_payload = [
                        {
                            "name":         it.get("name", ""),
                            "quantity":     it.get("quantity", 1),
                            "price":        it.get("price"),
                            "activity_tag": resolve_activity_tag(it.get("name", ""), paid_hour),
                        }
                        for it in save_items if it.get("name")
                    ]
                    create_receipt_items(receipt["id"], items_payload)

                st.session_state['uploaded_file_data'] = []
                st.session_state['ocr_results'] = {}
                st.session_state.pop('analytics_receipts', None)
                st.success("✅ 저장 완료!")
                time.sleep(0.8)
                st.rerun()

            except Exception as e:
                st.error(f"저장 실패: {e}")

    # --- [3. 전체 영수증 내역] ---
    st.divider()
    st.subheader("📅 전체 영수증 내역")

    if st.button("🔄 새로고침", key="upload_refresh"):
        st.session_state.pop('analytics_receipts', None)

    if 'analytics_receipts' not in st.session_state:
        try:
            st.session_state['analytics_receipts'] = get_receipts_by_user(DEFAULT_USER_ID)
        except Exception as e:
            st.error(f"데이터 조회 실패: {e}")
            return

    receipts_all = st.session_state['analytics_receipts']
    if not receipts_all:
        st.write("아직 저장된 내역이 없습니다. 영수증을 업로드해 보세요!")
    else:
        from datetime import datetime as _dt
        cat_id_to_name = {v: k for k, v in st.session_state['categories'].items()}
        df = pd.DataFrame(receipts_all)
        df['날짜'] = pd.to_datetime(df['paid_at']).dt.tz_convert('Asia/Seoul').dt.tz_localize(None)
        df['연월'] = df['날짜'].dt.strftime('%Y-%m')
        df['금액'] = df['total_amount']
        df['상호명'] = df['store_name']
        df['카테고리'] = df['category_id'].map(cat_id_to_name).fillna("기타")
        display_df = df.sort_values('날짜', ascending=False).reset_index(drop=True)

        # --- [장부 다운로드] ---
        import io
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
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
            cat_rows = pd.DataFrame({'날짜': cat_summary['카테고리'].values, '상호명': '', '금액': cat_summary['합계'].values, '카테고리': ''})
            spacer = pd.DataFrame([{'날짜': '', '상호명': '', '금액': '', '카테고리': ''}])
            header_row = pd.DataFrame([{'날짜': '[전체 내역]', '상호명': '', '금액': '', '카테고리': ''}])
            full_sheet = pd.concat([summary_rows, cat_rows, spacer, header_row, all_df], ignore_index=True)
            full_sheet.to_excel(writer, sheet_name='전체 내역', index=False)
            for month in sorted(display_df['연월'].unique().tolist()):
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
                m_cat_rows = pd.DataFrame({'날짜': m_cat['카테고리'].values, '상호명': '', '금액': m_cat['합계'].values, '카테고리': ''})
                month_sheet = pd.concat([m_summary, m_cat_rows, pd.DataFrame([{'날짜': '', '상호명': '', '금액': '', '카테고리': ''}]), pd.DataFrame([{'날짜': '[상세 내역]', '상호명': '', '금액': '', '카테고리': ''}]), month_data], ignore_index=True)
                month_sheet.to_excel(writer, sheet_name=month, index=False)

        st.download_button("📥 내역 다운로드", data=excel_buffer.getvalue(), file_name="장부.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # --- [페이지네이션] ---
        PAGE_SIZE = 10
        total_rows = len(display_df)
        total_pages = max(1, (total_rows + PAGE_SIZE - 1) // PAGE_SIZE)
        if 'receipt_page' not in st.session_state:
            st.session_state['receipt_page'] = 1
        current_page = st.session_state['receipt_page']
        start_idx = (current_page - 1) * PAGE_SIZE
        page_df = display_df.iloc[start_idx:min(start_idx + PAGE_SIZE, total_rows)]

        select_all = st.checkbox("전체 선택", key="select_all_receipts")
        for _, row in page_df.iterrows():
            date_str = row['날짜'].strftime('%Y-%m-%d')
            receipt_id = row.get('id')
            chk_col, exp_col = st.columns([0.3, 9.7])
            with chk_col:
                st.checkbox("sel", key=f"chk_{receipt_id}", value=select_all, label_visibility="collapsed")
            with exp_col:
                with st.expander(f"{date_str}  |  {row['상호명']}  |  {row['금액']:,.0f}원  |  {row['카테고리']}"):
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

        # --- [선택 삭제] ---
        selected_ids = [row.get('id') for _, row in page_df.iterrows() if st.session_state.get(f"chk_{row.get('id')}", False)]
        selected_image_paths = [row.get('image_path') for _, row in page_df.iterrows() if st.session_state.get(f"chk_{row.get('id')}", False) and row.get('image_path') and str(row.get('image_path')) != 'None']

        st.write("")
        with st.columns([3, 7])[0]:
            if st.button(f"🗑️ 선택 영수증 삭제 ({len(selected_ids)}건)", disabled=(len(selected_ids) == 0 or DEMO_MODE), use_container_width=True, type="primary"):
                st.session_state['confirm_delete'] = True
                st.session_state['delete_ids'] = selected_ids
                st.session_state['delete_image_paths'] = selected_image_paths

        if st.session_state.get('confirm_delete'):
            st.warning(f"⚠️ 정말 {len(st.session_state.get('delete_ids', []))}건의 영수증을 삭제하시겠습니까?")
            conf_col1, conf_col2, _ = st.columns([1, 1, 3])
            with conf_col1:
                if st.button("삭제 확인", type="primary", key="confirm_yes"):
                    for rid in st.session_state.get('delete_ids', []):
                        try:
                            delete_receipt(rid)
                        except Exception as e:
                            st.error(f"DB 삭제 실패 (id={rid}): {e}")
                    for img_path in st.session_state.get('delete_image_paths', []):
                        try:
                            delete_image(img_path)
                        except Exception:
                            pass
                    st.session_state.pop('analytics_receipts', None)
                    st.session_state['confirm_delete'] = False
                    st.session_state.pop('delete_ids', None)
                    st.session_state.pop('delete_image_paths', None)
                    time.sleep(1)
                    st.rerun()
            with conf_col2:
                if st.button("취소", key="confirm_no"):
                    st.session_state['confirm_delete'] = False
                    st.session_state.pop('delete_ids', None)
                    st.session_state.pop('delete_image_paths', None)
                    st.rerun()

        if total_pages > 1:
            st.write("")
            nav_cols = st.columns([1, 2, 1])
            with nav_cols[0]:
                if st.button("◀ 이전", disabled=(current_page <= 1), key="prev_page"):
                    st.session_state['receipt_page'] = current_page - 1
                    st.rerun()
            with nav_cols[1]:
                st.markdown(f"<div style='text-align:center'>{current_page} / {total_pages} 페이지</div>", unsafe_allow_html=True)
            with nav_cols[2]:
                if st.button("다음 ▶", disabled=(current_page >= total_pages), key="next_page"):
                    st.session_state['receipt_page'] = current_page + 1
                    st.rerun()


# --- 4. 지출 분석 페이지 ---
def page_analytics():
    import re
    import plotly.graph_objects as go
    from datetime import datetime
    from collections import Counter


    from backend.api.receipt_items import get_items_by_activity_tag

    st.title("😉 AI 지출 분석")

    # --- [DB 조회 — 세션 캐시 활용] ---
    if st.button("🔄 데이터 새로고침", key="analytics_refresh"):
        st.session_state.pop('analytics_receipts', None)
        st.session_state.pop('analytics_tag_counts', None)

    if 'analytics_receipts' not in st.session_state:
        try:
            st.session_state['analytics_receipts'] = get_receipts_by_user(DEFAULT_USER_ID)
        except Exception as e:
            st.error(f"데이터 조회 실패: {e}")
            return

    receipts = st.session_state['analytics_receipts']

    if not receipts:
        st.info("저장된 영수증 데이터가 없습니다. 영수증을 업로드하고 저장해 주세요.")
        return

    # --- [데이터 준비] ---
    cat_id_to_name = {v: k for k, v in st.session_state['categories'].items()}
    now = datetime.now()

    df = pd.DataFrame(receipts)
    df['날짜'] = pd.to_datetime(df['paid_at']).dt.tz_convert('Asia/Seoul').dt.tz_localize(None)
    df['연월'] = df['날짜'].dt.strftime('%Y-%m')
    df['금액'] = df['total_amount']
    df['상호명'] = df['store_name']
    df['카테고리'] = df['category_id'].map(cat_id_to_name).fillna("기타")

    # 최근 12개월 필터 (정수 연산으로 월 경계 정확하게 계산)
    cutoff_month = now.month - 11
    cutoff_year = now.year
    if cutoff_month <= 0:
        cutoff_month += 12
        cutoff_year -= 1
    cutoff_dt = datetime(cutoff_year, cutoff_month, 1)
    df_12 = df[df['날짜'] >= pd.Timestamp(cutoff_dt)].copy()
    if df_12.empty:
        df_12 = df.copy()

    total_12 = df_12['금액'].sum()
    count_12 = len(df_12)
    avg_12 = df_12['금액'].mean() if count_12 > 0 else 0

    # --- [Chart 1: 월별 지출 버블 (최근 12개월)] ---
    month_list = []
    for i in range(11, -1, -1):
        m = now.month - i
        y = now.year
        if m <= 0:
            m += 12
            y -= 1
        month_list.append(f"{y}-{m:02d}")

    monthly_map = df_12.groupby('연월')['금액'].sum().to_dict()
    chart1_amounts = [float(monthly_map.get(m, 0)) for m in month_list]
    chart1_labels  = [m[5:].lstrip('0') + '월' for m in month_list]
    nonzero_amts = [a for a in chart1_amounts if a > 0]
    max_amt = max(nonzero_amts) if nonzero_amts else 1
    min_amt = min(nonzero_amts) * 0.5 if nonzero_amts else 0  # 실제 최솟값의 절반 → 색상 범위 확대

    fig1 = go.Figure(go.Scatter(
        x=list(range(len(month_list))),
        y=[0] * len(month_list),
        mode='markers+text',
        marker=dict(
            size=100,
            color=chart1_amounts,
            colorscale=[[0, "#F7DBDE"], [0.5, '#FF6B6B'], [1, "#9B1919"]],
            cmin=min_amt,
            cmax=max_amt,
            line=dict(width=0),
        ),
        text=chart1_labels,
        textposition='middle center',
        textfont=dict(size=10, color='white'),
        hovertext=[
            f"{lbl}: {int(amt):,}원" if amt > 0 else f"{lbl}: 데이터 없음"
            for lbl, amt in zip(chart1_labels, chart1_amounts)
        ],
        hovertemplate='%{hovertext}<extra></extra>',
    ))
    fig1.update_layout(
        title='월별 지출 현황',
        height=200,
        xaxis=dict(
            showgrid=False, zeroline=False,
            tickmode='array',
            tickvals=list(range(len(month_list))),
            ticktext=chart1_labels,
            tickfont=dict(size=20),
            range=[-0.5, len(month_list) - 0.5],
        ),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-1, 1]),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=40, b=30, l=0, r=0),
    )
    st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})

    # --- [Chart 2 & 3 나란히] ---
    # 12개월 cutoff (Chart 2 날짜 필터용)
    cutoff_month_c2 = now.month - 11
    cutoff_year_c2  = now.year
    if cutoff_month_c2 <= 0:
        cutoff_month_c2 += 12
        cutoff_year_c2  -= 1
    cutoff_start = f"{cutoff_year_c2}-{cutoff_month_c2:02d}-01T00:00:00+09:00"

    c_left, c_right = st.columns(2)

    # --- [Chart 2: 활동 태그 버블] ---
    with c_left:
        ACTIVITY_TAG_INFO = {
            'caffeine':   ('☕ 카페인', '#6F4E37'),
            'alcohol':    ('🍺 음주',   '#E07B39'),
            'late_snack': ('🌆 야식',   '#4B3F72'),
        }
        if 'analytics_tag_counts' not in st.session_state:
            tag_counts: Counter = Counter()
            for tag in ACTIVITY_TAG_INFO:
                try:
                    items = get_items_by_activity_tag(tag, DEFAULT_USER_ID)
                    count = sum(
                        1 for it in items
                        if (it.get('receipts') or {}).get('paid_at', '') >= cutoff_start
                    )
                    if count > 0:
                        tag_counts[tag] = count
                except Exception:
                    pass
            st.session_state['analytics_tag_counts'] = dict(tag_counts)

        tag_counts = Counter(st.session_state['analytics_tag_counts'])

        if tag_counts:
            tags_order = ['caffeine', 'alcohol', 'late_snack']
            present = [t for t in tags_order if t in tag_counts]
            labels  = [ACTIVITY_TAG_INFO[t][0] for t in present]
            colors  = [ACTIVITY_TAG_INFO[t][1] for t in present]
            counts  = [tag_counts[t] for t in present]
            max_c   = max(counts) or 1

            fig2 = go.Figure(go.Scatter(
                x=list(range(len(present))),
                y=[0] * len(present),
                mode='markers+text',
                marker=dict(
                    size=[max(50, min(110, c / max_c * 60 + 50)) for c in counts],
                    color=colors,
                    line=dict(width=1, color='#ccc'),
                ),
                text=[f"{lbl}<br><b>{c}회</b>" for lbl, c in zip(labels, counts)],
                textposition='middle center',
                textfont=dict(size=13, color='white'),
                hovertemplate='%{text}<extra></extra>',
            ))
            fig2.update_layout(
                title='활동 태그 분포',
                height=300,
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-1, 1]),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(t=40, b=0, l=0, r=0),
            )
            st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("활동 태그 데이터가 없습니다.")

    # --- [Chart 3: 메모 키워드 버블] ---
    with c_right:
        STOPWORDS = {
            '', '함', '이', '가', '을', '를', '은', '는', '에', '도', '와', '과',
            '으로', '로', '에서', '의', '후', '시작', '중', '안', '집', '거',
        }
        memo_texts = [r.get('memo') or '' for r in receipts if r.get('paid_at', '') >= cutoff_start]
        word_counts: Counter = Counter()
        for memo in memo_texts:
            for w in re.split(r'[\s,./!?]+', memo.strip()):
                w = w.strip()
                if len(w) >= 2 and w not in STOPWORDS:
                    word_counts[w] += 1

        top10 = word_counts.most_common(10)

        if top10:
            COLORS_10 = [
                '#FF6B6B', '#FF8E53', '#FFC857', '#6BCB77', '#4D96FF',
                '#C77DFF', '#FF6FD8', '#00BBF9', '#A8E063', '#FF9A3C',
            ]
            kw_words  = [k for k, _ in top10]
            kw_counts = [c for _, c in top10]
            max_kw = max(kw_counts) or 1

            fig3 = go.Figure()
            for idx, (word, count) in enumerate(zip(kw_words, kw_counts)):
                fig3.add_trace(go.Scatter(
                    x=[idx],
                    y=[0],
                    mode='markers+text',
                    marker=dict(
                        size=max(30, min(80, count / max_kw * 50 + 30)),
                        color=COLORS_10[idx % 10],
                        line=dict(width=1, color='#ccc'),
                    ),
                    text=[f"{word}<br><b>{count}회</b>"],
                    textposition='middle center',
                    textfont=dict(size=11, color='white'),
                    hovertemplate=f"{word}: {count}회<extra></extra>",
                    showlegend=False,
                ))
            fig3.update_layout(
                title='메모 키워드 Top 10',
                height=300,
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-1, 1]),
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                margin=dict(t=40, b=0, l=0, r=0),
            )
            st.plotly_chart(fig3, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("메모 키워드 데이터가 없습니다.")

    if 'chat_messages' not in st.session_state:
        st.session_state['chat_messages'] = []

    # --- [AI 챗봇] ---
    st.divider()
    st.subheader("🆗 AI 지출 분석 챗봇")

    # 대화창 (고정 높이 스크롤)
    chat_container = st.container(height=200)
    with chat_container:
        if not st.session_state['chat_messages']:
            st.caption("식비 지출에 대해 자유롭게 질문해 보세요!")
        for msg in st.session_state['chat_messages']:
            with st.chat_message(msg['role']):
                st.markdown(msg['content'])

    # 입력란 + 전송 버튼
    input_col, btn_col = st.columns([8, 1])
    with input_col:
        user_input = st.text_input(
            "질문 입력",
            key="chat_input_text",
            placeholder="배달 비용이 얼마야?  |  이번 달 가장 많이 간 곳은?",
            label_visibility="collapsed",
        )
    with btn_col:
        send = st.button("전송", use_container_width=True)

    if (send or user_input) and user_input and user_input != st.session_state.get('_last_chat_input'):
        st.session_state['_last_chat_input'] = user_input
        st.session_state['chat_messages'].append({"role": "user", "content": user_input})
        with st.spinner("답변 생성 중..."):
            try:
                from services.ai.chat import chat
                reply = chat(st.session_state['chat_messages'])
            except Exception as e:
                reply = f"오류: {e}"
        st.session_state['chat_messages'].append({"role": "assistant", "content": reply})
        st.rerun()

    # --- [요약 지표] ---
    st.divider()
    st.subheader("최근 12개월 요약")
    m1, m2, m3 = st.columns(3)
    m1.metric("총 지출", f"{total_12:,.0f}원")
    m2.metric("영수증 수", f"{count_12}건")
    m3.metric("건당 평균", f"{avg_12:,.0f}원")


# --- 5. 실행 로직 ---
main_app()
