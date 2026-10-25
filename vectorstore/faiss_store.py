import os
import uuid
from pathlib import Path
from types import SimpleNamespace

from langchain_community.vectorstores import FAISS


class FAISSVectorStore:
    """
    Local FAISS vector store.

    Replaces Azure AI Search with a completely
    local vector database.
    """

    def __init__(
        self,
        embeddings,
        index_path: str = "data/vectorstore"
    ) -> None:

        self.embeddings = embeddings
        self.index_path = index_path
        self.vectorstore = None

    # --------------------------------------------------
    # Upload / store chunks
    # --------------------------------------------------

    def upload_chunks(
        self,
        chunks,
        embeddings,
        company: str,
        year: str,
        source_file: str
    ) -> None:
        """
        Convert chunks into embeddings and store them
        in a local FAISS index.
        """

        if not chunks:
            print("No chunks to store.")
            return

        documents = []

        for chunk in chunks:

            # Copy the chunk metadata
            metadata = dict(chunk.metadata)

            # Add our financial-document metadata
            metadata.update(
                {
                    "id": str(uuid.uuid4()),
                    "company": company,
                    "year": year,
                    "source_file": source_file
                }
            )

            chunk.metadata = metadata

            documents.append(chunk)

        # --------------------------------------------------
        # Create or update FAISS index
        # --------------------------------------------------

        if self.vectorstore is None:

            # Check whether an existing FAISS index exists
            index_file = Path(self.index_path) / "index.faiss"

            if index_file.exists():

                print("Existing FAISS index found.")
                print("Loading existing vector store...")

                self.vectorstore = FAISS.load_local(
                    self.index_path,
                    embeddings,
                    allow_dangerous_deserialization=True
                )

                self.vectorstore.add_documents(
                    documents
                )

            else:

                print("Creating new FAISS index...")

                self.vectorstore = FAISS.from_documents(
                    documents,
                    embeddings
                )

        else:

            print("Adding documents to existing FAISS index...")

            self.vectorstore.add_documents(
                documents
            )

        # --------------------------------------------------
        # Save FAISS index
        # --------------------------------------------------

        os.makedirs(
            self.index_path,
            exist_ok=True
        )

        self.vectorstore.save_local(
            self.index_path
        )

        print(
            f"Stored {len(documents)} chunks "
            f"in FAISS."
        )

        print(
            f"FAISS index saved to: "
            f"{self.index_path}"
        )

    # --------------------------------------------------
    # Retriever
    # --------------------------------------------------

    def as_retriever(self):
        """
        Return a LangChain retriever for RAG.
        """

        if self.vectorstore is None:

            index_file = Path(
                self.index_path
            ) / "index.faiss"

            if not index_file.exists():

                raise RuntimeError(
                    "FAISS index does not exist. "
                    "Run the ingestion pipeline first."
                )

            self.vectorstore = FAISS.load_local(
                self.index_path,
                self.embeddings,
                allow_dangerous_deserialization=True
            )

        return self.vectorstore.as_retriever(
            search_kwargs={
                "k": 20
            }
        )

    # --------------------------------------------------
    # Direct search
    # --------------------------------------------------

    def search(
        self,
        query: str,
        top_k: int = 5,
        company: str | None = None,
        year: int | None = None
    ):

        if self.vectorstore is None:

            index_file = Path(
                self.index_path
            ) / "index.faiss"

            if not index_file.exists():

                raise RuntimeError(
                    "FAISS index does not exist. "
                    "Run ingestion first."
                )

            self.vectorstore = FAISS.load_local(
                self.index_path,
                self.embeddings,
                allow_dangerous_deserialization=True
            )

        # --------------------------------------------------
        # Metadata filtering
        # --------------------------------------------------

        filter_function = None

        if company or year:

            def filter_function(metadata):

                if company:

                    if metadata.get("company") != company:
                        return False

                if year:

                    if str(metadata.get("year")) != str(year):
                        return False

                return True

        # --------------------------------------------------
        # Search
        # --------------------------------------------------

        if filter_function:

            results = self.vectorstore.similarity_search(
                query,
                k=top_k,
                filter=filter_function
            )

        else:

            results = self.vectorstore.similarity_search(
                query,
                k=top_k
            )

        return results


class Retriever:
    """
    Simple wrapper around FAISS.

    Designed to behave similarly to the old
    Azure Retriever.
    """

    def __init__(
        self,
        vectorstore: FAISSVectorStore
    ):
        self.vectorstore = vectorstore

    def invoke(
        self,
        query: str,
        company: str | None = None,
        year: int | None = None,
        top_k: int = 20
    ) -> list:

        results = self.vectorstore.search(
            query=query,
            top_k=top_k,
            company=company,
            year=year
        )

        documents = []

        for result in results:

            documents.append(
                SimpleNamespace(
                    page_content=result.page_content,
                    metadata=result.metadata
                )
            )

        return documents