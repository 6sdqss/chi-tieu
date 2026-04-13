import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
from app.config import PRIMARY_COLOR, ACCENT_COLOR, SUCCESS_COLOR, DANGER_COLOR
from app.utils import format_vnd, get_current_month
import app.services as svc

def inject_css():
    st.markdown(f"""
        <style>
            /* Ẩn các thành phần thừa của Streamlit */
            #MainMenu, footer, header {{visibility: hidden;}}
            
            /* Background tổng thể trong trẻo hơn */
            .stApp {{
                background-color: #f0fdfa;
            }}
            
            /* Chỉnh lại khung làm việc gọn gàng */
            .block-container {{ 
                max-width: 1000px; 
                padding: 2rem 1rem 6rem 1rem; 
            }}
            
            /* Banner Gradient phía trên */
            .hero-card {{
                background: linear-gradient(135deg, #0d9488 0%, #0f766e 100%);
                color: white; 
                border-radius: 20px; 
                padding: 24px;
                box-shadow: 0 10px 25px -5px rgba(13, 148, 136, 0.4); 
                margin-bottom: 24px;
            }}
            .hero-card div:first-child {{ font-size: 1.6rem; font-weight: 800; letter-spacing: -0.5px; }}
            
            /* Thẻ trắng bo góc mềm mại (Apple Style) */
            .soft-card {{
                background: #ffffff; 
                border: 1px solid #e2e8f0;
                border-radius: 16px; 
                padding: 16px; 
                margin-bottom: 12px;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
                transition: transform 0.2s ease;
            }}
            .soft-card:hover {{
                transform: translateY(-2px);
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08);
            }}
            
            /* Căn chỉnh lại các hộp hiển thị số tiền */
            div[data-testid="metric-container"] {{
                border: none; 
                border-radius: 16px; 
                padding: 16px;
                background: #ffffff; 
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            }}
            div[data-testid="stMetricValue"] {{ font-weight: 800; color: #0f172a; }}
            div[data-testid="stMetricLabel"] {{ color: #64748b; font-size: 0.95rem; }}
            
            /* Nút bấm to, bo góc lớn, dễ bấm trên mobile */
            .stButton>button {{ 
                border-radius: 14px !important; 
                min-height: 50px; 
                font-weight: 700; 
                font-size: 1.05rem;
                border: 1px solid #e2e8f0 !important;
                background: #ffffff !important;
                color: #0f172a !important;
                box-shadow: 0 2px 4px rgba(0,0,0,0.02) !important;
            }}
            .stButton>button:hover {{
                border-color: #0f766e !important;
                color: #0f766e !important;
            }}
            
            /* Nút bấm chính (Primary Button) */
            button[kind="primary"] {{
                background: #0f766e !important;
                color: #ffffff !important;
                border: none !important;
            }}
            button[kind="primary"]:hover {{
                background: #0d9488 !important;
                box-shadow: 0 4px 12px rgba(13,148,136,0.3) !important;
            }}
            
            /* Thanh menu bên trái sáng sủa, sạch sẽ */
            div[data-testid="stSidebar"] {{ 
                background: #ffffff; 
                border-right: 1px solid #e2e8f0;
            }}
            div[data-testid="stSidebar"] * {{ color: #1e293b; }}
            
            /* Input Form gọn gàng */
            .stTextInput>div>div>input, .stNumberInput>div>div>input {{
                border-radius: 10px;
            }}
            
            /* Nút "+" nổi ở góc dưới (Floating Action Button) */
            div[data-testid="stPopover"] {{
                position: fixed !important; right: 24px !important; bottom: 24px !important; z-index: 999;
            }}
            div[data-testid="stPopover"] > button {{
                width: 64px !important; height: 64px !important; border-radius: 50% !important;
                background: #14b8a6 !important;
                border: 4px solid #fff !important; 
                box-shadow: 0 10px 25px rgba(20,184,166,0.5) !important;
            }}
            div[data-testid="stPopover"] > button * {{ display: none !important; }}
            div[data-testid="stPopover"] > button::after {{
                content: "+"; color: white; font-size: 34px; font-weight: 300; line-height: 1.1;
            }}
        </style>
    """, unsafe_allow_html=True)

