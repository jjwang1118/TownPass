import datetime as dt
import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.config import get_settings
from app.core.errors import Conflict, Forbidden, NotFound
from app.integrations.townpass.messages import PhoneCallMessage
from app.modules.auth.service import AuthService
from app.modules.emergency_card.service import EmergencyCardService
from app.modules.family.service import Access, FamilyService
from app.modules.medication import rules as med_rules
from app.modules.medication.models import SlotKey
from app.modules.medication.schemas import DoseItem
from app.modules.medication.service import MedicationService
from app.modules.notification.schemas import PushType
from app.modules.notification.service import NotificationService
from app.modules.reminder import rules
from app.modules.reminder.models import ReminderEvent
from app.modules.reminder.repository import ReminderRepository
from app.modules.reminder.schemas import ReminderOut, ReminderStatus
from app.modules.speech import rules as speech

logger = logging.getLogger(__name__)


class ReminderService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ReminderRepository(session)
        self.auth = AuthService(session)
        self.family = FamilyService(session)
        self.medication = MedicationService(session)
        self.cards = EmergencyCardService(session)
        self.notification = NotificationService(session)

    # ---------- API ----------

    async def get(self, user_id: UUID, event_id: UUID) -> ReminderOut:
        event = await self._get(event_id)
        await self.family.ensure_access(user_id, event.elder_id, Access.READ)
        return await self._to_out(event)

    async def ack(self, user_id: UUID, event_id: UUID) -> ReminderOut:
        """長輩按「好，我知道了」。只有長輩本人可以按；重複按不會重複通知。"""
        event = await self._get(event_id)
        if user_id != event.elder_id:
            raise Forbidden("只有長輩本人可以回應提醒", code="ELDER_ONLY")
        if event.acked_at is not None:
            return await self._to_out(event)

        event.acked_at = clock.now()
        await self.session.commit()

        time_text = rules.hhmm(event.scheduled_at, clock.TAIPEI)
        for member in await self.family.list_family_members(event.elder_id):
            if member.notify_on_ack:
                await self._push(
                    [member.family_id],
                    PushType.MEDICATION_ACKED,
                    "吃藥提醒已回應",
                    rules.acked_text(member.relation_label, time_text),
                    event,
                )
        return await self._to_out(event)

    async def list_by_date(self, user_id: UUID, elder_id: UUID, date: dt.date) -> list[ReminderOut]:
        await self.family.ensure_access(user_id, elder_id, Access.READ)
        return [await self._to_out(e) for e in await self.repo.list_by_date(elder_id, date)]

    async def nudge(self, family_id: UUID, elder_id: UUID) -> None:
        """功能規格 1-6：家人提醒長輩吃藥。只有綁定的家人可以使用。"""
        if family_id == elder_id:
            raise Forbidden("這個功能只有家人可以使用", code="FAMILY_ONLY")
        await self.family.ensure_access(family_id, elder_id, Access.READ)
        name = (await self.auth.get_me(family_id)).real_name
        pending = await self.repo.latest_pending(elder_id)
        await self._push(
            [elder_id],
            PushType.MEDICATION_NUDGE,
            "家人提醒",
            rules.nudge_text(name),
            pending,
        )

    # ---------- 排程（/internal/tick 每分鐘呼叫，規格書 §6.1） ----------

    async def create_due_events(self, now: dt.datetime) -> int:
        """時段到了：建立提醒並推播長輩（第 1 次）。排程延誤超過 30 分鐘就不補發。"""
        local = now.astimezone(clock.TAIPEI)
        today = local.date()
        created = 0
        for elder_id in await self.medication.elders_scheduled_on(today):
            for slot_key, slot_time in (await self.medication.slot_times(elder_id)).items():
                at = dt.datetime.combine(today, slot_time, tzinfo=clock.TAIPEI)
                if not (at <= local < at + rules.LATE_WINDOW):
                    continue
                if await self.create_event(elder_id, slot_key, at, now) is not None:
                    created += 1
        await self.session.commit()
        return created

    async def create_event(
        self, elder_id: UUID, slot_key: SlotKey, at: dt.datetime, now: dt.datetime
    ) -> ReminderEvent | None:
        """建立某個時段的提醒並推播長輩；這個時段沒有藥或今天已提醒過時回傳 None。"""
        day = at.astimezone(clock.TAIPEI).date()
        doses = await self.medication.doses_for_slot(elder_id, slot_key, day)
        if not doses:
            return None
        names = await self.medication.speech_names(elder_id)
        event = await self.repo.create_event(
            elder_id=elder_id,
            slot_key=slot_key,
            scheduled_date=day,
            scheduled_at=at,
            items=[
                {"number": d.number, "name": d.name, "speech_name": names.get(d.number, d.name), "qty": str(d.qty)}
                for d in doses
            ],
            now=now,
        )
        if event is not None:
            await self._push_elder_reminder(event)
        return event

    async def repush_unacked(self, now: dt.datetime) -> int:
        """沒回應：每隔 REMIND_INTERVAL_MINUTES 再推播，最多 3 次。"""
        events = await self.repo.claim_repush(now, now - self._interval(), rules.MAX_ATTEMPTS)
        await self.session.commit()
        for event in events:
            await self._push_elder_reminder(event)
        return len(events)

    async def escalate_no_response(self, now: dt.datetime) -> int:
        """第 3 次推播後仍沒回應：通知所有綁定家人，附撥給長輩的一鍵撥號。"""
        events = await self.repo.claim_escalation(now, now - self._interval(), rules.MAX_ATTEMPTS)
        await self.session.commit()
        for event in events:
            await self.notify_no_response(event)
        return len(events)

    async def notify_no_response(self, event: ReminderEvent) -> None:
        _, gender = await self._elder_title(event.elder_id)
        time_text = rules.hhmm(event.scheduled_at, clock.TAIPEI)
        call = PhoneCallMessage.to(await self.auth.get_phone(event.elder_id))
        for member in await self.family.list_family_members(event.elder_id):
            await self._push(
                [member.family_id],
                PushType.MEDICATION_NO_RESPONSE,
                "吃藥提醒沒有回應",
                rules.no_response_text(member.relation_label, time_text, gender),
                event,
                extra={"call": call.model_dump_json()},
            )

    async def send_refill_reminders(self, now: dt.datetime) -> int:
        """功能規格 3-1：每天 09:00 起，藥再 7 天吃完時提醒長輩與家人；同一個吃完日只發一次。"""
        local = now.astimezone(clock.TAIPEI)
        if local.time() < rules.REFILL_SEND_AT:
            return 0
        run_out = local.date() + dt.timedelta(days=rules.REFILL_DAYS_BEFORE)
        sent = 0
        for elder_id, numbers in (await self.medication.running_out_on(run_out)).items():
            if not await self.repo.create_refill_notice(elder_id, run_out, numbers):
                continue
            await self.session.commit()
            await self.notify_refill(elder_id, numbers)
            sent += 1
        await self.session.commit()
        return sent

    async def notify_refill(self, elder_id: UUID, numbers: list[int]) -> None:
        recipients = [elder_id, *await self.family.list_family_ids(elder_id)]
        await self._push(recipients, PushType.REFILL_REMINDER, "回診提醒", rules.refill_text(numbers), None)

    # ---------- Demo（只在 DEMO_MODE 由 demo 模組呼叫，正式版移除） ----------

    async def demo_trigger_reminder(self, user_id: UUID, elder_id: UUID) -> ReminderOut:
        """立即提醒今天第一個有藥的時段；今天已提醒過就重新開始（次數歸零）。"""
        await self.family.ensure_access(user_id, elder_id, Access.READ)
        now = clock.now()
        today = now.astimezone(clock.TAIPEI).date()
        slot_times = await self.medication.slot_times(elder_id)
        for slot_key, _ in sorted(slot_times.items(), key=lambda kv: kv[1]):
            if not await self.medication.doses_for_slot(elder_id, slot_key, today):
                continue
            event = await self.repo.get_by_day_slot(elder_id, slot_key, today)
            if event is None:
                event = await self.create_event(elder_id, slot_key, now, now)
            else:
                event.attempts, event.last_pushed_at = 1, now
                event.acked_at = event.escalated_at = None
                await self._push_elder_reminder(event)
            await self.session.commit()
            assert event is not None
            return await self._to_out(event)
        raise Conflict("今天沒有要吃的藥，請先新增藥品", code="NO_DOSE_TODAY")

    async def demo_trigger_no_response(self, user_id: UUID, elder_id: UUID) -> ReminderOut:
        """把最近一筆未回應的提醒當作 3 次沒回應，立即通知家人。"""
        event = await self.repo.latest_pending(elder_id)
        if event is None:
            event = await self._get((await self.demo_trigger_reminder(user_id, elder_id)).id)
        else:
            await self.family.ensure_access(user_id, elder_id, Access.READ)
        event.attempts, event.escalated_at = rules.MAX_ATTEMPTS, clock.now()
        await self.session.commit()
        await self.notify_no_response(event)
        return await self._to_out(event)

    async def demo_trigger_refill(self, user_id: UUID, elder_id: UUID) -> list[int]:
        """立即發回診提醒，提醒最快吃完的那幾號藥。"""
        await self.family.ensure_access(user_id, elder_id, Access.READ)
        soonest = await self.medication.soonest_run_out(elder_id)
        if not soonest:
            raise Conflict("沒有進行中的藥", code="NO_ACTIVE_MEDICATION")
        await self.notify_refill(elder_id, soonest)
        return soonest

    # ---------- 內部 ----------

    @staticmethod
    def _interval() -> dt.timedelta:
        return dt.timedelta(minutes=get_settings().remind_interval_minutes)

    async def _get(self, event_id: UUID) -> ReminderEvent:
        event = await self.repo.get(event_id)
        if event is None:
            raise NotFound("找不到這個提醒", code="REMINDER_NOT_FOUND")
        return event

    async def _elder_title(self, elder_id: UUID) -> tuple[str, str | None]:
        """救命卡上的稱呼（如「陳阿嬤」）；還沒建立救命卡時用台北通的姓名。"""
        card = await self.cards.elder_title(elder_id)
        if card is not None:
            return card[0], card[1]
        return (await self.auth.get_me(elder_id)).real_name, None

    async def _push_elder_reminder(self, event: ReminderEvent) -> None:
        title, _ = await self._elder_title(event.elder_id)
        await self._push(
            [event.elder_id],
            PushType.MEDICATION_REMINDER,
            "吃藥時間到囉",
            self._speech(title, event),
            event,
        )

    async def _push(
        self,
        user_ids: list[UUID],
        type: PushType,
        title: str,
        body: str,
        event: ReminderEvent | None,
        extra: dict[str, str] | None = None,
    ) -> None:
        """推播失敗只記 log，不影響提醒狀態。"""
        data = dict(extra or {})
        if event is not None:
            data["event_id"] = str(event.id)
            data["deeplink"] = f"{get_settings().frontend_base_url.rstrip('/')}/reminder/{event.id}"
        try:
            await self.notification.push(user_ids, type, title, body, data)
        except Exception:
            logger.exception("推播失敗 type=%s users=%s", type, user_ids)

    @staticmethod
    def _speech(title: str, event: ReminderEvent) -> str:
        """朗讀藥名用建立提醒時的快照（編號停用後會被重用）；舊資料沒有 speech_name 時由藥名推得。"""
        items = [
            (i["number"], i.get("speech_name") or speech.drug_name(i["name"]), Decimal(i["qty"])) for i in event.items
        ]
        return speech.reminder(title=title, meal_word=rules.MEAL_WORD[event.slot_key], items=items)

    async def _to_out(self, event: ReminderEvent) -> ReminderOut:
        title, _ = await self._elder_title(event.elder_id)
        if event.acked_at is not None:
            status = ReminderStatus.ACKED
        elif event.escalated_at is not None:
            status = ReminderStatus.NO_RESPONSE
        else:
            status = ReminderStatus.PENDING
        return ReminderOut(
            id=event.id,
            elder_id=event.elder_id,
            elder_title=title,
            slot_key=event.slot_key,
            label=med_rules.SLOT_LABELS[event.slot_key],
            scheduled_at=event.scheduled_at,
            items=[DoseItem(number=i["number"], name=i["name"], qty=Decimal(i["qty"])) for i in event.items],
            speech_text=self._speech(title, event),
            status=status,
            attempts=event.attempts,
            acked_at=event.acked_at,
            escalated_at=event.escalated_at,
        )
