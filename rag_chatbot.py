# Hệ thống RAG Local cho Chatbot Xếp Thời Khóa Biểu
# Tech Stack: Qdrant + multilingual-e5-small + Llama 3.2-1B + LangChain + MySQL

import logging
from typing import ClassVar, List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json
from fastapi import logger
import mysql.connector
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from langchain.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import re
# from qdrant_client.http import models
import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from qdrant_client.http.models import models as qdrant_models
load_dotenv()


# ============================================================================
# CONFIGURATION
# ============================================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
class IntentType(Enum):
    INPUT_INTERPRETATION = "input_interpretation"
    SCHEDULE_RETRIEVAL = "schedule_retrieval"
    METRIC_ANALYSIS = "metric_analysis"
    VIOLATION_REVIEW = "violation_review"
    SCHEDULE_COMPARISON = "schedule_comparison"

# @dataclass
# class Config:
#     # Qdrant
#     qdrant_host: str = "qdrant"
#     qdrant_port: int = 6333
    
#     # MySQL
#     mysql_host: str = "localhost"
#     mysql_user: str = "schedule_user"
#     mysql_password: str = "schedule_pass"
#     mysql_database: str = "schedule_db"
    
#     # Ollama
#     ollama_base_url: str = "http://localhost:11434"
#     llama_model: str = "meta-llama/Llama-3.2-1B"
    
#     # Embedding
#     embedding_model: str = "intfloat/multilingual-e5-small"
    
#     # Collections
#     metrics_collection: str = "schedule_metrics"
#     constraints_collection: str = "schedule_constraints"
#     examples_collection: str = "schedule_examples"
#     docs_collection: str = "schedule_docs"


class Config(BaseSettings):
    # Qdrant
    qdrant_models: ClassVar = qdrant_models
    model_config = {
        "ignored_types": (type(qdrant_models),)
    }
    qdrant_host: str = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port: int = int(os.getenv("QDRANT_PORT", 6333))

    # MySQL
    mysql_host: str = os.getenv("MYSQL_HOST", "localhost")
    mysql_port: int = int(os.getenv("MYSQL_PORT", 3307))
    mysql_user: str = os.getenv("MYSQL_USER", "schedule_user")
    mysql_password: str = os.getenv("MYSQL_PASSWORD", "schedule_pass")
    mysql_database: str = os.getenv("MYSQL_DATABASE", "schedule_db")

    # Ollama
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    llama_model: str = os.getenv("LLAMA_MODEL", "meta-llama/Llama-3.2-1B")

    # Embedding
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-small")

    # Collections
    metrics_collection: str = os.getenv("METRICS_COLLECTION", "schedule_metrics")
    constraints_collection: str = os.getenv("CONSTRAINTS_COLLECTION", "schedule_constraints")
    examples_collection: str = os.getenv("EXAMPLES_COLLECTION", "schedule_examples")
    docs_collection: str = os.getenv("DOCS_COLLECTION", "schedule_docs")


# ============================================================================
# VECTOR DATABASE MANAGER
# ============================================================================

# class QdrantManager:
#     def __init__(self, config: Config):
#         self.client = QdrantClient(host=config.qdrant_host, port=config.qdrant_port)
#         self.embedding_model = SentenceTransformer(config.embedding_model)
#         self.config = config
        
#     def initialize_collections(self):
#         """Tạo các collections cần thiết"""
#         collections = [
#             self.config.metrics_collection,
#             self.config.constraints_collection,
#             self.config.examples_collection,
#             self.config.docs_collection
#         ]
        
#         vector_size = self.embedding_model.get_sentence_embedding_dimension()
        
#         for collection in collections:
            
#             if not self.client.collection_exists(collection):
#                 self.client.create_collection(
#                     collection_name=collection,
#                     vectors_config=VectorParams(
#                         size=vector_size,
#                         distance=Distance.COSINE
#                     )
#                 )
                
#         logger.info("Qdrant collections initialized.")
    # from qdrant_client.http import models

