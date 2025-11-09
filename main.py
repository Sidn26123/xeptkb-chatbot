from fastapi import FastAPI, HTTPException
from fastapi.concurrency import asynccontextmanager
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
from rag_chatbot import ScheduleRAGChatbot, Config, IntentType
# Initialize chatbot
config = Config()
chatbot = None

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     global chatbot
#     try:
#         chatbot = ScheduleRAGChatbot(config)
#         chatbot.initialize()
#         logger.info("Chatbot initialized successfully")
#     except Exception as e:
#         logger.error(f"Failed to initialize chatbot: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    global chatbot
    try:
        logger.info("🚀 Lifespan startup triggered")
        logger.info("Initializing chatbot...")
        chatbot = ScheduleRAGChatbot(config)
        
        chatbot.initialize()

        logger.info("✅ Chatbot initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize chatbot: {e}")

    # very important
    yield

    logger.info("🛑 Application shutdown")

# app = FastAPI(lifespan=lifespan)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Schedule RAG Chatbot API",
    description="AI Chatbot for Schedule Management System",
    version="1.0.0",
    lifespan=lifespan
)



# ============================================
# Request/Response Models
# ============================================

class QueryRequest(BaseModel):
    query: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class QueryResponse(BaseModel):
    query: str
    response: str
    intent: str
    entities: Dict[str, Any]
    confidence: float

class HealthResponse(BaseModel):
    status: str
    services: Dict[str, bool]

# ============================================
# API Endpoints
# ============================================

@app.get("/", tags=["General"])
async def root():
    return {
        "message": "Schedule RAG Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "query": "/api/query",
            "intents": "/api/intents"
        }
    }

@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health_check():
    logger.info("Performing health check")
    services = {
        "chatbot": chatbot is not None,
        "qdrant": False,
        "mysql": False,
        "ollama": False
    }
    
    try:
        # Check Qdrant
        chatbot.qdrant.client.get_collections()
        services["qdrant"] = True
    except:
        pass
    
    try:
        # Check MySQL
        chatbot.mysql.connection.ping(reconnect=True)
        services["mysql"] = True
    except:
        pass
    
    try:
        # Check Ollama
        import requests
        response = requests.get(f"{config.ollama_base_url}/api/tags", timeout=5)
        services["ollama"] = response.status_code == 200
    except:
        pass
    
    status = "healthy" if all(services.values()) else "degraded"
    
    return HealthResponse(status=status, services=services)

@app.post("/api/query", response_model=QueryResponse, tags=["Chat"])
async def process_query(request: QueryRequest):
    if not chatbot:
        raise HTTPException(status_code=503, detail="Chatbot not initialized")
    
    try:
        # Detect intent
        intent_result = chatbot.intent_detector.detect(request.query)
        
        # Process query
        response = chatbot.process_query(request.query)
        
        return QueryResponse(
            query=request.query,
            response=response,
            intent=intent_result.get("intent", "unknown"),
            entities=intent_result.get("entities", {}),
            confidence=0.85  # Mock confidence score
        )
    
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/intents", tags=["Chat"])
async def get_intents():
    return {
        "intents": [
            {
                "name": IntentType.INPUT_INTERPRETATION.value,
                "description": "Hiểu và tiền xử lý input người dùng"
            },
            {
                "name": IntentType.SCHEDULE_RETRIEVAL.value,
                "description": "Tìm và hiển thị thời khoá biểu"
            },
            {
                "name": IntentType.METRIC_ANALYSIS.value,
                "description": "Phân tích bằng các metric mẫu"
            },
            {
                "name": IntentType.VIOLATION_REVIEW.value,
                "description": "Kiểm tra các vi phạm"
            },
            {
                "name": IntentType.SCHEDULE_COMPARISON.value,
                "description": "So sánh các TKB"
            }
        ]
    }

@app.post("/api/feedback", tags=["Chat"])
async def submit_feedback(query: str, response: str, rating: int):
    # Log feedback for improvement
    logger.info(f"Feedback - Query: {query}, Rating: {rating}")
    return {"message": "Feedback received", "status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)