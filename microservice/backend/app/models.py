"""匯入所有 ORM 模型，讓 Base.metadata 完整（Alembic 使用）。新增模組時記得加在這裡。"""

from app.core.db import Base
from app.modules.appointment import models as _appointment  # noqa: F401
from app.modules.auth import models as _auth  # noqa: F401
from app.modules.emergency_card import models as _emergency_card  # noqa: F401
from app.modules.family import models as _family  # noqa: F401
from app.modules.medication import models as _medication  # noqa: F401
from app.modules.notification import models as _notification  # noqa: F401
from app.modules.reminder import models as _reminder  # noqa: F401
from app.modules.responder import models as _responder  # noqa: F401

metadata = Base.metadata