def page_header(title: str, subtitle: str):
    st.markdown(f"""
        <div class="hero-card">
            <div>{title}</div>
            <div style="opacity: .9; margin-top: 4px; font-size: 0.95rem;">{subtitle}</div>
        </div>
    """, unsafe_allow_html=True)

def render_auth_page(db):
    page_header("💎 FinPro Mobile", "Quản lý tài chính cá nhân toàn diện trên Cloud.")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["🔐 Đăng nhập", "📝 Đăng ký"])
        with tab1:
            with st.form("login"):
                usr = st.text_input("Tên đăng nhập")
                pwd = st.text_input("Mật khẩu", type="password")
                if st.form_submit_button("Đăng nhập", type="primary", use_container_width=True):
                    user = svc.authenticate_user(db, usr, pwd)
                    if user:
                        if user.is_approved == 0:
                            st.warning("Tài khoản đang chờ duyệt.")
                        else:
                            st.session_state.update({"logged_in": True, "uid": user.id, "username": user.username, "role": user.role})
                            st.rerun()
                    else:
                        st.error("Sai thông tin đăng nhập.")
        with tab2:
            with st.form("register"):
                new_usr = st.text_input("Tên đăng nhập mới")
                new_pwd = st.text_input("Mật khẩu", type="password")
                if st.form_submit_button("Tạo tài khoản", use_container_width=True):
                    if len(new_usr) < 3 or len(new_pwd) < 6:
                        st.warning("Username >= 3 và Password >= 6 ký tự.")
                    else:
                        ok, msg = svc.register_user(db, new_usr, new_pwd)
                        st.success(msg) if ok else st.error(msg)

def render_dashboard(db, uid: int):
    page_header("🏠 Tổng quan", "Theo dõi dòng tiền và tài sản hiện tại.")
    
    wallets = svc.get_wallets(db, uid)
    total_assets = sum(w.balance for w in wallets)
    
    current_month = get_current_month()
    budget = svc.get_budget(db, uid, current_month)
    df = svc.get_transactions_df(db, uid)
    
    month_df = df[df["month"] == current_month] if not df.empty else pd.DataFrame()
    income = month_df[month_df["type"] == "income"]["amount"].sum() if not month_df.empty else 0.0
    expense = month_df[month_df["type"] == "expense"]["amount"].sum() if not month_df.empty else 0.0
    
    c1, c2 = st.columns(2)
    c1.metric("Tổng tài sản", format_vnd(total_assets))
    c2.metric("Chênh lệch tháng", format_vnd(income - expense))
    
    c3, c4 = st.columns(2)
    c3.metric("Thu nhập tháng", format_vnd(income))
    c4.metric("Chi tiêu tháng", format_vnd(expense))
    
    if budget > 0:
        ratio = min(expense / budget, 1.0)
        st.progress(ratio)
        if expense > budget:
            st.error(f"⚠️ Vượt ngân sách: {format_vnd(expense - budget)}")
        else:
            st.success(f"Ngân sách còn lại: {format_vnd(budget - expense)}")

    st.markdown("### 💼 Ví của bạn")
    if not wallets:
        st.info("Chưa có ví.")
    else:
        for w in wallets:
            icon = "🏦" if w.type == "bank" else "💵"
            st.markdown(f"""
                <div class="soft-card" style="display:flex; justify-content:space-between;">
                    <div><strong>{icon} {w.name}</strong></div>
                    <div style="color:{PRIMARY_COLOR}; font-weight:800;">{format_vnd(w.balance)}</div>
                </div>
            """, unsafe_allow_html=True)

