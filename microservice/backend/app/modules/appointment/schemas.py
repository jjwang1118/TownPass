import datetime as dt
from uuid import UUID

from pydantic import BaseModel

from app.integrations.townpass.messages import LaunchMapMessage
from app.modules.appointment.models import AppointmentStatus, Period, SessionStatus


class HospitalOut(BaseModel):
    """步驟 1：選院區。"""

    id: UUID
    name: str
    address: str
    map: LaunchMapMessage  # 「帶我去醫院」：前端直接 postMessage(JSON.stringify(map))


class DepartmentOut(BaseModel):
    """步驟 2：選科別。上次看的科別排第一。"""

    id: UUID
    name: str
    last_visited: bool


class DoctorOut(BaseModel):
    """步驟 3：選醫師。預設選取上次看診的醫師。"""

    id: UUID
    name: str
    last_visited: bool


class SessionOut(BaseModel):
    """步驟 5：選時段。"""

    session_id: UUID
    period: Period
    label: str  # 上午、下午、晚上
    status: SessionStatus
    available: bool  # 開診且未額滿；false 時前端顯示灰色不可選


class ClinicDayOut(BaseModel):
    """步驟 4：選日期。只列出這位醫師有門診的日子。"""

    date: dt.date
    label: str  # 11/12（星期三）
    available: bool  # 這天至少有一個時段可以預約
    sessions: list[SessionOut]


class AppointmentCreate(BaseModel):
    """步驟 6：確認預約。"""

    session_id: UUID


class ReminderToggle(BaseModel):
    enabled: bool


class AppointmentOut(BaseModel):
    """完成頁與我的預約。"""

    id: UUID
    hospital: HospitalOut
    department: str
    doctor: str
    date: dt.date
    date_label: str
    period: Period
    period_label: str
    visit_no: int  # 看診號碼
    status: AppointmentStatus
    reminder_enabled: bool  # 已「加入提醒」
