# src/api/routes.py
from fastapi import APIRouter, HTTPException, Request
from .models import QuestionQuery
from src.services.gemini import GeminiService
from src.utils.logger import get_logger
from src.utils.helpers import create_metadata, log_request, log_response
from src.core.searcher import EnhancedSearcher

logger = get_logger(__name__)
router = APIRouter()
gemini_service = GeminiService()

@router.post("/ask")
async def ask_question(request: Request, query: QuestionQuery):
    request_id = log_request("/ask", query.dict())
    
    try:
        
        searcher = request.app.state.searcher
        if not searcher:
            raise HTTPException(status_code=500, detail="Search system not initialized")
        searcher = EnhancedSearcher.load()

        
        search_results = searcher.search(query.question, k=query.context_limit)
       
        context_chunks = [result['content'] for result in search_results]
        
        answer = gemini_service.get_answer(
            question=query.question,
            context_chunks=context_chunks
        )
        
        response_data = {
            "answer": answer,
            "metadata": create_metadata({
                "request_id": request_id,
                "context_chunks": len(context_chunks)
            })
        }
        
        log_response(request_id, response_data)
        return response_data
        
    except Exception as e:
        logger.error(f"Error processing question: {str(e)}", extra={"request_id": request_id})
        raise HTTPException(status_code=500, detail=str(e))