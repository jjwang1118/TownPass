"""把種子資料匯入資料庫。可以重複執行（已存在的資料會更新）。

在 microservice/backend 執行：uv run python -m seed.load
"""

import asyncio
import json
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal, engine
from app.core.security import hash_password
from app.integrations.fda.importer import import_licenses
from app.modules.responder.models import Responder

DATA_DIR = Path(__file__).parent / "data"


def read(name: str) -> list[dict]:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


async def load_licenses(session: AsyncSession) -> int:
    return await import_licenses(session, read("drug_licenses.json"))


async def load_responders(session: AsyncSession) -> int:
    """模擬消防局名冊。密碼以 argon2 雜湊後存入。"""
    rows = [
        {**{k: v for k, v in r.items() if k != "password"}, "password_hash": hash_password(r["password"])}
        for r in read("responders.json")
    ]
    stmt = insert(Responder).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Responder.account],
        set_={col: stmt.excluded[col] for col in rows[0] if col != "account"},
    )
    await session.execute(stmt)
    return len(rows)


async def main() -> None:
    async with SessionLocal() as session:
        licenses = await load_licenses(session)
        responders = await load_responders(session)
        await session.commit()
    await engine.dispose()
    print(f"食藥署許可證（範例）：{licenses} 筆")
    print(f"消防局名冊（模擬）：{responders} 筆")


if __name__ == "__main__":
    asyncio.run(main())
