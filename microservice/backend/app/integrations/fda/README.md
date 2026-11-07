# app/integrations/fda/

藥品資料，用於同成分檢查：新增藥品時，比對它和長輩其他藥品的主成分。資料來源是健保署「健保用藥品項查詢檔」（115 年 11 月）；目錄名稱沿用原本規劃的食藥署許可證資料。

| 檔案 | 內容 |
|---|---|
| `importer.py` | `from_nhi()`：健保品項 → `drug_licenses` 的一筆；`import_licenses()`：分批新增或更新，可重複執行 |

## 對照

| `drug_licenses` | 健保用藥品項 |
|---|---|
| `license_no` | 藥品代號（10 碼，藥袋 QR 的 `lic`） |
| `name_zh`、`name_en` | 中文品名、英文品名 |
| `ingredients` | ATC 代碼，**只有 7 碼時才放**（7 碼＝同一種化學成分；3～5 碼只是藥物類別，比對會誤報） |

- 不同牌子、同成分的藥 ATC 相同（例如脈優錠、壓可平錠都是 amlodipine `C08CA01`），會跳出同成分警示。
- **限制**：複方藥有自己的 ATC（例如易安穩 amlodipine＋valsartan 是 `C09DB01`），不會和單方比對到。

## 更新資料

1. 把新的查詢檔轉成 JSON（格式同 `resent_docs/健保用藥品名_英文a-z.json`），用英文版：中文版少了沒有中文品名的品項。
2. 在 `microservice/backend` 執行 `uv run python -m seed.make_nhi_drugs <JSON 路徑>`，產生 `seed/data/nhi_drugs.json.gz`。
3. 後端啟動時（`seed.load`）會自動匯入，約 3 秒。

資料來源要列在繳交的「資料來源清單」。

狀態：✅ 完成。
