# alembic/

資料表變更（migration）。資料表定義在各模組的 `models.py`，Alembic 比對後產生變更檔。

| 路徑 | 內容 |
|---|---|
| `env.py` | 從 `DATABASE_URL` 連線，讀 `app/models.py` 取得全部資料表 |
| `script.py.mako` | 產生 migration 檔的範本 |
| [versions/](versions/) | 每次變更一個檔案 |

## 常用指令

在 `microservice/backend` 執行：

```bash
uv run alembic upgrade head                            # 套用到最新
uv run alembic revision --autogenerate -m "說明"       # 修改 models.py 後產生變更檔
uv run alembic downgrade -1                            # 退回上一版
uv run alembic current                                 # 目前版本
```

## 規則

- 自動產生的檔案**一定要看過再 commit**。部分唯一索引、資料轉換等，Alembic 不一定判斷得正確。
- 已經 commit 或部署過的 migration 不要修改，要改就新增一個。
- 加密欄位（`EncryptedText`、`EncryptedJSON`）在資料庫裡只是 `Text`，`env.py` 的 `_render_item` 會自動寫成 `sa.Text()`。
