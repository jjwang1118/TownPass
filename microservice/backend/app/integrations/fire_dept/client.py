"""臺北市政府消防局人員名冊。

比賽期間讀本服務的 responders 表（EMT-001～003），正式版以這個介面查詢消防局。
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RosterEntry:
    account: str
    name: str
    unit: str
    title: str
    active: bool
    has_ems_permission: bool


class FireDeptRoster(Protocol):
    async def find(self, account: str) -> RosterEntry | None: ...
