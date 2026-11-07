import datetime as dt
import json
from collections import Counter
from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import clock
from app.core.errors import Conflict, NotFound, ValidationFailed
from app.modules.family.service import Access, FamilyService
from app.modules.medication import rules
from app.modules.medication.models import (
    DrugLicense,
    MealTiming,
    Medication,
    MedicationStatus,
    Prescription,
    PrescriptionSource,
    PrescriptionStatus,
    SlotKey,
    StopReason,
)
from app.modules.medication.repository import MedicationRepository
from app.modules.medication.schemas import (
    DoseItem,
    DraftItem,
    DrugSearchItem,
    LastVisit,
    MedicationOut,
    MedicationUpdate,
    MedicationWarning,
    NextDoseOut,
    PhotoIn,
    PrescriptionCreate,
    PrescriptionCreated,
    PrescriptionDraft,
    PrescriptionOut,
    PrescriptionUpdate,
    PreviewItem,
    PreviewOut,
    RxQrPayload,
    RxQrPayloadV1,
    ScheduleRow,
    SlotGroup,
    StrengthOption,
    TimeSlotItem,
    TodayOut,
    TodaySlot,
    Uncertain,
    WarningType,
)
from app.modules.speech import rules as speech

# 往後找「下一次吃藥」最多找幾天
_NEXT_DOSE_LOOKAHEAD_DAYS = 7
_SEARCH_LIMIT = 8
_SEARCH_MIN_CHARS = 2

Row = tuple[Medication, Prescription]
Names = dict[str, tuple[str, str | None]]


class _Match(BaseModel):
    license_no: str | None
    strength: str | None
    score: float


class MedicationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = MedicationRepository(session)
        self.family = FamilyService(session)

    # ---------- 新增藥單的三條路徑：預覽（不寫入） ----------

    async def preview_qr(self, user_id: UUID, elder_id: UUID, raw: str | None) -> PreviewOut:
        """掃藥袋 QR Code。"""
        await self.family.ensure_access(user_id, elder_id, Access.WRITE)
        return await self._preview(elder_id, self._parse_qr(raw), [])

    async def preview_photo(self, user_id: UUID, elder_id: UUID, body: PhotoIn) -> PreviewOut:
        """拍藥袋照片：手機辨識出欄位後送來，後端比對健保藥品資料、算出每個欄位的信心分數。"""
        await self.family.ensure_access(user_id, elder_id, Access.WRITE)
        draft, uncertain = await self._recognize(body)
        return await self._preview(elder_id, draft, uncertain)

    async def preview(self, user_id: UUID, elder_id: UUID, draft: PrescriptionDraft) -> PreviewOut:
        """手動新增，或在確認畫面修改後，再看一次全部資料（E06a）。"""
        await self.family.ensure_access(user_id, elder_id, Access.WRITE)
        return await self._preview(elder_id, draft, [])

    # ---------- 加入、藥單 ----------

    async def create(self, user_id: UUID, elder_id: UUID, body: PrescriptionCreate) -> PrescriptionCreated:
        """「確認無誤，加入藥單」：配一個字母，記錄核對的人。"""
        await self.family.ensure_access(user_id, elder_id, Access.WRITE)
        if body.days is None:
            raise ValidationFailed("請填寫吃幾天", code="DAYS_REQUIRED")

        await self.repo.lock_elder(elder_id)
        letter = await self._next_letter(elder_id)
        warnings = await self._warnings(letter, body.items, await self.repo.list_active(elder_id))

        prescription = Prescription(
            elder_id=elder_id,
            letter=letter,
            source=body.source,
            hospital=body.hospital,
            department=body.department,
            doctor=body.doctor,
            visit_date=body.visit_date,
            days=body.days,
            status=PrescriptionStatus.ACTIVE,
            created_by=user_id,
        )
        await self.repo.add(prescription)
        medications = []
        for seq, item in enumerate(body.items, start=1):
            medication = Medication(
                prescription_id=prescription.id,
                elder_id=elder_id,
                seq=seq,
                status=MedicationStatus.ACTIVE,
                **{**item.model_dump(), "slots": [s.value for s in item.slots]},
            )
            await self.repo.add(medication)
            medications.append(medication)
        await self.session.commit()

        codes = "、".join(rules.code(letter, m.seq) for m in medications)
        return PrescriptionCreated(
            prescription=await self._prescription_out(prescription, medications),
            warnings=warnings,
            schedule=self._schedule(letter, body.items),
            message=f"請用筆在這個藥袋上寫一個大大的「{letter}」。手機上的 {codes}，就是這個藥袋裡的藥。",
        )

    async def list_prescriptions(
        self, user_id: UUID, elder_id: UUID, status: PrescriptionStatus = PrescriptionStatus.ACTIVE
    ) -> list[PrescriptionOut]:
        """我的藥單：吃藥中（依字母），或已吃完（新的在前）。"""
        await self.family.ensure_access(user_id, elder_id, Access.READ)
        await self.repo.finish_expired(elder_id, clock.today_taipei(), clock.now())
        prescriptions = await self.repo.list_prescriptions(elder_id, status)
        medications = await self.repo.list_by_prescriptions([p.id for p in prescriptions])
        await self.session.commit()
        names = await self._names(medications)
        return [
            await self._prescription_out(p, [m for m in medications if m.prescription_id == p.id], names)
            for p in prescriptions
        ]

    async def get_prescription(self, user_id: UUID, elder_id: UUID, prescription_id: UUID) -> PrescriptionOut:
        await self.family.ensure_access(user_id, elder_id, Access.READ)
        prescription = await self._get_prescription(elder_id, prescription_id)
        return await self._prescription_out(prescription, await self.repo.list_by_prescriptions([prescription.id]))

    async def update_prescription(
        self, user_id: UUID, elder_id: UUID, prescription_id: UUID, body: PrescriptionUpdate
    ) -> PrescriptionOut:
        """補填院區、科別、醫師，或修改看診日、天數。"""
        await self.family.ensure_access(user_id, elder_id, Access.WRITE)
        prescription = await self._get_prescription(elder_id, prescription_id)
        for field, value in body.model_dump(exclude_none=True).items():
            setattr(prescription, field, value)
        await self.session.commit()
        return await self._prescription_out(prescription, await self.repo.list_by_prescriptions([prescription.id]))

    async def finish_prescription(self, user_id: UUID, elder_id: UUID, prescription_id: UUID) -> PrescriptionOut:
        """提早移到「已吃完」（例如醫生說不用吃了），字母釋放。重複呼叫不會出錯。"""
        await self.family.ensure_access(user_id, elder_id, Access.WRITE)
        prescription = await self._get_prescription(elder_id, prescription_id)
        if prescription.status is PrescriptionStatus.ACTIVE:
            prescription.status = PrescriptionStatus.FINISHED
            prescription.finished_at = clock.now()
            await self.session.commit()
        return await self._prescription_out(prescription, await self.repo.list_by_prescriptions([prescription.id]))

    # ---------- 藥品 ----------

    async def get_medication(self, user_id: UUID, elder_id: UUID, medication_id: UUID) -> MedicationOut:
        await self.family.ensure_access(user_id, elder_id, Access.READ)
        medication, prescription = await self._get_medication(elder_id, medication_id)
        return self._to_out(medication, prescription, await self._names([medication]))

    async def update_medication(
        self, user_id: UUID, elder_id: UUID, medication_id: UUID, body: MedicationUpdate
    ) -> MedicationOut:
        await self.family.ensure_access(user_id, elder_id, Access.WRITE)
        medication, prescription = await self._get_medication(elder_id, medication_id)
        if medication.status is MedicationStatus.STOPPED or prescription.status is PrescriptionStatus.FINISHED:
            raise Conflict("這個藥已經停用或吃完，不能修改", code="MEDICATION_STOPPED")
        for field, value in body.model_dump(exclude_none=True).items():
            setattr(medication, field, [s.value for s in value] if field == "slots" else value)
        await self.session.commit()
        return self._to_out(medication, prescription, await self._names([medication]))

    async def stop_medication(
        self, user_id: UUID, elder_id: UUID, medication_id: UUID, reason: StopReason
    ) -> MedicationOut:
        """停用後不再提醒。重複停用不會出錯。"""
        await self.family.ensure_access(user_id, elder_id, Access.WRITE)
        medication, prescription = await self._get_medication(elder_id, medication_id)
        if medication.status is MedicationStatus.ACTIVE:
            medication.status = MedicationStatus.STOPPED
            medication.stopped_at = clock.now()
            medication.stop_reason = reason
            await self.session.commit()
        return self._to_out(medication, prescription, await self._names([medication]))

    # ---------- 藥名搜尋（手動新增） ----------

    async def search_drugs(self, query: str) -> list[DrugSearchItem]:
        """打 2 個字以上才搜尋；中英文都可以、不分大小寫、比對字首；同藥名只出現一次，再選劑量。

        北市聯醫常用藥（模擬）排前面，口服劑型排在注射、外用前面，再依品項多寡，最多 8 筆。
        """
        query = query.strip()
        if len(query) < _SEARCH_MIN_CHARS:
            return []
        candidates = [
            d
            for d in await self.repo.search_candidates([rules.search_key(query)])
            if rules.matches_prefix(query, d.product_en, d.product_zh, d.ingredient_en, rules.display_name(d.product_en))
        ]
        groups: dict[str, list[DrugLicense]] = {}
        for d in candidates:
            groups.setdefault(d.product_en or d.name_en or d.name_zh, []).append(d)

        q = rules.search_key(query)
        ranked = sorted(
            ((self._search_item(rows), len(rows)) for rows in groups.values()),
            key=lambda pair: (
                not pair[0].common,
                not rules.is_oral(pair[0].form),
                not rules.search_key(pair[0].name).startswith(q),
                -pair[1],  # 品項多（多家藥廠、多種包裝）的比較常見
                len(pair[0].name),
                pair[0].name,
            ),
        )
        return [item for item, _ in ranked[:_SEARCH_LIMIT]]

    # ---------- 今天、下一次吃藥 ----------

    async def today(self, user_id: UUID, elder_id: UUID, day: dt.date | None = None) -> TodayOut:
        """今天四個時段的藥（首頁、時段用藥詳情、家屬首頁）。沒有藥的時段不列出。"""
        await self.family.ensure_access(user_id, elder_id, Access.READ)
        day = day or clock.today_taipei()
        rows = await self.repo.list_active(elder_id)
        slots = [s for slot_key in rules.SLOT_ORDER if (s := self._slot_view(rows, slot_key, day)) is not None]
        return TodayOut(date=day, slots=slots)

    async def next_dose(self, user_id: UUID, elder_id: UUID) -> NextDoseOut | None:
        """首頁「下一次吃藥」。沒有要吃的藥時回傳 null。"""
        await self.family.ensure_access(user_id, elder_id, Access.READ)
        rows = await self.repo.list_active(elder_id)
        now = clock.now().astimezone(clock.TAIPEI)
        for offset in range(_NEXT_DOSE_LOOKAHEAD_DAYS + 1):
            day = now.date() + dt.timedelta(days=offset)
            for slot_key in rules.SLOT_ORDER:
                at = dt.datetime.combine(day, rules.SLOT_TIMES[slot_key], tzinfo=clock.TAIPEI)
                if at <= now:
                    continue
                if items := self._doses(rows, slot_key, day):
                    return NextDoseOut(
                        slot_key=slot_key, label=rules.SLOT_LABELS[slot_key], at=at, is_today=offset == 0, items=items
                    )
        return None

    # ---------- 提供給其他模組（呼叫端自行檢查權限） ----------

    async def list_active_doses(self, elder_id: UUID, day: dt.date | None = None) -> list[DoseItem]:
        """正在吃的藥（救命卡用）：吃藥中、且這天在用藥期間內。"""
        day = day or clock.today_taipei()
        return [
            self._dose(m, p)
            for m, p in await self.repo.list_active(elder_id)
            if rules.is_scheduled_on(p.visit_date, p.days, day)
        ]

    async def slot_view(self, elder_id: UUID, slot_key: SlotKey, day: dt.date) -> TodaySlot | None:
        """某天某時段要吃的藥與朗讀稿（吃藥提醒用）；沒有藥時回傳 None。"""
        return self._slot_view(await self.repo.list_active(elder_id), slot_key, day)

    async def elders_scheduled_on(self, day: dt.date) -> list[UUID]:
        """這天有藥要吃的長輩（排程用）。"""
        rows = await self.repo.list_all_active()
        return sorted({m.elder_id for m, p in rows if rules.is_scheduled_on(p.visit_date, p.days, day)})

    async def running_out_on(self, run_out: dt.date) -> dict[UUID, list[Prescription]]:
        """在這天吃完的吃藥中藥單，依長輩分組（回診提醒用）。"""
        result: dict[UUID, dict[UUID, Prescription]] = {}
        for _, p in await self.repo.list_all_active():
            if rules.run_out_date(p.visit_date, p.days) == run_out:
                result.setdefault(p.elder_id, {})[p.id] = p
        return {elder_id: sorted(ps.values(), key=lambda p: p.letter) for elder_id, ps in result.items()}

    async def soonest_run_out(self, elder_id: UUID) -> list[Prescription]:
        """最快吃完的那幾張藥單（Demo 回診提醒用）。"""
        prescriptions = {p.id: p for _, p in await self.repo.list_active(elder_id)}.values()
        if not prescriptions:
            return []
        soonest = min(rules.run_out_date(p.visit_date, p.days) for p in prescriptions)
        return sorted(
            (p for p in prescriptions if rules.run_out_date(p.visit_date, p.days) == soonest), key=lambda p: p.letter
        )

    async def last_visit(self, elder_id: UUID) -> LastVisit | None:
        """最近看診的吃藥中藥單（回診預約「已從藥單 A 帶入科別」）。"""
        prescription = await self.repo.latest_active_prescription(elder_id)
        if prescription is None:
            return None
        return LastVisit(
            letter=prescription.letter,
            hospital=prescription.hospital,
            department=prescription.department,
            doctor=prescription.doctor,
            date=prescription.visit_date,
        )

    # ---------- 內部：預覽 ----------

    async def _preview(self, elder_id: UUID, draft: PrescriptionDraft, uncertain: list[Uncertain]) -> PreviewOut:
        await self.repo.finish_expired(elder_id, clock.today_taipei(), clock.now())
        letter = await self._next_letter(elder_id)
        warnings = await self._warnings(letter, draft.items, await self.repo.list_active(elder_id))
        await self.session.commit()
        items = []
        for seq, item in enumerate(draft.items, start=1):
            code = rules.code(letter, seq)
            fields = [u.field.removeprefix(f"items.{seq - 1}.") for u in uncertain if u.field.startswith(f"items.{seq - 1}.")]
            items.append(
                PreviewItem(
                    code=code,
                    slots=self._slot_items(item.slots),
                    meal_timing_label=rules.MEAL_TIMING_LABELS[item.meal_timing],
                    warnings=[w for w in warnings if w.code == code],
                    uncertain=bool(fields),
                    uncertain_fields=fields,
                )
            )
        return PreviewOut(
            letter=letter,
            draft=draft,
            items=items,
            uncertain=uncertain,
            warnings=warnings,
            schedule=self._schedule(letter, draft.items),
        )

    async def _next_letter(self, elder_id: UUID) -> str:
        letter = rules.next_letter(await self.repo.active_letters(elder_id))
        if letter is None:
            raise Conflict("吃藥中的藥單太多了，請先把吃完的藥單移到已吃完", code="TOO_MANY_PRESCRIPTIONS")
        return letter

    @staticmethod
    def _parse_qr(raw: str | None) -> PrescriptionDraft:
        if raw is None:
            raise ValidationFailed("沒有掃到 QR Code", code="QR_EMPTY")
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and data.get("v") == 1:
                return MedicationService._from_qr_v1(RxQrPayloadV1.model_validate(data))
            payload = RxQrPayload.model_validate(data)
        except (json.JSONDecodeError, ValidationError, TypeError) as exc:
            raise ValidationFailed("這不是藥袋上的 QR Code", code="QR_INVALID") from exc
        return PrescriptionDraft(
            source=PrescriptionSource.QR,
            hospital=payload.hosp,
            department=payload.dept,
            doctor=payload.dr,
            visit_date=payload.date,
            days=payload.days,
            items=[
                DraftItem(
                    name=i.name,
                    license_no=i.lic,
                    strength=i.mg,
                    purpose=i.use,
                    dose_qty=i.qty,
                    slots=i.when or rules.FREQUENCY_SLOTS[i.freq],  # type: ignore[index]  # schema 已確認擇一
                    meal_timing=i.meal,
                )
                for i in payload.items
            ],
        )

    @staticmethod
    def _from_qr_v1(payload: RxQrPayloadV1) -> PrescriptionDraft:
        bedtime = payload.meal == "bedtime"
        return PrescriptionDraft(
            source=PrescriptionSource.QR,
            hospital=payload.hosp,
            department=payload.dept,
            doctor=payload.dr,
            visit_date=payload.date,
            days=payload.days,
            items=[
                DraftItem(
                    name=payload.name,
                    license_no=payload.lic,
                    purpose=payload.use,
                    dose_qty=payload.qty,
                    slots=[SlotKey.BEDTIME] if bedtime else rules.FREQUENCY_SLOTS[payload.freq],
                    meal_timing=MealTiming.AFTER if bedtime else MealTiming(payload.meal),
                )
            ],
        )

    async def _recognize(self, body: PhotoIn) -> tuple[PrescriptionDraft, list[Uncertain]]:
        """把手機辨識的結果整理成草稿；看不出來的欄位填預設值，並列入「不確定」。"""
        uncertain: list[Uncertain] = []

        def check(field: str, confidence: float, message: str = "電腦不確定這一項，請照藥袋核對") -> None:
            if confidence < rules.CONFIDENCE_THRESHOLD:
                uncertain.append(Uncertain(field=field, confidence=round(confidence, 2), message=message))

        for field in ("hospital", "department", "doctor"):
            if getattr(body, field) is not None:
                check(field, body.confidence.get(field, 1.0))
        check("visit_date", body.confidence.get("visit_date", 1.0) if body.visit_date else 0.0, "請確認看診日")
        check("days", body.confidence.get("days", 1.0) if body.days else 0.0, "請照藥袋填寫吃幾天")

        items = []
        for index, item in enumerate(body.items):
            prefix, conf = f"items.{index}.", item.confidence
            match = await self._match_drug(item.name, item.license_no, item.strength)
            name = item.name or "看不清楚的藥"
            name_conf = min(conf.get("name", 1.0), match.score) if (item.name or item.license_no) else 0.0
            check(prefix + "name", name_conf, "電腦不確定這個藥名，請照藥袋核對")
            strength = item.strength or match.strength
            strength_conf = conf.get("strength", 1.0) if item.strength else (0.9 if match.strength else 0.0)
            if item.strength and match.strength and rules.search_key(item.strength) != rules.search_key(match.strength):
                strength_conf = min(strength_conf, 0.5)
            check(prefix + "strength", strength_conf, "請照藥袋核對毫克數")
            if item.purpose:
                check(prefix + "purpose", conf.get("purpose", 1.0))
            check(prefix + "dose_qty", conf.get("dose_qty", 1.0) if item.dose_qty else 0.0, "請照藥袋核對一次幾顆")
            slots = item.slots or (rules.FREQUENCY_SLOTS[item.frequency] if item.frequency else None)
            check(prefix + "slots", conf.get("slots", conf.get("frequency", 1.0)) if slots else 0.0, "請照藥袋核對什麼時候吃")
            check(prefix + "meal_timing", conf.get("meal_timing", 1.0) if item.meal_timing else 0.0, "請照藥袋核對飯前還是飯後")
            items.append(
                DraftItem(
                    name=name,
                    license_no=match.license_no,
                    strength=strength,
                    purpose=item.purpose,
                    dose_qty=item.dose_qty or Decimal(1),
                    slots=slots or [SlotKey.MORNING],
                    meal_timing=item.meal_timing or MealTiming.AFTER,
                )
            )
        draft = PrescriptionDraft(
            source=PrescriptionSource.PHOTO,
            hospital=body.hospital,
            department=body.department,
            doctor=body.doctor,
            visit_date=body.visit_date or clock.today_taipei(),
            days=body.days,
            items=items,
        )
        return draft, uncertain

    async def _match_drug(self, name: str | None, license_no: str | None, strength: str | None) -> _Match:
        """辨識出的藥名（或藥袋上的健保碼）對到健保藥品資料；score 為相似度。"""
        if license_no and (found := (await self.repo.get_licenses([license_no])).get(license_no)):
            return _Match(license_no=found.license_no, strength=found.strength, score=1.0)
        if not name:
            return _Match(license_no=None, strength=None, score=0.0)
        # 用每個字的前 3 個字母（中文前 2 個字）找候選，辨識錯字通常不在開頭
        key = rules.search_key(name)
        prefixes = list(dict.fromkeys(w[:3] if w.isascii() else w[:2] for w in key.split() if len(w) >= 2))[:3]
        best, best_score = None, 0.0
        for candidate in await self.repo.search_candidates(prefixes):
            score = max(
                rules.similarity(name, text)
                for text in (
                    candidate.product_en or "",
                    rules.display_name(candidate.product_en),
                    candidate.product_zh or "",
                    candidate.ingredient_en or "",
                    candidate.name_en or "",
                    candidate.name_zh,
                )
            )
            # 劑量也相同時優先
            if strength and candidate.strength and rules.search_key(strength) == rules.search_key(candidate.strength):
                score += 0.01
            if score > best_score:
                best, best_score = candidate, score
        if best is None or best_score < rules.NAME_MATCH_MIN:
            return _Match(license_no=None, strength=None, score=best_score)
        return _Match(license_no=best.license_no, strength=best.strength, score=min(best_score, 1.0))

    async def _warnings(self, letter: str, items: Sequence[DraftItem], active: list[Row]) -> list[MedicationWarning]:
        """和吃藥中的藥、或同一張藥單裡的另一個藥成分相同時標示。只標示，不阻擋。"""
        licenses = [i.license_no for i in items if i.license_no] + [m.license_no for m, _ in active if m.license_no]
        ingredients = await self.repo.ingredients_by_license(sorted(set(licenses)))

        def same(a: str | None, b: str | None) -> bool:
            return rules.same_ingredient(a, ingredients.get(a or "", []), b, ingredients.get(b or "", []))

        warnings = []
        for seq, item in enumerate(items, start=1):
            if not item.license_no:
                continue
            code = rules.code(letter, seq)
            others = [(rules.code(p.letter, m.seq), m.license_no) for m, p in active]
            others += [(rules.code(letter, s), i.license_no) for s, i in enumerate(items[: seq - 1], start=1)]
            warnings += [
                MedicationWarning(
                    type=WarningType.SAME_INGREDIENT, code=code, with_code=with_code, message=rules.SAME_INGREDIENT_MESSAGE
                )
                for with_code, other in others
                if same(item.license_no, other)
            ]
        return warnings

    @staticmethod
    def _schedule(letter: str, items: Sequence[DraftItem]) -> list[ScheduleRow]:
        return [
            ScheduleRow(
                slot_key=slot_key,
                label=rules.SLOT_LABELS[slot_key],
                time=rules.SLOT_TIMES[slot_key],
                codes=[rules.code(letter, seq) for seq, i in enumerate(items, start=1) if slot_key in i.slots],
            )
            for slot_key in rules.SLOT_ORDER
        ]

    @staticmethod
    def _search_item(rows: list[DrugLicense]) -> DrugSearchItem:
        first = rows[0]
        by_strength: dict[str, str] = {}
        for d in sorted(rows, key=lambda d: d.license_no):
            by_strength.setdefault(d.strength or "不分劑量", d.license_no)
        forms = Counter(d.form for d in rows if d.form)
        return DrugSearchItem(
            name=rules.display_name(first.product_en, first.name_en or first.name_zh),
            name_zh=next((d.product_zh for d in rows if d.product_zh), None),
            ingredient=next((d.ingredient_en for d in rows if d.ingredient_en), None),
            form=forms.most_common(1)[0][0] if forms else None,
            strengths=[
                StrengthOption(label=label, license_no=license_no)
                for label, license_no in sorted(by_strength.items(), key=lambda kv: rules.strength_number(kv[0]))
            ],
            common=any(atc in rules.COMMON_ATC for d in rows for atc in d.ingredients),
        )

    # ---------- 內部：輸出 ----------

    async def _get_prescription(self, elder_id: UUID, prescription_id: UUID) -> Prescription:
        prescription = await self.repo.get_prescription(elder_id, prescription_id)
        if prescription is None:
            raise NotFound("找不到這張藥單", code="PRESCRIPTION_NOT_FOUND")
        return prescription

    async def _get_medication(self, elder_id: UUID, medication_id: UUID) -> Row:
        row = await self.repo.get_medication(elder_id, medication_id)
        if row is None:
            raise NotFound("找不到這個藥", code="MEDICATION_NOT_FOUND")
        return row

    async def _names(self, medications: Sequence[Medication]) -> Names:
        """藥品代號 →（健保中文品名, 英文品名），朗讀藥名用。"""
        return await self.repo.names_by_license(sorted({m.license_no for m in medications if m.license_no}))

    async def _prescription_out(
        self, p: Prescription, medications: list[Medication], names: Names | None = None
    ) -> PrescriptionOut:
        names = names if names is not None else await self._names(medications)
        return PrescriptionOut(
            id=p.id,
            letter=p.letter,
            source=p.source,
            hospital=p.hospital,
            department=p.department,
            doctor=p.doctor,
            visit_date=p.visit_date,
            days=p.days,
            run_out_date=rules.run_out_date(p.visit_date, p.days),
            days_left=rules.days_left(p.visit_date, p.days, clock.today_taipei()),
            status=p.status,
            needs_review=any(m.needs_review for m in medications if m.status is MedicationStatus.ACTIVE),
            medications=[self._to_out(m, p, names) for m in sorted(medications, key=lambda m: m.seq)],
        )

    def _to_out(self, m: Medication, p: Prescription, names: Names) -> MedicationOut:
        slots = self._slot_items(rules.sort_slots(m.slots))
        name_zh, name_en = names.get(m.license_no or "", (None, None))
        card = dict(
            number=m.seq,
            department=p.department or "",
            purpose=m.purpose or "",
            dose_qty=m.dose_qty,
            meal_label=rules.MEAL_TIMING_LABELS[m.meal_timing],
            times=[s.time for s in slots],
            days_left=rules.days_left(p.visit_date, p.days, clock.today_taipei()),
        )
        return MedicationOut(
            id=m.id,
            prescription_id=p.id,
            letter=p.letter,
            seq=m.seq,
            code=rules.code(p.letter, m.seq),
            name=m.name,
            license_no=m.license_no,
            strength=m.strength,
            purpose=m.purpose,
            dose_qty=m.dose_qty,
            slots=slots,
            meal_timing=m.meal_timing,
            meal_timing_label=rules.MEAL_TIMING_LABELS[m.meal_timing],
            needs_review=m.needs_review,
            status=m.status,
            stop_reason=m.stop_reason,
            speech_text=speech.medication_card(drug=speech.drug_name(m.name, name_zh), **card),
            speech_text_en=speech.medication_card(
                drug=speech.drug_name_en(m.name, name_en), lang=speech.Lang.EN, **card
            ),
        )

    @staticmethod
    def _dose(m: Medication, p: Prescription) -> DoseItem:
        return DoseItem(
            code=rules.code(p.letter, m.seq),
            letter=p.letter,
            seq=m.seq,
            name=m.name,
            strength=m.strength,
            qty=m.dose_qty,
            purpose=m.purpose,
            meal_timing_label=rules.MEAL_TIMING_LABELS[m.meal_timing],
        )

    def _doses(self, rows: list[Row], slot_key: SlotKey, day: dt.date) -> list[DoseItem]:
        return [
            self._dose(m, p)
            for m, p in rows
            if slot_key.value in m.slots and rules.is_scheduled_on(p.visit_date, p.days, day)
        ]

    def _slot_view(self, rows: list[Row], slot_key: SlotKey, day: dt.date) -> TodaySlot | None:
        selected = [
            (m, p) for m, p in rows if slot_key.value in m.slots and rules.is_scheduled_on(p.visit_date, p.days, day)
        ]
        if not selected:
            return None
        groups: dict[str, SlotGroup] = {}
        for m, p in selected:
            group = groups.setdefault(
                p.letter, SlotGroup(letter=p.letter, hospital=p.hospital, department=p.department, items=[])
            )
            group.items.append(self._dose(m, p))
        time = rules.SLOT_TIMES[slot_key]
        spoken = [(g.letter, g.department or "", [(i.seq, i.qty) for i in g.items]) for g in groups.values()]
        return TodaySlot(
            slot_key=slot_key,
            label=rules.SLOT_LABELS[slot_key],
            time=time,
            items=[self._dose(m, p) for m, p in selected],
            groups=list(groups.values()),
            speech_text=speech.slot(time=time, groups=spoken),
            speech_text_en=speech.slot(time=time, groups=spoken, lang=speech.Lang.EN),
        )

    @staticmethod
    def _slot_items(slots: Sequence[SlotKey]) -> list[TimeSlotItem]:
        return [TimeSlotItem(slot_key=s, label=rules.SLOT_LABELS[s], time=rules.SLOT_TIMES[s]) for s in slots]
