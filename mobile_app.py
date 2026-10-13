import streamlit as st
import gspread
from datetime import datetime

st.set_page_config(page_title="현장 입출고 스캐너", layout="centered")

@st.cache_resource
def init_connection():
    gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
    sh = gc.open_by_key("1U7vg4CSRWQOKJx3Wj45aLGlEKWgjdNqTg7IyLOjQ2xY")
    return sh

try:
    sh = init_connection()
    ws_ledger = sh.worksheet("세트원장")
    ws_detail = sh.worksheet("품목상세")
except Exception as e:
    st.error("❌ 구글 시트 연결 실패. 인증키를 확인하세요.")
    st.stop()

query_params = st.query_params
set_id = query_params.get("id", "")

if not set_id:
    st.info("📷 박스의 QR코드를 스캔하세요.")
    set_id = st.text_input("또는 고유번호 수동 입력")

if set_id:
    cell = ws_ledger.find(set_id, in_column=1)
    if not cell:
        st.error(f"❌ '{set_id}' 내역을 찾을 수 없습니다.")
    else:
        row_idx = cell.row
        row_data = ws_ledger.row_values(row_idx)
        while len(row_data) < 7: row_data.append("")
            
        _, set_name, detail, init_qty, cur_qty, created_at, history = row_data[:7]
        cur_qty = int(cur_qty) if str(cur_qty).isdigit() else 0
        init_qty = int(init_qty) if str(init_qty).isdigit() else 0

        # 대제목 크게 강조
        st.markdown(f"# 📦 {set_name}")
        st.caption(f"NO: {set_id} | 발행: {created_at}")
        
        # 🔥 상세 구성 가독성 극대화 (아주 큼직한 글씨로 세로 나열)
        with st.container(border=True):
            st.markdown("### 🥩 세트 상세 구성")
            if "]" in detail:
                rep_date, parts = detail.split("]", 1)
                st.markdown(f"#### 📅 {rep_date.replace('[표기:', '대표 기한: ').strip()}")
                st.divider()
                for p in parts.split(" / "): 
                    if p.strip():
                        st.markdown(f"## 🔹 {p.strip()}")
            else:
                for p in detail.split(" / "):
                    if p.strip():
                        st.markdown(f"## 🔹 {p.strip()}")
        
        st.divider()
        
        # 🔥 남은 수량 강조 표시
        st.markdown(f"### 📊 현재 남은 수량: **{cur_qty} EA**")
        
        st.divider()
        
        # 🔥 [핵심] 1로 변하는 입력창을 아예 없애고, 남은 파렛트 수량이 고정 박힌 '원터치 대형 출고 버튼' 생성
        st.subheader("📤 반출(사용) 처리")
        if cur_qty > 0:
            st.info(f"💡 버튼을 누르면 현재 남은 수량 **{cur_qty}개**가 한 번에 일괄 출고됩니다.")
            if st.button(f"🚀 [원터치] 파렛트 전체 {cur_qty}개 출고하기", type="primary", use_container_width=True):
                now_str = datetime.now().strftime("%m/%d %H:%M")
                new_hist = f"{now_str} (출고 -{cur_qty}개) | {history}"
                ws_ledger.update_cell(row_idx, 5, 0) # 잔여수량을 0으로 만듦
                ws_ledger.update_cell(row_idx, 7, new_hist)
                st.success(f"✅ {cur_qty}개 출고가 완료되었습니다!")
                st.rerun()
        else:
            st.warning("⚠️ 이미 출고가 완료된 파렛트입니다.")

        st.divider()
        
        # 2. 추가(복구) 수량
        st.subheader("📥 추가 (반품/입고 복구)")
        col1, col2 = st.columns([2, 1])
        with col1:
            in_qty = st.number_input("추가할 수량 입력", min_value=1, value=1, key=f"in_qty_{set_id}", label_visibility="collapsed")
        with col2:
            if st.button("➕ 추가 적용", use_container_width=True):
                new_qty = cur_qty + in_qty
                now_str = datetime.now().strftime("%m/%d %H:%M")
                new_hist = f"{now_str} (입고 +{in_qty}개) | {history}"
                ws_ledger.update_cell(row_idx, 5, new_qty)
                ws_ledger.update_cell(row_idx, 7, new_hist)
                st.info(f"✅ {in_qty}개 추가 완료!")
                st.rerun()

        st.divider()
        with st.expander("🚨 (관리자) 발행 취소 및 영구 삭제"):
            st.error("잘못 발행한 주기표인가요? 장부에서 완전히 삭제합니다.")
            if st.button("🗑️ 이 파렛트 완전 삭제", type="primary", use_container_width=True):
                ws_ledger.delete_rows(row_idx)
                detail_cells = ws_detail.findall(set_id, in_column=1)
                if detail_cells:
                    rows_to_delete = sorted(list(set([c.row for c in detail_cells])), reverse=True)
                    for r in rows_to_delete:
                        ws_detail.delete_rows(r)
                st.success("✅ 장부에서 완벽히 삭제되었습니다.")
                st.stop()