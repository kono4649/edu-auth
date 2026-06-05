"""開発用シードデータ。"""

import uuid

from app.database import SessionLocal, engine, Base
from app.models import User, Product, UserRole

ADMIN_USER_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
SAMPLE_USER_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")

Base.metadata.create_all(bind=engine)

db = SessionLocal()

# 管理者ユーザー
admin = db.query(User).filter(User.email == "admin@example.com").first()
if not admin:
    admin = User(
        id=ADMIN_USER_ID,
        email="admin@example.com",
        username="admin",
        role=UserRole.ADMIN,
    )
    db.add(admin)
    print("管理者ユーザーを作成しました: admin@example.com")

# 一般ユーザー
user = db.query(User).filter(User.email == "user@example.com").first()
if not user:
    user = User(
        id=SAMPLE_USER_ID,
        email="user@example.com",
        username="testuser",
    )
    db.add(user)
    print("一般ユーザーを作成しました: user@example.com")

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
