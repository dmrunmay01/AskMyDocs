# Taking document chunks → converting them into embeddings → storing them in Chroma → retrieving relevant chunks when the user asks a question.
from langchain_community.vectorstores import Chroma   #Chroma is our vector database.
from langchain_huggingface import HuggingFaceEmbeddings  #loads the Hugging Face embedding model, The embedding model converts into a vector.
from langchain.schema import Document #represents a piece of text plus metadata.

import asyncio
import json
import time
from pathlib import Path
from typing import List, Optional, Tuple
import structlog

from app.core.config import settings
from app.core.exceptions import NoDocumentsIndexedError, VectorStoreError

logger = structlog.get_logger(__name__)


class VectorStoreService:  #This wraps all Chroma-related operations into one service
    def __init__(self):
        self._store = None  #This will eventually contain the Chroma database.
        self._embeddings = None  #This will hold the Hugging Face embedding model.
        self._doc_metadata = {}  #This is a Python dictionary tracking documents that have been indexed. Important: this is only an in-memory dictionary
        self._lock = asyncio.Lock()  #This prevents multiple operations from modifying/using the vector store simultaneously.
        self._persist_dir = str(settings.VECTOR_STORE_DIR) #This tells Chroma where to store its database on disk.
        self._initialized = False

    async def initialize(self):
        logger.info("initializing_vector_store") #This simply writes a log message.

        self._embeddings = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL  #This loads the embedding model.
        )

                # Load existing DB if exists
        try:
            self._store = Chroma(
                persist_directory=self._persist_dir,
                embedding_function=self._embeddings
            )

            logger.info("chroma_loaded")

            # Restore document metadata from existing Chroma chunks
            try:
                stored_data = self._store.get()
                metadatas = stored_data.get("metadatas", [])

                documents = {}

                for metadata in metadatas:
                    if not metadata or "doc_id" not in metadata:
                        continue

                    doc_id = metadata["doc_id"]

                    if doc_id not in documents:
                        documents[doc_id] = {
                            "doc_id": doc_id,
                            "filename": metadata.get("filename", "Unknown"),
                            "original_filename": metadata.get(
                                "filename", "Unknown"
                            ),
                            "file_size_bytes": 0,
                            "file_type": Path(
                                metadata.get("filename", "")
                            ).suffix.lower(),
                            "status": "indexed",
                            "num_chunks": 0,
                            "num_pages": None,
                            "metadata": {
                                "title": metadata.get("title", ""),
                                "description": metadata.get("description", ""),
                            },
                        }

                    documents[doc_id]["num_chunks"] += 1

                    page_number = metadata.get("page_number")
                    if page_number is not None:
                        current_pages = documents[doc_id]["num_pages"]
                        if current_pages is None:
                            documents[doc_id]["num_pages"] = page_number
                        else:
                            documents[doc_id]["num_pages"] = max(
                                current_pages, page_number
                            )

                self._doc_metadata = documents

                logger.info(
                    "document_metadata_restored",
                    total_documents=len(self._doc_metadata),
                )

            except Exception as e:
                logger.warning(
                    "document_metadata_restore_failed",
                    error=str(e),
                )

        except Exception:
            self._store = None

    async def add_documents(self, chunks: List[Document], doc_id: str, metadata: dict): #It receives:chunks, doc_id:An identifier for the original document, metadata:Information about the document.
        if not chunks: #If there are no chunks, don't do anything.
            return 0

        async with self._lock:  #Again, we're protecting the vector store from concurrent operations.
            try:
                if self._store is None:  #If there is no existing Chroma database
                    self._store = Chroma.from_documents(
                        documents=chunks,
                        embedding=self._embeddings,
                        persist_directory=self._persist_dir
                    )
                else:
                    self._store.add_documents(chunks) #If Chroma already exists, simply add the new chunks.

                self._store.persist()  #This tells Chroma to save the database to disk.So the data isn't only sitting in RAM.

                self._doc_metadata[doc_id] = {  #Metadata tracking
                    "num_chunks": len(chunks),
                    **metadata
                }

                return len(chunks)

            except Exception as e:
                raise VectorStoreError("add_documents", str(e))

    async def similarity_search(  #The query gets passed here.
        self,
        query: str,
        top_k: int = 3,
        doc_ids: Optional[List[str]] = None,
        use_mmr: bool = False,
        score_threshold: float = 0.0,
    ) -> List[Tuple[Document, float]]:

        if self._store is None:   #If we don't have a vector database, there are no documents to search.
            raise NoDocumentsIndexedError()

        async with self._lock:
            try:
                results = self._store.similarity_search_with_relevance_scores(query, k=top_k)

                # Filter out results below the configured relevance threshold
                if score_threshold > 0:
                    results = [
                        (doc, score)
                        for doc, score in results
                        if score >= score_threshold
                    ]

                return results

            except Exception as e:
                raise VectorStoreError("search", str(e))

    async def delete_document(self, doc_id: str):
        # Simple version (Chroma handles deletion differently)
        if doc_id in self._doc_metadata:
            del self._doc_metadata[doc_id]
        return True

    def list_documents(self):
        """Return metadata for all indexed documents."""
        return list(self._doc_metadata.values())

    def get_document_metadata(self, doc_id: str):
        """Return metadata for a specific document."""
        return self._doc_metadata.get(doc_id)

    def get_stats(self):
        """Return statistics about the current vector store."""

        total_chunks = 0

        if self._store is not None:
            try:
                total_chunks = self._store._collection.count()
            except Exception:
                total_chunks = sum(
                    doc.get("num_chunks", 0)
                    for doc in self._doc_metadata.values()
                )

        return {
            "total_documents": len(self._doc_metadata),
            "total_chunks": total_chunks,
            "index_size_mb": 0.0,
            "embedding_model": settings.EMBEDDING_MODEL,
            "embedding_dimension": 384,
            "index_type": "Chroma",
    }

    async def cleanup(self):
        if self._store:
            self._store.persist()