def render_transactions(db, uid: int):
    page_header("📝 Giao dịch", "Quản lý dòng tiền của bạn.")
    wallets = svc.get_wallets(db, uid)
    if not wallets:
        st.error("Cần tạo ví trước.")
        return
        
    w_map = {w.name: w.id for w in wallets}
    
    t1, t2, t3 = st.tabs(["💸 Chi tiêu", "💰 Thu nhập", "🔄 Chuyển khoản"])
    
    with t1:
        with st.form("add_exp"):
            cats = svc.get_categories(db, uid, "expense")
            c_map = {f"{c.icon} {c.name}": c.id for c in cats}
            
            c1, c2 = st.columns(2)
            amt = c1.number_input("Số tiền", min_value=0.0, step=50000.0)
            dt = c2.date_input("Ngày", value=date.today())
            
            c3, c4 = st.columns(2)
            cat = c3.selectbox("Danh mục", list(c_map.keys())) if c_map else None
            wallet = c4.selectbox("Từ ví", list(w_map.keys()))
            
            note = st.text_input("Ghi chú")
            if st.form_submit_button("Lưu khoản chi", type="primary", use_container_width=True):
                if amt > 0 and cat:
                    svc.create_transaction(db, uid, w_map[wallet], c_map[cat], "expense", amt, dt, note)
                    st.success("Đã lưu.")
                    st.rerun()

    with t2:
        with st.form("add_inc"):
            cats = svc.get_categories(db, uid, "income")
            c_map = {f"{c.icon} {c.name}": c.id for c in cats}
            
            c1, c2 = st.columns(2)
            amt = c1.number_input("Số tiền thu", min_value=0.0, step=50000.0)
            dt = c2.date_input("Ngày thu", value=date.today())
            
            c3, c4 = st.columns(2)
            cat = c3.selectbox("Nguồn thu", list(c_map.keys())) if c_map else None
            wallet = c4.selectbox("Vào ví", list(w_map.keys()))
            
            note = st.text_input("Ghi chú thu")
            if st.form_submit_button("Lưu thu nhập", type="primary", use_container_width=True):
                if amt > 0 and cat:
                    svc.create_transaction(db, uid, w_map[wallet], c_map[cat], "income", amt, dt, note)
                    st.success("Đã lưu.")
                    st.rerun()
                    
    with t3:
        with st.form("add_trans"):
            c1, c2 = st.columns(2)
            amt = c1.number_input("Số tiền chuyển", min_value=0.0, step=50000.0)
            dt = c2.date_input("Ngày chuyển", value=date.today())
            
            c3, c4 = st.columns(2)
            from_w = c3.selectbox("Từ ví nguồn", list(w_map.keys()))
            to_w = c4.selectbox("Tới ví đích", list(w_map.keys()))
            
            note = st.text_input("Nội dung")
            if st.form_submit_button("Chuyển tiền", type="primary", use_container_width=True):
                if amt > 0 and from_w != to_w:
                    svc.create_transaction(db, uid, w_map[from_w], None, "transfer", amt, dt, note, w_map[to_w])
                    st.success("Đã chuyển.")
                    st.rerun()

    st.markdown("### 📒 Lịch sử giao dịch")
    df = svc.get_transactions_df(db, uid)
    if not df.empty:
        df["Hiển thị"] = df.apply(lambda r: f"-{format_vnd(r['amount'])}" if r['type']=='expense' else f"+{format_vnd(r['amount'])}", axis=1)
        st.dataframe(df[["date", "wallet_name", "category_name", "Hiển thị", "note"]], use_container_width=True, hide_index=True)

def render_quick_add(db, uid: int):
    with st.popover("Thêm nhanh"):
        st.markdown("**⚡ Ghi chi tiêu nhanh**")
        wallets = svc.get_wallets(db, uid)
        cats = svc.get_categories(db, uid, "expense")
        if not wallets or not cats:
            st.warning("Thiếu ví hoặc danh mục.")
            return
            
        with st.form("quick_add", clear_on_submit=True):
            amt = st.number_input("Số tiền", min_value=0.0, step=10000.0)
            c_dict = {f"{c.icon} {c.name}": c.id for c in cats}
            cat = st.selectbox("Mục", list(c_dict.keys()))
            if st.form_submit_button("Lưu ngay", type="primary", use_container_width=True):
                if amt > 0:
                    svc.create_transaction(db, uid, wallets[0].id, c_dict[cat], "expense", amt, date.today(), "")
                    st.rerun()
