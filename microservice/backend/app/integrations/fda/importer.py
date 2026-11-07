"""匯入食藥署「藥品許可證」開放資料到 drug_licenses 表，用於同成分檢查。

資料來源：data.fda.gov.tw（全部藥品許可證資料集）。比賽時只匯入範例藥品需要的幾筆。
"""

from typing import TypedDict

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.medication.models import DrugLicense


class LicenseRow(TypedDict):
    license_no: str
    name_zh: str
    name_en: str | None
    ingredients: list[str]


async def import_licenses(session: AsyncSession, rows: list[LicenseRow]) -> int:
    """新增或更新許可證資料，回傳筆數。不 commit，由呼叫端決定。"""
    if not rows:
        return 0
    stmt = insert(DrugLicense).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[DrugLicense.license_no],
        set_={
            "name_zh": stmt.excluded.name_zh,
            "name_en": stmt.excluded.name_en,
            "ingredients": stmt.excluded.ingredients,
        },
    )
    await session.execute(stmt)
    return len(rows)
