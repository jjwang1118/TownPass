from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.modules.auth.models import UserRole


class RoleIn(BaseModel):
    role: UserRole


class MeOut(BaseModel):
    id: UUID
    role: UserRole | None
    real_name: str
    birth_year: int | None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: MeOut