class QdrantManager:
    def __init__(self, config: Config):
        self.client = QdrantClient(host=config.qdrant_host, port=config.qdrant_port)
        self.embedding_model = SentenceTransformer(config.embedding_model)
        self.config = config

    def initialize_collections(self):
        """Tạo các collections cần thiết"""
        collections = [
            self.config.metrics_collection,
            self.config.constraints_collection,
            self.config.examples_collection,
            self.config.docs_collection
        ]

        vector_size = self.embedding_model.get_sentence_embedding_dimension()

        # Lấy danh sách collection hiện có
        existing_collections = [c.name for c in self.client.get_collections().collections]

        for collection in collections:
            if collection not in existing_collections:
                self.client.create_collection(
                    collection_name=collection,
                    vectors_config=qdrant_models.VectorParams(
                        size=vector_size,
                        distance=qdrant_models.Distance.COSINE
                    )
                )

        logger.info("Qdrant collections initialized.")

    def add_documents(self, collection: str, documents: List[Dict[str, Any]]):
        """Thêm documents vào collection"""
        points = []
        for idx, doc in enumerate(documents):
            text = doc.get("text", "")
            vector = self.embedding_model.encode(text).tolist()
            
            points.append(PointStruct(
                id=idx,
                vector=vector,
                payload=doc
            ))
        
        self.client.upsert(collection_name=collection, points=points)
    
    def search(self, collection: str, query: str, limit: int = 5) -> List[Dict]:
        """Tìm kiếm documents tương tự"""
        query_vector = self.embedding_model.encode(query).tolist()
        
        results = self.client.search(
            collection_name=collection,
            query_vector=query_vector,
            limit=limit
        )
        
        return [
            {
                "score": hit.score,
                "payload": hit.payload
            }
            for hit in results
        ]

# ============================================================================
# MYSQL DATABASE MANAGER
# ============================================================================

class MySQLManager:
    def __init__(self, config: Config):
        self.config = config
        self.connection = None
        
    def connect(self):
        """Kết nối MySQL"""
        self.connection = mysql.connector.connect(
            host=self.config.mysql_host,
            user=self.config.mysql_user,
            password=self.config.mysql_password,
            database=self.config.mysql_database
        )
        
    def get_schedule(self, schedule_code: str) -> Optional[Dict]:
        """Lấy thông tin TKB từ DB"""
        cursor = self.connection.cursor(dictionary=True)
        query = """
            SELECT s.*, 
                   GROUP_CONCAT(DISTINCT c.course_name) as courses,
                   GROUP_CONCAT(DISTINCT r.room_name) as rooms
            FROM schedules s
            LEFT JOIN schedule_courses sc ON s.schedule_id = sc.schedule_id
            LEFT JOIN courses c ON sc.course_id = c.course_id
            LEFT JOIN schedule_rooms sr ON s.schedule_id = sr.schedule_id
            LEFT JOIN rooms r ON sr.room_id = r.room_id
            WHERE s.schedule_code = %s
            GROUP BY s.schedule_id
        """
        cursor.execute(query, (schedule_code,))
        return cursor.fetchone()
    
    def get_schedules_by_week(self, week: int) -> List[Dict]:
        """Lấy danh sách TKB theo tuần"""
        cursor = self.connection.cursor(dictionary=True)
        query = "SELECT * FROM schedules WHERE week = %s"
        cursor.execute(query, (week,))
        return cursor.fetchall()
    
    def get_schedule_violations(self, schedule_code: str) -> List[Dict]:
        """Lấy danh sách vi phạm của TKB"""
        cursor = self.connection.cursor(dictionary=True)
        query = """
            SELECT v.*, c.constraint_name, c.severity
            FROM violations v
            JOIN constraints c ON v.constraint_id = c.constraint_id
            WHERE v.schedule_code = %s
            ORDER BY c.severity DESC
        """
        cursor.execute(query, (schedule_code,))
        return cursor.fetchall()

# ============================================================================
# INTENT DETECTION
# ============================================================================

