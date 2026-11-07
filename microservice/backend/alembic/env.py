import asyncio
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.types import TypeDecorator

from alembic import context
from app.core.config import get_settings
from app.models import metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _render_item(type_: str, obj: object, autogen_context: object) -> str | bool:
    # 加密欄位等自訂 TypeDecorator 在資料庫裡只是底層型別（如 Text），migration 寫成 sa.Text()
    if type_ == "type" and isinstance(obj, TypeDecorator):
        return f"sa.{obj.impl!r}"
    return False


def run_migrations_offline() -> None:
    context.configure(
        url=get_settings().database_url,
        target_metadata=metadata,
        render_item=_render_item,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _run_sync(connection) -> None:
    context.configure(
        connection=connection, target_metadata=metadata, compare_type=True, render_item=_render_item
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(get_settings().database_url)
    async with engine.connect() as connection:
        await connection.run_sync(_run_sync)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
