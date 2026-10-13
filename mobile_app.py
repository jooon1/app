import streamlit as st
import gspread
from datetime import datetime

st.set_page_config(page_title="현장 재고 스캐너", layout="centered")

@st.cache_resource
def init_connection():
    # 인터넷(Streamlit Cloud) 배포 환경에서 구글 시트에 안전하게 접속하는 방식
    gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
    sh = gc.open_by_key("1U7vg4CSRWQOKJx3Wj45aLGlEKWgjdNqTg7IyLOjQ2xY")
    return sh.worksheet("세트원장")

try:
    ws_ledger = init_connection()
except Exception as e:
    st.error("❌ 구글 시트 연결 실패. (인증 설정을 확인하세요)")
    st.stop()

# 스마트폰 카메라로 QR을 찍으면 주소창 뒤에 ?id=SET-261014-001 형태로 고유번호가 붙습니다.
query_params = st.query_params
set_id = query_params.get("id", "")

if not set_id:
    st.info("📷 박스의 QR코드를 스캔하거나 고유번호를 직접 입력하세요.")
    set_id = st.text_input("고유번호 수동 입력 (예: SET-261013-001)")

if set_id:
    cell = ws_ledger.find(set_id, in_column=1)
    
    if not cell:
        st.error(f"❌ '{set_id}' 내역을 구글 시트에서 찾을 수 없습니다.")
    else:
        row_idx = cell.row
        row_data = ws_ledger.row_values(row_idx)
        while len(row_data) < 7: 
            row_data.append("")
            
        _, set_name, detail, init_qty, cur_qty, created_at, history = row_data[:7]
        cur_qty = int(cur_qty) if str(cur_qty).isdigit() else 0

        st.title(f"📦 {set_name}")
        st.caption(f"NO: {set_id} | 발행일시: {created_at}")
        
        with st.container(border=True):
            st.markdown(f"**🥩 세트 상세 구성**\n\n{detail}")
        
        st.metric("현재 남은 수량 (세트/파렛트)", f"{cur_qty} EA")
        if history:
            st.caption(f"최근 이력: {history}")
        
        st.divider()
        
        col1, col2 = st.columns(2)
        
        # ➖ 반출(차감) 버튼
        with col1:
            out_qty = st.number_input("📤 반출(사용) 수량", min_value=1, max_value=max(1, cur_qty), value=1)
            if st.button("🚀 반출 적용", type="primary", use_container_width=True, disabled=(cur_qty <= 0)):
                new_qty = cur_qty - out_qty
                now_str = datetime.now().strftime("%m/%d %H:%M")
                new_hist = f"{now_str} (-{out_qty}개) | {history}"
                
                ws_ledger.update_cell(row_idx, 5, new_qty)
                ws_ledger.update_cell(row_idx, 7, new_hist)
                st.success(f"✅ {out_qty}개 반출 완료!")
                st.rerun()
                
        # ➕ 추가(복구) 버튼
        with col2:
            in_qty = st.number_input("📥 추가(복구) 수량", min_value=1, value=1)
            if st.button("➕ 추가 적용", use_container_width=True):
                new_qty = cur_qty + in_qty
                now_str = datetime.now().strftime("%m/%d %H:%M")
                new_hist = f"{now_str} (+{in_qty}개) | {history}"
                
                ws_ledger.update_cell(row_idx, 5, new_qty)
                ws_ledger.update_cell(row_idx, 7, new_hist)
                st.info(f"✅ {in_qty}개 추가 완료!")
                st.rerun()