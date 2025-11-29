from app.modules.elasticsearch.repositories import ElasticsearchRepository
from core.services.BaseService import BaseService
from app.modules.elasticsearch.repositories import ElasticsearchRepository

from elasticsearch import ApiError, BadRequestError, ConnectionError, NotFoundError, Elasticsearch
import time
from datetime import datetime

class ElasticsearchService(BaseService):
    def __init__(self, host="http://elasticsearch:9200", index_name="search_index"):
        
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
        
        if not self.wait_for_elasticsearch():
            print("Error: No se pudo conectar a Elasticsearch en el host proporcionado.")
                 
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
                                "filename": {
                                    "type": "text",
                                    "analyzer": "custom_filename_analyzer",
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
                                "dataset_id": {"type": "integer"},
                                "fits_model_id": {"type": "integer"},
                                "dataset_title": {
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

    def search(self, query: str, publication_type=None, sorting="newest", tags=None, date_from=None, date_to=None, page=1, size=10):
        pass
    
    
    
    