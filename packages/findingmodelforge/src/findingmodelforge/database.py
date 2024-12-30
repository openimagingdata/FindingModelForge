from typing import NamedTuple, Sequence

import lancedb  # type: ignore
from lancedb.embeddings import OpenAIEmbeddings, get_registry  # type: ignore
from lancedb.pydantic import LanceModel, Vector  # type: ignore
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from rerankers import Reranker  # type: ignore
from rerankers.reranker import BaseRanker  # type: ignore

from .config import settings
from .models.finding_info_db import FindingInfoDb
from .models.finding_model_db import FindingModelDb

# from .models.user_db import UserDb

_mongodb_client: AsyncIOMotorClient | None = None


def get_mongodb_client() -> AsyncIOMotorClient:
    global _mongodb_client
    if _mongodb_client is None:
        _mongodb_client = AsyncIOMotorClient(str(settings.mongo_dsn.get_secret_value()))
    return _mongodb_client


def get_mongodb_database() -> AsyncIOMotorDatabase:
    db = get_mongodb_client().get_database(settings.database_name)
    return db


def _create_beanie_initializer():
    from beanie import init_beanie

    beanie_initialized = False

    async def _init_beanie(verbose: bool = False) -> None:
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


init_document_models = _create_beanie_initializer()


def _init_lancedb_embedding_model() -> OpenAIEmbeddings:
    registry = get_registry()
    openai_embedding: OpenAIEmbeddings = registry.get("openai")
    return openai_embedding.create(
        name=settings.lancedb_embeddings_model, api_key=settings.openai_api_key.get_secret_value()
    )


_lancedb_embedding_model: OpenAIEmbeddings = _init_lancedb_embedding_model()

_lancedb_connection: lancedb.DBConnection | None = None


def get_lancedb_connection() -> lancedb.DBConnection:
    global _lancedb_connection
    if _lancedb_connection is None:
        _lancedb_connection = lancedb.connect(settings.lancedb_uri)
    return _lancedb_connection


class FindingModel(LanceModel):
    model_id: str
    name: str
    tags: list[str]
    text: str = _lancedb_embedding_model.SourceField()
    vector: Vector(_lancedb_embedding_model.ndims()) = _lancedb_embedding_model.VectorField()  # type: ignore


def has_semantic_indices() -> bool:
    db_conn = get_lancedb_connection()
    return "finding_models" in db_conn.table_names()
    # TODO: Check if the table has the expected embeddings config and number of records


async def build_semantic_indices(drop_if_exists=False) -> int:
    db_conn = get_lancedb_connection()
    mode = "overwrite" if drop_if_exists else "create"
    fm_table = db_conn.create_table("finding_models", schema=FindingModel, mode=mode)

    await init_document_models()
    data_to_load = []
    async for fm in FindingModelDb.find():
        data = {
            "model_id": str(fm.id),
            "tags": fm.tags,
            "name": fm.name,
            "text": f"{fm.name}\n\nDescription: {fm.description}",
        }
        data_to_load.append(data)

    fm_table.add(data_to_load)
    fm_table.create_fts_index("text", replace=True)
    fm_table.create_scalar_index("model_id", replace=True)
    # TODO: Create an appropriate index on the tags field
    return fm_table.count_rows()


_reranker: BaseRanker | None = None


def get_reranker() -> BaseRanker:
    global _reranker
    if _reranker is None:
        _reranker = Reranker("rankllm", api_key=settings.openai_api_key.get_secret_value(), verbose=False)
        assert _reranker is not None
    return _reranker


class LanceDbSearchResult(NamedTuple):
    model_id: str
    name: str
    tags: list[str]
    text: str


def do_hybrid_search(query: str) -> Sequence[LanceDbSearchResult]:
    fm_table = get_lancedb_connection().open_table("finding_models")
    results = fm_table.search(query, query_type="hybrid").to_list()
    return [
        LanceDbSearchResult(model_id=r["model_id"], name=r["name"], tags=r["tags"], text=r["text"]) for r in results
    ]


async def search(query: str, reranked: bool = True, top_k: int = 5) -> Sequence[FindingModelDb]:
    raw_results = do_hybrid_search(query)
    if reranked:
        ranked_results = await get_reranker().rank_async(
            query, docs=[r.text for r in raw_results], doc_ids=[r.model_id for r in raw_results]
        )
        model_ids = [r.doc_id for r in ranked_results.top_k(top_k)]
    else:
        model_ids = [r.model_id for r in raw_results[:top_k]]
    finding_models = await FindingModelDb.get_many(model_ids)
    return finding_models
