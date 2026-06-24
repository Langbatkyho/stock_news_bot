# Kế hoạch Triển khai Stock News Bot (SSOT)

Kế hoạch này đóng vai trò là **Single Source of Truth (SSOT)**. Tất cả các Subagent phải tuân thủ nghiêm ngặt định dạng dữ liệu này khi truyền dữ liệu giữa các Layer.

## Data Contract (Bắt buộc tuân thủ)

### 1. News Schema (Đầu ra của DataCrawlerAgent -> Đầu vào của AiAnalyzerAgent)
Dữ liệu tin tức thô thu thập từ `vnstock_news` bắt buộc trả về dưới dạng Pandas DataFrame có chứa các cột sau, và khi chuyển sang dạng Dictionary (`_to_native()`), nó phải có các key tương ứng:
- `url` (str): Đường dẫn duy nhất của bài viết (dùng làm ID cho cache).
- `title` (str): Tiêu đề bài viết.
- `short_description` (str): Mô tả ngắn/Tóm tắt có sẵn.
- `content` (str): Nội dung bài viết (đã được làm sạch sang dạng Markdown).
- `publish_time` (str): Thời gian xuất bản (chuyển đổi sang chuẩn ISO string).
- `category` (str): Chuyên mục tin tức.

### 2. AI Analyzer Schema (Đầu ra của AiAnalyzerAgent -> Đầu vào của TelegramBotAgent)
Kết quả trả về từ Gemini API (đã qua parse JSON) phải là một Dictionary có các key chuẩn hóa:
- `summary` (str): Tóm tắt phân tích của AI.
- `impact` (str): Đánh giá tác động (Tích cực/Tiêu cực/Trung tính/Không rõ).
- `sentiment` (str): Tâm lý thị trường chung từ bài viết.
- `ticker` (str | None): Mã cổ phiếu liên quan (nếu có, ví dụ: "FPT").
- `source_url` (str): Trùng khớp với `url` của bài báo gốc.

## Danh sách Task Thực thi Tuần tự

- **Task 1**: `.env.example` -> Tạo file mẫu khai báo biến môi trường.
- **Task 2**: `utils/logger.py` -> Cấu hình RotatingFileHandler, xuất log chuẩn format.
- **Task 3**: `config/settings.py` -> Class `Settings` đọc `.env`, parse biến.
- **Task 4**: `cache/state_cache.py` -> Xử lý Alert Cache (atomic write, check bài viết mới).
- **Task 5**: `crawlers/news_crawler.py` -> Lớp `NewsCrawler` bọc thư viện `vnstock_news` trả DataFrame đúng News Schema, có Retry Logic.
- **Task 6**: `analyzer/utils.py` -> Hàm `_to_native(obj)` chuyển kiểu Python để tương thích với LLM.
- **Task 7**: `analyzer/prompts.py` -> Các hàm build Dynamic Prompt không chứa logic suy diễn ảo.
- **Task 8**: `analyzer/ai_analyzer.py` -> `AIAnalyzer` gọi Gemini, tuân thủ AI Analyzer Schema, Retry lỗi 429.
- **Task 9**: `bot/telegram_bot.py` -> Định dạng Scorecard và xử lý chunk message, tự đổi sang plain-text nếu lỗi parse_mode.
- **Task 10**: `main.py` -> Orchestrator trung tâm nối các Layer lại qua `schedule`.
- **Task 11 & 12**: `run.sh` và `run.bat` -> Script chạy bot cho nhiều HĐH.
- **Task 13**: `docs/implementation_plan.md` -> File này.
- **Task 14**: `docs/changelog.md` -> Changelog ghi nhận thay đổi file liên tục.

## Ràng buộc của Agent
- Mọi kết nối mạng phải có Try/Catch và Retry loop.
- Không tự ý tải dependencies ngoài.
- Dịch tiếng Việt chỉ làm ở `TelegramReporter`.
- Mọi logic phải đồng bộ cập nhật vào `docs/changelog.md`.
