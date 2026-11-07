"""救命卡卡號的純計算規則（規格書 §8.2）。"""

import re
import secrets
from urllib.parse import urlparse

# 去掉 0、1、I、L、O 等容易看錯的字元，共 31 個
CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
CODE_PREFIX = "TPE"
_CODE_PATTERN = re.compile(rf"^{CODE_PREFIX}-[{CODE_ALPHABET}]{{4}}-[{CODE_ALPHABET}]{{4}}$")

COMMON_CHRONIC_CONDITIONS = ["高血壓", "糖尿病", "高血脂", "心臟病", "氣喘", "慢性腎臟病", "失智症", "中風"]
COMMON_ALLERGIES = [
    {"type": "drug", "name": "盤尼西林"},
    {"type": "drug", "name": "阿斯匹靈"},
    {"type": "drug", "name": "磺胺類"},
    {"type": "food", "name": "海鮮"},
    {"type": "food", "name": "花生"},
    {"type": "food", "name": "蛋"},
]

DISCLAIMER = "本資料由本人或家屬提供，僅供參考，請以醫療專業判斷為準"


def generate_code() -> str:
    """例如 TPE-7K3Q-9X2M。"""
    chars = "".join(secrets.choice(CODE_ALPHABET) for _ in range(8))
    return f"{CODE_PREFIX}-{chars[:4]}-{chars[4:]}"


def normalize_code(raw: str) -> str | None:
    """忽略大小寫、空白和連字號。格式不符回傳 None。"""
    chars = re.sub(r"[\s-]", "", raw).upper()
    if chars.startswith(CODE_PREFIX):
        chars = chars[len(CODE_PREFIX):]
    code = f"{CODE_PREFIX}-{chars[:4]}-{chars[4:]}"
    return code if _CODE_PATTERN.match(code) else None


def qr_url(frontend_base_url: str, code: str) -> str:
    """救命卡 QR 的內容。路人用一般相機掃到會開啟前端公開頁（只顯示請撥 119）。"""
    return f"{frontend_base_url.rstrip('/')}/c/{code}"


def code_from_qr(scanned: str) -> str | None:
    """從 qr_code_scan 掃到的網址取出卡號。"""
    path = urlparse(scanned).path
    match = re.search(r"/c/([^/?#]+)$", path)
    return normalize_code(match.group(1)) if match else None