class IntentDetector:
    def __init__(self, llm):
        self.llm = llm
        self.intent_prompt = PromptTemplate(
            input_variables=["query"],
            template="""Phân tích câu hỏi sau và xác định intent:
Query: {query}

Các intent có thể:
1. input_interpretation - Hiểu yêu cầu, trích xuất thông tin
2. schedule_retrieval - Tìm và hiển thị TKB
3. metric_analysis - Phân tích chất lượng TKB
4. violation_review - Kiểm tra vi phạm
5. schedule_comparison - So sánh nhiều TKB

Trả về JSON format:
{{"intent": "...", "entities": {{"schedule_code": "...", "week": ..., "constraints": []}}}}"""
        )
        
    def detect(self, query: str) -> Dict:
        """Phát hiện intent và trích xuất entities"""
        chain = LLMChain(llm=self.llm, prompt=self.intent_prompt)
        result = chain.run(query=query)
        
        try:
            # Parse JSON response
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
            
        # Fallback: Simple pattern matching
        entities = {}
        
        # Extract schedule code (format: ABC123, CLB102, etc)
        code_match = re.search(r'\b([A-Z]{2,3}\d{2,3})\b', query)
        if code_match:
            entities["schedule_code"] = code_match.group(1)
        
        # Extract week
        week_match = re.search(r'tuần\s+(\d+)', query)
        if week_match:
            entities["week"] = int(week_match.group(1))
        
        # Determine intent
        intent = IntentType.INPUT_INTERPRETATION.value
        
        if any(kw in query.lower() for kw in ["hiển thị", "xem", "lấy", "cho mình"]):
            intent = IntentType.SCHEDULE_RETRIEVAL.value
        elif any(kw in query.lower() for kw in ["chất lượng", "điểm", "cân bằng", "đánh giá"]):
            intent = IntentType.METRIC_ANALYSIS.value
        elif any(kw in query.lower() for kw in ["vi phạm", "nhận xét", "vấn đề"]):
            intent = IntentType.VIOLATION_REVIEW.value
        elif any(kw in query.lower() for kw in ["so sánh", "tốt hơn"]):
            intent = IntentType.SCHEDULE_COMPARISON.value
        
        return {"intent": intent, "entities": entities}

# ============================================================================
# RAG CHATBOT
# ============================================================================

