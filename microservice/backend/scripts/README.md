# scripts/

小工具，Windows、Mac 都可以執行。

| 檔案 | 指令 | 用途 |
|---|---|---|
| `init_env.py` | `uv run python -m scripts.init_env` | 從 `.env.example` 建立 `.env`，並產生新的 `JWT_SECRET`、`FIELD_ENCRYPTION_KEY`、`INTERNAL_SECRET`。已經有 `.env` 時不修改既有的值，只補上新增的設定 |

`FIELD_ENCRYPTION_KEY` 開始存資料後就不能更換，遺失就解不開已加密的個資。換電腦 Demo 時要把 `.env` 一起帶過去。部署步驟見 [../../docs/deploy.md](../../docs/deploy.md)。
