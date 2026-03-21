"""
開発用シードデータ
管理者ユーザーとサンプル商品を作成する
"""
from app.database import SessionLocal, engine, Base
from app.models import User, Product, UserRole
from app.auth import hash_password

Base.metadata.create_all(bind=engine)

db = SessionLocal()

# 管理者ユーザー
admin = db.query(User).filter(User.email == "admin@example.com").first()
if not admin:
    admin = User(
        email="admin@example.com",
        username="admin",
        hashed_password=hash_password("admin123"),
        role=UserRole.ADMIN,
    )
    db.add(admin)
    print("管理者ユーザーを作成しました: admin@example.com / admin123")

# 一般ユーザー
user = db.query(User).filter(User.email == "user@example.com").first()
if not user:
    user = User(
        email="user@example.com",
        username="testuser",
        hashed_password=hash_password("user123"),
    )
    db.add(user)
    print("一般ユーザーを作成しました: user@example.com / user123")

# サンプル商品
products = [
    {"name": "ノートパソコン", "description": "高性能 15インチ ノートPC", "price": 98000, "stock": 10},
    {"name": "ワイヤレスマウス", "description": "人間工学デザイン Bluetooth マウス", "price": 3500, "stock": 50},
    {"name": "USBハブ", "description": "7ポート USB-C ハブ", "price": 4200, "stock": 30},
    {"name": "モニター", "description": "27インチ 4K ディスプレイ", "price": 45000, "stock": 5},
    {"name": "キーボード", "description": "メカニカル テンキーレス キーボード", "price": 12000, "stock": 20},
]

for p in products:
    if not db.query(Product).filter(Product.name == p["name"]).first():
        db.add(Product(**p))
        print(f"商品を追加しました: {p['name']}")

db.commit()
db.close()
print("シードデータの投入が完了しました")
