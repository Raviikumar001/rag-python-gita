from src.core.chunker import DocumentChunker
import os

def main():
    chunker = DocumentChunker()
   
    input_path = 'data/raw/gita.md'
    
    if not os.path.exists(input_path):
        print(f"Please place your README.md in {input_path}")
        return
    
    try:
        chunks = chunker.process_documentation(input_path)
        print(f"\nSuccessfully processed {len(chunks)} chunks")
        
        # Print summary of all chunks
        print("\nChunks Summary:")
        print("-" * 80)
        for i, chunk in enumerate(chunks):
            print(f"\nChunk {i + 1}:")
            # print(f"Section: {chunk['metadata']['section']}")
            # print(f"Type: {chunk['metadata']['type']}")
            print(f"Content Preview (first 200 chars):")
            print("-" * 40)
            print(chunk['content'][:1500] + "...")
            print("-" * 40)

    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()


     