# src/core/embedder.py

from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict
from pathlib import Path
from datetime import datetime
import faiss
import pickle

CURRENT_TIME = "2025-01-14 13:28:48"
CURRENT_USER = "ravi-hisoka"

class DocumentEmbedder:
    def __init__(self, model_name: str = 'all-distilroberta-v1'):
        
        print(f"\nInitializing DocumentEmbedder...")
        print(f"├── Model: {model_name}")
        print(f"├── User: {CURRENT_USER}")
        print(f"└── Time: {CURRENT_TIME}")
        
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        # DistilRoBERTa has 768 dimensions
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
        self.index = None

    def generate_embeddings(self, chunks: List[Dict[str, str]]) -> np.ndarray:
        
        texts = [chunk['content'] for chunk in chunks]
        print(f"\nGenerating embeddings:")
        print(f"├── Total chunks: {len(texts)}")
        print(f"└── Model: {self.model_name}")
        
        # DistilRoBERTa works well with these parameters
        embeddings = self.model.encode(
            texts, 
            show_progress_bar=True,
            batch_size=32,  
            normalize_embeddings=True  # DistilRoBERTa works better with normalized embeddings
        )
        
        print(f"\nEmbeddings generated:")
        print(f"└── Shape: {embeddings.shape}")
        return embeddings

    def create_faiss_index(self, embeddings: np.ndarray):
        """
        Create FAISS index from embeddings
        """
        print(f"\nCreating FAISS index:")
        print(f"├── Vectors: {len(embeddings)}")
        print(f"└── Dimensions: {self.embedding_dim}")
        
        # Using IndexFlatL2 since embeddings are normalized
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


# from sentence_transformers import SentenceTransformer
# import numpy as np
# from typing import List, Dict
# from pathlib import Path
# from datetime import datetime
# import faiss
# import pickle

# CURRENT_TIME = "2025-01-11 13:00:39"
# CURRENT_USER = "Anonymous"

# class DocumentEmbedder:
#     def __init__(self, model_name: str = 'all-mpnet-base-v2'):
        
#         print(f"\nInitializing DocumentEmbedder...")
#         print(f"├── Model: {model_name}")
#         print(f"├── User: {CURRENT_USER}")
#         print(f"└── Time: {CURRENT_TIME}")
        
#         self.model_name = model_name
#         self.model = SentenceTransformer(model_name)
#         # Get the correct embedding dimension from the model
#         self.embedding_dim = self.model.get_sentence_embedding_dimension()
#         self.index = None

#     def generate_embeddings(self, chunks: List[Dict[str, str]]) -> np.ndarray:
        
#         texts = [chunk['content'] for chunk in chunks]
#         print(f"\nGenerating embeddings:")
#         print(f"├── Total chunks: {len(texts)}")
#         print(f"└── Model: {self.model_name}")
        
        
#         embeddings = self.model.encode(
#             texts, 
#             show_progress_bar=True,
#             batch_size=32  
#         )
        
#         print(f"\nEmbeddings generated:")
#         print(f"└── Shape: {embeddings.shape}")
#         return embeddings

#     def create_faiss_index(self, embeddings: np.ndarray):
#         """
#         Create FAISS index from embeddings
#         """
#         print(f"\nCreating FAISS index:")
#         print(f"├── Vectors: {len(embeddings)}")
#         print(f"└── Dimensions: {self.embedding_dim}")
        
#         # Create index with correct dimension
#         self.index = faiss.IndexFlatL2(embeddings.shape[1])
#         self.index.add(embeddings.astype('float32'))
        
#         print(f"Index created successfully with {self.index.ntotal} vectors")

#     def save_artifacts(self, chunks: List[Dict], embeddings: np.ndarray):
        
#         timestamp = datetime.strptime(CURRENT_TIME, "%Y-%m-%d %H:%M:%S").strftime('%Y%m%d_%H%M%S')
#         artifacts_dir = Path('data/processed/faiss_index')
#         artifacts_dir.mkdir(parents=True, exist_ok=True)

        
#         index_path = artifacts_dir / f'docs_index_{timestamp}.faiss'
#         faiss.write_index(self.index, str(index_path))

        
#         chunk_data_path = artifacts_dir / f'chunk_data_{timestamp}.pkl'
#         metadata = {
#             'chunks': chunks,
#             'created_at': CURRENT_TIME,
#             'created_by': CURRENT_USER,
#             'embedding_model': self.model_name,
#             'embedding_dimension': self.embedding_dim,
#             'total_chunks': len(chunks),
#             'total_vectors': self.index.ntotal
#         }
        
#         with open(chunk_data_path, 'wb') as f:
#             pickle.dump(metadata, f)

#         print(f"\nArtifacts saved successfully:")
#         print(f"├── Index: {index_path}")
#         print(f"└── Chunks: {chunk_data_path}")
        
#         print(f"\nMetadata summary:")
#         print(f"├── Total chunks: {len(chunks)}")
#         print(f"├── Model: {self.model_name}")
#         print(f"├── Dimension: {self.embedding_dim}")
#         print(f"├── Vectors: {self.index.ntotal}")
#         print(f"├── Created by: {metadata['created_by']}")
#         print(f"└── Created at: {metadata['created_at']}")

#     def process_chunks(self, chunks: List[Dict[str, str]]):
       
#         try:
#             embeddings = self.generate_embeddings(chunks)
#             self.create_faiss_index(embeddings)
#             self.save_artifacts(chunks, embeddings)
#             return True
#         except Exception as e:
#             print(f"\n❌ Error processing chunks: {str(e)}")
#             raise
