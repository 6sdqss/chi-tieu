import os

# Cấu hình UI
APP_TITLE = "💎 FinPro Mobile"
PRIMARY_COLOR = "#0f766e"
ACCENT_COLOR = "#14b8a6"
DANGER_COLOR = "#ef4444"
WARNING_COLOR = "#f59e0b"
SUCCESS_COLOR = "#10b981"

# Cấu hình Database
# Ví dụ: postgresql://postgres:password@localhost:5432/finpro
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:postgres@localhost:5432/finpro_db"
)

# Fix cho các platform host DB sử dụng 'postgres://' cũ (như Heroku)
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
