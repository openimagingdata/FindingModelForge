import pytest_asyncio
from beanie import init_beanie
from findingmodelforge.models.finding_model_db import FindingModelDb
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_DSN = "mongodb://localhost:27017"
DATABASE_NAME = "fmf_test"


@pytest_asyncio.fixture()
async def db_init():
    client: AsyncIOMotorClient = AsyncIOMotorClient(MONGO_DSN)
    database = client.get_database(DATABASE_NAME)
    await init_beanie(database, document_models=[FindingModelDb])
    yield
    await client.drop_database(DATABASE_NAME)
    client.close()
