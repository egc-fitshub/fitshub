import time
from datetime import datetime

from elasticsearch import (
    ApiError,
    BadRequestError,
    ConnectionError,
    Elasticsearch,
    NotFoundError,
)
from flask import current_app

from app.modules.elasticsearch.repositories import ElasticsearchRepository
from core.services.BaseService import BaseService


class ElasticsearchService(BaseService):
    def __init__(self, host=None, index_name=None):
        config = {}
        try:
            config = current_app.config
        except RuntimeError:
            # No application context available (e.g., running from CLI)
            config = {}

        if host is None:
            host = config.get(
                "ELASTICSEARCH_HOST",
                "http://elasticsearch:9200",
            )

        if index_name is None:
            index_name = config.get("ELASTICSEARCH_INDEX", "search_index")
        retry_attempts = int(config.get("ELASTICSEARCH_RETRY_ATTEMPTS", 5))
        retry_delay = int(config.get("ELASTICSEARCH_RETRY_DELAY", 2))

        if not isinstance(index_name, str):
            raise ValueError("El nombre del índice debe ser una cadena de texto.")

        if not index_name:
            raise ValueError("El nombre del índice no puede estar vacío.")

        if any(c in index_name for c in r" #?/\*\"<>|,"):
            raise ValueError("El nombre del índice contiene caracteres no permitidos.")

        if not index_name.islower():
            raise ValueError("El nombre del índice debe estar en minúsculas.")

        if index_name.startswith(("-", "_", "+")):
            raise ValueError("El nombre del índice no puede comenzar con '-', '_' o '+'.")

        super().__init__(ElasticsearchRepository())
        self.es = Elasticsearch(hosts=[host])
        self.index_name = index_name
        self.host = host
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay

        if not self.wait_for_elasticsearch(retries=self.retry_attempts, delay=self.retry_delay):
            raise ConnectionError(f"No se pudo conectar a Elasticsearch en el host proporcionado: {host}")

        try:
            self.create_index_if_not_exists()
        except Exception:
            # Si la creación falla, permitimos que continúe; las búsquedas gestionarán el error.
            try:
                current_app.logger.exception("No se pudo asegurar la existencia del índice de Elasticsearch")
            except RuntimeError:
                print("[WARN] No se pudo asegurar la existencia del índice de Elasticsearch")

    def wait_for_elasticsearch(self, retries=5, delay=2):
        for attempt in range(retries):
            try:
                if self.es.ping():
                    return True
            except ConnectionError:
                pass
            time.sleep(delay)
        return False

    def create_index_if_not_exists(self):
        print(f"Verificando si el índice '{self.index_name}' existe...")
        try:
            existe_index = self.es.indices.exists(index=self.index_name)

            if not existe_index:
                self.es.indices.create(
                    index=self.index_name,
                    body={
                        "settings": {
                            "analysis": {
                                "analyzer": {
                                    "custom_text_analyzer": {
                                        "type": "custom",
                                        "tokenizer": "standard",
                                        "filter": ["lowercase", "asciifolding"],
                                    },
                                    "custom_filename_analyzer": {
                                        "type": "custom",
                                        "tokenizer": "custom_filename_tokenizer",
                                        "filter": ["lowercase", "asciifolding"],
                                    },
                                },
                                "tokenizer": {
                                    "custom_filename_tokenizer": {
                                        "type": "pattern",
                                        "pattern": "[_\\W]+",
                                    }
                                },
                            },
                            "index": {"number_of_shards": 1, "number_of_replicas": 0},
                        },
                        "mappings": {
                            "properties": {
                                "type": {"type": "keyword"},
                                "title": {
                                    "type": "text",
                                    "analyzer": "custom_text_analyzer",
                                },
                                "description": {
                                    "type": "text",
                                    "analyzer": "custom_text_analyzer",
                                },
                                "filename": {
                                    "type": "text",
                                    "analyzer": "custom_filename_analyzer",
                                },
                                "tags": {
                                    "type": "text",
                                    "analyzer": "custom_text_analyzer",
                                    "fields": {"keyword": {"type": "keyword"}},
                                },
                                "publication_type": {"type": "keyword"},
                                "publication_type_label": {
                                    "type": "text",
                                    "analyzer": "custom_text_analyzer",
                                },
                                "created_at": {"type": "date"},
                                "doi": {"type": "keyword"},
                                "authors": {
                                    "type": "nested",
                                    "properties": {
                                        "name": {
                                            "type": "text",
                                            "analyzer": "custom_text_analyzer",
                                        },
                                        "affiliation": {
                                            "type": "text",
                                            "analyzer": "custom_text_analyzer",
                                        },
                                        "orcid": {"type": "keyword"},
                                    },
                                },
                                "content": {
                                    "type": "text",
                                    "analyzer": "custom_text_analyzer",
                                },
                                "url": {"type": "keyword"},
                                "dataset_id": {"type": "integer"},
                                "fits_model_id": {"type": "integer"},
                                "dataset_title": {
                                    "type": "text",
                                    "analyzer": "custom_text_analyzer",
                                },
                                "checksum": {"type": "keyword"},
                                "total_size_in_bytes": {"type": "long"},
                                "files_count": {"type": "integer"},
                                "size_in_bytes": {"type": "long"},
                                "size_in_human_format": {
                                    "type": "text",
                                    "analyzer": "custom_text_analyzer",
                                },
                            }
                        },
                    },
                )

            else:
                print(f"El índice '{self.index_name}' ya existe.")

        except BadRequestError as e:
            print(f"Error al crear el índice '{self.index_name}': {e.info}")
            raise
        except ApiError as e:
            print(f"Error de API al crear el índice '{self.index_name}': {e.info}")
            raise
        except Exception as e:
            print(f"Error inesperado al crear el índice '{self.index_name}': {str(e)}")
            raise

    def index_document(self, doc_id: str, data: dict):
        try:
            self.es.index(index=self.index_name, id=doc_id, document=data)
        except Exception as e:
            print(f"Error al indexar el documento con ID '{doc_id}': {str(e)}")
            raise

    def delete_document(self, doc_id: str):
        try:
            self.es.delete(index=self.index_name, id=doc_id)
        except NotFoundError:
            print(f"Documento con ID '{doc_id}' no encontrado para eliminar.")
        except Exception as e:
            print(f"Error al eliminar el documento con ID '{doc_id}': {str(e)}")
            raise

    def search(
        self,
        query: str,
        publication_type=None,
        sorting="newest",
        tags=None,
        date_from=None,
        date_to=None,
        page=1,
        size=10,
    ):
        try:
            print(
                f"[DEBUG] Buscando en '{self.index_name}' "
                f"con query: '{query}', "
                f"tipo: {publication_type}, "
                f"tags: {tags}, "
                f"orden: {sorting}, "
                f"página: {page}, tamaño: {size}"
            )

            must_clauses = []
            filter_clauses = []

            # Texto libre
            if query:
                text_fields_clause = {
                    "multi_match": {
                        "query": query,
                        "fields": [
                            "title^4",
                            "description^3",
                            "filename^2",
                        ],
                        "fuzziness": "AUTO",
                    }
                }

                author_nested_clause = {
                    "nested": {
                        "path": "authors",
                        "score_mode": "avg",
                        "query": {
                            "multi_match": {
                                "query": query,
                                "fields": [
                                    "authors.name^2",
                                    "authors.affiliation",
                                ],
                                "fuzziness": "AUTO",
                                "operator": "and",
                            }
                        },
                    }
                }

                must_clauses.append(
                    {
                        "bool": {
                            "should": [text_fields_clause, author_nested_clause],
                            "minimum_should_match": 1,
                        }
                    }
                )

            # Filtro por tipo de publicación (ignorar valores sentinela como "any"/"all")
            normalized_publication_type = (publication_type or "").strip()
            if normalized_publication_type:
                normalized_publication_type = normalized_publication_type.lower()

            if normalized_publication_type not in ("", "any", "all"):
                filter_clauses.append({"term": {"publication_type": normalized_publication_type}})

            # Filtro por tags
            if tags:
                filter_clauses.append({"terms": {"tags.keyword": tags}})

            # Filtro por fechas
            if date_from or date_to:
                try:
                    range_query = {"range": {"created_at": {}}}

                    if date_from:
                        # Normalizar y validar formato
                        dt_from = datetime.strptime(date_from, "%Y-%m-%d")
                        range_query["range"]["created_at"]["gte"] = dt_from.strftime("%Y-%m-%dT00:00:00Z")

                    if date_to:
                        dt_to = datetime.strptime(date_to, "%Y-%m-%d")
                        range_query["range"]["created_at"]["lte"] = dt_to.strftime("%Y-%m-%dT23:59:59Z")

                    if "gte" in range_query["range"]["created_at"] or "lte" in range_query["range"]["created_at"]:
                        filter_clauses.append(range_query)

                except ValueError as e:
                    print(f"[WARN] Formato de fecha inválido recibido: from={date_from}, to={date_to}. Error: {e}")

            # Ordenación
            sort_clause = [
                {"created_at": {"order": "desc"}} if sorting == "newest" else {"created_at": {"order": "asc"}}
            ]

            # Calcular offset
            from_ = (page - 1) * size

            body = {
                "query": {
                    "bool": {
                        "must": must_clauses if must_clauses else [{"match_all": {}}],
                        "filter": filter_clauses,
                    }
                },
                "sort": sort_clause,
            }

            try:
                result = self.es.search(
                    index=self.index_name,
                    body=body,
                    from_=from_,
                    size=size,
                )
            except NotFoundError:
                self.create_index_if_not_exists()
                return [], 0

            hits = result["hits"]["hits"]
            total = result["hits"]["total"]["value"]

            print(f"[SUCCESS] Búsqueda completada. Página {page}, resultados: {len(hits)}, total: {total}")

            return [self._format_hit(hit) for hit in hits], total

        except Exception as e:
            print(f"[ERROR] Fallo en la búsqueda: {e}")
            raise

    def _format_hit(self, hit):
        from datetime import datetime

        source = hit["_source"]

        # Formato de fecha
        if "created_at" in source:
            try:
                dt = datetime.fromisoformat(source["created_at"])
                source["created_at"] = dt.strftime("%d %b %Y, %H:%M")
            except Exception:
                pass

        # Tamaño legible
        if "total_size_in_bytes" in source:
            source["total_size_in_human_format"] = self._human_readable_size(source["total_size_in_bytes"])

        return source

    def _human_readable_size(self, size_bytes):
        if size_bytes is None:
            return ""
        if size_bytes == 0:
            return "0 B"
        size_name = ("B", "KB", "MB", "GB", "TB")
        i = int(min(len(size_name) - 1, max(0, (size_bytes.bit_length() - 1) // 10)))
        p = 1 << (i * 10)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"


class IndexingService:
    """
    Encapsula la lógica de indexación en Elasticsearch.
    """

    def __init__(self, index_dataset_fn, index_hubfile_fn, logger):
        self.index_dataset = index_dataset_fn
        self.index_hubfile = index_hubfile_fn
        self.logger = logger

    def index_dataset_and_hubfiles(self, dataset, created_fms):
        try:
            # Re-obtener dataset actualizado
            self.index_dataset(dataset)
            self.logger.info(f"[INDEX] Dataset {dataset.id} indexed")

            for fm in created_fms:
                hubfiles = getattr(fm, "hubfiles", None)
                if hubfiles is None:
                    hubfiles = getattr(fm, "files", [])

                for hubfile in hubfiles:
                    self.index_hubfile(hubfile)
                    self.logger.info(f"[INDEX] Hubfile {hubfile.id} indexed")

        except Exception as exc:
            self.logger.exception(f"[INDEX ERROR] Failed to index dataset {dataset.id}: {exc}")
            raise
