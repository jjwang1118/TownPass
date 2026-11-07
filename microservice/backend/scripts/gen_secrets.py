"""產生部署用的環境變數檔 .env.cloud（含 3 組新金鑰），金鑰不會印在畫面上。Windows、Mac 都可以執行：

    uv run python -m scripts.gen_secrets

產生後打開 .env.cloud，填入 DATABASE_URL（Neon）與 FRONTEND_BASE_URL，再整份貼到 Render 的
Environment →「Add from .env」。.env.cloud 已設定不會被 commit、不會打包進映像檔。

FIELD_ENCRYPTION_KEY 一旦開始存資料就不能更換，遺失就無法解開已加密的個資，請另外妥善保存。
已經有 .env.cloud 時不會覆蓋，避免不小心換掉金鑰。
"""

import secrets
import sys
from pathlib import Path

from cryptography.fernet import Fernet

TARGET = Path(".env.cloud")

TEMPLATE = """# 部署用環境變數（不可 commit）。說明見 microservice/docs/deploy.md
# Neon 的連線字串直接貼上（postgresql://…?sslmode=require）
DATABASE_URL=

JWT_SECRET={jwt}
# 開始存資料後不可更換、不可遺失，請另外存到密碼管理工具
FIELD_ENCRYPTION_KEY={fernet}
INTERNAL_SECRET={internal}

# 前端（Firebase Hosting）網址，例如 https://xxx.web.app，結尾不加 /
FRONTEND_BASE_URL=
# 前端在本機開發時也要連這個後端就填 http://localhost:5173，否則留空
EXTRA_CORS_ORIGINS=http://localhost:5173

# Firebase 服務帳戶金鑰（JSON 內容或檔案路徑）；留空時推播只寫在 log
FIREBASE_CREDENTIALS=
REMIND_INTERVAL_MINUTES=10
# 比賽 Demo 期間開啟，才能用 /demo/trigger/*
DEMO_MODE=true
"""


def main() -> None:
    if TARGET.exists():
        sys.exit(f"{TARGET} 已經存在，為了不換掉金鑰所以不覆蓋。真的要重新產生，請先自行刪除。")
    TARGET.write_text(
        TEMPLATE.format(
            jwt=secrets.token_urlsafe(48),
            fernet=Fernet.generate_key().decode(),
            internal=secrets.token_urlsafe(32),
        ),
        encoding="utf-8",
    )
    print(f"已產生 {TARGET.resolve()}")
    print("請打開它填入 DATABASE_URL 與 FRONTEND_BASE_URL。")


if __name__ == "__main__":
    main()
