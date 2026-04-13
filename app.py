import os
import sqlite3
import hashlib
from io import BytesIO
from datetime import datetime, date
import pandas as pd
import plotly.express as px
import streamlit as st

# ==============================================================================
# 1. CẤU HÌNH TRANG & CÁC HẰNG SỐ MẶC ĐỊNH
# ==============================================================================
st.set_page_config(page_title="FinPro Ultimate", page_icon="💎", layout="wide", initial_sidebar_state="collapsed")

DB_PATH = "finpro_ultimate_offline.db"

DEFAULT_CATEGORIES = [
    ("Ăn uống", "expense", "🍜"), ("Tiền nhà / Điện nước", "expense", "🏠"),
    ("Di chuyển / Xăng xe", "expense", "⛽"), ("Mua sắm / Quần áo", "expense", "🛍️"),
    ("Tã & Sữa / Con cái", "expense", "🍼"), ("Sức khỏe / Y tế", "expense", "💊"),
    ("Giải trí / Du lịch", "expense", "🎬"), ("Giáo dục / Học tập", "expense", "📚"),
    ("Bảo hiểm / Trả nợ", "expense", "🛡️"), ("Khác (Chi tiêu)", "expense", "📦"),
    ("Lương", "income", "💰"), ("Thưởng / Lợi nhuận", "income", "🎁"),
    ("Đầu tư sinh lời", "income", "📈"), ("Thu nhập thụ động", "income", "🛌"),
    ("Khác (Thu nhập)", "income", "📥"),
]

# ==============================================================================
# 2. KHỞI TẠO SESSION STATE (BIẾN TẠM)
# ==============================================================================
if 'logged_in' not in st.session_state:
    st.session_state.update({
        "logged_in": False, "uid": None, "uname": "", "role": "",
        "draft_expense": {"amount": 0.0, "category": "Ăn uống", "note": ""}
    })

# ==============================================================================
# 3. CSS ĐỊNH DẠNG GIAO DIỆN (SANG TRỌNG, MOBILE-FIRST, NÚT NỔI)
# ==============================================================================
def inject_global_css():
    st.markdown("""
    <style>
    /* Ẩn các thành phần thừa */
    #MainMenu, header, footer {visibility: hidden;}
    .stApp { background-color: #f4f7f6; font-family: 'Inter', sans-serif; }
    
    /* Canh chỉnh khung chính */
    .block-container { max-width: 1100px; padding-top: 1.5rem !important; padding-bottom: 7rem !important; }
    
    /* Thiết kế thẻ Thống kê (Metric) */
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #e2e8f0; border-radius: 16px; padding: 15px 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02); transition: transform 0.2s ease;
    }
    div[data-testid="metric-container"]:hover { transform: translateY(-3px); box-shadow: 0 6px 12px rgba(0,0,0,0.08); }
    
    /* Làm đẹp các nút bấm */
    .stButton > button { border-radius: 12px !important; font-weight: 600 !important; transition: all 0.2s ease !important; }
    .stButton > button:active { transform: scale(0.97) !important; }
    
    /* --- NÚT NỔI GHI NHANH Ở GÓC DƯỚI BÊN PHẢI --- */
    div[data-testid="stPopover"] {
        position: fixed !important; bottom: 30px !important; right: 30px !important; z-index: 99999 !important;
    }
    div[data-testid="stPopover"] > button {
        width: 65px !important; height: 65px !important; border-radius: 50% !important;
        background: linear-gradient(135deg, #10b981, #059669) !important; border: 4px solid white !important; 
        box-shadow: 0 8px 25px rgba(16, 185, 129, 0.5) !important;
        display: flex !important; align-items: center !important; justify-content: center !important; padding: 0 !important;
    }
    div[data-testid="stPopover"] > button:hover { transform: scale(1.1) rotate(90deg) !important; }
    div[data-testid="stPopover"] > button * { display: none !important; }
    div[data-testid="stPopover"] > button::after { content: "➕" !important; font-size: 32px !important; color: white !important; }
    
    /* Responsive cho Điện thoại */
    @media (max-width: 768px) {
        .block-container { padding-left: 1rem !important; padding-right: 1rem !important; }
        div[data-testid="stPopover"] { right: 15px !important; bottom: 20px !important; }
        div[data-testid="stPopover"] > button { width: 55px !important; height: 55px !important; }
        div[data-testid="stPopover"] > button::after { font-size: 26px !important; }
    }
    </style>
    """, unsafe_allow_html=True)

