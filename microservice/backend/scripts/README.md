# scripts/

開發與部署用的小工具，Windows、Mac 都可以執行。

| 檔案 | 指令 | 用途 |
|---|---|---|
| `gen_secrets.py` | `uv run python -m scripts.gen_secrets` | 產生部署用的 `.env.cloud`，含新的 `JWT_SECRET`、`FIELD_ENCRYPTION_KEY`、`INTERNAL_SECRET`（不印在畫面上；已存在時不覆蓋） |

`FIELD_ENCRYPTION_KEY` 開始存資料後就不能更換，遺失就解不開已加密的個資，請另外妥善保存。部署步驟見 [../../docs/deploy.md](../../docs/deploy.md)。
