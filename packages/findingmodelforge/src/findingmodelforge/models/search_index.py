from collections.abc import Iterable
from typing import TYPE_CHECKING, NamedTuple, Sequence, TypedDict

import lancedb  # type: ignore
from lancedb.embeddings import OpenAIEmbeddings, get_registry  # type: ignore
from lancedb.pydantic import LanceModel, Vector  # type: ignore
from rerankers import Reranker  # type: ignore

from ..config import settings

if TYPE_CHECKING:
    from rerankers.reranker import BaseRanker  # type: ignore


def _lancedb_connection_closure():
    lancedb_connection: lancedb.DBConnection | None = None  # type: ignore

    def _get_lancedb_connection() -> lancedb.DBConnection:
        nonlocal lancedb_connection
        if lancedb_connection is None:
            lancedb_connection = lancedb.connect(settings.lancedb_uri)
        return lancedb_connection

    return _get_lancedb_connection


get_lancedb_connection = _lancedb_connection_closure()


class SearchIndexRecord(TypedDict):
    model_id: str
    name: str
    tags: list[str]
    text: str


class SearchResult(NamedTuple):
    model_id: str
    name: str
    tags: list[str]
    text: str


class SearchIndex:
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.db_conn: lancedb.DBConnection = get_lancedb_connection()

        def init_embedding_model():
            registry = get_registry()
            openai_embedding: OpenAIEmbeddings = registry.get("openai")  # type: ignore
            return openai_embedding.create(
                name=settings.lancedb_embeddings_model, api_key=settings.openai_api_key.get_secret_value()
            )

        self.embedding_model: OpenAIEmbeddings = init_embedding_model()

        class SearchIndexRecordModel(LanceModel):
            model_id: str
            name: str
            tags: list[str]
            text: str = self.embedding_model.SourceField()
            vector: Vector(self.embedding_model.ndims()) = self.embedding_model.VectorField()  # type: ignore

        self.schema = SearchIndexRecordModel
        _reranker = Reranker("rankllm", api_key=settings.openai_api_key.get_secret_value(), verbose=False)
        assert _reranker is not None
        self.reranker: BaseRanker = _reranker
        self._table = None

    @property
    def table(self):
        if self._table is None:
            self._table = self.db_conn.open_table(self.table_name)
        return self._table

    def index_defined(self) -> bool:
        return self.table_name in self.db_conn.table_names()
        # TODO: Check if the table has the expected embeddings config and number of records

    def index_count(self) -> int:
        return self.table.count_rows()

    async def build_semantic_indices(self, data_to_load: Iterable[SearchIndexRecord], drop_if_exists=False) -> int:
        db_conn = get_lancedb_connection()
        mode = "overwrite" if drop_if_exists else "create"
        fm_table = db_conn.create_table(self.table_name, schema=self.schema, mode=mode)

        fm_table.add(data_to_load)
        # TODO: Make sure we create a ANN search index on the vector field
        fm_table.create_fts_index("text", replace=True)
        fm_table.create_scalar_index("model_id", replace=True)
        # TODO: Create an appropriate index on the tags field
        self._table = fm_table
        return fm_table.count_rows()

    def has_record(self, model_id: str) -> bool:
        return self.table.count_rows(f"model_id == '{model_id}'") > 0

    def add_or_update_record(self, record: SearchIndexRecord | list[SearchIndexRecord]) -> None:
        records = record if isinstance(record, list) else [record]
        for record in records:
            if self.has_record(record["model_id"]):
                self.table.update(
                    where=f"model_id == '{record['model_id']}'",
                    values={"name": record["name"], "tags": record["tags"], "text": record["text"]},
                )
            else:
                self.table.add([record])

    def remove_record(self, model_id: str) -> None:
        self.table.delete(f"model_id == '{model_id}'")

    def hybrid_search(self, query: str) -> Sequence[SearchResult]:
        results = self.table.search(query, query_type="hybrid").to_list()
        return [SearchResult(r["model_id"], r["name"], r["tags"], r["text"]) for r in results]

    async def search(self, query: str, rerank: bool = True, top_k: int = 5) -> Sequence[SearchResult]:
        raw_results = self.hybrid_search(query)
        if not rerank:
            return raw_results[:top_k]
        result_index = {r.model_id: r for r in raw_results}
        ranked_results = await self.reranker.rank_async(
            query, docs=[r.text for r in raw_results], doc_ids=[r.model_id for r in raw_results]
        )
        results = [result_index[r.doc_id] for r in ranked_results.top_k(top_k)]
        return results
