from sqlalchemy.ext.asyncio import AsyncSession


class AppointmentRepository:
    """appointments 的存取。院區、科別、醫師、門診經由 integrations/tpech 取得。"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
