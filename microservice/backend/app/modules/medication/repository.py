from sqlalchemy.ext.asyncio import AsyncSession


class MedicationRepository:
    """medications、time_slots、drug_licenses 的存取。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
