"""把種子資料匯入資料庫。可以重複執行（已存在的資料會更新，已預約的門診不會被覆蓋）。

在 microservice/backend 執行：uv run python -m seed.load

門診只產生「明天起 2 週」，Demo 前一天請再執行一次。
"""

import asyncio
import datetime as dt
import json
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.db import SessionLocal, engine
from app.core.security import hash_password
from app.integrations.fda.importer import import_licenses
from app.modules.appointment import rules as appointment_rules
from app.modules.appointment.models import ClinicSession, Department, Doctor, Hospital, Period, SessionStatus
from app.modules.responder.models import Responder

DATA_DIR = Path(__file__).parent / "data"
# 固定的 namespace，讓院區、科別、醫師每次匯入都得到相同的 id
_SEED_NAMESPACE = uuid.UUID("6f1c7a52-3f0e-4b5e-9a57-2c1d9e7f4a10")


def read(name: str) -> Any:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def seed_id(*parts: str) -> uuid.UUID:
    return uuid.uuid5(_SEED_NAMESPACE, "/".join(parts))


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


async def load_clinics(session: AsyncSession, today: dt.date | None = None) -> int:
    """聯醫院區、科別、醫師，以及明天起 2 週的門診（模擬）。回傳新增的門診數。

    Demo 用：仁愛院區家醫科林醫師的第 1 個門診額滿、第 2 個門診停診。
    """
    data = read("tpech_clinics.json")
    today = today or clock.today_taipei()
    start, end = appointment_rules.booking_window(today)

    hospitals, departments, doctors, sessions = [], [], [], []
    for hospital in data["hospitals"]:
        hospital_id = seed_id(hospital["name"])
        hospitals.append({"id": hospital_id, **hospital})
        for department_name, doctor_names in data["doctors_by_department"].items():
            department_id = seed_id(hospital["name"], department_name)
            departments.append({"id": department_id, "hospital_id": hospital_id, "name": department_name})
            for index, doctor_name in enumerate(doctor_names):
                doctor_id = seed_id(hospital["name"], department_name, doctor_name)
                doctors.append({"id": doctor_id, "department_id": department_id, "name": doctor_name})
                schedule = data["weekly_schedules"][index % len(data["weekly_schedules"])]
                sessions += _sessions_for(doctor_id, schedule, start, end, data["capacity"])

    demo = data["demo"]
    demo_doctor = seed_id(demo["hospital"], demo["department"], demo["doctor"])
    demo_sessions = sorted(
        (s for s in sessions if s["doctor_id"] == demo_doctor),
        key=lambda s: (s["date"], list(Period).index(s["period"])),
    )
    if len(demo_sessions) >= 2:
        demo_sessions[0].update(booked_count=data["capacity"], issued_count=data["capacity"])
        demo_sessions[1].update(status=SessionStatus.SUSPENDED)

    await _upsert(session, Hospital, hospitals, update=["name", "address"])
    await _upsert(session, Department, departments, update=["name"])
    await _upsert(session, Doctor, doctors, update=["name"])
    result = await session.execute(
        insert(ClinicSession)
        .values(sessions)
        .on_conflict_do_nothing(index_elements=["doctor_id", "date", "period"])
        .returning(ClinicSession.id)
    )
    return len(result.all())


def _sessions_for(
    doctor_id: uuid.UUID, schedule: list[list], start: dt.date, end: dt.date, capacity: int
) -> list[dict[str, Any]]:
    rows = []
    day = start
    while day <= end:
        for weekday, period in schedule:
            if day.weekday() == weekday:
                rows.append(
                    {
                        "id": uuid.uuid4(),
                        "doctor_id": doctor_id,
                        "date": day,
                        "period": Period(period),
                        "capacity": capacity,
                        "booked_count": 0,
                        "issued_count": 0,
                        "status": SessionStatus.OPEN,
                    }
                )
        day += dt.timedelta(days=1)
    return rows


async def _upsert(session: AsyncSession, model: type, rows: list[dict], update: list[str]) -> None:
    stmt = insert(model).values(rows)
    stmt = stmt.on_conflict_do_update(index_elements=["id"], set_={col: stmt.excluded[col] for col in update})
    await session.execute(stmt)


async def main() -> None:
    async with SessionLocal() as session:
        licenses = await load_licenses(session)
        responders = await load_responders(session)
        clinics = await load_clinics(session)
        await session.commit()
    await engine.dispose()
    print(f"食藥署許可證（範例）：{licenses} 筆")
    print(f"消防局名冊（模擬）：{responders} 筆")
    print(f"聯醫門診（模擬）：新增 {clinics} 個門診（明天起 2 週）")


if __name__ == "__main__":
    asyncio.run(main())
