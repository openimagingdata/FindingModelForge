import pytest_asyncio
from beanie import init_beanie
from findingmodelforge.models.finding_model_db import FindingModelDb
from motor.motor_asyncio import AsyncIOMotorClient

MONGO_DSN = "mongodb://localhost:27017"
DATABASE_NAME = "fmf_test"


@pytest_asyncio.fixture()  # scope="module", loop_scope="module")
async def db_init():
    client = AsyncIOMotorClient(MONGO_DSN)
    await client.drop_database(DATABASE_NAME)
    database = client.get_database(DATABASE_NAME)
    # loop = asyncio.get_event_loop()
    await init_beanie(database, document_models=[FindingModelDb])
    # return loop
