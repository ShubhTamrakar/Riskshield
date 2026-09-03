import pytest
import pytest_asyncio
import asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from app.main import app
from app.api.deps import get_db
from app.core.config import settings

test_engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI, poolclass=NullPool)
TestingSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    # Tables are created by Alembic migrations; nothing to do here.
    yield


@pytest_asyncio.fixture()
async def db() -> AsyncSession:
    async with TestingSessionLocal() as session:
        yield session


@pytest_asyncio.fixture()
async def client(db: AsyncSession) -> AsyncClient:
    app.dependency_overrides[get_db] = lambda: db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
