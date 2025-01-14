# test_embeddings.py

from src.core.chunker import DocumentChunker
from src.core.embedder import DocumentEmbedder
import time

def main():
    start_time = time.time()
    
    # Initialize components
    print("\n🚀 Starting document processing pipeline...")
    chunker = DocumentChunker()
    embedder = DocumentEmbedder()
    
    # Process documentation into chunks
    input_path = 'data/raw/gita.md'
    
    try:
        # Chunk the documentation
        print("\n1️⃣ Chunking documentation...")
        chunks = chunker.process_documentation(input_path)
        print(f"└── Created {len(chunks)} chunks")
        
        # Process chunks and generate embeddings
        print("\n2️⃣ Processing chunks...")
        embedder.process_chunks(chunks)
        
        # Report completion
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"\n✨ Processing completed successfully!")
        print(f"└── Total time: {processing_time:.2f} seconds")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        raise

if __name__ == "__main__":
    main()