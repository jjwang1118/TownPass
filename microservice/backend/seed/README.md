# seed/

Demo 與測試用的種子資料。規格書 §11.1。

**所有資料都是模擬資料**，藥品內容需經藥師審核才能用於正式環境。繳交時要列在「資料來源清單」並註明為模擬資料。

## 檔案

| 路徑 | 內容 |
|---|---|
| `data/drug_licenses.json` | 食藥署許可證範例 3 筆，字號用 `DEMO-` 開頭，避免和真實藥品混淆 |
| `data/rx_samples.json` | 範例藥袋 QR 的內容（格式見規格書 §8.1） |
| `qr/*.png` | 由 `rx_samples.json` 產生的 QR 圖檔，可以印出來或用另一支手機顯示給 App 掃 |
| `load.py` | 匯入資料庫，可以重複執行 |
| `make_qr.py` | 重新產生 `qr/*.png` |

## 範例藥袋

| 檔案 | 藥 | 示範 |
|---|---|---|
| `rx_1_amlodipine_5mg.png` | 家醫科，降血壓，一天一次飯後，1 顆 | |
| `rx_2_metformin_500mg.png` | 新陳代謝科，降血糖，一天兩次飯後，1 顆 | |
| `rx_3_amlodipine_10mg.png` | 心臟內科，降血壓，一天一次飯後，半顆 | 和 1 號同成分，跳出「這兩包好像是同一種藥，請問藥師」 |

## 指令

在 `microservice/backend` 執行：

```bash
uv run python -m seed.load      # 匯入資料庫
uv run python -m seed.make_qr   # 修改 rx_samples.json 後重新產生 QR
```

## 尚未加入

- 救護人員名冊（EMT-001～003）
- 聯醫院區、科別、醫師、門診

長輩和家人的帳號不放在這裡：修改 App 的 `assets/mock_data/account.json`（`birthday`、`citizen`）即可切換。
