# main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import router
from src.core.searcher import EnhancedSearcher
from src.core.chunker import DocumentChunker
from src.core.embedder import DocumentEmbedder
from datetime import datetime
import os
from pathlib import Path
from glob import glob

# Initialize FastAPI
app = FastAPI(
    title="Crustdata API",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def setup_directories():
    """Create necessary directories if they don't exist"""
    directories = [
        "data/raw",
        "data/processed/faiss_index",
        "data/processed/chunks"
    ]
    
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {dir_path}")

def check_existing_files():
    """Check if processed files exist"""
    
    chunks_exist = len(glob("data/processed/chunks/gita_processed_*.json")) > 0
    
    # Check for any embeddings
    embeddings_exist = len(glob("data/processed/faiss_index/chunk_data_*.pkl")) > 0
    
    return chunks_exist and embeddings_exist

@app.on_event("startup")
async def startup_event():
    """Initialize system on startup"""
    try:
        
        setup_directories()
        
        
        if not check_existing_files():
            print("\nProcessing documentation...")
            
            
            chunker = DocumentChunker()
            embedder = DocumentEmbedder()
            
            
            chunks = chunker.process_documentation('data/raw/gita.md')
            embedder.process_chunks(chunks)
        else:
            print("\nUsing existing processed files...")
        
       
        app.state.searcher = EnhancedSearcher()
        print("Search system initialized")
            
    except Exception as e:
        print(f"Error during startup: {str(e)}")
        raise


app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    
    if not app.state.searcher:
        raise HTTPException(status_code=500, detail="Search system not initialized")
        
    return {
        "status": "healthy",
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "components_initialized": True
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
