from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

settings = get_settings()

# Normalise the URL to use the psycopg2 async dialect.
# Supabase provides  postgresql://  or  postgres://
# SQLAlchemy async needs  postgresql+psycopg2://  for sync-wrapped async
# or  postgresql+asyncpg://  for pure async.
# Since asyncpg won't build on Render's free/starter image without gcc,
# we use psycopg2 via the aiopg async wrapper instead.
_url = settings.database_url

# Strip any existing driver suffix first
for prefix in (
    "postgresql+asyncpg://",
    "postgresql+psycopg2://",
    "postgresql+aiopg://",
    "postgresql://",
    "postgres://",
):
    if _url.startswith(prefix):
        _url = "postgresql+psycopg2://" + _url[len(prefix):]
        break

engine = create_async_engine(
    _url,
    echo=settings.debug,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    # psycopg2 requires this flag when used with SQLAlchemy async
    pool_use_lifo=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields an async DB session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()