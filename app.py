import os
import sqlite3
import hashlib
from datetime import datetime, date
from contextlib import closing

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# =========================================================
# CONFIG
# =========================================================
st.set_page_config(
    page_title="FinPro Mobile",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_PATH = os.getenv("FINPRO_DB_PATH", "finpro_mobile.db")
APP_TITLE = "💎 FinPro Mobile"
PRIMARY = "#0f766e"
ACCENT = "#14b8a6"
DANGER = "#ef4444"
WARNING = "#f59e0b"
SUCCESS = "#10b981"

DEFAULT_CATEGORIES = [
    ("Ăn uống", "expense", "🍜"),
    ("Tiền nhà / Điện nước", "expense", "🏠"),
    ("Di chuyển / Xăng xe", "expense", "⛽"),
    ("Mua sắm", "expense", "🛍️"),
    ("Con cái", "expense", "🍼"),
    ("Sức khỏe", "expense", "💊"),
    ("Giải trí", "expense", "🎬"),
    ("Giáo dục", "expense", "📚"),
    ("Bảo hiểm / Nợ", "expense", "🛡️"),
    ("Khác (Chi tiêu)", "expense", "📦"),
    ("Lương", "income", "💰"),
    ("Thưởng", "income", "🎁"),
    ("Kinh doanh", "income", "🏪"),
    ("Đầu tư", "income", "📈"),
    ("Khác (Thu nhập)", "income", "📥"),
]

DEFAULT_WALLETS = [
    ("Tiền mặt", 0.0, "cash", 1),
    ("Tài khoản ngân hàng", 0.0, "bank", 0),
]

# seed account requested by user
SEED_USERS = [
    ("admin", "admin123", "admin", 1),
    ("duc1", "123456", "admin", 1),
]

# =========================================================
# UI / STYLE
# =========================================================
def inject_css():
    st.markdown(
        f"""
        <style>
            #MainMenu, footer, header {{visibility: hidden;}}
            .stApp {{
                background:
                    radial-gradient(circle at top left, rgba(20,184,166,0.10), transparent 25%),
                    linear-gradient(180deg, #f8fafc 0%, #eef6f6 100%);
                color: #0f172a;
            }}
            .block-container {{
                max-width: 1200px;
                padding-top: 1.1rem;
                padding-bottom: 8rem;
            }}
            .hero-card {{
                background: linear-gradient(135deg, {PRIMARY} 0%, #115e59 100%);
                color: white;
                border-radius: 24px;
                padding: 22px 24px;
                box-shadow: 0 18px 40px rgba(15,118,110,0.20);
                margin-bottom: 16px;
            }}
            .soft-card {{
                background: rgba(255,255,255,0.88);
                border: 1px solid #e2e8f0;
                border-radius: 18px;
                padding: 16px;
                box-shadow: 0 8px 30px rgba(15,23,42,0.05);
            }}
            div[data-testid="metric-container"] {{
                border: 1px solid #dbe4ea;
                border-radius: 18px;
                padding: 14px 18px;
                background: rgba(255,255,255,0.95);
                box-shadow: 0 8px 24px rgba(15,23,42,0.05);
            }}
            .stButton>button, .stDownloadButton>button {{
                border-radius: 12px !important;
                border: none !important;
                font-weight: 700 !important;
            }}
            .chip {{
                display: inline-block;
                padding: 6px 10px;
                background: #ecfeff;
                color: {PRIMARY};
                border-radius: 999px;
                font-size: 12px;
                font-weight: 700;
                margin-right: 8px;
                margin-bottom: 8px;
                border: 1px solid #ccfbf1;
            }}
            .danger-text {{ color: {DANGER}; font-weight: 700; }}
            .success-text {{ color: {SUCCESS}; font-weight: 700; }}
            div[data-testid="stSidebar"] {{
                background: linear-gradient(180deg, #0f172a 0%, #111827 100%);
            }}
            div[data-testid="stSidebar"] * {{ color: #f8fafc; }}
            div[data-testid="stPopover"] {{
                position: fixed !important;
                right: 22px !important;
                bottom: 20px !important;
                z-index: 999999 !important;
            }}
            div[data-testid="stPopover"] > button {{
                width: 62px !important;
                height: 62px !important;
                border-radius: 999px !important;
                background: linear-gradient(135deg, {SUCCESS}, {ACCENT}) !important;
                box-shadow: 0 15px 30px rgba(20,184,166,.35) !important;
                border: 4px solid #ffffff !important;
            }}
            div[data-testid="stPopover"] > button * {{ display: none !important; }}
            div[data-testid="stPopover"] > button::after {{
                content: "+";
                color: white;
                font-size: 34px;
                font-weight: 700;
            }}
            @media (max-width: 768px) {{
                .block-container {{
                    padding-left: 1rem;
                    padding-right: 1rem;
                }}
                div[data-testid="stHorizontalBlock"] {{ gap: 0.7rem; }}
                div[data-testid="stPopover"] > button {{ width: 56px !important; height: 56px !important; }}
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str):
    st.markdown(
        f"""
        <div class="hero-card">
            <div style="font-size: 1.9rem; font-weight: 900;">{title}</div>
            <div style="opacity: .9; margin-top: 6px; font-size: 1rem;">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# DB
# =========================================================
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn


def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def init_db():
    with closing(get_conn()) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                is_approved INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('income','expense')),
                icon TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, name, type),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS wallets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                balance REAL NOT NULL DEFAULT 0,
                type TEXT NOT NULL DEFAULT 'bank',
                is_default INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                month TEXT NOT NULL,
                amount REAL NOT NULL DEFAULT 0,
                UNIQUE(user_id, month),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                target_amount REAL NOT NULL,
                current_amount REAL NOT NULL DEFAULT 0,
                deadline TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                wallet_id INTEGER NOT NULL,
                category_id INTEGER,
                type TEXT NOT NULL CHECK(type IN ('income','expense','transfer')),
                amount REAL NOT NULL CHECK(amount >= 0),
                date TEXT NOT NULL,
                note TEXT,
                target_wallet_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(wallet_id) REFERENCES wallets(id),
                FOREIGN KEY(target_wallet_id) REFERENCES wallets(id),
                FOREIGN KEY(category_id) REFERENCES categories(id)
            )
            """
        )

        for username, password, role, approved in SEED_USERS:
            row = cur.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
            if not row:
                cur.execute(
                    "INSERT INTO users (username, password, role, is_approved) VALUES (?, ?, ?, ?)",
                    (username, hash_pw(password), role, approved),
                )
                user_id = cur.lastrowid
                seed_user_data(conn, user_id)

        conn.commit()


def seed_user_data(conn, user_id: int):
    cur = conn.cursor()
    for name, cat_type, icon in DEFAULT_CATEGORIES:
        cur.execute(
            "INSERT OR IGNORE INTO categories (user_id, name, type, icon) VALUES (?, ?, ?, ?)",
            (user_id, name, cat_type, icon),
        )
    for name, balance, wallet_type, is_default in DEFAULT_WALLETS:
        cur.execute(
            "INSERT INTO wallets (user_id, name, balance, type, is_default) VALUES (?, ?, ?, ?, ?)",
            (user_id, name, balance, wallet_type, is_default),
        )
    month = datetime.now().strftime("%Y-%m")
    cur.execute(
        "INSERT OR IGNORE INTO budgets (user_id, month, amount) VALUES (?, ?, 0)",
        (user_id, month),
    )


# =========================================================
# HELPERS
# =========================================================
def ensure_session_state():
    defaults = {
        "logged_in": False,
        "uid": None,
        "username": "",
        "role": "",
        "editing_txn_id": None,
        "active_page": "🏠 Tổng quan",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def money(value: float) -> str:
    return f"{value:,.0f} ₫".replace(",", ".")


def month_label() -> str:
    return datetime.now().strftime("%Y-%m")


def to_dataframe(query: str, params=()):
    with closing(get_conn()) as conn:
        return pd.read_sql_query(query, conn, params=params)


def auth_user(username: str, password: str):
    with closing(get_conn()) as conn:
        return conn.execute(
            "SELECT id, username, role, is_approved FROM users WHERE username=? AND password=?",
            (username.strip(), hash_pw(password)),
        ).fetchone()


def register_user(username: str, password: str):
    username = username.strip()
    if len(username) < 3 or len(password) < 6:
        return False, "Tên đăng nhập tối thiểu 3 ký tự, mật khẩu tối thiểu 6 ký tự."
    with closing(get_conn()) as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO users (username, password, role, is_approved) VALUES (?, ?, 'user', 1)",
                (username, hash_pw(password)),
            )
            seed_user_data(conn, cur.lastrowid)
            conn.commit()
            return True, "Tạo tài khoản thành công."
        except sqlite3.IntegrityError:
            return False, "Tên đăng nhập đã tồn tại."


def get_wallets(uid: int):
    return to_dataframe(
        "SELECT * FROM wallets WHERE user_id=? ORDER BY is_default DESC, id ASC", (uid,)
    )


def get_categories(uid: int, cat_type: str | None = None):
    if cat_type:
        return to_dataframe(
            "SELECT * FROM categories WHERE user_id=? AND type=? ORDER BY name ASC",
            (uid, cat_type),
        )
    return to_dataframe("SELECT * FROM categories WHERE user_id=? ORDER BY type, name", (uid,))


def get_budget(uid: int, month: str):
    with closing(get_conn()) as conn:
        row = conn.execute(
            "SELECT amount FROM budgets WHERE user_id=? AND month=?", (uid, month)
        ).fetchone()
        return float(row[0]) if row else 0.0


def get_goals(uid: int):
    return to_dataframe(
        "SELECT * FROM goals WHERE user_id=? ORDER BY status ASC, deadline ASC, id DESC", (uid,)
    )


def get_transactions(uid: int):
    query = """
        SELECT
            t.id, t.user_id, t.wallet_id, t.category_id, t.type, t.amount, t.date, t.note,
            t.target_wallet_id, t.created_at, t.updated_at,
            w.name AS wallet_name,
            tw.name AS target_wallet_name,
            c.name AS category_name,
            c.icon AS category_icon
        FROM transactions t
        LEFT JOIN wallets w ON t.wallet_id = w.id
        LEFT JOIN wallets tw ON t.target_wallet_id = tw.id
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = ?
        ORDER BY t.date DESC, t.id DESC
    """
    df = to_dataframe(query, (uid,))
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df["month"] = df["date"].dt.strftime("%Y-%m")
    return df


def add_wallet(uid: int, name: str, balance: float, wallet_type: str):
    with closing(get_conn()) as conn:
        conn.execute(
            "INSERT INTO wallets (user_id, name, balance, type) VALUES (?, ?, ?, ?)",
            (uid, name.strip(), balance, wallet_type),
        )
        conn.commit()


def add_category(uid: int, name: str, cat_type: str, icon: str):
    with closing(get_conn()) as conn:
        conn.execute(
            "INSERT INTO categories (user_id, name, type, icon) VALUES (?, ?, ?, ?)",
            (uid, name.strip(), cat_type, icon.strip() or "🏷️"),
        )
        conn.commit()


def update_budget(uid: int, month: str, amount: float):
    with closing(get_conn()) as conn:
        conn.execute(
            """
            INSERT INTO budgets (user_id, month, amount) VALUES (?, ?, ?)
            ON CONFLICT(user_id, month) DO UPDATE SET amount = excluded.amount
            """,
            (uid, month, amount),
        )
        conn.commit()


def add_goal(uid: int, name: str, target_amount: float, deadline):
    with closing(get_conn()) as conn:
        conn.execute(
            "INSERT INTO goals (user_id, name, target_amount, deadline) VALUES (?, ?, ?, ?)",
            (uid, name.strip(), target_amount, str(deadline)),
        )
        conn.commit()


def fund_goal(goal_id: int, amount: float):
    with closing(get_conn()) as conn:
        cur = conn.cursor()
        cur.execute("UPDATE goals SET current_amount = current_amount + ? WHERE id=?", (amount, goal_id))
        row = cur.execute("SELECT current_amount, target_amount FROM goals WHERE id=?", (goal_id,)).fetchone()
        if row and row[0] >= row[1]:
            cur.execute("UPDATE goals SET status='completed' WHERE id=?", (goal_id,))
        conn.commit()


def create_transaction(uid: int, wallet_id: int, category_id: int | None, tx_type: str, amount: float, tx_date, note: str, target_wallet_id: int | None = None):
    with closing(get_conn()) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO transactions (user_id, wallet_id, category_id, type, amount, date, note, target_wallet_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (uid, wallet_id, category_id, tx_type, amount, str(tx_date), note.strip(), target_wallet_id),
        )
        apply_wallet_impact(cur, wallet_id, target_wallet_id, tx_type, amount, mode="apply")
        conn.commit()


def apply_wallet_impact(cur, wallet_id: int, target_wallet_id: int | None, tx_type: str, amount: float, mode: str):
    factor = 1 if mode == "apply" else -1
    if tx_type == "income":
        cur.execute("UPDATE wallets SET balance = balance + ? WHERE id=?", (amount * factor, wallet_id))
    elif tx_type == "expense":
        cur.execute("UPDATE wallets SET balance = balance - ? WHERE id=?", (amount * factor, wallet_id))
    elif tx_type == "transfer":
        cur.execute("UPDATE wallets SET balance = balance - ? WHERE id=?", (amount * factor, wallet_id))
        if target_wallet_id:
            cur.execute("UPDATE wallets SET balance = balance + ? WHERE id=?", (amount * factor, target_wallet_id))


def delete_transaction(tx_id: int, uid: int):
    with closing(get_conn()) as conn:
        cur = conn.cursor()
        row = cur.execute(
            "SELECT wallet_id, target_wallet_id, type, amount FROM transactions WHERE id=? AND user_id=?",
            (tx_id, uid),
        ).fetchone()
        if not row:
            return False
        apply_wallet_impact(cur, row[0], row[1], row[2], row[3], mode="revert")
        cur.execute("DELETE FROM transactions WHERE id=? AND user_id=?", (tx_id, uid))
        conn.commit()
        return True


def update_transaction(tx_id: int, uid: int, wallet_id: int, category_id: int | None, tx_type: str, amount: float, tx_date, note: str, target_wallet_id: int | None = None):
    with closing(get_conn()) as conn:
        cur = conn.cursor()
        old = cur.execute(
            "SELECT wallet_id, target_wallet_id, type, amount FROM transactions WHERE id=? AND user_id=?",
            (tx_id, uid),
        ).fetchone()
        if not old:
            return False
        apply_wallet_impact(cur, old[0], old[1], old[2], old[3], mode="revert")
        cur.execute(
            """
            UPDATE transactions
            SET wallet_id=?, category_id=?, type=?, amount=?, date=?, note=?, target_wallet_id=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=? AND user_id=?
            """,
            (wallet_id, category_id, tx_type, amount, str(tx_date), note.strip(), target_wallet_id, tx_id, uid),
        )
        apply_wallet_impact(cur, wallet_id, target_wallet_id, tx_type, amount, mode="apply")
        conn.commit()
        return True


def approve_user(user_id: int):
    with closing(get_conn()) as conn:
        conn.execute("UPDATE users SET is_approved=1 WHERE id=?", (user_id,))
        conn.commit()


def reset_user_password(user_id: int, new_password: str):
    with closing(get_conn()) as conn:
        conn.execute("UPDATE users SET password=? WHERE id=?", (hash_pw(new_password), user_id))
        conn.commit()


def get_users_admin_view():
    return to_dataframe(
        "SELECT id, username, role, is_approved, created_at FROM users ORDER BY created_at DESC"
    )


# =========================================================
# BUSINESS METRICS
# =========================================================
def build_summary(uid: int):
    tx = get_transactions(uid)
    wallets = get_wallets(uid)
    current_month = month_label()
    month_df = tx[tx["month"] == current_month] if not tx.empty else pd.DataFrame()
    total_assets = wallets["balance"].sum() if not wallets.empty else 0.0
    month_income = month_df.loc[month_df["type"] == "income", "amount"].sum() if not month_df.empty else 0.0
    month_expense = month_df.loc[month_df["type"] == "expense", "amount"].sum() if not month_df.empty else 0.0
    budget = get_budget(uid, current_month)
    balance = month_income - month_expense
    return {
        "tx": tx,
        "wallets": wallets,
        "month_df": month_df,
        "total_assets": float(total_assets),
        "month_income": float(month_income),
        "month_expense": float(month_expense),
        "budget": float(budget),
        "balance": float(balance),
    }


def export_transactions_csv(df: pd.DataFrame):
    if df.empty:
        return b""
    export_df = df.copy()
    export_df["date"] = export_df["date"].astype(str)
    return export_df.to_csv(index=False).encode("utf-8-sig")


# =========================================================
# AUTH PAGE
# =========================================================
def render_auth_page():
    page_header(APP_TITLE, "Ứng dụng quản lý chi tiêu tối ưu cho điện thoại, tablet và desktop.")
    st.info("Tài khoản mẫu đã được tạo sẵn: **duc1 / 123456**")
    left, center, right = st.columns([1, 1.5, 1])
    with center:
        tab_login, tab_register = st.tabs(["🔐 Đăng nhập", "📝 Đăng ký"])
        with tab_login:
            with st.container(border=True):
                with st.form("login_form"):
                    username = st.text_input("Tên đăng nhập")
                    password = st.text_input("Mật khẩu", type="password")
                    submitted = st.form_submit_button("Vào hệ thống", type="primary", use_container_width=True)
                    if submitted:
                        user = auth_user(username, password)
                        if not user:
                            st.error("Sai tài khoản hoặc mật khẩu.")
                        elif user[3] == 0:
                            st.warning("Tài khoản chưa được duyệt.")
                        else:
                            st.session_state.logged_in = True
                            st.session_state.uid = user[0]
                            st.session_state.username = user[1]
                            st.session_state.role = user[2]
                            st.rerun()
        with tab_register:
            with st.container(border=True):
                with st.form("register_form"):
                    new_user = st.text_input("Tên đăng nhập mới")
                    new_password = st.text_input("Mật khẩu mới", type="password")
                    submitted = st.form_submit_button("Tạo tài khoản", use_container_width=True)
                    if submitted:
                        ok, msg = register_user(new_user, new_password)
                        if ok:
                            st.success(msg)
                        else:
                            st.error(msg)


# =========================================================
# PAGES
# =========================================================
def render_dashboard(uid: int):
    data = build_summary(uid)
    tx = data["tx"]
    wallets = data["wallets"]
    month_df = data["month_df"]
    page_header("🏠 Tổng quan tài chính", "Theo dõi tài sản, ngân sách và dòng tiền mỗi ngày.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng tài sản", money(data["total_assets"]))
    c2.metric("Thu nhập tháng", money(data["month_income"]))
    c3.metric("Chi tiêu tháng", money(data["month_expense"]))
    c4.metric("Chênh lệch tháng", money(data["balance"]))

    budget = data["budget"]
    spent = data["month_expense"]
    if budget > 0:
        ratio = min(spent / budget, 1.0)
        st.progress(ratio)
        remain = budget - spent
        if remain < 0:
            st.error(f"Bạn đã vượt ngân sách {money(abs(remain))}.")
        elif remain <= budget * 0.2:
            st.warning(f"Bạn còn {money(remain)} trước khi chạm ngưỡng ngân sách.")
        else:
            st.success(f"Ngân sách còn lại: {money(remain)}")
    else:
        st.info("Bạn chưa đặt ngân sách cho tháng hiện tại.")

    left, right = st.columns([1.1, 1.4])
    with left:
        st.markdown("### 💼 Ví hiện có")
        if wallets.empty:
            st.info("Chưa có ví.")
        else:
            for _, wallet in wallets.iterrows():
                icon = "🏦" if wallet["type"] == "bank" else "💵" if wallet["type"] == "cash" else "💳"
                st.markdown(
                    f"""
                    <div class="soft-card" style="margin-bottom: 10px;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div><strong>{icon} {wallet['name']}</strong><br><span style="color:#64748b; font-size: 13px;">{wallet['type']}</span></div>
                            <div style="font-weight:800; color:{PRIMARY};">{money(wallet['balance'])}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        if not month_df.empty:
            recent = month_df.head(5).copy()
            recent["display"] = recent.apply(
                lambda r: (
                    f"🔴 -{money(r['amount'])}" if r["type"] == "expense" else
                    f"🟢 +{money(r['amount'])}" if r["type"] == "income" else
                    f"🔄 {money(r['amount'])}"
                ),
                axis=1,
            )
            st.markdown("### 🕒 Gần đây")
            st.dataframe(
                recent[["date", "wallet_name", "category_name", "display", "note"]].rename(
                    columns={
                        "date": "Ngày",
                        "wallet_name": "Ví",
                        "category_name": "Danh mục",
                        "display": "Số tiền",
                        "note": "Ghi chú",
                    }
                ),
                hide_index=True,
                use_container_width=True,
            )

    with right:
        st.markdown("### 📊 Cơ cấu chi tiêu tháng")
        exp_df = month_df[month_df["type"] == "expense"] if not month_df.empty else pd.DataFrame()
        if not exp_df.empty:
            pie_df = exp_df.groupby("category_name", dropna=False)["amount"].sum().reset_index()
            fig = px.pie(
                pie_df,
                values="amount",
                names="category_name",
                hole=0.58,
                color_discrete_sequence=px.colors.sequential.Tealgrn,
            )
            fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Chưa có dữ liệu chi tiêu trong tháng.")

        st.markdown("### 📈 Dòng tiền 14 ngày gần nhất")
        if not tx.empty:
            flow_df = tx[tx["type"].isin(["income", "expense"])].copy()
            flow_df = flow_df[flow_df["date"] >= (pd.Timestamp.today().normalize() - pd.Timedelta(days=14))]
            if not flow_df.empty:
                daily = flow_df.groupby(["date", "type"])["amount"].sum().reset_index()
                daily.loc[daily["type"] == "expense", "amount"] *= -1
                fig2 = px.bar(
                    daily,
                    x="date",
                    y="amount",
                    color="type",
                    color_discrete_map={"income": SUCCESS, "expense": DANGER},
                )
                fig2.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Chưa có dữ liệu 14 ngày gần nhất.")


