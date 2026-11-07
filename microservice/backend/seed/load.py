"""把種子資料匯入資料庫。可以重複執行（已存在的資料會更新）。

在 microservice/backend 執行：uv run python -m seed.load
"""

import asyncio
import json
from pathlib import Path

from app.core.db import SessionLocal, engine
from app.integrations.fda.importer import import_licenses

DATA_DIR = Path(__file__).parent / "data"


def read(name: str) -> list[dict]:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


async def main() -> None:
    async with SessionLocal() as session:
        licenses = await import_licenses(session, read("drug_licenses.json"))
        await session.commit()
    await engine.dispose()
    print(f"食藥署許可證（範例）：{licenses} 筆")


if __name__ == "__main__":
    asyncio.run(main())
