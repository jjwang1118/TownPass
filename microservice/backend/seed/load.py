"""把種子資料匯入資料庫。可以重複執行（已存在的資料會更新，已預約的門診不會被覆蓋）。

在 microservice/backend 執行：uv run python -m seed.load

門診只產生「明天起 2 週」，Demo 前一天請再執行一次。
"""

import asyncio
import datetime as dt
import gzip
import json
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.db import SessionLocal, engine
from app.core.security import hash_password
from app.integrations.fda.importer import import_licenses
from app.modules.appointment import rules as appointment_rules
from app.modules.appointment.models import (
    Appointment,
    ClinicSession,
    ClinicSlot,
    Department,
    Doctor,
    Hospital,
    Period,
    SessionStatus,
)
from app.modules.emergency_card.models import CardAccessLog
from app.modules.medication.models import DrugLicense
from app.modules.responder.models import Responder

DATA_DIR = Path(__file__).parent / "data"
# 固定的 namespace，讓院區、科別、醫師每次匯入都得到相同的 id
_SEED_NAMESPACE = uuid.UUID("6f1c7a52-3f0e-4b5e-9a57-2c1d9e7f4a10")


def read(name: str) -> Any:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def seed_id(*parts: str) -> uuid.UUID:
    return uuid.uuid5(_SEED_NAMESPACE, "/".join(parts))


def sample_drug_codes() -> set[str]:
    """範例藥袋 QR 用到的健保藥品代號。"""
    return {item["lic"] for s in read("rx_samples.json") for item in s["payload"]["items"] if item.get("lic")}


async def load_licenses(session: AsyncSession, only: set[str] | None = None) -> int:
    """健保用藥品項（seed.make_nhi_drugs 產生）。only：只匯入這些藥品代號（測試用，避免每次匯入 4.5 萬筆）。"""
    rows = json.loads(gzip.decompress((DATA_DIR / "nhi_drugs.json.gz").read_bytes()))["rows"]
    if only is not None:
        rows = [r for r in rows if r["license_no"] in only]
    await session.execute(delete(DrugLicense).where(DrugLicense.license_no.like("DEMO-%")))  # 舊版的模擬資料
    return await import_licenses(session, rows)


async def load_responders(session: AsyncSession) -> int:
    """模擬消防局名冊。密碼以 argon2 雜湊後存入。名冊已移除、也沒有查看紀錄的帳號會刪除。"""
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
    await session.execute(
        delete(Responder).where(
            Responder.account.not_in([r["account"] for r in rows]),
            Responder.id.not_in(select(CardAccessLog.responder_id)),
        )
    )
    return len(rows)