def render_transactions(uid: int):
    page_header("📝 Giao dịch", "Thêm, sửa, xóa và theo dõi toàn bộ lịch sử thu chi.")
    wallets_df = get_wallets(uid)
    if wallets_df.empty:
        st.error("Bạn cần tạo ít nhất một ví trước khi ghi giao dịch.")
        return
    wallet_map = {row["name"]: int(row["id"]) for _, row in wallets_df.iterrows()}

    tab_expense, tab_income, tab_transfer, tab_edit = st.tabs([
        "💸 Chi tiêu", "💰 Thu nhập", "🔄 Chuyển khoản", "✏️ Sửa giao dịch"
    ])

    with tab_expense:
        cats = get_categories(uid, "expense")
        cat_map = {f"{r['icon']} {r['name']}": int(r['id']) for _, r in cats.iterrows()}
        with st.form("add_expense_form", clear_on_submit=True):
            a, b = st.columns(2)
            amount = a.number_input("Số tiền", min_value=0.0, step=10000.0)
            category_label = b.selectbox("Danh mục", list(cat_map.keys()))
            c1, c2, c3 = st.columns([1.2, 1.8, 1])
            wallet_name = c1.selectbox("Chi từ ví", list(wallet_map.keys()), key="expense_wallet")
            note = c2.text_input("Ghi chú")
            tx_date = c3.date_input("Ngày", value=date.today(), key="expense_date")
            submitted = st.form_submit_button("Lưu khoản chi", type="primary", use_container_width=True)
            if submitted:
                if amount <= 0:
                    st.warning("Số tiền phải lớn hơn 0.")
                else:
                    create_transaction(uid, wallet_map[wallet_name], cat_map[category_label], "expense", amount, tx_date, note)
                    st.success("Đã lưu khoản chi.")
                    st.rerun()

    with tab_income:
        cats = get_categories(uid, "income")
        cat_map = {f"{r['icon']} {r['name']}": int(r['id']) for _, r in cats.iterrows()}
        with st.form("add_income_form", clear_on_submit=True):
            a, b = st.columns(2)
            amount = a.number_input("Số tiền", min_value=0.0, step=100000.0, key="income_amount")
            category_label = b.selectbox("Nguồn thu", list(cat_map.keys()))
            c1, c2, c3 = st.columns([1.2, 1.8, 1])
            wallet_name = c1.selectbox("Vào ví", list(wallet_map.keys()), key="income_wallet")
            note = c2.text_input("Ghi chú", key="income_note")
            tx_date = c3.date_input("Ngày", value=date.today(), key="income_date")
            submitted = st.form_submit_button("Lưu thu nhập", type="primary", use_container_width=True)
            if submitted:
                if amount <= 0:
                    st.warning("Số tiền phải lớn hơn 0.")
                else:
                    create_transaction(uid, wallet_map[wallet_name], cat_map[category_label], "income", amount, tx_date, note)
                    st.success("Đã lưu thu nhập.")
                    st.rerun()

    with tab_transfer:
        with st.form("transfer_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            amount = c1.number_input("Số tiền", min_value=0.0, step=50000.0, key="transfer_amount")
            from_wallet = c2.selectbox("Từ ví", list(wallet_map.keys()), key="from_wallet")
            to_wallet = c3.selectbox("Đến ví", list(wallet_map.keys()), key="to_wallet")
            d1, d2 = st.columns([2, 1])
            note = d1.text_input("Nội dung", key="transfer_note")
            tx_date = d2.date_input("Ngày", value=date.today(), key="transfer_date")
            submitted = st.form_submit_button("Thực hiện chuyển khoản", type="primary", use_container_width=True)
            if submitted:
                if amount <= 0:
                    st.warning("Số tiền phải lớn hơn 0.")
                elif from_wallet == to_wallet:
                    st.error("Ví nguồn và ví đích phải khác nhau.")
                else:
                    create_transaction(
                        uid,
                        wallet_map[from_wallet],
                        None,
                        "transfer",
                        amount,
                        tx_date,
                        note,
                        target_wallet_id=wallet_map[to_wallet],
                    )
                    st.success("Đã chuyển khoản.")
                    st.rerun()

    tx_df = get_transactions(uid)
    if tx_df.empty:
        st.info("Chưa có giao dịch nào.")
        return

    st.markdown("### 📒 Nhật ký giao dịch")
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    month_options = ["Tất cả"] + sorted(tx_df["month"].unique().tolist(), reverse=True)
    selected_month = filter_col1.selectbox("Lọc theo tháng", month_options)
    selected_type = filter_col2.selectbox("Lọc theo loại", ["Tất cả", "expense", "income", "transfer"])
    keyword = filter_col3.text_input("Tìm ghi chú / danh mục")

    view_df = tx_df.copy()
    if selected_month != "Tất cả":
        view_df = view_df[view_df["month"] == selected_month]
    if selected_type != "Tất cả":
        view_df = view_df[view_df["type"] == selected_type]
    if keyword.strip():
        mask = (
            view_df["note"].fillna("").str.contains(keyword, case=False)
            | view_df["category_name"].fillna("").str.contains(keyword, case=False)
            | view_df["wallet_name"].fillna("").str.contains(keyword, case=False)
        )
        view_df = view_df[mask]

    view_df["Hiển thị"] = view_df.apply(
        lambda r: (
            f"🔴 -{money(r['amount'])}" if r["type"] == "expense" else
            f"🟢 +{money(r['amount'])}" if r["type"] == "income" else
            f"🔄 {money(r['amount'])}"
        ),
        axis=1,
    )
    view_df["Danh mục"] = view_df.apply(
        lambda r: r["category_name"] if pd.notna(r["category_name"]) else (f"{r['wallet_name']} → {r['target_wallet_name']}" if r["type"] == "transfer" else "-"),
        axis=1,
    )
    st.dataframe(
        view_df[["id", "date", "wallet_name", "Danh mục", "Hiển thị", "note", "type"]].rename(
            columns={
                "id": "ID",
                "date": "Ngày",
                "wallet_name": "Ví",
                "note": "Ghi chú",
                "type": "Loại",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    csv_data = export_transactions_csv(view_df)
    if csv_data:
        st.download_button(
            "⬇️ Tải CSV giao dịch",
            data=csv_data,
            file_name=f"transactions_{uid}.csv",
            mime="text/csv",
            use_container_width=False,
        )

    with tab_edit:
        editable_ids = tx_df["id"].tolist()
        edit_id = st.selectbox("Chọn ID cần sửa", editable_ids)
        selected = tx_df[tx_df["id"] == edit_id].iloc[0]
        tx_type = st.selectbox("Loại", ["expense", "income", "transfer"], index=["expense", "income", "transfer"].index(selected["type"]), key="edit_type")
        amount = st.number_input("Số tiền", min_value=0.0, value=float(selected["amount"]), step=10000.0, key="edit_amount")
        tx_date = st.date_input("Ngày", value=selected["date"].date(), key="edit_date")
        note = st.text_input("Ghi chú", value=selected["note"] or "", key="edit_note")
        wallet_name = st.selectbox(
            "Ví chính",
            list(wallet_map.keys()),
            index=list(wallet_map.values()).index(int(selected["wallet_id"])),
            key="edit_wallet",
        )

        category_id = None
        target_wallet_id = None
        if tx_type in ["expense", "income"]:
            cats = get_categories(uid, tx_type)
            cat_map = {f"{r['icon']} {r['name']}": int(r['id']) for _, r in cats.iterrows()}
            cat_values = list(cat_map.values())
            current_cat_index = cat_values.index(int(selected["category_id"])) if pd.notna(selected["category_id"]) and int(selected["category_id"]) in cat_values else 0
            category_label = st.selectbox("Danh mục", list(cat_map.keys()), index=current_cat_index, key="edit_category")
            category_id = cat_map[category_label]
        else:
            target_wallet_name = selected["target_wallet_name"] if pd.notna(selected["target_wallet_name"]) else list(wallet_map.keys())[0]
            target_wallet_label = st.selectbox(
                "Ví nhận",
                list(wallet_map.keys()),
                index=list(wallet_map.keys()).index(target_wallet_name) if target_wallet_name in list(wallet_map.keys()) else 0,
                key="edit_target_wallet",
            )
            target_wallet_id = wallet_map[target_wallet_label]

        e1, e2 = st.columns(2)
        if e1.button("💾 Cập nhật giao dịch", type="primary", use_container_width=True):
            if tx_type == "transfer" and wallet_map[wallet_name] == target_wallet_id:
                st.error("Ví nguồn và ví nhận phải khác nhau.")
            elif amount <= 0:
                st.warning("Số tiền phải lớn hơn 0.")
            else:
                update_transaction(
                    edit_id,
                    uid,
                    wallet_map[wallet_name],
                    category_id,
                    tx_type,
                    amount,
                    tx_date,
                    note,
                    target_wallet_id,
                )
                st.success("Đã cập nhật giao dịch.")
                st.rerun()
        if e2.button("🗑️ Xóa giao dịch", use_container_width=True):
            if delete_transaction(edit_id, uid):
                st.success("Đã xóa giao dịch và hoàn tác số dư ví.")
                st.rerun()
            else:
                st.error("Không tìm thấy giao dịch.")


def render_wallets_goals(uid: int):
    page_header("💼 Ví & quỹ", "Quản lý tài khoản tiền và mục tiêu tiết kiệm dài hạn.")
    tab_wallets, tab_goals = st.tabs(["🏦 Ví tiền", "🎯 Mục tiêu tiết kiệm"])

    with tab_wallets:
        with st.form("add_wallet_form"):
            c1, c2, c3 = st.columns([2, 1.2, 1])
            name = c1.text_input("Tên ví")
            balance = c2.number_input("Số dư ban đầu", min_value=0.0, step=100000.0)
            wallet_type = c3.selectbox("Loại", ["bank", "cash", "credit"])
            submitted = st.form_submit_button("Tạo ví", type="primary", use_container_width=True)
            if submitted:
                if not name.strip():
                    st.warning("Tên ví không được để trống.")
                else:
                    add_wallet(uid, name, balance, wallet_type)
                    st.success("Đã tạo ví mới.")
                    st.rerun()

        wallets = get_wallets(uid)
        if wallets.empty:
            st.info("Chưa có ví.")
        else:
            display = wallets[["name", "balance", "type", "is_default"]].copy()
            display["balance"] = display["balance"].map(money)
            display["is_default"] = display["is_default"].map(lambda x: "Mặc định" if x else "")
            st.dataframe(
                display.rename(columns={"name": "Tên ví", "balance": "Số dư", "type": "Loại", "is_default": "Ghi chú"}),
                use_container_width=True,
                hide_index=True,
            )

    with tab_goals:
        with st.form("goal_form"):
            c1, c2, c3 = st.columns([2, 1.2, 1.2])
            goal_name = c1.text_input("Tên mục tiêu")
            target_amount = c2.number_input("Mục tiêu số tiền", min_value=0.0, step=500000.0)
            deadline = c3.date_input("Hạn chót", value=date.today())
            submitted = st.form_submit_button("Tạo mục tiêu", type="primary", use_container_width=True)
            if submitted:
                if not goal_name.strip() or target_amount <= 0:
                    st.warning("Nhập tên và mục tiêu hợp lệ.")
                else:
                    add_goal(uid, goal_name, target_amount, deadline)
                    st.success("Đã tạo mục tiêu.")
                    st.rerun()

        goals = get_goals(uid)
        if goals.empty:
            st.info("Chưa có mục tiêu tiết kiệm.")
        else:
            for _, goal in goals.iterrows():
                pct = min(goal["current_amount"] / goal["target_amount"], 1.0) if goal["target_amount"] > 0 else 0
                icon = "✅" if goal["status"] == "completed" else "🎯"
                st.markdown(f"### {icon} {goal['name']}")
                st.progress(pct)
                st.caption(f"Đã có {money(goal['current_amount'])} / {money(goal['target_amount'])} · Hạn: {goal['deadline']}")
                with st.expander(f"Nạp tiền vào quỹ: {goal['name']}"):
                    amount = st.number_input(
                        "Số tiền nạp",
                        min_value=0.0,
                        step=50000.0,
                        key=f"goal_fund_{goal['id']}",
                    )
                    if st.button("Nạp tiền", key=f"goal_btn_{goal['id']}", type="primary"):
                        if amount > 0:
                            fund_goal(int(goal["id"]), amount)
                            st.success("Đã cập nhật quỹ.")
                            st.rerun()


def render_analytics(uid: int):
    page_header("📈 Phân tích", "Xem xu hướng chi tiêu và hiệu quả quản lý tài chính.")
    df = get_transactions(uid)
    if df.empty:
        st.info("Chưa có dữ liệu để phân tích.")
        return

    month_options = ["Tất cả"] + sorted(df["month"].unique().tolist(), reverse=True)
    selected_month = st.selectbox("Chọn tháng", month_options)
    plot_df = df if selected_month == "Tất cả" else df[df["month"] == selected_month]
    if plot_df.empty:
        st.warning("Không có giao dịch ở bộ lọc hiện tại.")
        return

    expense_df = plot_df[plot_df["type"] == "expense"]
    income_df = plot_df[plot_df["type"] == "income"]
    total_income = income_df["amount"].sum()
    total_expense = expense_df["amount"].sum()
    net = total_income - total_expense

    c1, c2, c3 = st.columns(3)
    c1.metric("Tổng thu", money(total_income))
    c2.metric("Tổng chi", money(total_expense))
    c3.metric("Lãi / lỗ", money(net), delta_color="normal" if net >= 0 else "inverse")

    left, right = st.columns(2)
    with left:
        st.markdown("### Cấu trúc chi tiêu")
        if not expense_df.empty:
            pie = px.pie(
                expense_df.groupby("category_name", dropna=False)["amount"].sum().reset_index(),
                values="amount",
                names="category_name",
                hole=0.5,
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            pie.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(pie, use_container_width=True)
        else:
            st.info("Không có chi tiêu ở kỳ này.")

    with right:
        st.markdown("### Cấu trúc thu nhập")
        if not income_df.empty:
            pie = px.pie(
                income_df.groupby("category_name", dropna=False)["amount"].sum().reset_index(),
                values="amount",
                names="category_name",
                hole=0.5,
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            pie.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(pie, use_container_width=True)
        else:
            st.info("Không có thu nhập ở kỳ này.")

    st.markdown("### Dòng tiền theo ngày")
    flow_df = plot_df[plot_df["type"].isin(["income", "expense"])].copy()
    grouped = flow_df.groupby(["date", "type"])["amount"].sum().reset_index()
    grouped.loc[grouped["type"] == "expense", "amount"] *= -1
    fig = px.bar(
        grouped,
        x="date",
        y="amount",
        color="type",
        color_discrete_map={"income": SUCCESS, "expense": DANGER},
    )
    fig.update_layout(height=360)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Xu hướng tích lũy")
    line_df = flow_df.copy()
    line_df["signed_amount"] = line_df.apply(lambda r: r["amount"] if r["type"] == "income" else -r["amount"], axis=1)
    trend = line_df.groupby("date")["signed_amount"].sum().sort_index().cumsum().reset_index()
    line = go.Figure()
    line.add_trace(go.Scatter(x=trend["date"], y=trend["signed_amount"], mode="lines+markers", line=dict(color=PRIMARY, width=3)))
    line.update_layout(height=340, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(line, use_container_width=True)


def render_settings(uid: int, role: str):
    page_header("⚙️ Cài đặt", "Tùy chỉnh ngân sách, danh mục và quản trị người dùng.")

    with st.container(border=True):
        st.markdown("### 💰 Ngân sách tháng")
        current_month = month_label()
        current_budget = get_budget(uid, current_month)
        c1, c2 = st.columns([3, 1])
        new_budget = c1.number_input(f"Ngân sách tháng {current_month}", value=current_budget, min_value=0.0, step=500000.0)
        if c2.button("Lưu ngân sách", type="primary", use_container_width=True):
            update_budget(uid, current_month, new_budget)
            st.success("Đã cập nhật ngân sách.")

    st.markdown("---")
    st.markdown("### 🗂️ Danh mục cá nhân")
    cat_tab1, cat_tab2 = st.tabs(["Chi tiêu", "Thu nhập"])
    with cat_tab1:
        with st.form("add_exp_category"):
            c1, c2 = st.columns([3, 1])
            name = c1.text_input("Tên danh mục chi")
            icon = c2.text_input("Emoji", value="🏷️")
            if st.form_submit_button("Thêm danh mục", type="primary"):
                if name.strip():
                    try:
                        add_category(uid, name, "expense", icon)
                        st.success("Đã thêm danh mục chi tiêu.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Danh mục đã tồn tại.")
        cats = get_categories(uid, "expense")
        st.write(" ".join([f"`{r['icon']} {r['name']}`" for _, r in cats.iterrows()]))

    with cat_tab2:
        with st.form("add_inc_category"):
            c1, c2 = st.columns([3, 1])
            name = c1.text_input("Tên danh mục thu")
            icon = c2.text_input("Emoji", value="💵")
            if st.form_submit_button("Thêm danh mục", type="primary"):
                if name.strip():
                    try:
                        add_category(uid, name, "income", icon)
                        st.success("Đã thêm danh mục thu nhập.")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Danh mục đã tồn tại.")
        cats = get_categories(uid, "income")
        st.write(" ".join([f"`{r['icon']} {r['name']}`" for _, r in cats.iterrows()]))

    st.markdown("---")
    st.markdown("### 🔐 Tài khoản")
    with st.expander("Đổi mật khẩu tài khoản hiện tại"):
        with st.form("change_my_password"):
            new_password = st.text_input("Mật khẩu mới", type="password")
            if st.form_submit_button("Đổi mật khẩu", type="primary"):
                if len(new_password) < 6:
                    st.warning("Mật khẩu tối thiểu 6 ký tự.")
                else:
                    reset_user_password(uid, new_password)
                    st.success("Đã đổi mật khẩu.")

    if role == "admin":
        st.markdown("---")
        st.markdown("### 🛡️ Quản trị hệ thống")
        users_df = get_users_admin_view()
        st.dataframe(users_df, use_container_width=True, hide_index=True)
        user_ids = users_df["id"].tolist()
        if user_ids:
            c1, c2 = st.columns(2)
            with c1:
                selected_user = st.selectbox("Chọn user để duyệt", user_ids, format_func=lambda x: f"ID {x} - {users_df[users_df['id']==x].iloc[0]['username']}")
                if st.button("Duyệt tài khoản", type="primary", use_container_width=True):
                    approve_user(int(selected_user))
                    st.success("Đã duyệt tài khoản.")
                    st.rerun()
            with c2:
                selected_reset = st.selectbox("Chọn user để reset mật khẩu", user_ids, format_func=lambda x: f"ID {x} - {users_df[users_df['id']==x].iloc[0]['username']}", key="reset_user_select")
                admin_new_pw = st.text_input("Mật khẩu mới cho user", type="password", key="admin_new_pw")
                if st.button("Reset mật khẩu", use_container_width=True):
                    if len(admin_new_pw) < 6:
                        st.warning("Mật khẩu tối thiểu 6 ký tự.")
                    else:
                        reset_user_password(int(selected_reset), admin_new_pw)
                        st.success("Đã reset mật khẩu user.")


def render_quick_add(uid: int):
    with st.popover("quick_add_hidden"):
        st.markdown("### ⚡ Ghi nhanh")
        wallets = get_wallets(uid)
        cats = get_categories(uid, "expense")
        if wallets.empty or cats.empty:
            st.warning("Cần có ví và danh mục để ghi nhanh.")
            return
        default_wallet_id = int(wallets.iloc[0]["id"])
        cat_labels = [f"{r['icon']} {r['name']}" for _, r in cats.iterrows()]
        cat_ids = [int(r['id']) for _, r in cats.iterrows()]
        with st.form("quick_add_form", clear_on_submit=True):
            amount = st.number_input("Số tiền", min_value=0.0, step=10000.0)
            idx = st.selectbox("Danh mục", options=list(range(len(cat_labels))), format_func=lambda x: cat_labels[x])
            note = st.text_input("Ghi chú")
            if st.form_submit_button("Lưu ngay", type="primary", use_container_width=True):
                if amount <= 0:
                    st.warning("Số tiền phải lớn hơn 0.")
                else:
                    create_transaction(uid, default_wallet_id, cat_ids[idx], "expense", amount, date.today(), note)
                    st.success("Đã ghi nhanh khoản chi.")
                    st.rerun()


# =========================================================
# MAIN
# =========================================================
def main():
    ensure_session_state()
    init_db()
    inject_css()

    if not st.session_state.logged_in:
        render_auth_page()
        return

    uid = st.session_state.uid
    username = st.session_state.username
    role = st.session_state.role

    with st.sidebar:
        st.markdown(f"## {APP_TITLE}")
        st.caption(f"Xin chào, {username}")
        st.markdown('<span class="chip">Mobile Friendly</span><span class="chip">SQLite Offline</span>', unsafe_allow_html=True)
        menu = st.radio(
            "Điều hướng",
            ["🏠 Tổng quan", "📝 Giao dịch", "💼 Ví & quỹ", "📈 Phân tích", "⚙️ Cài đặt"],
            label_visibility="collapsed",
        )
        st.markdown("---")
        st.caption("Tài khoản mẫu: duc1 / 123456")
        if st.button("🚪 Đăng xuất", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    if menu == "🏠 Tổng quan":
        render_dashboard(uid)
    elif menu == "📝 Giao dịch":
        render_transactions(uid)
    elif menu == "💼 Ví & quỹ":
        render_wallets_goals(uid)
    elif menu == "📈 Phân tích":
        render_analytics(uid)
    elif menu == "⚙️ Cài đặt":
        render_settings(uid, role)

    render_quick_add(uid)


if __name__ == "__main__":
    main()
