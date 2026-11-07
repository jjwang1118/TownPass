"""建立本機設定檔 .env，並產生加密金鑰。Windows、Mac 都可以執行：

    uv run python -m scripts.init_env

- 沒有 .env：從 .env.example 複製，並填入新產生的 JWT_SECRET、FIELD_ENCRYPTION_KEY、INTERNAL_SECRET。
- 已經有 .env：不修改既有的值（避免換掉加密金鑰），只補上 .env.example 新增、而 .env 還沒有的設定。
"""

import re
import secrets
from pathlib import Path

from cryptography.fernet import Fernet

EXAMPLE = Path(".env.example")
TARGET = Path(".env")
_LINE = re.compile(r"^([A-Z_][A-Z0-9_]*)=(.*)$")


def _keys(text: str) -> dict[str, str]:
    return {m.group(1): m.group(2) for line in text.splitlines() if (m := _LINE.match(line))}


def _generated() -> dict[str, str]:
    return {
        "JWT_SECRET": secrets.token_urlsafe(48),
        "FIELD_ENCRYPTION_KEY": Fernet.generate_key().decode(),
        "INTERNAL_SECRET": secrets.token_urlsafe(32),
    }


def main() -> None:
    example = EXAMPLE.read_text(encoding="utf-8")

    if not TARGET.exists():
        values = _generated()
        lines = []
        for line in example.splitlines():
            match = _LINE.match(line)
            lines.append(f"{match.group(1)}={values[match.group(1)]}" if match and match.group(1) in values else line)
        TARGET.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"已建立 {TARGET.resolve()}，並產生新的金鑰。")
        print("FIELD_ENCRYPTION_KEY 開始存資料後不可更換，請另外備份。")
        return

    current_text = TARGET.read_text(encoding="utf-8")
    current = _keys(current_text)
    missing = {k: v for k, v in _keys(example).items() if k not in current}
    if not current.get("FIELD_ENCRYPTION_KEY"):
        print("⚠️ .env 的 FIELD_ENCRYPTION_KEY 是空的。如果資料庫還沒有個資，可以填入：")
        print(f"   FIELD_ENCRYPTION_KEY={Fernet.generate_key().decode()}")
    if missing:
        with TARGET.open("a", encoding="utf-8") as f:
            f.write("\n# 以下由 scripts.init_env 從 .env.example 補上\n")
            f.writelines(f"{k}={v}\n" for k, v in missing.items())
        print(f".env 已存在，補上新設定：{', '.join(missing)}")
    else:
        print(".env 已存在，設定齊全，沒有修改。")


if __name__ == "__main__":
    main()
