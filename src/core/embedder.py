# src/core/embedder.py

from google import genai
import numpy as np
from typing import List, Dict
from pathlib import Path
from datetime import datetime
import faiss
import pickle
import os

CURRENT_TIME = "2025-01-14 13:28:48"
CURRENT_USER = "ravi-hisoka"

class DocumentEmbedder:
    def __init__(self, model_name: str = "gemini-embedding-2-preview"):
        print(f"\nInitializing DocumentEmbedder...")
        print(f"├── Model: {model_name}")
        print(f"├── User: {CURRENT_USER}")
        print(f"└── Time: {CURRENT_TIME}")
        
        self.model_name = model_name
        
        # Initialize Gemini Client
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        
        self.client = genai.Client(api_key=api_key)
        
        # gemini-embedding-2-preview uses 3072-dimensional embeddings
        self.embedding_dim = 3072
        self.index = None

    def generate_embeddings(self, chunks: List[Dict[str, str]]) -> np.ndarray:
        texts = [chunk['content'] for chunk in chunks]
        print(f"\nGenerating embeddings:")
        print(f"├── Total chunks: {len(texts)}")
        print(f"└── Model: {self.model_name}")
        
        embeddings = []
        for text in texts:
            result = self.client.models.embed_content(
                model=self.model_name,
                contents=text,
                config={'task_type': "RETRIEVAL_DOCUMENT"}
            )
            
            if isinstance(result.embeddings, list):
                embeddings.append(result.embeddings[0].values)
            else:
                embeddings.append(result.embeddings.values)
        
        embeddings_array = np.array(embeddings)
        print(f"\nEmbeddings generated:")
        print(f"└── Shape: {embeddings_array.shape}")
        return embeddings_array
        
        embeddings_array = np.array(embeddings)
        print(f"\nEmbeddings generated:")
        print(f"└── Shape: {embeddings_array.shape}")
        return embeddings_array

    def create_faiss_index(self, embeddings: np.ndarray):
        print(f"\nCreating FAISS index:")
        print(f"├── Vectors: {len(embeddings)}")
        print(f"└── Dimensions: {self.embedding_dim}")
        
        self.index = faiss.IndexFlatL2(self.embedding_dim)
        self.index.add(embeddings.astype('float32'))
        
        print(f"Index created successfully with {self.index.ntotal} vectors")

    def save_artifacts(self, chunks: List[Dict], embeddings: np.ndarray):
        timestamp = datetime.strptime(CURRENT_TIME, "%Y-%m-%d %H:%M:%S").strftime('%Y%m%d_%H%M%S')
        artifacts_dir = Path('data/processed/faiss_index')
        artifacts_dir.mkdir(parents=True, exist_ok=True)

        index_path = artifacts_dir / f'docs_index_{timestamp}.faiss'
        faiss.write_index(self.index, str(index_path))

        chunk_data_path = artifacts_dir / f'chunk_data_{timestamp}.pkl'
        metadata = {
            'chunks': chunks,
            'created_at': CURRENT_TIME,
            'created_by': CURRENT_USER,
            'embedding_model': self.model_name,
            'embedding_dimension': self.embedding_dim,
            'total_chunks': len(chunks),
            'total_vectors': self.index.ntotal
        }
        
        with open(chunk_data_path, 'wb') as f:
            pickle.dump(metadata, f)

        print(f"\nArtifacts saved successfully:")
        print(f"├── Index: {index_path}")
        print(f"└── Chunks: {chunk_data_path}")
        
        print(f"\nMetadata summary:")
        print(f"├── Total chunks: {len(chunks)}")
        print(f"├── Model: {self.model_name}")
        print(f"├── Dimension: {self.embedding_dim}")
        print(f"├── Vectors: {self.index.ntotal}")
        print(f"├── Created by: {metadata['created_by']}")
        print(f"└── Created at: {metadata['created_at']}")

    def process_chunks(self, chunks: List[Dict[str, str]]):
        try:
            embeddings = self.generate_embeddings(chunks)
            self.create_faiss_index(embeddings)
            self.save_artifacts(chunks, embeddings)
            return True
        except Exception as e:
            print(f"\n❌ Error processing chunks: {str(e)}")
            raise

