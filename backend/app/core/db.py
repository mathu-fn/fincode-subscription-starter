from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """``AsyncSession`` を yield する FastAPI 依存関係。

    トランザクションは各サービスが ``session.begin()`` で開く責務を持つ。
    終了時にセッションはクローズされるが、自動コミットは行わない。
    """

    async with AsyncSessionLocal() as session:
        yield session
