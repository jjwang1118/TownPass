"""匯入藥品資料到 drug_licenses 表，用於同成分檢查。

資料來源：健保署「健保用藥品項查詢檔」。`license_no` 存健保藥品代號（10 碼），
`ingredients` 存 ATC 7 碼（同一種化學成分）。原本規劃的食藥署許可證資料也可以用同一個格式匯入。
"""

from typing import TypedDict

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.medication.models import DrugLicense

# PostgreSQL 一個指令最多 32767 個參數，每筆 4 個欄位，分批寫入
_BATCH = 5000


class LicenseRow(TypedDict):
    license_no: str
    name_zh: str
    name_en: str | None
    ingredients: list[str]


def from_nhi(item: dict[str, str]) -> LicenseRow:
    """健保用藥品項的一筆品項 → LicenseRow。

    ATC 只有 7 碼時才代表單一化學成分；3～5 碼只是藥物類別（例如 R05X 感冒複方），
    拿來比對會誤報，所以不列入成分。
    """
    atc = item["ATC代碼"].strip().upper()
    return {
        "license_no": item["藥品代號"].strip(),
        "name_zh": item["中文品名"].strip(),
        "name_en": item["英文品名"].strip() or None,
        "ingredients": [atc] if len(atc) == 7 else [],
    }


async def import_licenses(session: AsyncSession, rows: list[LicenseRow]) -> int:
    """新增或更新藥品資料，回傳筆數。不 commit，由呼叫端決定。"""
    for start in range(0, len(rows), _BATCH):
        stmt = insert(DrugLicense).values(rows[start : start + _BATCH])
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
