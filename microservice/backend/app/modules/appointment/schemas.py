import datetime as dt
from uuid import UUID

from pydantic import BaseModel

from app.integrations.townpass.messages import LaunchMapMessage
from app.modules.appointment.models import AppointmentStatus, Period, SessionStatus


class HospitalOut(BaseModel):
    """選院區（E10d）：9 個院址附地址。"""

    id: UUID
    name: str
    address: str
    map: LaunchMapMessage  # 「帶我去醫院」：前端直接 postMessage(JSON.stringify(map))


class DepartmentOut(BaseModel):
    """選科別（E10e）。從藥單帶入的科別排第一。"""

    id: UUID
    name: str
    last_visited: bool
    from_letter: str | None  # 例如 A：前端顯示「藥單 A 的科別」


class DoctorOut(BaseModel):
    """選醫師（E10b）：門診時間；2 週內都額滿時灰色不可選。"""

    id: UUID
    name: str
    last_visited: bool  # 藥單上的醫師，前端預設選取
    schedule: str  # 週一、週五 上午
    available: bool
    note: str | None  # 已額滿


class ClinicDayOut(BaseModel):
    """選日期（E10f）：只列這位醫師的門診；額滿、停診為灰色不可選。"""

    session_id: UUID
    date: dt.date
    label: str  # 11/14（五）
    period: Period
    period_label: str  # 上午門診
    status: SessionStatus
    available: bool
    note: str | None  # 已額滿、停診


class SlotOut(BaseModel):
    """選時段（E10g）：每個看診時間的剩餘名額；額滿為灰色不可選。"""

    slot_id: UUID
    time: dt.time
    label: str  # 上午 09:30
    remaining: int
    available: bool
    note: str  # 還有 3 個名額、已額滿


class AppointmentCreate(BaseModel):
    """確認預約（E11）。"""

    slot_id: UUID


class AppointmentOut(BaseModel):
    """預約成功（E12）與我的預約。"""

    id: UUID
    hospital: HospitalOut
    department: str
    doctor: str
    date: dt.date
    date_label: str  # 11/14（五）
    time: dt.time
    time_label: str  # 上午 09:30
    period: Period
    visit_no: int  # 看診號碼
    status: AppointmentStatus
    message: str  # 回診前一天，您和家屬都會收到提醒。
