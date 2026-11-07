"""匯入食藥署「藥品許可證」開放資料到 drug_licenses 表，用於同成分檢查。

資料來源：data.fda.gov.tw（全部藥品許可證資料集）。比賽時只匯入範例藥品需要的幾筆。
"""

from sqlalchemy.ext.asyncio import AsyncSession


async def import_licenses(session: AsyncSession, rows: list[dict]) -> int:
    """rows：{license_no, name_zh, name_en, ingredients}。回傳匯入筆數。"""
    raise NotImplementedError