# ==============================================================================
# 4. DATABASE & LÕI XỬ LÝ (CORE LOGIC)
# ==============================================================================
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def hash_pw(pw: str): return hashlib.sha256(pw.encode()).hexdigest()

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'user', is_approved INTEGER NOT NULL DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, name TEXT NOT NULL, type TEXT NOT NULL, icon TEXT, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)""")
    c.execute("""CREATE TABLE IF NOT EXISTS wallets (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, name TEXT NOT NULL, balance REAL NOT NULL DEFAULT 0.0, type TEXT DEFAULT 'bank', is_default INTEGER DEFAULT 0, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)""")
    c.execute("""CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, wallet_id INTEGER NOT NULL, category_id INTEGER, type TEXT NOT NULL, amount REAL NOT NULL, date TEXT NOT NULL, note TEXT, target_wallet_id INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE, FOREIGN KEY(wallet_id) REFERENCES wallets(id), FOREIGN KEY(category_id) REFERENCES categories(id))""")
    c.execute("""CREATE TABLE IF NOT EXISTS budgets (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, month TEXT NOT NULL, amount REAL NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE, UNIQUE(user_id, month))""")
    c.execute("""CREATE TABLE IF NOT EXISTS goals (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, name TEXT NOT NULL, target_amount REAL NOT NULL, current_amount REAL NOT NULL DEFAULT 0.0, deadline TEXT, status TEXT DEFAULT 'active', FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)""")
    
    # Tạo sẵn Admin
    if not c.execute("SELECT 1 FROM users WHERE username='admin'").fetchone():
        c.execute("INSERT INTO users (username, password, role, is_approved) VALUES (?, ?, 'admin', 1)", ('admin', hash_pw('admin123')))
    if not c.execute("SELECT 1 FROM users WHERE username='ducpro'").fetchone():
        c.execute("INSERT INTO users (username, password, role, is_approved) VALUES (?, ?, 'admin', 1)", ('ducpro', hash_pw('234766')))
    conn.commit(); conn.close()

def setup_new_user(user_id):
    conn = get_conn()
    c = conn.cursor()
    for name, c_type, icon in DEFAULT_CATEGORIES:
        c.execute("INSERT INTO categories (user_id, name, type, icon) VALUES (?, ?, ?, ?)", (user_id, name, c_type, icon))
    c.execute("INSERT INTO wallets (user_id, name, balance, type, is_default) VALUES (?, ?, ?, ?, ?)", (user_id, "Tiền mặt", 0.0, "cash", 1))
    c.execute("INSERT INTO wallets (user_id, name, balance, type) VALUES (?, ?, ?, ?)", (user_id, "Tài khoản Ngân hàng", 0.0, "bank"))
    c.execute("INSERT INTO budgets (user_id, month, amount) VALUES (?, ?, ?)", (user_id, datetime.now().strftime("%Y-%m"), 0.0))
    conn.commit(); conn.close()

def auth_user(username, password):
    conn = get_conn()
    user = conn.execute("SELECT id, username, role, is_approved FROM users WHERE username=? AND password=?", (username.strip(), hash_pw(password))).fetchone()
    conn.close()
    return user

def register_user(username, password):
    conn = get_conn()
    try:
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password, role, is_approved) VALUES (?, ?, 'user', 0)", (username.strip(), hash_pw(password)))
        setup_new_user(c.lastrowid)
        conn.commit(); conn.close(); return True
    except:
        conn.close(); return False

# --- CÁC HÀM TRUY VẤN (READ) ---
def get_wallets(uid):
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM wallets WHERE user_id=? ORDER BY is_default DESC, id ASC", conn, params=(uid,))
    conn.close(); return df

def get_categories(uid, c_type=None):
    conn = get_conn()
    q = "SELECT * FROM categories WHERE user_id=?"
    p = [uid]
    if c_type: q += " AND type=?"; p.append(c_type)
    df = pd.read_sql_query(q, conn, params=tuple(p))
    conn.close(); return df

def get_total_budget(uid, month):
    conn = get_conn()
    row = conn.execute("SELECT amount FROM budgets WHERE user_id=? AND month=?", (uid, month)).fetchone()
    conn.close()
    return float(row[0]) if row else 0.0

def get_transactions_df(uid, month=None):
    conn = get_conn()
    q = """SELECT t.id, t.date, t.type, t.amount, t.note, w.name as wallet_name, c.name as cat_name, c.icon as cat_icon, t.target_wallet_id 
           FROM transactions t LEFT JOIN wallets w ON t.wallet_id = w.id LEFT JOIN categories c ON t.category_id = c.id WHERE t.user_id = ?"""
    p = [uid]
    if month: q += " AND strftime('%Y-%m', t.date) = ?"; p.append(month)
    q += " ORDER BY t.date DESC, t.id DESC"
    df = pd.read_sql_query(q, conn, params=tuple(p))
    conn.close()
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df['month'] = df['date'].dt.strftime('%Y-%m')
    return df

def get_goals(uid):
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM goals WHERE user_id=? ORDER BY status DESC, deadline ASC", conn, params=(uid,))
    conn.close(); return df

def get_last_price(uid, keyword):
    conn = get_conn()
    row = conn.execute("SELECT amount FROM transactions WHERE user_id=? AND note LIKE ? AND type='expense' ORDER BY date DESC LIMIT 1", (uid, f"%{keyword}%")).fetchone()
    conn.close()
    return float(row[0]) if row else 0.0

# --- CÁC HÀM THỰC THI (WRITE) ---
def execute_transaction(uid, w_id, cat_id, t_type, amount, t_date, note, target_w_id=None):
    conn = get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO transactions (user_id, wallet_id, category_id, type, amount, date, note, target_wallet_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (uid, w_id, cat_id, t_type, amount, str(t_date), note, target_w_id))
    if t_type == "income": c.execute("UPDATE wallets SET balance = balance + ? WHERE id = ?", (amount, w_id))
    elif t_type == "expense": c.execute("UPDATE wallets SET balance = balance - ? WHERE id = ?", (amount, w_id))
    elif t_type == "transfer":
        c.execute("UPDATE wallets SET balance = balance - ? WHERE id = ?", (amount, w_id))
        if target_w_id: c.execute("UPDATE wallets SET balance = balance + ? WHERE id = ?", (amount, target_w_id))
    conn.commit(); conn.close()

def delete_transaction(txn_id, uid):
    conn = get_conn()
    c = conn.cursor()
    txn = c.execute("SELECT wallet_id, type, amount, target_wallet_id FROM transactions WHERE id=? AND user_id=?", (txn_id, uid)).fetchone()
    if txn:
        w_id, t_type, amt, tw_id = txn
        c.execute("DELETE FROM transactions WHERE id=?", (txn_id,))
        if t_type == 'income': c.execute("UPDATE wallets SET balance = balance - ? WHERE id=?", (amt, w_id))
        elif t_type == 'expense': c.execute("UPDATE wallets SET balance = balance + ? WHERE id=?", (amt, w_id))
        elif t_type == 'transfer':
            c.execute("UPDATE wallets SET balance = balance + ? WHERE id=?", (amt, w_id))
            if tw_id: c.execute("UPDATE wallets SET balance = balance - ? WHERE id=?", (amt, tw_id))
        conn.commit(); conn.close(); return True
    conn.close(); return False

def update_budget(uid, month, amount):
    conn = get_conn()
    conn.execute("INSERT INTO budgets (user_id, month, amount) VALUES (?, ?, ?) ON CONFLICT(user_id, month) DO UPDATE SET amount=excluded.amount", (uid, month, amount))
    conn.commit(); conn.close()

def add_goal(uid, name, target_amount, deadline):
    conn = get_conn()
    conn.execute("INSERT INTO goals (user_id, name, target_amount, deadline) VALUES (?, ?, ?, ?)", (uid, name, target_amount, str(deadline)))
    conn.commit(); conn.close()

def fund_goal(goal_id, amount):
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE goals SET current_amount = current_amount + ? WHERE id=?", (amount, goal_id))
    g = c.execute("SELECT current_amount, target_amount FROM goals WHERE id=?", (goal_id,)).fetchone()
    if g and g[0] >= g[1]: c.execute("UPDATE goals SET status='completed' WHERE id=?", (goal_id,))
    conn.commit(); conn.close()

def add_wallet(uid, name, balance, w_type):
    conn = get_conn()
    conn.execute("INSERT INTO wallets (user_id, name, balance, type) VALUES (?, ?, ?, ?)", (uid, name, balance, w_type))
    conn.commit(); conn.close()

def fmt_money(value): return f"{value:,.0f} ₫".replace(",", ".")

# ==============================================================================
# 5. CÁC MÀN HÌNH GIAO DIỆN (PAGES)
# ==============================================================================

# --- A. ĐĂNG NHẬP / ĐĂNG KÝ ---
def page_auth():
    st.markdown("""<div style='text-align:center; padding: 3rem 0 1rem 0;'><h1 style='color:#059669; font-size: 3.5rem; font-weight: 900; margin-bottom: 0;'>💎 FinPro Ultimate</h1><p style='color:#64748b; font-size: 1.2rem;'>Hệ Sinh Thái Quản Lý Tài Chính & Dòng Tiền</p></div>""", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 1.5, 1])
    with col:
        t1, t2 = st.tabs(["🔐 Đăng Nhập", "📝 Tạo Tài Khoản"])
        with t1:
            with st.container(border=True):
                with st.form("login_form"):
                    u = st.text_input("Tên đăng nhập")
                    p = st.text_input("Mật khẩu", type="password")
                    if st.form_submit_button("Vào Hệ Thống 🚀", type="primary", use_container_width=True):
                        user = auth_user(u, p)
                        if not user: st.error("❌ Thông tin không chính xác!")
                        elif user[3] == 0: st.warning("⏳ Tài khoản đang chờ Admin duyệt.")
                        else: st.session_state.update({"logged_in": True, "uid": user[0], "uname": user[1], "role": user[2]}); st.rerun()
        with t2:
            with st.container(border=True):
                st.info("Dữ liệu của bạn được lưu trữ hoàn toàn riêng biệt và bảo mật.")
                with st.form("reg_form"):
                    nu = st.text_input("Tên đăng nhập mới")
                    np = st.text_input("Mật khẩu", type="password")
                    if st.form_submit_button("Đăng Ký Miễn Phí", use_container_width=True):
                        if nu and np:
                            if register_user(nu, np): st.success("🎉 Thành công! Chờ Admin duyệt nhé.")
                            else: st.error("⚠️ Tên đăng nhập đã tồn tại.")
                        else: st.warning("Vui lòng điền đủ thông tin.")

# --- B. DASHBOARD (TỔNG QUAN) ---
def page_dashboard(uid):
    st.markdown("<h2>🏠 Tổng Quan Tài Chính</h2>", unsafe_allow_html=True)
    cm = datetime.now().strftime("%Y-%m")
    budget = get_total_budget(uid, cm)
    wallets = get_wallets(uid)
    txns = get_transactions_df(uid, cm)
    
    total_assets = wallets['balance'].sum() if not wallets.empty else 0.0
    spent = txns[txns['type'] == 'expense']['amount'].sum() if not txns.empty else 0.0
    income = txns[txns['type'] == 'income']['amount'].sum() if not txns.empty else 0.0
    
    m1, m2, m3 = st.columns(3)
    m1.metric("💰 Tổng Tài Sản", fmt_money(total_assets))
    m2.metric("📥 Thu Nhập Tháng", fmt_money(income))
    m3.metric("💸 Đã Chi Tiêu", fmt_money(spent), f"Ngân sách: {fmt_money(budget)}", delta_color="off")
    
    if budget > 0:
        prog = min(spent/budget, 1.0)
        st.progress(prog)
        rem = budget - spent
        if rem < 0: st.error(f"⚠️ Vượt ngân sách {fmt_money(abs(rem))}!")
        elif rem < budget * 0.2: st.warning(f"⚠️ Sắp cạn ngân sách. Chỉ còn {fmt_money(rem)}.")
        else: st.success(f"✅ An toàn. Còn lại {fmt_money(rem)}.")
    else: st.info("💡 Bạn chưa thiết lập Ngân sách tháng này.")

    st.markdown("---")
    col_w, col_c = st.columns([1.5, 2])
    with col_w:
        st.markdown("#### 💼 Quản lý Ví của bạn")
        if not wallets.empty:
            for _, w in wallets.iterrows():
                ic = "🏦" if w['type']=='bank' else "💳" if w['type']=='credit' else "💵"
                st.markdown(f"<div style='padding: 15px; border: 1px solid #e1e4e8; border-radius: 12px; margin-bottom: 12px; display: flex; justify-content: space-between; background: white;'><span>{ic} <b>{w['name']}</b></span><span style='color: #059669; font-weight: 700;'>{fmt_money(w['balance'])}</span></div>", unsafe_allow_html=True)
        else: st.warning("Bạn chưa có Ví nào.")
                
    with col_c:
        st.markdown("#### 📊 Cơ cấu Chi Tiêu Tháng Này")
        if not txns.empty and spent > 0:
            exp_df = txns[txns['type'] == 'expense']
            cat_sum = exp_df.groupby('cat_name')['amount'].sum().reset_index()
            fig = px.pie(cat_sum, values='amount', names='cat_name', hole=0.5)
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(margin=dict(t=10,b=10,l=10,r=10), height=300)
            st.plotly_chart(fig, use_container_width=True)
        else: st.info("Chưa có khoản chi nào.")

# --- C. GIAO DỊCH (TRANSACTIONS) ---
def page_transactions(uid):
    st.markdown("<h2>📝 Quản lý Giao Dịch</h2>", unsafe_allow_html=True)
    w_df = get_wallets(uid)
    if w_df.empty: st.error("⚠️ Hãy vào mục 'Ví & Quỹ' tạo Ví trước khi ghi chép!"); return
    w_dict = {r['name']: r['id'] for _, r in w_df.iterrows()}
    
    with st.expander("➕ GHI CHÉP GIAO DỊCH MỚI", expanded=True):
        t1, t2, t3 = st.tabs(["💸 Chi Tiền", "💰 Thu Nhập", "🔄 Chuyển Khoản"])
        
        with t1:
            with st.form("f_exp", clear_on_submit=True):
                c1, c2 = st.columns(2)
                amt = c1.number_input("Số tiền chi (₫)", min_value=0.0, step=10000.0)
                cats = get_categories(uid, 'expense')
                cat_d = {f"{r['icon']} {r['name']}": r['id'] for _, r in cats.iterrows()}
                cat_id = c2.selectbox("Mục chi tiêu", list(cat_d.keys()))
                c3, c4, c5 = st.columns([1.5, 2, 1])
                w_id = c3.selectbox("Nguồn tiền", list(w_dict.keys()))
                note = c4.text_input("Ghi chú", placeholder="Vd: Tiền điện")
                d = c5.date_input("Ngày", value=date.today())
                if st.form_submit_button("Lưu Khoản Chi 💾", type="primary", use_container_width=True):
                    if amt > 0: execute_transaction(uid, w_dict[w_id], cat_d[cat_id], 'expense', amt, d, note); st.toast("✅ Đã ghi!"); st.rerun()
                    else: st.warning("Nhập số tiền.")

        with t2:
            with st.form("f_inc", clear_on_submit=True):
                c1, c2 = st.columns(2)
                amt = c1.number_input("Số tiền thu (₫)", min_value=0.0, step=100000.0)
                cats = get_categories(uid, 'income')
                cat_d = {f"{r['icon']} {r['name']}": r['id'] for _, r in cats.iterrows()}
                cat_id = c2.selectbox("Nguồn thu", list(cat_d.keys()))
                c3, c4, c5 = st.columns([1.5, 2, 1])
                w_id = c3.selectbox("Vào ví", list(w_dict.keys()))
                note = c4.text_input("Ghi chú")
                d = c5.date_input("Ngày", value=date.today())
                if st.form_submit_button("Lưu Thu Nhập 📥", type="primary", use_container_width=True):
                    if amt > 0: execute_transaction(uid, w_dict[w_id], cat_d[cat_id], 'income', amt, d, note); st.toast("✅ Đã ghi!"); st.rerun()

        with t3:
            with st.form("f_tra", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                amt = c1.number_input("Số tiền (₫)", min_value=0.0, step=50000.0)
                fw = c2.selectbox("Từ ví", list(w_dict.keys()), key='fw')
                tw = c3.selectbox("Đến ví", list(w_dict.keys()), key='tw')
                c4, c5 = st.columns([2, 1])
                note = c4.text_input("Lý do")
                d = c5.date_input("Ngày", value=date.today(), key='dt')
                if st.form_submit_button("Thực Hiện Chuyển 🔄", type="primary", use_container_width=True):
                    if amt > 0 and fw != tw: execute_transaction(uid, w_dict[fw], None, 'transfer', amt, d, note, target_w_id=w_dict[tw]); st.toast("✅ Hoàn tất!"); st.rerun()
                    elif fw == tw: st.error("Ví nguồn và đích phải khác nhau.")

    st.markdown("### 📋 Sổ cái (Lịch sử)")
    df = get_transactions_df(uid)
    if not df.empty:
        df['Hiển thị'] = df.apply(lambda r: f"🔴 -{fmt_money(r['amount'])}" if r['type']=='expense' else f"🟢 +{fmt_money(r['amount'])}" if r['type']=='income' else f"🔄 {fmt_money(r['amount'])}", axis=1)
        col1, col2 = st.columns(2)
        f_month = col1.selectbox("Lọc Tháng", ["Tất cả"] + sorted(df['month'].unique().tolist(), reverse=True))
        if f_month != "Tất cả": df = df[df['month'] == f_month]
        st.dataframe(df[['id', 'date', 'wallet_name', 'cat_name', 'Hiển thị', 'note']].rename(columns={'id':'ID','date':'Ngày','wallet_name':'Ví','cat_name':'Mục','note':'Ghi chú'}), use_container_width=True, hide_index=True)
        
        with st.expander("🗑️ Hủy/Xóa Giao Dịch"):
            del_id = st.selectbox("Chọn ID", df['id'].tolist())
            if st.button("Xác nhận Xóa (Hoàn tiền về Ví)", type="primary"):
                if delete_transaction(del_id, uid): st.success("Đã xóa!"); st.rerun()
    else: st.info("Sổ cái trống.")

# --- D. VÍ & QUỸ (WALLETS & GOALS) ---
def page_wallets_goals(uid):
    st.markdown("<h2>💼 Quản lý Ví & Quỹ Để Dành</h2>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["🏦 Quản lý Ví Tiền", "🎯 Quỹ Tiết Kiệm (Để dành)"])
    
    with t1:
        st.markdown("#### Mở Ví mới")
        with st.form("new_w"):
            c1, c2, c3 = st.columns([2, 1.5, 1])
            n = c1.text_input("Tên Ví (Vd: Thẻ Visa, Két sắt...)")
            b = c2.number_input("Số dư hiện có", min_value=0.0, step=100000.0)
            t = c3.selectbox("Loại", ["bank", "cash", "credit"])
            if st.form_submit_button("Tạo Ví", type="primary", use_container_width=True):
                if n: add_wallet(uid, n, b, t); st.success("Đã tạo!"); st.rerun()
        
        st.markdown("#### Trạng thái các Ví")
        w_df = get_wallets(uid)
        if not w_df.empty: st.dataframe(w_df[['name', 'balance', 'type']].rename(columns={'name':'Tên Ví', 'balance':'Số Dư', 'type':'Phân loại'}).style.format({"Số Dư":"{:,.0f} ₫"}), use_container_width=True, hide_index=True)

    with t2:
        st.info("💡 Trích lập các quỹ riêng (Mua xe, Tiền học, Trả nợ...) để dễ theo dõi.")
        with st.form("new_g"):
            c1, c2, c3 = st.columns([2, 1.5, 1.5])
            n = c1.text_input("Tên Quỹ / Mục tiêu")
            tg = c2.number_input("Cần gom bao nhiêu (₫)?", min_value=0.0, step=1000000.0)
            dead = c3.date_input("Hạn chót")
            if st.form_submit_button("Khởi Tạo Mục Tiêu", type="primary", use_container_width=True):
                if n and tg > 0: add_goal(uid, n, tg, dead); st.success("Thành công!"); st.rerun()
                
        df_g = get_goals(uid)
        if not df_g.empty:
            for _, g in df_g.iterrows():
                with st.container(border=True):
                    is_done = g['status'] == 'completed'
                    icon = "✅" if is_done else "⏳"
                    pct = min(g['current_amount'] / g['target_amount'], 1.0) if g['target_amount'] > 0 else 0
                    st.markdown(f"#### {icon} {g['name']}")
                    st.write(f"Mục tiêu: **{fmt_money(g['target_amount'])}** | Hạn chót: {g['deadline']}")
                    cp, ct = st.columns([4, 1])
                    cp.progress(pct); ct.write(f"**{pct*100:.1f}%**")
                    st.write(f"Đã gom: <span style='color:#059669;font-weight:bold;'>{fmt_money(g['current_amount'])}</span> | Còn thiếu: <span style='color:#ef4444;'>{fmt_money(g['target_amount'] - g['current_amount'])}</span>", unsafe_allow_html=True)
                    if not is_done:
                        with st.expander("Bơm tiền vào quỹ"):
                            with st.form(f"fund_{g['id']}"):
                                a = st.number_input("Số tiền", min_value=0.0, step=50000.0)
                                if st.form_submit_button("Bơm 🚀", type="primary"):
                                    if a > 0: fund_goal(g['id'], a); st.toast("Đã tăng quỹ!"); st.rerun()
        else: st.caption("Danh sách Quỹ trống.")

# --- E. THỐNG KÊ (ANALYTICS) ---
def page_analytics(uid):
    st.markdown("<h2>📈 Báo Cáo & Dòng Tiền</h2>", unsafe_allow_html=True)
    df = get_transactions_df(uid)
    if df.empty: st.info("Chưa có dữ liệu!"); return
    
    m = st.selectbox("📅 Lọc theo tháng", ["Tất cả thời gian"] + sorted(df['month'].unique().tolist(), reverse=True))
    plot_df = df if m == "Tất cả thời gian" else df[df['month'] == m]
    if plot_df.empty: st.warning("Không có giao dịch."); return

    exp_df, inc_df = plot_df[plot_df['type'] == 'expense'], plot_df[plot_df['type'] == 'income']
    t_exp, t_inc = exp_df['amount'].sum(), inc_df['amount'].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Tổng Thu", fmt_money(t_inc))
    c2.metric("Tổng Chi", fmt_money(t_exp))
    c3.metric("Chênh Lệch", fmt_money(t_inc - t_exp), delta_color="normal" if (t_inc - t_exp)>=0 else "inverse")

    st.markdown("---")
    cl1, cl2 = st.columns(2)
    with cl1:
        st.markdown("#### 🔴 Tiền đi đâu?")
        if not exp_df.empty: st.plotly_chart(px.pie(exp_df.groupby('cat_name')['amount'].sum().reset_index(), values='amount', names='cat_name', hole=0.45), use_container_width=True)
    with cl2:
        st.markdown("#### 🟢 Tiền đến từ đâu?")
        if not inc_df.empty: st.plotly_chart(px.pie(inc_df.groupby('cat_name')['amount'].sum().reset_index(), values='amount', names='cat_name', hole=0.45), use_container_width=True)

    st.markdown("#### 📊 Lưu lượng dòng tiền (Cashflow)")
    flow = plot_df[plot_df['type'].isin(['income','expense'])].groupby(['date','type'])['amount'].sum().reset_index()
    flow.loc[flow['type']=='expense', 'amount'] *= -1
    st.plotly_chart(px.bar(flow, x='date', y='amount', color='type', color_discrete_map={'income':'#10b981','expense':'#ef4444'}, title="Thu - Chi theo ngày"), use_container_width=True)

# --- F. CÀI ĐẶT & ADMIN (SETTINGS) ---
def page_settings(uid, role):
    st.markdown("<h2>⚙️ Cài Đặt Hệ Thống</h2>", unsafe_allow_html=True)
    
    with st.container(border=True):
        st.markdown("#### 💰 Cấu hình Ngân Sách Tổng")
        cm = datetime.now().strftime("%Y-%m")
        cur_bg = get_total_budget(uid, cm)
        c_b, c_btn = st.columns([3, 1])
        new_bg = c_b.number_input(f"Ngân sách tháng {cm} (₫)", value=cur_bg, step=500000.0)
        c_btn.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        if c_btn.button("Lưu Ngân Sách", type="primary", use_container_width=True):
            update_budget(uid, cm, new_bg); st.success("✅ Đã cập nhật!")

    st.markdown("---")
    with st.expander("🗂️ Thêm Danh Mục Cá Nhân Mới", expanded=False):
        t1, t2 = st.tabs(["🔴 Mục Chi Tiêu", "🟢 Mục Thu Nhập"])
        with t1:
            with st.form("f_add_exp"):
                c1, c2 = st.columns([3, 1])
                n = c1.text_input("Tên (VD: Cafe, Mua Game)")
                i = c2.text_input("Icon Emoji", value="🏷️")
                if st.form_submit_button("Thêm Mục", type="primary"):
                    if n: 
                        conn=get_conn(); conn.execute("INSERT INTO categories (user_id, name, type, icon) VALUES (?, ?, 'expense', ?)", (uid, n, i)); conn.commit(); conn.close(); st.rerun()
            st.write("Các mục hiện có: " + ", ".join([f"{r['icon']} {r['name']}" for _, r in get_categories(uid, 'expense').iterrows()]))
        with t2:
            with st.form("f_add_inc"):
                c1, c2 = st.columns([3, 1])
                n = c1.text_input("Tên (VD: Tiền lãi)")
                i = c2.text_input("Icon Emoji", value="💵")
                if st.form_submit_button("Thêm Mục", type="primary"):
                    if n: 
                        conn=get_conn(); conn.execute("INSERT INTO categories (user_id, name, type, icon) VALUES (?, ?, 'income', ?)", (uid, n, i)); conn.commit(); conn.close(); st.rerun()
            st.write("Các mục hiện có: " + ", ".join([f"{r['icon']} {r['name']}" for _, r in get_categories(uid, 'income').iterrows()]))

    if role == "admin":
        st.markdown("---")
        st.markdown("### 🛡️ Quản Trị Hệ Thống (Dành riêng Admin)")
        conn = get_conn()
        pending = conn.execute("SELECT id, username, created_at FROM users WHERE is_approved=0").fetchall()
        if pending:
            for r in pending:
                with st.container(border=True):
                    c1, c2 = st.columns([4, 1])
                    c1.markdown(f"👤 Tài khoản: **{r[1]}** (Đăng ký: {r[2]})")
                    if c2.button("Duyệt Ngay", key=f"appr_{r[0]}", type="primary"):
                        conn.execute("UPDATE users SET is_approved=1 WHERE id=?", (r[0],)); conn.commit(); st.rerun()
        else: st.info("Không có tài khoản chờ duyệt.")
        conn.close()

# ==============================================================================
# 6. ROUTER & MAIN EXECUTION
# ==============================================================================
def main():
    init_db()
    inject_global_css()

    if not st.session_state.logged_in:
        st.markdown("<h1 style='text-align:center; color:#059669; margin-top:50px; font-weight: 800;'>💎 FinPro Ultimate</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:gray;'>Phần Mềm Quản Lý Tài Chính & Dòng Tiền Không Giới Hạn</p>", unsafe_allow_html=True)
        _, col, _ = st.columns([1, 1.5, 1])
        with col:
            t1, t2 = st.tabs(["Đăng Nhập Hệ Thống", "Mở Tài Khoản Mới"])
            with t1:
                with st.container(border=True):
                    with st.form("login_form"):
                        u = st.text_input("Tên đăng nhập")
                        p = st.text_input("Mật khẩu", type="password")
                        if st.form_submit_button("Vào Hệ Thống 🚀", type="primary", use_container_width=True):
                            user = auth_user(u, p)
                            if not user: st.error("❌ Thông tin đăng nhập không chính xác!")
                            elif user[3] == 0: st.warning("⏳ Tài khoản đang chờ Admin xét duyệt.")
                            else:
                                st.session_state.update({"logged_in": True, "uid": user[0], "uname": user[1], "role": user[2]})
                                st.rerun()
            with t2:
                with st.container(border=True):
                    st.info("Hệ thống sẽ tự động cấp phát Ví và Danh mục chuẩn cho tài khoản mới.")
                    with st.form("reg_form"):
                        nu = st.text_input("Tên đăng nhập mong muốn")
                        np = st.text_input("Mật khẩu", type="password")
                        if st.form_submit_button("Đăng Ký Miễn Phí", use_container_width=True):
                            if nu and np:
                                if register_user(nu, np): st.success("🎉 Tạo tài khoản thành công! Vui lòng báo Admin duyệt.")
                                else: st.error("⚠️ Tên đăng nhập này đã tồn tại.")
                            else: st.warning("Vui lòng nhập đủ thông tin.")
    else:
        uid = st.session_state.uid
        
        # SIDEBAR
        with st.sidebar:
            st.markdown(f"### 👋 Xin chào,<br><span style='color:#059669;'>{st.session_state.uname.upper()}</span>", unsafe_allow_html=True)
            st.markdown("---")
            menu = st.radio("MENU", ["🏠 Tổng Quan", "📝 Giao Dịch", "💼 Ví & Quỹ", "📈 Thống Kê", "⚙️ Cài Đặt"], label_visibility="collapsed")
            st.markdown("---")
            if st.button("🚪 Đăng Xuất", use_container_width=True):
                st.session_state.clear(); st.rerun()

        # ĐIỀU HƯỚNG CÁC TRANG
        if menu == "🏠 Tổng Quan": page_dashboard(uid)
        elif menu == "📝 Giao Dịch": page_transactions(uid)
        elif menu == "💼 Ví & Quỹ": page_wallets_goals(uid)
        elif menu == "📈 Thống Kê": page_analytics(uid)
        elif menu == "⚙️ Cài Đặt": page_settings(uid, st.session_state.role)

        # NÚT QUICK ADD NỔI Ở GÓC DƯỚI BÊN PHẢI
        with st.popover("QuickAddHiddenBtn"):
            st.markdown("##### ⚡ Ghi Chi Tiêu Nhanh")
            w_df = get_wallets(uid)
            if not w_df.empty:
                def_w = w_df.iloc[0]['id']
                with st.form("quick_exp_form", clear_on_submit=True):
                    amt = st.number_input("Số tiền chi (₫)", min_value=0.0, step=10000.0)
                    cats_exp = get_categories(uid, 'expense')
                    cat_names = [f"{r['icon']} {r['name']}" for _, r in cats_exp.iterrows()]
                    cat_ids = [r['id'] for _, r in cats_exp.iterrows()]
                    c_idx = st.selectbox("Mục đích", range(len(cat_names)), format_func=lambda x: cat_names[x])
                    nt = st.text_input("Ghi chú", placeholder="Ăn trưa, đổ xăng...")
                    if st.form_submit_button("LƯU NGAY 🚀", type="primary", use_container_width=True):
                        if amt > 0:
                            execute_transaction(uid, def_w, cat_ids[c_idx], 'expense', amt, date.today(), nt)
                            st.toast("✅ Đã ghi nhận!"); st.rerun()
                        else: st.warning("Nhập số tiền > 0.")
            else: st.error("⚠️ Bạn chưa có Ví nào. Xin hãy qua menu 'Ví & Quỹ' để tạo ví.")

if __name__ == "__main__":
    main()