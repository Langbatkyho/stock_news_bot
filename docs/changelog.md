# Nhật ký Thay đổi (Changelog) - Stock News Bot

Tất cả các thay đổi về mã nguồn và logic nghiệp vụ được ghi nhận tại đây theo thứ tự thời gian đảo ngược.

---

## [v2.0.0] - 2026-06-24
### Added
*   **Pydantic Data Contracts**: Khởi tạo [schemas.py](file:///d:/Nghiên cứu AI/vnstock-agent-guide/stock_news_bot/models/schemas.py) định nghĩa `ArticleSchema`, `ArticleAnalysisSchema` và `CategorySummarySchema` giúp kiểm soát chặt chẽ luồng dữ liệu đầu vào và đầu ra.
*   **Instructor Integration & Self-Correction**: Tích hợp thư viện `instructor` cùng mô hình Gemini trong [ai_analyzer.py](file:///d:/Nghiên cứu AI/vnstock-agent-guide/stock_news_bot/analyzer/ai_analyzer.py) thực thi cơ chế tự sửa lỗi (Self-Correction) với `max_retries=3` khi Pydantic reject dữ liệu lỗi từ LLM.
*   **Subagent Metrics Logging**: Thiết lập ghi nhận nhật ký hiệu suất của Subagent (`logs/agent_metrics.jsonl`) lưu thông tin thời gian xử lý, số lần retry, trạng thái thành công/thất bại và lỗi cụ thể của từng lượt gọi AI.
*   **Tách biệt Module Trách nhiệm**:
    *   Tách lớp lọc từ khóa thô watchlist sang [filters.py](file:///d:/Nghiên cứu AI/vnstock-agent-guide/stock_news_bot/utils/filters.py).
    *   Tách lớp định dạng báo cáo Telegram sang [formatters.py](file:///d:/Nghiên cứu AI/vnstock-agent-guide/stock_news_bot/utils/formatters.py).
*   **Quy tắc Toàn cục**: Thiết lập [GLOBAL_CONSTRAINTS.md](file:///d:/Nghiên cứu AI/vnstock-agent-guide/docs/GLOBAL_CONSTRAINTS.md) ràng buộc hành vi của mọi coding agent khi chỉnh sửa dự án.

### Changed
*   **Giải phóng Orchestrator**: Refactor [main.py](file:///d:/Nghiên cứu AI/vnstock-agent-guide/stock_news_bot/main.py) thành pure pipeline coordinator, loại bỏ hoàn toàn các logic xử lý nghiệp vụ, lọc và định dạng.
*   **End-to-End Data Contract**: Nâng cấp [news_crawler.py](file:///d:/Nghiên cứu AI/vnstock-agent-guide/stock_news_bot/crawlers/news_crawler.py) để trả về trực tiếp `List[ArticleSchema]` thay vì Pandas `DataFrame`, loại bỏ Pandas hoàn toàn khỏi các ranh giới module.
*   **Quy tắc Nghiệp vụ tại Schema**: Di chuyển toàn bộ business logic kiểm thử (như lọc thẻ HTML rác, kiểm tra độ dài mảng dữ liệu) vào `@field_validator` của `CategorySummarySchema`.
*   **Nâng cấp Test Suite**: Mở rộng [test_contracts.py](file:///d:/Nghiên cứu AI/vnstock-agent-guide/stock_news_bot/tests/test_contracts.py) từ 3 test cases lên 7 test cases toàn diện, bao phủ kiểm thử Schema, Filters và Formatters (100% Passed).

### Removed
*   **Nợ Kỹ thuật**: Xóa bỏ hoàn toàn file helper `analyzer/utils.py` và hàm `_to_native()`.
*   **Dead Code**: Xóa bỏ file `utils/validator.py` không còn sử dụng. Loại bỏ các dead import (`import html` thừa trong `main.py`).

---

## [v1.4.0] - 2026-06-19
### Fixed
*   **Data Contract Lỗi**: Bổ sung `_to_native(art)` khi duyệt tin tức trong `generate_category_summary` tại `ai_analyzer.py`, đảm bảo toàn bộ dữ liệu chuyển đổi sang kiểu Python thuần trước khi gửi cho Gemini API.
*   **Mid-cycle Caching**: Di chuyển lệnh `mark_as_processed` ra khỏi vòng lặp gửi tin trong `main.py`, gom vào khối `finally` ở cuối chu kỳ chạy và chỉ đánh dấu các bài viết gửi thành công để đảm bảo tính nguyên tử của dữ liệu cache.
*   **Dead Code**: Xóa bỏ phương thức không còn sử dụng `format_scorecard()` trong `telegram_bot.py`.

### Changed
*   **Khởi tạo tài nguyên tối ưu**: Truyền tham số `settings` từ `main()` xuyên suốt qua `run_cycle()` và `run_cycle_async()`, tránh khởi tạo lại `Settings()` liên tục gây tốn tài nguyên I/O.
*   **Đóng gói Python Package**: Bổ sung tệp `__init__.py` rỗng vào 6 thư mục module con (`analyzer`, `bot`, `cache`, `config`, `crawlers`, `utils`) giúp chuẩn hóa cấu trúc import của Python.
*   **Bảo mật & Dọn dẹp**: 
    *   Tạo file cấu hình mẫu `.env.example` chuẩn để bảo vệ thông tin cá nhân.
    *   Tạo file `.gitignore` cục bộ để loại bỏ các tệp nhạy cảm (`.env`), cache, sqlite và tệp tạm.
    *   Xóa bỏ file test rác ngoài luồng (`test_category_crawler.py`) và các file CSV tạm debug.

---

## [v1.3.0] - 2026-06-19
### Added
*   **Gemini API Key Rotation**: Hỗ trợ cấu hình nhiều API Key phân cách bằng dấu phẩy trong `.env`. Bot tự động xoay key tiếp theo lập tức khi gặp lỗi `RESOURCE_EXHAUSTED` (429).
*   **Tách đôi bản tin**: `main.py` chia tách báo cáo thành 2 tin nhắn độc lập: *Bản tin Vĩ mô & Thị trường* (gửi tin Vĩ mô) và *Bản tin Ngành & Doanh nghiệp* (gửi tin Vi mô).
*   **Độ trễ requests**: Thêm trễ 2 giây (`time.sleep(2)`) giữa các requests AI để tránh quá tải API.

### Changed
*   **Loại bỏ ngôn ngữ thưa gửi**: Cập nhật lại các prompt trong `analyzer/prompts.py` ép AI chỉ xuất Plain Text trực diện, cấm các câu chào hỏi xã giao hoặc thưa gửi mở/kết.
*   **HTML Escaping cho AI summary**: Sử dụng `html.escape()` mã hóa văn bản tóm tắt thô từ AI để triệt tiêu các lỗi parsing của Telegram khi gặp các ký tự so sánh tài chính như `<` hoặc `>`.

---

## [v1.2.0] - 2026-06-19
### Added
*   **RSS 4 danh mục**: Thay đổi nguồn cào CafeF sitemap sang 10 nguồn RSS chia làm 4 danh mục: Vĩ mô Việt Nam, Vĩ mô Thế giới, Kinh tế Ngành, Doanh nghiệp & Đầu tư.
*   **Lọc kép (Pre-filter bằng code)**: Thêm bộ lọc so khớp từ khóa liên quan đến Watchlist (Ngân hàng, Chứng khoán...) đối với danh mục Ngành & Doanh nghiệp để giảm 50% lượng bài gửi lên AI.
*   **Prompt tổng hợp nhóm tin**: Thêm hàm `build_category_prompt` và `generate_category_summary` để AI tóm tắt đồng thời nhiều bài viết và suy luận tác động lên `SHB` và `VND`.

---

## [v1.1.0] - 2026-06-18
### Fixed
*   **Lỗi Windows UTF-8**: Sửa lỗi `UnicodeEncodeError` khi in log ra console Windows bằng cách reconfigure stdout/stderr sang UTF-8.
*   **Lọc Watchlist**: Khắc phục lỗi so khớp từ khóa không chính xác bằng cách dùng regex match word boundary (`\bSYMBOL\b`).
*   **Tham số Crawler**: Sửa lỗi gọi sai tham số `top_n` sang `max_articles` trong `EnhancedNewsCrawler`.

---

## [v1.0.0] - 2026-06-18
### Added
*   Khởi tạo cấu trúc thư mục dự án và file cấu hình `.env.example`.
*   Tạo `utils/logger.py` cấu hình RotatingFileHandler xuất log ra tệp và console.
*   Tạo `config/settings.py` tải và xác thực biến môi trường.
*   Tạo `cache/state_cache.py` quản lý alert cache bằng ghi file nguyên tử (atomic write).
*   Tạo `crawlers/news_crawler.py` cào tin tức sitemap CafeF ban đầu.
*   Tạo `analyzer/ai_analyzer.py` kết nối Gemini API.
*   Tạo `bot/telegram_bot.py` gửi tin nhắn HTML có phân đoạn (chunking).
*   Tạo `main.py` phối hợp chu kỳ chạy định kỳ.
