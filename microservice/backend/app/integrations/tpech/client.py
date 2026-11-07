"""臺北市立聯合醫院掛號系統。

比賽期間院區、科別、醫師、門診都存在本服務資料庫（seed 模擬資料），
正式上線時以這個介面串接聯醫，service 不需修改。
"""

import datetime as dt
from typing import Protocol
from uuid import UUID


class TpechClient(Protocol):
    async def list_sessions(self, doctor_id: UUID, start: dt.date, end: dt.date) -> list[dict]: ...

    async def book(self, session_id: UUID, elder_name: str) -> int:
        """回傳看診號碼。"""
        ...

    async def cancel(self, session_id: UUID, visit_no: int) -> None: ...
