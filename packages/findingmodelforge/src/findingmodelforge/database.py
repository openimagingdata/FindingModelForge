from typing import Callable, Coroutine, Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from .config import settings
from .models.finding_info_db import FindingInfoDb
from .models.finding_model_db import FindingModelDb

# from .models.user_db import UserDb


def _mongodb_client_closure() -> Callable[[], AsyncIOMotorClient]:
    mongodb_client: AsyncIOMotorClient | None = None

    def _get_mongodb_client() -> AsyncIOMotorClient:
        nonlocal mongodb_client
        if mongodb_client is None:
            mongodb_client = AsyncIOMotorClient(str(settings.mongo_dsn.get_secret_value()))
        return mongodb_client

    return _get_mongodb_client


get_mongodb_client = _mongodb_client_closure()


def get_mongodb_database() -> AsyncIOMotorDatabase:
    db = get_mongodb_client().get_database(settings.database_name)
    return db


def _beanie_initializer_closure() -> Callable[[Optional[bool]], Coroutine[None, None, None]]:
    from beanie import init_beanie

    beanie_initialized = False

    async def _init_beanie(verbose: Optional[bool] = False) -> None:
        nonlocal beanie_initialized
        if not beanie_initialized:
            db = get_mongodb_database()
            await init_beanie(db, document_models=[FindingModelDb, FindingInfoDb])  # , UserDb])
            beanie_initialized = True
            if verbose:
                print("Initialized Beanie ODM with models: FindingModelDb, FindingInfoDb")  # , UserDb")
                print("Finding models: ", await FindingModelDb.count())
                print("Finding info: ", await FindingInfoDb.count())

    return _init_beanie


init_document_models = _beanie_initializer_closure()
