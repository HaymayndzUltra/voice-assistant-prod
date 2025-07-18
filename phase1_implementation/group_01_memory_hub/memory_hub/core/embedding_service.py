"""Embedding Service for semantic search with vector storage."""

import json
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

import faiss
from sentence_transformers import SentenceTransformer
from pydantic import BaseModel

logger = logging.getLogger("memory_hub.embedding")


class EmbeddingConfig(BaseModel):
    """Configuration for embedding service."""
    model_name: str = "all-MiniLM-L6-v2"  # Fast, good quality
    index_path: str = "data/embeddings.index"
    metadata_path: str = "data/embeddings_metadata.json"
    dimension: int = 384  # Dimension for all-MiniLM-L6-v2
    batch_size: int = 32
    similarity_threshold: float = 0.7


class EmbeddingMetadata(BaseModel):
    """Metadata for stored embeddings."""
    id: str
    namespace: str
    content: str
    doc_id: Optional[str] = None
    category: Optional[str] = None
    metadata: Dict[str, Any] = {}
    created_at: datetime


class EmbeddingService:
    """
    Unified embedding service for semantic search.
    Uses sentence-transformers for embeddings and FAISS for fast similarity search.
    """
    
    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self.model: Optional[SentenceTransformer] = None
        self.index: Optional[faiss.IndexFlatIP] = None  # Inner product for cosine similarity
        self.metadata: List[EmbeddingMetadata] = []
        self.id_to_index: Dict[str, int] = {}
        self._initialized = False
    
    async def initialize(self):
        """Initialize the embedding service."""
        if self._initialized:
            return
        
        logger.info(f"Loading embedding model: {self.config.model_name}")
        self.model = SentenceTransformer(self.config.model_name)
        
        # Initialize FAISS index
        self.index = faiss.IndexFlatIP(self.config.dimension)
        
        # Load existing embeddings if available
        await self._load_index()
        
        self._initialized = True
        logger.info(f"EmbeddingService initialized with {self.index.ntotal} embeddings")
    
    async def _load_index(self):
        """Load existing index and metadata."""
        try:
            # Load FAISS index
            if await self._file_exists(self.config.index_path):
                self.index = faiss.read_index(self.config.index_path)
                logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors")
            
            # Load metadata
            if await self._file_exists(self.config.metadata_path):
                with open(self.config.metadata_path, 'r') as f:
                    metadata_list = json.load(f)
                
                self.metadata = [
                    EmbeddingMetadata(**item) for item in metadata_list
                ]
                
                # Rebuild id_to_index mapping
                self.id_to_index = {
                    meta.id: idx for idx, meta in enumerate(self.metadata)
                }
                
                logger.info(f"Loaded {len(self.metadata)} embedding metadata entries")
        
        except Exception as e:
            logger.warning(f"Could not load existing index: {e}")
            # Create fresh index
            self.index = faiss.IndexFlatIP(self.config.dimension)
            self.metadata = []
            self.id_to_index = {}
    
    async def _file_exists(self, path: str) -> bool:
        """Check if file exists (async-safe)."""
        import os
        return os.path.exists(path)
    
    async def _save_index(self):
        """Save index and metadata to disk."""
        try:
            # Ensure directory exists
            import os
            os.makedirs(os.path.dirname(self.config.index_path), exist_ok=True)
            
            # Save FAISS index
            faiss.write_index(self.index, self.config.index_path)
            
            # Save metadata
            metadata_dict = [
                {
                    "id": meta.id,
                    "namespace": meta.namespace,
                    "content": meta.content,
                    "doc_id": meta.doc_id,
                    "category": meta.category,
                    "metadata": meta.metadata,
                    "created_at": meta.created_at.isoformat()
                }
                for meta in self.metadata
            ]
            
            with open(self.config.metadata_path, 'w') as f:
                json.dump(metadata_dict, f, indent=2)
            
            logger.debug("Saved embedding index and metadata")
        
        except Exception as e:
            logger.error(f"Failed to save embedding index: {e}")
    
    def _generate_embedding_id(self, namespace: str, content_hash: str) -> str:
        """Generate unique ID for embedding."""
        import hashlib
        return f"{namespace}:{content_hash[:16]}"
    
    def _get_content_hash(self, content: str) -> str:
        """Get hash of content for deduplication."""
        import hashlib
        return hashlib.sha256(content.encode()).hexdigest()
    
    async def add_embedding(self, namespace: str, content: str, 
                          doc_id: Optional[str] = None,
                          category: Optional[str] = None,
                          metadata: Dict[str, Any] = None) -> str:
        """
        Add content to embedding index.
        Returns embedding ID.
        """
        if not self._initialized:
            await self.initialize()
        
        content_hash = self._get_content_hash(content)
        embedding_id = self._generate_embedding_id(namespace, content_hash)
        
        # Check if already exists
        if embedding_id in self.id_to_index:
            logger.debug(f"Embedding {embedding_id} already exists")
            return embedding_id
        
        # Generate embedding
        embedding = self.model.encode([content], convert_to_tensor=False)[0]
        
        # Normalize for cosine similarity
        embedding = embedding / np.linalg.norm(embedding)
        
        # Add to FAISS index
        self.index.add(np.array([embedding], dtype=np.float32))
        
        # Store metadata
        embedding_meta = EmbeddingMetadata(
            id=embedding_id,
            namespace=namespace,
            content=content,
            doc_id=doc_id,
            category=category,
            metadata=metadata or {},
            created_at=datetime.now()
        )
        
        index_position = len(self.metadata)
        self.metadata.append(embedding_meta)
        self.id_to_index[embedding_id] = index_position
        
        # Save periodically
        if len(self.metadata) % 100 == 0:
            await self._save_index()
        
        logger.debug(f"Added embedding {embedding_id} at index {index_position}")
        return embedding_id
    
    async def search_similar(self, query: str, namespace: Optional[str] = None,
                           limit: int = 10, min_similarity: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Search for similar content using semantic similarity.
        Returns list of similar items with similarity scores.
        """
        if not self._initialized:
            await self.initialize()
        
        if self.index.ntotal == 0:
            return []
        
        # Generate query embedding
        query_embedding = self.model.encode([query], convert_to_tensor=False)[0]
        query_embedding = query_embedding / np.linalg.norm(query_embedding)
        
        # Search FAISS index
        similarities, indices = self.index.search(
            np.array([query_embedding], dtype=np.float32), 
            min(limit * 2, self.index.ntotal)  # Get more results for filtering
        )
        
        results = []
        threshold = min_similarity or self.config.similarity_threshold
        
        for similarity, idx in zip(similarities[0], indices[0]):
            if idx == -1:  # No more results
                break
            
            if similarity < threshold:
                continue
            
            meta = self.metadata[idx]
            
            # Filter by namespace if specified
            if namespace and meta.namespace != namespace:
                continue
            
            result = {
                "id": meta.id,
                "namespace": meta.namespace,
                "content": meta.content,
                "doc_id": meta.doc_id,
                "category": meta.category,
                "metadata": meta.metadata,
                "similarity": float(similarity),
                "created_at": meta.created_at.isoformat()
            }
            
            results.append(result)
            
            if len(results) >= limit:
                break
        
        return results
    
    async def get_embedding_by_id(self, embedding_id: str) -> Optional[Dict[str, Any]]:
        """Get embedding metadata by ID."""
        if embedding_id not in self.id_to_index:
            return None
        
        idx = self.id_to_index[embedding_id]
        meta = self.metadata[idx]
        
        return {
            "id": meta.id,
            "namespace": meta.namespace,
            "content": meta.content,
            "doc_id": meta.doc_id,
            "category": meta.category,
            "metadata": meta.metadata,
            "created_at": meta.created_at.isoformat()
        }
    
    async def delete_embedding(self, embedding_id: str) -> bool:
        """
        Delete embedding by ID.
        Note: FAISS doesn't support deletion, so we mark as deleted in metadata.
        """
        if embedding_id not in self.id_to_index:
            return False
        
        idx = self.id_to_index[embedding_id]
        
        # Mark as deleted (we'll rebuild index periodically to remove deleted entries)
        self.metadata[idx].metadata["_deleted"] = True
        
        logger.debug(f"Marked embedding {embedding_id} as deleted")
        return True
    
    async def rebuild_index(self):
        """
        Rebuild FAISS index excluding deleted embeddings.
        This is an expensive operation, run periodically.
        """
        if not self._initialized:
            return
        
        logger.info("Rebuilding embedding index...")
        
        # Filter out deleted embeddings
        active_metadata = [
            meta for meta in self.metadata 
            if not meta.metadata.get("_deleted", False)
        ]
        
        if not active_metadata:
            # Create empty index
            self.index = faiss.IndexFlatIP(self.config.dimension)
            self.metadata = []
            self.id_to_index = {}
            await self._save_index()
            return
        
        # Generate embeddings for active items
        contents = [meta.content for meta in active_metadata]
        embeddings = self.model.encode(contents, batch_size=self.config.batch_size)
        
        # Normalize embeddings
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
        
        # Create new index
        new_index = faiss.IndexFlatIP(self.config.dimension)
        new_index.add(embeddings.astype(np.float32))
        
        # Update state
        self.index = new_index
        self.metadata = active_metadata
        self.id_to_index = {
            meta.id: idx for idx, meta in enumerate(self.metadata)
        }
        
        await self._save_index()
        logger.info(f"Rebuilt index with {len(self.metadata)} active embeddings")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get embedding service statistics."""
        if not self._initialized:
            await self.initialize()
        
        total_embeddings = len(self.metadata)
        active_embeddings = len([
            meta for meta in self.metadata 
            if not meta.metadata.get("_deleted", False)
        ])
        
        namespace_counts = {}
        for meta in self.metadata:
            if not meta.metadata.get("_deleted", False):
                namespace_counts[meta.namespace] = namespace_counts.get(meta.namespace, 0) + 1
        
        return {
            "total_embeddings": total_embeddings,
            "active_embeddings": active_embeddings,
            "deleted_embeddings": total_embeddings - active_embeddings,
            "namespace_counts": namespace_counts,
            "model_name": self.config.model_name,
            "dimension": self.config.dimension
        }
    
    async def close(self):
        """Save and cleanup."""
        if self._initialized:
            await self._save_index()
        logger.info("EmbeddingService closed") 