class ScheduleRAGChatbot:
    def __init__(self, config: Config):
        self.config = config
        self.qdrant = QdrantManager(config)
        self.mysql = MySQLManager(config)
        self.llm = Ollama(
            model=config.llama_model,
            base_url=config.ollama_base_url
        )
        self.intent_detector = IntentDetector(self.llm)
        
    def initialize(self):
        """Khởi tạo hệ thống"""
        logger.info("Initializing Qdrant collections...")
        self.qdrant.initialize_collections()
        logger.info("Qdrant collections initialized.")
        logger.info("Sql connect prepare.")
        self.mysql.connect()
        logger.info("MySQL connected.")
        
    def process_query(self, query: str) -> str:
        """Xử lý câu hỏi từ người dùng"""
        # 1. Detect intent
        intent_result = self.intent_detector.detect(query)
        intent = intent_result["intent"]
        entities = intent_result["entities"]
        
        # 2. Route to appropriate handler
        if intent == IntentType.SCHEDULE_RETRIEVAL.value:
            return self._handle_schedule_retrieval(entities, query)
        elif intent == IntentType.METRIC_ANALYSIS.value:
            return self._handle_metric_analysis(entities, query)
        elif intent == IntentType.VIOLATION_REVIEW.value:
            return self._handle_violation_review(entities, query)
        elif intent == IntentType.SCHEDULE_COMPARISON.value:
            return self._handle_schedule_comparison(entities, query)
        else:
            return self._handle_input_interpretation(query)
    
    def _handle_schedule_retrieval(self, entities: Dict, query: str) -> str:
        """Xử lý intent: Tìm và hiển thị TKB"""
        schedule_code = entities.get("schedule_code")
        
        if not schedule_code:
            return "Vui lòng cung cấp mã thời khóa biểu (ví dụ: CLB101, ABC123)"
        
        # Query MySQL
        schedule = self.mysql.get_schedule(schedule_code)
        
        if not schedule:
            return f"Không tìm thấy thời khóa biểu với mã {schedule_code}"
        
        # Format response
        response = f"""
📅 **Thời Khóa Biểu: {schedule_code}**

- Tuần: {schedule.get('week', 'N/A')}
- Môn học: {schedule.get('courses', 'N/A')}
- Phòng học: {schedule.get('rooms', 'N/A')}
- Trạng thái: {schedule.get('status', 'N/A')}
"""
        return response.strip()
    
    def _handle_metric_analysis(self, entities: Dict, query: str) -> str:
        """Xử lý intent: Phân tích metric"""
        schedule_code = entities.get("schedule_code")
        
        # Search relevant metrics from Qdrant
        metric_docs = self.qdrant.search(
            collection=self.config.metrics_collection,
            query=query,
            limit=3
        )
        
        # Get schedule from MySQL
        schedule = None
        if schedule_code:
            schedule = self.mysql.get_schedule(schedule_code)
        
        # Build context
        context = "Các metric đánh giá:\n"
        for doc in metric_docs:
            context += f"- {doc['payload'].get('text', '')}\n"
        
        # Generate analysis with LLM
        prompt = PromptTemplate(
            input_variables=["context", "query", "schedule"],
            template="""Dựa trên các metric sau:
{context}

Thông tin TKB: {schedule}

Câu hỏi: {query}

Hãy phân tích và đánh giá chất lượng TKB. Trả lời ngắn gọn, rõ ràng."""
        )
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        result = chain.run(
            context=context,
            query=query,
            schedule=json.dumps(schedule, ensure_ascii=False) if schedule else "Chưa có thông tin"
        )
        
        return result
    
    def _handle_violation_review(self, entities: Dict, query: str) -> str:
        """Xử lý intent: Kiểm tra vi phạm"""
        schedule_code = entities.get("schedule_code")
        
        if not schedule_code:
            return "Vui lòng cung cấp mã thời khóa biểu để kiểm tra vi phạm"
        
        # Get violations from MySQL
        violations = self.mysql.get_schedule_violations(schedule_code)
        
        if not violations:
            return f"✅ Thời khóa biểu {schedule_code} không có vi phạm nào!"
        
        # Format violations
        response = f"⚠️ **Vi phạm của TKB {schedule_code}:**\n\n"
        
        for v in violations:
            severity = "🔴 Nghiêm trọng" if v['severity'] == 'high' else "🟡 Trung bình"
            response += f"- {severity}: {v['constraint_name']}\n"
            response += f"  Chi tiết: {v.get('description', 'N/A')}\n\n"
        
        response += f"\n📊 Tổng số vi phạm: {len(violations)}"
        return response
    
    def _handle_schedule_comparison(self, entities: Dict, query: str) -> str:
        """Xử lý intent: So sánh TKB"""
        # Extract multiple schedule codes
        codes = re.findall(r'\b([A-Z]{2,3}\d{2,3})\b', query)
        
        if len(codes) < 2:
            return "Vui lòng cung cấp ít nhất 2 mã TKB để so sánh (ví dụ: CLB101 và CLB102)"
        
        schedules = []
        for code in codes[:3]:  # Limit to 3 schedules
            schedule = self.mysql.get_schedule(code)
            if schedule:
                schedules.append(schedule)
        
        if len(schedules) < 2:
            return "Không đủ thông tin để so sánh các TKB"
        
        # Build comparison
        response = "📊 **So sánh Thời Khóa Biểu:**\n\n"
        
        for s in schedules:
            response += f"**{s['schedule_code']}:**\n"
            response += f"- Tuần: {s.get('week', 'N/A')}\n"
            response += f"- Số môn: {len(s.get('courses', '').split(','))}\n\n"
        
        return response
    
    def _handle_input_interpretation(self, query: str) -> str:
        """Xử lý intent: Hiểu và giải thích yêu cầu"""
        # Search examples
        examples = self.qdrant.search(
            collection=self.config.examples_collection,
            query=query,
            limit=2
        )
        
        context = "Các ví dụ tương tự:\n"
        for ex in examples:
            context += f"- {ex['payload'].get('text', '')}\n"
        
        prompt = PromptTemplate(
            input_variables=["context", "query"],
            template="""Dựa trên các ví dụ:
{context}

Câu hỏi của người dùng: {query}

Hãy giải thích người dùng muốn làm gì và gợi ý cách hỏi rõ hơn."""
        )
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        return chain.run(context=context, query=query)

# ============================================================================
# MAIN - USAGE EXAMPLE
# ============================================================================

def main():
    # Initialize
    config = Config()
    chatbot = ScheduleRAGChatbot(config)
    chatbot.initialize()
    
    # Sample data for Qdrant (chỉ chạy 1 lần khi setup)
    sample_metrics = [
        {
            "text": "Điểm cân bằng tuần: Đánh giá mức độ phân bổ đều các môn học trong tuần, tránh tình trạng quá tải vào một số ngày",
            "type": "metric",
            "name": "weekly_balance"
        },
        {
            "text": "Điểm vi phạm room capacity: Kiểm tra số phòng học có vượt sức chứa hay không",
            "type": "metric",
            "name": "room_capacity_violation"
        }
    ]
    
    chatbot.qdrant.add_documents(
        collection=config.metrics_collection,
        documents=sample_metrics
    )
    
    # Test queries
    queries = [
        "Cho mình xem thời khóa biểu CLB101",
        "TKB ABC123 có vi phạm gì không?",
        "So sánh lịch CLB101 và CLB102"
    ]
    
    for query in queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"{'='*60}")
        response = chatbot.process_query(query)
        print(response)

if __name__ == "__main__":
    main()