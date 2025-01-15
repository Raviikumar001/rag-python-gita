# src/api/routes.py
from flask import Blueprint, request, jsonify, current_app
from .models import QuestionQuery
from src.services.gemini import GeminiService
from src.utils.logger import get_logger
from src.utils.helpers import create_metadata, log_request, log_response
from src.core.searcher import EnhancedSearcher

logger = get_logger(__name__)
router = Blueprint('api', __name__)
gemini_service = GeminiService()

@router.route("/ask", methods=['POST'])
def ask_question():
    # Get data from request
    data = request.get_json()
    query = QuestionQuery(**data)
    request_id = log_request("/ask", data)
    
    try:

        searcher = EnhancedSearcher.load()
        search_results = searcher.search(query.question, k=query.context_limit)
        context_chunks = [result['content'] for result in search_results]
        
 
        answer = gemini_service.get_answer(
            question=query.question,
            context_chunks=context_chunks
        )
        
        # Create response
        response_data = {
            "answer": answer,
            "metadata": create_metadata({
                "request_id": request_id,
                "context_chunks": len(context_chunks),
            })
        }
        
        log_response(request_id, response_data)
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error processing question: {str(e)}", extra={"request_id": request_id})
        return jsonify({"error": str(e)}), 500

