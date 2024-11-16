from typing import AsyncGenerator

import pytest
import pytest_asyncio
from beanie import init_beanie
from dynaconf import settings  # type: ignore
from findingmodelforge.models.finding_model_db import FindingModelDb
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_DSN = "mongodb://localhost:27017"
DATABASE_NAME = "fmf_test"


@pytest.fixture(scope="session", autouse=True)
def set_test_settings():
    settings.configure(FORCE_ENV_FOR_DYNACONF="testing")


@pytest_asyncio.fixture()
async def db_init() -> AsyncGenerator[None, None]:
    client: AsyncIOMotorClient = AsyncIOMotorClient(settings.MONGO_DSN)
    database = client.get_database(settings.DATABASE_NAME)
    await init_beanie(database, document_models=[FindingModelDb])
    yield
    await client.drop_database(settings.DATABASE_NAME)
    client.close()
