# src/core/searcher.py

import faiss
import numpy as np
import google.generativeai as genai
from typing import List, Dict, Optional
from pathlib import Path
import pickle
from datetime import datetime, timezone
import os

class EnhancedSearcher:
    def __init__(self, model_name: str = "models/text-embedding-004"):
        # Initialize Gemini
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        
        genai.configure(api_key=api_key)
        self.model_name = model_name
        self.embedding_dim = 768  # Gemini embeddings dimension
        self.index = None
        self.chunks = []
        self.similarity_threshold = 0.3

    def build_index(self, chunks: List[Dict], timestamp: str = None) -> bool:
        """Build FAISS index from chunks"""
        try:
            if timestamp is None:
                timestamp = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
                
            print(f"\nBuilding index at {timestamp}")
            self.chunks = chunks
            
            # Generate embeddings using Gemini
            texts = [chunk['content'] for chunk in chunks]
            embeddings = []
            for text in texts:
                result = genai.embed_content(
                    model=self.model_name,
                    content=text,
                    task_type="SEMANTIC_SIMILARITY"
                )
                embeddings.append(result['embedding'])
            embeddings = np.array(embeddings)
            
            # Create and populate FAISS index
            self.index = faiss.IndexFlatL2(self.embedding_dim)
            self.index.add(embeddings.astype(np.float32))
            
            self._save_index(timestamp)
            
            print(f"Successfully built index with {len(chunks)} vectors")
            return True
            
        except Exception as e:
            print(f"Error building index: {str(e)}")
            return False

    def _save_index(self, timestamp: str):
        base_path = Path('data/processed/faiss_index')
        base_path.mkdir(parents=True, exist_ok=True)
        
        index_path = base_path / f'docs_index_{timestamp}.faiss'
        faiss.write_index(self.index, str(index_path))
        
        chunks_path = base_path / f'chunk_data_{timestamp}.pkl'
        chunk_data = {
            'chunks': self.chunks,
            'embedding_model': self.model_name,
            'created_at': timestamp,
            'created_by': 'ravi-hisoka',
            'vector_count': len(self.chunks),
            'vector_dimension': self.embedding_dim,
            'current_date_utc': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open(chunks_path, 'wb') as f:
            pickle.dump(chunk_data, f)
            
        print(f"Saved index and metadata at: {base_path}")

    @classmethod
    def load(cls, timestamp: str = None):
        """Load an existing index"""
        try:
            base_path = Path('data/processed/faiss_index')
            
            if timestamp is None:
                # Get latest index
                index_files = list(base_path.glob('docs_index_*.faiss'))
                if not index_files:
                    raise FileNotFoundError("No index files found")
                index_path = max(index_files)
                timestamp = index_path.stem.split('_', 2)[-1]
            else:
                index_path = base_path / f'docs_index_{timestamp}.faiss'
                
            chunks_path = base_path / f'chunk_data_{timestamp}.pkl'
            
            if not index_path.exists():
                raise FileNotFoundError(f"Index file not found: {index_path}")
            if not chunks_path.exists():
                raise FileNotFoundError(f"Chunks file not found: {chunks_path}")
                
            
            instance = cls()
            instance.index = faiss.read_index(str(index_path))
            
            with open(chunks_path, 'rb') as f:
                chunk_data = pickle.load(f)
                instance.chunks = chunk_data['chunks']
                
            print(f"Loaded index from: {index_path}")
            print(f"Number of vectors: {instance.index.ntotal}")
            return instance
            
        except Exception as e:
            print(f"Error loading index: {str(e)}")
            return None

    def search(self, query: str, k: int = 3) -> List[Dict]:
        try:
            if self.index is None:
                raise ValueError("Index not loaded")
                
            # Generate query embedding using Gemini
            query_embedding = genai.embed_content(
                model=self.model_name,
                content=query,
                task_type="SEMANTIC_SIMILARITY"
            )['embedding']
            query_embedding = np.array(query_embedding).astype(np.float32).reshape(1, -1)
            
            # Search
            distances, indices = self.index.search(query_embedding, k * 2)
            
            results = []
            for distance, idx in zip(distances[0], indices[0]):
                if idx != -1:  # Valid index
                    similarity_score = 1 - (distance / 2)  # Convert L2 distance to similarity
                    if similarity_score >= self.similarity_threshold:
                        result = {
                            'content': self.chunks[idx]['content'],
                            'score': float(similarity_score),
                            'chunk_index': int(idx)
                        }
                        results.append(result)
            
            return self._deduplicate_results(results)[:k]
            
        except Exception as e:
            print(f"Error during search: {str(e)}")
            return []

    def _deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        
        seen = set()
        unique_results = []
        
        for result in sorted(results, key=lambda x: x['score'], reverse=True):
            if result['chunk_index'] not in seen:
                seen.add(result['chunk_index'])
                unique_results.append(result)
                
        return unique_results
