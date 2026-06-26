import time
import json
from typing import Dict, Any, List
from utils.logger import get_logger
from analyzer.prompts import build_company_prompt, build_industry_prompt, build_macro_prompt, build_category_prompt
from models.schemas import CategorySummarySchema, ArticleAnalysisSchema

try:
    from google import genai
    import instructor
except ImportError:
    genai = None
    instructor = None

logger = get_logger(__name__)

class AIAnalyzer:
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.api_keys = [k.strip() for k in api_key.split(",") if k.strip()]
        self.current_key_index = 0
        self.model = model
        self.client = None
        self.genai_client = None
        self._init_client()

    def _init_client(self):
        if genai and instructor and self.api_keys:
            key = self.api_keys[self.current_key_index]
            masked_key = key[:6] + "..." + key[-4:] if len(key) > 10 else "..."
            logger.info(f"Khởi tạo Gemini Client với API Key: {masked_key} (Vị trí: {self.current_key_index + 1}/{len(self.api_keys)})")
            self.genai_client = genai.Client(api_key=key)
            self.client = instructor.from_genai(
                client=self.genai_client,
                mode=instructor.Mode.GEMINI_JSON,
            )
        else:
            logger.warning("Thư viện google-genai hoặc instructor chưa được cài đặt hoặc thiếu API Key.")
            self.client = None

    def rotate_key(self) -> bool:
        """Xoay vòng API Key tiếp theo. Trả về True nếu xoay vòng thành công, False nếu chỉ có 1 key."""
        if len(self.api_keys) <= 1:
            return False
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        self._init_client()
        return True

    def analyze_article(self, article: Dict[str, Any], context_type: str = "company") -> ArticleAnalysisSchema:
        if not self.client:
            return ArticleAnalysisSchema(summary="Lỗi phân tích AI (Chưa cấu hình client)", impact="N/A", sentiment="N/A", ticker=None, source_url=article.get("url", ""))

        if context_type == "company":
            prompt = build_company_prompt(article)
        elif context_type == "industry":
            prompt = build_industry_prompt(article)
        else:
            prompt = build_macro_prompt(article)

        # Cho phép xoay vòng key nếu gặp lỗi quota/quá tải
        max_retries = max(2, len(self.api_keys) * 2)
        start_time = time.time()
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    response_model=ArticleAnalysisSchema,
                    max_retries=3
                )
                response = response.model_copy(update={"source_url": article.get("url", "")})
                
                # Ghi nhận Agent Metrics
                exec_time = time.time() - start_time
                self._log_metrics("analyze_article", 1, attempt, exec_time, "success")
                
                return response
                
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "ResourceExhausted" in error_msg or "503" in error_msg or "quota" in error_msg.lower():
                    logger.warning(f"Lỗi API ({error_msg}) từ Gemini.")
                    if self.rotate_key():
                        logger.info("Đã tự động xoay sang API Key dự phòng và thử lại ngay lập tức...")
                        continue
                    else:
                        if attempt == 0:
                            logger.warning("Chờ 65s để thử lại với API Key duy nhất...")
                            time.sleep(65)
                            continue
                logger.error(f"Lỗi phân tích bài báo: {e}")
                self._log_metrics("analyze_article", 1, attempt, time.time() - start_time, f"failed: {e}")
                break
                
        self._log_metrics("analyze_article", 1, max_retries, time.time() - start_time, "failed: max retries")
        return ArticleAnalysisSchema(summary="Lỗi phân tích AI", impact="N/A", sentiment="N/A", ticker=None, source_url=article.get("url", ""))

    def generate_category_summary(self, category_name: str, articles: List[Dict[str, Any]], watchlist: List[str]) -> CategorySummarySchema:
        """Sử dụng LLM để tạo báo cáo tổng hợp cho danh mục bằng Pydantic Schema"""
        if not self.client:
            return CategorySummarySchema(category_name=category_name, summary_points=["Lỗi: Chưa cấu hình AI client."], impacts=[])
            
        if not articles:
            return CategorySummarySchema(category_name=category_name, summary_points=["Không có tin tức mới nào được ghi nhận cho danh mục này."], impacts=[])
            
        # Tạo prompt tổng hợp
        articles_text = ""
        for i, art in enumerate(articles, 1):
            title = art.get("title", "Không có tiêu đề")
            desc = art.get("short_description", "")
            content = art.get("content", "")[:1000] # Lấy 1000 ký tự đầu để tránh quá tải token
            url = art.get("url", "")
            articles_text += f"\n--- BÀI BÁO {i} ---\nTiêu đề: {title}\nTóm tắt: {desc}\nNội dung sơ bộ: {content}\nNguồn: {url}\n"
            
        prompt = build_category_prompt(category_name, articles_text, watchlist)
        
        # Cho phép xoay vòng key nếu gặp lỗi quota/quá tải
        max_retries = max(2, len(self.api_keys) * 2)
        start_time = time.time()
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    response_model=CategorySummarySchema,
                    max_retries=3, # Validator feedback loop: instructor sẽ tự động trả lỗi cho LLM tự sửa
                )
                response = response.model_copy(update={"category_name": category_name}) # override in case AI misclassifies
                
                # Ghi nhận Agent Metrics
                exec_time = time.time() - start_time
                self._log_metrics(category_name, len(articles), attempt, exec_time, "success")
                
                return response
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "ResourceExhausted" in error_msg or "503" in error_msg or "quota" in error_msg.lower():
                    logger.warning(f"Lỗi API ({error_msg}) từ Gemini.")
                    if self.rotate_key():
                        logger.info("Đã tự động xoay sang API Key dự phòng và thử lại ngay lập tức...")
                        continue
                    else:
                        if attempt == 0:
                            logger.warning("Chờ 65s để thử lại với API Key duy nhất...")
                            time.sleep(65)
                            continue
                logger.error(f"Lỗi khi gọi AI tổng hợp danh mục {category_name}: {e}")
                
                self._log_metrics(category_name, len(articles), attempt, time.time() - start_time, f"failed: {e}")
                
                return CategorySummarySchema(
                    category_name=category_name, 
                    summary_points=[f"Lỗi hệ thống khi tổng hợp tin tức cho danh mục {category_name}: {e}"], 
                    impacts=[]
                )
                
        self._log_metrics(category_name, len(articles), max_retries, time.time() - start_time, "failed: max retries")
        return CategorySummarySchema(
            category_name=category_name, 
            summary_points=[f"Lỗi hệ thống khi tổng hợp tin tức cho danh mục {category_name}"], 
            impacts=[]
        )

    def _log_metrics(self, category: str, num_articles: int, retry_count: int, exec_time: float, status: str):
        import os, datetime
        log_file = "logs/agent_metrics.jsonl"
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        metric = {
            "timestamp": datetime.datetime.now().isoformat(),
            "agent": "AIAnalyzer",
            "task": "generate_category_summary",
            "category": category,
            "articles_count": num_articles,
            "retries": retry_count,
            "execution_time_sec": round(exec_time, 2),
            "status": status
        }
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(metric, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Lỗi ghi metrics: {e}")
