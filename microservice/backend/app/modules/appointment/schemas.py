import datetime as dt
from uuid import UUID

from pydantic import BaseModel

from app.integrations.townpass.messages import LaunchMapMessage
from app.modules.appointment.models import AppointmentStatus, Period, SessionStatus


class HospitalOut(BaseModel):
    id: UUID
    name: str
    address: str
    map: LaunchMapMessage  # 「帶我去醫院」：前端直接 postMessage(JSON.stringify(map))


class DepartmentOut(BaseModel):
    id: UUID
    name: str
    last_visited: bool  # 上次看的科別，排在第一個


class DoctorOut(BaseModel):
    id: UUID
    name: str
    last_visited: bool  # 上次看診的醫師，預設選取


class SessionOut(BaseModel):
    id: UUID
    date: dt.date
    period: Period
    status: SessionStatus
    available: bool  # 開診且未額滿


class AppointmentCreate(BaseModel):
    session_id: UUID


class AppointmentOut(BaseModel):
    id: UUID
    hospital: HospitalOut
    department: str
    doctor: str
    date: dt.date
    period: Period
    visit_no: int
    status: AppointmentStatus
