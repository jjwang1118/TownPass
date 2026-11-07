from sqlalchemy.ext.asyncio import AsyncSession


class ResponderRepository:
    """responders 的存取。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
