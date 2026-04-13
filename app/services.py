import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import User, Wallet, Category, Transaction, Budget, Goal
from app.utils import hash_password, verify_password

DEFAULT_CATEGORIES = [
    ("Ăn uống", "expense", "🍜"), ("Tiền nhà / Điện nước", "expense", "🏠"),
    ("Di chuyển / Xăng xe", "expense", "⛽"), ("Mua sắm", "expense", "🛍️"),
    ("Lương", "income", "💰"), ("Thưởng", "income", "🎁"), ("Kinh doanh", "income", "🏪")
]

# --- AUTH SERVICES ---
def authenticate_user(db: Session, username: str, password: str):
    user = db.query(User).filter(User.username == username).first()
    if user and verify_password(password, user.password_hash):
        return user
    return None

def register_user(db: Session, username: str, password: str) -> tuple[bool, str]:
    if db.query(User).filter(User.username == username).first():
        return False, "Tên đăng nhập đã tồn tại."
    
    new_user = User(username=username, password_hash=hash_password(password))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Seed dữ liệu mặc định
    seed_user_data(db, new_user.id)
    return True, "Tạo tài khoản thành công."

def seed_user_data(db: Session, user_id: int):
    for name, c_type, icon in DEFAULT_CATEGORIES:
        db.add(Category(user_id=user_id, name=name, type=c_type, icon=icon))
    db.add(Wallet(user_id=user_id, name="Tiền mặt", balance=0.0, type="cash", is_default=1))
    db.add(Wallet(user_id=user_id, name="Tài khoản ngân hàng", balance=0.0, type="bank", is_default=0))
    db.commit()

# --- DATA SERVICES ---
def get_wallets(db: Session, user_id: int):
    return db.query(Wallet).filter(Wallet.user_id == user_id).order_by(Wallet.is_default.desc(), Wallet.id).all()

def get_categories(db: Session, user_id: int, cat_type: str = None):
    query = db.query(Category).filter(Category.user_id == user_id)
    if cat_type:
        query = query.filter(Category.type == cat_type)
    return query.order_by(Category.name).all()

def get_budget(db: Session, user_id: int, month: str) -> float:
    budget = db.query(Budget).filter(Budget.user_id == user_id, Budget.month == month).first()
    return budget.amount if budget else 0.0

def update_budget(db: Session, user_id: int, month: str, amount: float):
    budget = db.query(Budget).filter(Budget.user_id == user_id, Budget.month == month).first()
    if budget:
        budget.amount = amount
    else:
        db.add(Budget(user_id=user_id, month=month, amount=amount))
    db.commit()

# --- TRANSACTION CORE ---
def create_transaction(db: Session, user_id: int, wallet_id: int, category_id: int, tx_type: str, amount: float, tx_date, note: str, target_wallet_id: int = None):
    try:
        tx = Transaction(
            user_id=user_id, wallet_id=wallet_id, category_id=category_id,
            type=tx_type, amount=amount, date=tx_date, note=note, target_wallet_id=target_wallet_id
        )
        db.add(tx)
        
        # Cập nhật số dư ví
        wallet = db.query(Wallet).filter(Wallet.id == wallet_id).first()
        if tx_type == "income":
            wallet.balance += amount
        elif tx_type == "expense":
            wallet.balance -= amount
        elif tx_type == "transfer":
            wallet.balance -= amount
            target_wallet = db.query(Wallet).filter(Wallet.id == target_wallet_id).first()
            target_wallet.balance += amount
            
        db.commit()
    except Exception as e:
        db.rollback()
        raise e

def delete_transaction(db: Session, user_id: int, tx_id: int) -> bool:
    tx = db.query(Transaction).filter(Transaction.id == tx_id, Transaction.user_id == user_id).first()
    if not tx:
        return False
    
    # Hoàn tác số dư
    wallet = db.query(Wallet).filter(Wallet.id == tx.wallet_id).first()
    if tx.type == "income":
        wallet.balance -= tx.amount
    elif tx.type == "expense":
        wallet.balance += tx.amount
    elif tx.type == "transfer":
        wallet.balance += tx.amount
        target_wallet = db.query(Wallet).filter(Wallet.id == tx.target_wallet_id).first()
        target_wallet.balance -= tx.amount
        
    db.delete(tx)
    db.commit()
    return True

# --- DATAFRAME QUERIES (Tối ưu cho Streamlit/Plotly) ---
def get_transactions_df(db: Session, user_id: int) -> pd.DataFrame:
    sql_query = f"""
        SELECT 
            t.id, t.type, t.amount, t.date, t.note,
            w.name AS wallet_name,
            tw.name AS target_wallet_name,
            c.name AS category_name, c.icon AS category_icon,
            TO_CHAR(t.date, 'YYYY-MM') as month
        FROM transactions t
        LEFT JOIN wallets w ON t.wallet_id = w.id
        LEFT JOIN wallets tw ON t.target_wallet_id = tw.id
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = {user_id}
        ORDER BY t.date DESC, t.id DESC
    """
    df = pd.read_sql_query(sql_query, db.bind)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df

def get_goals(db: Session, user_id: int):
    return db.query(Goal).filter(Goal.user_id == user_id).order_by(Goal.status, Goal.deadline).all()

def add_wallet(db: Session, user_id: int, name: str, balance: float, wallet_type: str):
    db.add(Wallet(user_id=user_id, name=name, balance=balance, type=wallet_type))
    db.commit()

def fund_goal(db: Session, goal_id: int, amount: float):
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if goal:
        goal.current_amount += amount
        if goal.current_amount >= goal.target_amount:
            goal.status = "completed"
        db.commit()
