from enum import StrEnum

from app.integrations.townpass.messages import PushTokenReply


class DeviceRegisterIn(PushTokenReply):
    """自訂 Handler { name: 'push_token' } 的回覆，前端原封不動送來。"""


class PushType(StrEnum):
    """推播 data.type（規格書 §6.2）。"""

    MEDICATION_REMINDER = "medication_reminder"
    MEDICATION_ACKED = "medication_acked"
    MEDICATION_NO_RESPONSE = "medication_no_response"
    MEDICATION_NUDGE = "medication_nudge"
    CARD_ACCESSED = "card_accessed"
    REFILL_REMINDER = "refill_reminder"
    APPOINTMENT_REMINDER = "appointment_reminder"
