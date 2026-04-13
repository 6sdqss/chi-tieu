import bcrypt
from datetime import datetime

def hash_password(password: str) -> str:
    """Mã hóa mật khẩu bằng bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Kiểm tra mật khẩu khớp với mã băm."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def format_vnd(amount: float) -> str:
    """Định dạng số tiền theo chuẩn VNĐ."""
    return f"{amount:,.0f} ₫".replace(",", ".")

def get_current_month() -> str:
    """Lấy tháng hiện tại định dạng YYYY-MM."""
    return datetime.now().strftime("%Y-%m")
