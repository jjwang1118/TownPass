from enum import StrEnum

from app.integrations.townpass.messages import PushTokenReply


class DeviceRegisterIn(PushTokenReply):
    """自訂 Handler { name: 'push_token' } 的回覆，前端原封不動送來。"""


class PushType(StrEnum):
    """推播 data.type（規格書 §6.2）。"""

    MEDICATION_REMINDER = "medication_reminder"  # 長輩：該吃藥了
    FAMILY_MEDICATION_REMINDER = "family_medication_reminder"  # 家屬：和長輩同時間收到
    MEDICATION_NUDGE = "medication_nudge"
    CARD_ACCESSED = "card_accessed"
    REFILL_REMINDER = "refill_reminder"
    APPOINTMENT_REMINDER = "appointment_reminder"
