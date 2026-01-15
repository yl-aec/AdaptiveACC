import os
from pathlib import Path
from typing import List, Dict, Any

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

from config import Config
from models.common_models import ToolMetadata
from utils.base_classes import Singleton


class ToolVectorManager(Singleton):
    """Specialized manager for tool vector operations only"""

    def __init__(self):
        super().__init__()

    def _initialize(self):
        """Initialize ToolVectorManager instance"""
        # Direct vectordb path management with default values
        self.vectordb_path = Path("vectordb") / "tools"
        self.vectordb_path.mkdir(parents=True, exist_ok=True)

        self.collection_name = "tool_vectors"
        
        # Use dedicated embedding API configuration
        embedding_kwargs = {
            "model": Config.EMBEDDING_MODEL_NAME,
            "openai_api_key": Config.EMBEDDING_API_KEY,
            "dimensions": 1536,
            "timeout": 60,  # 60 second timeout for embedding API calls
            "max_retries": 2  # Retry up to 2 times on failure
        }

        # Add base URL if specified for embedding API
        if Config.EMBEDDING_API_BASE:
            embedding_kwargs["openai_api_base"] = Config.EMBEDDING_API_BASE
            
        self.embeddings = OpenAIEmbeddings(**embedding_kwargs)
        self.vector_store = None

        print("ToolVectorManager: Singleton instance initialized")
    
    # Removed duplicate get_instance method - inherited from Singleton base class
    
    def _ensure_loaded(self):
        """Ensure vector store is loaded (lazy loading)"""
        if self.vector_store is None:
            try:
                self.vector_store = self._load_vector_store()
                print("Tool vector database initialized successfully")
            except Exception as e:
                print(f"Warning: Could not initialize tool vector database: {e}")
                self.vector_store = None
    
    def _load_vector_store(self) -> Chroma:
        """Load the existing tool vector store"""
        if not self.vectordb_path.exists():
            raise FileNotFoundError(f"Tool vector database not found at {self.vectordb_path}")
        
        return Chroma(
            persist_directory=str(self.vectordb_path),
            embedding_function=self.embeddings,
            collection_name=self.collection_name
        )
    
    def search_tools(self, query: str, k: int = 5, metadata_filter: dict = None, score_threshold: float = 1.2) -> List[Dict[str, Any]]:
        """Search for tools using semantic vector search with relevance threshold

        Args:
            query: Search query string
            k: Maximum number of results to return
            metadata_filter: Optional metadata filter
            score_threshold: Maximum distance score (lower is better). Default 1.2 balances precision and recall.
                           Scores: <1.0=highly relevant, 1.0-1.2=moderately relevant, >1.2=not relevant

        Returns:
            List of tool metadata dictionaries with relevance_score field
        """

        self._ensure_loaded()

        if self.vector_store is None:
            return []

        try:
            # Search for extra results to account for threshold filtering
            search_k = k * 2

            # Execute vector search
            if metadata_filter:
                results = self.vector_store.similarity_search_with_score(
                    query, k=search_k, filter=metadata_filter
                )
            else:
                results = self.vector_store.similarity_search_with_score(query, k=search_k)

            # Filter by similarity score threshold and process results
            tool_results = []
            for doc, score in results:
                # Only include tools that pass the threshold (lower score = more similar)
                if score <= score_threshold:
                    tool_metadata = doc.metadata.copy()
                    tool_metadata['relevance_score'] = score
                    tool_metadata['content'] = doc.page_content
                    tool_results.append(tool_metadata)

            # Return up to k results that passed the threshold
            return tool_results[:k]

        except Exception as e:
            print(f"Tool vector search error: {e}")
            return []

    def add_tool(self, tool_metadata: Dict[str, Any]) -> bool:
        """Add a tool to the vector database"""
        self._ensure_loaded()
        
        if self.vector_store is None:
            return False
            
        try:
            # Create text content for embedding
            text_content = self._create_tool_text(tool_metadata)
            
            # Filter metadata for Chroma compatibility
            filtered_metadata = self._filter_metadata_for_chroma(tool_metadata)
            
            # Add to vector store
            self.vector_store.add_texts([text_content], metadatas=[filtered_metadata])
            
            print(f"Added tool '{tool_metadata.get('ifc_tool_name', 'unknown')}' to vector database")
            return True
            
        except Exception as e:
            print(f"Error adding tool to vector database: {e}")
            return False
    
    def _create_tool_text(self, tool_metadata: Dict[str, Any]) -> str:
        """Create text content for tool embedding using all metadata fields"""
        parts = []

        for key, value in tool_metadata.items():
            if value:  # Only include fields with values
                parts.append(f"{key}: {value}")

        return "\n".join(parts)
    
    def _filter_metadata_for_chroma(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Filter metadata to be compatible with Chroma"""
        # Chroma requires metadata values to be strings, numbers, or booleans
        filtered = {}
        
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)):
                filtered[key] = value
            elif isinstance(value, list):
                # Convert list to string
                filtered[key] = ', '.join(str(v) for v in value)
            elif value is not None:
                # Convert other types to string
                filtered[key] = str(value)
        
        return filtered
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector database statistics"""
        self._ensure_loaded()
        
        if self.vector_store is None:
            return {"status": "unavailable", "error": "Vector store not loaded"}
        
        try:
            # Get collection info
            collection = self.vector_store._collection
            count = collection.count()
            
            return {
                "status": "available",
                "tool_count": count,
                "collection_name": self.collection_name,
                "vectordb_path": str(self.vectordb_path)
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def is_available(self) -> bool:
        """Check if vector database is available"""
        self._ensure_loaded()
        return self.vector_store is not None

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all tools from vector database

        Returns:
            List of tool metadata dictionaries
        """
        self._ensure_loaded()

        if self.vector_store is None:
            return []

        try:
            # Get all documents from the collection
            collection = self.vector_store._collection
            results = collection.get(include=["metadatas", "documents"])

            # Convert to tool metadata format
            tools = []
            if results and results.get('metadatas'):
                for i, metadata in enumerate(results['metadatas']):
                    tool_data = metadata.copy()
                    if i < len(results.get('documents', [])):
                        tool_data['content'] = results['documents'][i]
                    if i < len(results.get('ids', [])):
                        tool_data['_id'] = results['ids'][i]
                    tools.append(tool_data)

            return tools

        except Exception as e:
            print(f"Error getting all tools from vector database: {e}")
            return []

    def delete_tool(self, tool_name: str) -> bool:
        """Delete a tool from vector database by tool_name

        Args:
            tool_name: Name of the tool to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        self._ensure_loaded()

        if self.vector_store is None:
            return False

        try:
            # Find the document ID(s) for this tool_name
            collection = self.vector_store._collection
            results = collection.get(
                where={"ifc_tool_name": tool_name},
                include=["metadatas"]
            )

            if not results or not results.get('ids'):
                print(f"Tool '{tool_name}' not found in vector database")
                return False

            # Delete all documents with this tool_name
            ids_to_delete = results['ids']
            self.vector_store.delete(ids=ids_to_delete)

            print(f"Deleted tool '{tool_name}' from vector database ({len(ids_to_delete)} documents)")
            return True

        except Exception as e:
            print(f"Error deleting tool from vector database: {e}")
            return False

    def delete_by_id(self, document_id: str) -> bool:
        """Delete a document from vector database by ID

        Args:
            document_id: ChromaDB document ID to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        self._ensure_loaded()

        if self.vector_store is None:
            return False

        try:
            self.vector_store.delete(ids=[document_id])
            return True

        except Exception as e:
            print(f"Error deleting document {document_id} from vector database: {e}")
            return False

    def update_tool(self, tool_metadata: Dict[str, Any]) -> bool:
        """Update a tool in vector database (delete old, add new)

        Args:
            tool_metadata: Updated tool metadata dictionary

        Returns:
            True if updated successfully, False otherwise
        """
        tool_name = tool_metadata.get('ifc_tool_name', 'unknown')

        # Delete old version
        self.delete_tool(tool_name)

        # Add new version
        success = self.add_tool(tool_metadata)

        if success:
            print(f"Updated tool '{tool_name}' in vector database")
        else:
            print(f"Failed to update tool '{tool_name}'")

        return success