from typing import AsyncGenerator

import pytest
import pytest_asyncio
from beanie import init_beanie
from findingmodelforge import settings
from findingmodelforge.models.finding_model_db import FindingModelDb
from motor.motor_asyncio import AsyncIOMotorClient


@pytest.fixture(scope="session", autouse=True)
def set_test_settings():
    settings.environment = "testing"


@pytest_asyncio.fixture()
async def db_init() -> AsyncGenerator[None, None]:
    client: AsyncIOMotorClient = AsyncIOMotorClient(str(settings.mongo_dsn))
    database = client.get_database(settings.database_name)
    await init_beanie(database, document_models=[FindingModelDb])
    yield
    await client.drop_database(settings.database_name)
    client.close()
