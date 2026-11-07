from sqlalchemy.ext.asyncio import AsyncSession


class EmergencyCardRepository:
    """emergency_cards、emergency_contacts、card_codes、card_access_logs、consents 的存取。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
