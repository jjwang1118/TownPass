"""救護人員的固定資料與規則。"""

import re

AGENCY = "臺北市政府消防局"

# 登入時選擇的所屬單位（UI R01b）。名稱為範例，正式名冊需由消防局提供（integrations/fire_dept）
UNITS = [
    "大安分隊",
    "信義分隊",
    "松山分隊",
    "中山分隊",
    "中正分隊",
    "萬華分隊",
    "大同分隊",
    "士林分隊",
    "北投分隊",
    "內湖分隊",
    "南港分隊",
    "文山分隊",
]


# 身分證字號（含新式居留證）：英文字母＋1、2、8、9 開頭的 9 位數字。只檢查格式，不驗檢查碼（Demo 帳號為範例號碼）
_ID_NO = re.compile(r"[A-Z][1289]\d{8}")


def is_id_no(raw: str) -> bool:
    return _ID_NO.fullmatch(raw.strip().upper()) is not None