async def load_clinics(session: AsyncSession, today: dt.date | None = None) -> int:
    """聯醫 7 院區（9 個院址）、各院址的科別與醫師，以及明天起 2 週的門診與看診時間（模擬）。回傳新增的門診數。

    每個看診時間有自己的名額，部分時間預先填入模擬的預約數（號碼接續發）。
    Demo 用：仁愛院區家醫科林醫師的第 1 個門診每個時間都額滿、第 2 個門診停診。
    """
    data = read("tpech_clinics.json")
    today = today or clock.today_taipei()
    start, end = appointment_rules.booking_window(today)
    capacity = data["slot_capacity"]

    hospitals, departments, doctors, sessions = [], [], [], []
    for hospital in data["hospitals"]:
        hospital_id = seed_id(hospital["name"])
        hospitals.append({"id": hospital_id, "name": hospital["name"], "address": hospital["address"]})
        for department_name in hospital["departments"]:
            department_id = seed_id(hospital["name"], department_name)
            departments.append({"id": department_id, "hospital_id": hospital_id, "name": department_name})
            for index, doctor_name in enumerate(data["doctors_by_department"][department_name]):
                doctor_id = seed_id(hospital["name"], department_name, doctor_name)
                doctors.append({"id": doctor_id, "department_id": department_id, "name": doctor_name})
                schedule = data["weekly_schedules"][index % len(data["weekly_schedules"])]
                sessions += _sessions_for(doctor_id, schedule, start, end)

    slots = []
    for s in sessions:
        session_slots = _slots_for(s, capacity)
        s["issued_count"] = sum(slot["booked_count"] for slot in session_slots)
        slots += session_slots

    demo = data["demo"]
    demo_doctor = seed_id(demo["hospital"], demo["department"], demo["doctor"])
    demo_sessions = sorted(
        (s for s in sessions if s["doctor_id"] == demo_doctor),
        key=lambda s: (s["date"], list(Period).index(s["period"])),
    )
    if len(demo_sessions) >= 2:
        full = [slot for slot in slots if slot["session_id"] == demo_sessions[0]["id"]]
        for slot in full:
            slot["booked_count"] = capacity
        demo_sessions[0]["issued_count"] = capacity * len(full)
        demo_sessions[1].update(status=SessionStatus.SUSPENDED)

    await _upsert(session, Hospital, hospitals, update=["name", "address"])
    await _upsert(session, Department, departments, update=["name"])
    await _upsert(session, Doctor, doctors, update=["name"])
    await _prune_retired(session, [h["id"] for h in hospitals], [d["id"] for d in departments], [d["id"] for d in doctors])
    result = await session.execute(
        insert(ClinicSession)
        .values(sessions)
        .on_conflict_do_nothing(index_elements=["doctor_id", "date", "period"])
        .returning(ClinicSession.id)
    )
    created = set(result.scalars().all())
    # 只替新建立的門診加入看診時間；已經存在的門診（可能已有預約）不動
    new_slots = [slot for slot in slots if slot["session_id"] in created]
    if new_slots:
        await session.execute(insert(ClinicSlot).values(new_slots))
    return len(created)


def _sessions_for(doctor_id: uuid.UUID, schedule: list[list], start: dt.date, end: dt.date) -> list[dict[str, Any]]:
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
                        "issued_count": 0,
                        "status": SessionStatus.OPEN,
                    }
                )
        day += dt.timedelta(days=1)
    return rows


def _slots_for(clinic: dict[str, Any], capacity: int) -> list[dict[str, Any]]:
    """門診的看診時間；預先填入的預約數由醫師、日期、時間決定（每次匯入結果相同），約 1/9 額滿。"""
    rows = []
    for at in appointment_rules.SLOT_TIMES[clinic["period"]]:
        key = seed_id(str(clinic["doctor_id"]), clinic["date"].isoformat(), at.isoformat())
        rows.append(
            {
                "id": uuid.uuid4(),
                "session_id": clinic["id"],
                "time": at,
                "capacity": capacity,
                "booked_count": min(key.int % (capacity + 1), capacity),
            }
        )
    return rows


async def _prune_retired(
    session: AsyncSession, hospital_ids: list[uuid.UUID], department_ids: list[uuid.UUID], doctor_ids: list[uuid.UUID]
) -> None:
    """移除 seed 已經不再提供的院區、科別、醫師及其門診（例如院區改名後的舊資料）。
    已經有預約用到的門診不刪，以免破壞預約紀錄；它們的醫師、科別、院區也會因此保留。"""
    used = select(Appointment.session_id)
    await session.execute(
        delete(ClinicSession).where(ClinicSession.doctor_id.not_in(doctor_ids), ClinicSession.id.not_in(used))
    )
    has_session = select(ClinicSession.doctor_id)
    await session.execute(delete(Doctor).where(Doctor.id.not_in(doctor_ids), Doctor.id.not_in(has_session)))
    has_doctor = select(Doctor.department_id)
    await session.execute(
        delete(Department).where(Department.id.not_in(department_ids), Department.id.not_in(has_doctor))
    )
    has_department = select(Department.hospital_id)
    await session.execute(delete(Hospital).where(Hospital.id.not_in(hospital_ids), Hospital.id.not_in(has_department)))


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
    print(f"健保用藥品項：{licenses} 筆")
    print(f"消防局名冊（模擬）：{responders} 筆")
    print(f"聯醫門診（模擬）：新增 {clinics} 個門診與看診時間（明天起 2 週）")


if __name__ == "__main__":
    asyncio.run(main())
