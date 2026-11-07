"""邀請碼的純計算規則。"""

import datetime as dt
import re
import secrets
from urllib.parse import urlparse

INVITE_TTL = dt.timedelta(minutes=10)
_CODE_PATTERN = re.compile(r"^\d{6}$")


def generate_invite_code() -> str:
    return f"{secrets.randbelow(10**6):06d}"


def invite_qr_url(frontend_base_url: str, code: str) -> str:
    """邀請 QR 的內容。家人用一般相機掃到也會開啟前端的綁定頁。"""
    return f"{frontend_base_url.rstrip('/')}/invite/{code}"


def code_from_input(raw: str) -> str | None:
    """接受 6 位數字（手動輸入，可含空白），或邀請 QR 的網址。格式不符回傳 None。"""
    raw = raw.strip()
    digits = re.sub(r"\s", "", raw)
    if _CODE_PATTERN.match(digits):
        return digits
    match = re.search(r"/invite/(\d{6})$", urlparse(raw).path)
    return match.group(1) if match else None
