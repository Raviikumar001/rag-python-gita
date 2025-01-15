# main.py
from flask import Flask, jsonify
from flask_cors import CORS
from src.api.routes import router  
from src.core.searcher import EnhancedSearcher
from src.core.chunker import DocumentChunker
from src.core.embedder import DocumentEmbedder
from datetime import datetime
import os
from pathlib import Path
from glob import glob


app = Flask(__name__)

# CORS setup
CORS(app, resources={r"/*": {"origins": "*"}})

def setup_directories():

    directories = [
        "data/raw",
        "data/processed/faiss_index",
        "data/processed/chunks"
    ]
    
    for dir_path in directories:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {dir_path}")

def check_existing_files():

    chunks_exist = len(glob("data/processed/chunks/gita_processed_*.json")) > 0
    embeddings_exist = len(glob("data/processed/faiss_index/chunk_data_*.pkl")) > 0
    return chunks_exist and embeddings_exist

def init_app():

    try:
        setup_directories()
        
        if not check_existing_files():
            print("\nProcessing documentation...")
            chunker = DocumentChunker()
            embedder = DocumentEmbedder()
            
            chunks = chunker.process_documentation('./data/raw/gita.md')
            embedder.process_chunks(chunks)
        else:
            print("\nUsing existing processed files...")
        
        # Store searcher in app config instead of state
        app.config['searcher'] = EnhancedSearcher()
        print("Search system initialized")
            
    except Exception as e:
        print(f"Error during startup: {str(e)}")
        raise

init_app()

app.register_blueprint(router, url_prefix='/api/v1')

@app.route("/health")
def health_check():
    searcher = app.config.get('searcher')
    if not searcher:
        return jsonify({
            "status": "unhealthy",
            "error": "Search system not initialized"
        }), 500
        
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().strftime('%Y-%M-%d %H:%M:%S'),
        "components_initialized": True
    })

if __name__ == "__main__":
    # Development server
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
