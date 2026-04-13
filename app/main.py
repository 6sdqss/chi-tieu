import sys
import os

# Ép hệ thống lùi lại 1 bước ra thư mục gốc để nhận diện thư mục 'app'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
from app.config import APP_TITLE
from app.database import init_db, get_db
from app.ui import inject_css, render_auth_page, render_dashboard, render_transactions, render_quick_add

def main():
    st.set_page_config(page_title=APP_TITLE, page_icon="💎", layout="wide", initial_sidebar_state="collapsed")
    inject_css()
    init_db()

    if "logged_in" not in st.session_state:
        st.session_state.update({"logged_in": False, "uid": None, "username": "", "role": ""})

    with get_db() as db:
        if not st.session_state.logged_in:
            render_auth_page(db)
            return

        uid = st.session_state.uid
        
        with st.sidebar:
            st.markdown(f"### {APP_TITLE}")
            st.caption(f"User: {st.session_state.username}")
            menu = st.radio("Menu", ["🏠 Tổng quan", "📝 Giao dịch", "📈 Phân tích"])
            if st.button("🚪 Đăng xuất", use_container_width=True):
                st.session_state.clear()
                st.rerun()

        if menu == "🏠 Tổng quan":
            render_dashboard(db, uid)
        elif menu == "📝 Giao dịch":
            render_transactions(db, uid)
        # Thêm các module khác tương tự ở đây
        
        # Floating Button cho thiết bị di động
        render_quick_add(db, uid)

if __name__ == "__main__":
    main()
