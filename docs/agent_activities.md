# Báo cáo Hoạt động của các Agent và Subagent

Tài liệu này ghi nhận sự phối hợp và nhật ký công việc của **Orchestrator (Main Agent)** và các **Subagent chuyên biệt** trong suốt vòng đời phát triển của dự án Stock News Bot.

---

## 1. Cơ cấu Phân vai (Agent Roles)

Dự án được triển khai dựa trên nguyên lý Multi-Agent, phân rã một hệ thống lớn thành các tác vụ chuyên biệt:

*   **Orchestrator (Main Agent)**: Đóng vai trò là kiến trúc sư trưởng và điều phối viên. Thiết lập Data Contract, Blueprint, kết nối các layer, rà soát mã nguồn của các subagent, sửa các lỗi tích hợp, tối ưu hóa prompt AI và xử lý các cơ chế bảo vệ (Lọc kép, Xoay vòng API Key, Tách tin nhắn).
*   **EnvSetupAgent (Subagent - `self`)**: Chuyên trách thiết lập môi trường và cấu hình hệ thống.
*   **DataCrawlerAgent (Subagent - `self`)**: Chuyên trách lớp cào tin tức và lưu cache thô.
*   **AiAnalyzerAgent (Subagent - `self`)**: Chuyên trách lớp kết nối Gemini API và xử lý prompts.
*   **TelegramBotAgent (Subagent - `self`)**: Chuyên trách lớp gửi tin nhắn và format HTML/Plain Text Telegram.

---

## 2. Nhật ký Hoạt động chi tiết (Agent Activities Log)

### 2.1 Hoạt động của EnvSetupAgent (Phân nhánh `8623175f`)
*   **Tác vụ thực hiện**:
    *   Tạo tệp cấu hình mẫu `.env.example` quy định các biến môi trường cần thiết.
    *   Tạo thư viện log [logger.py](file:///d:/Nghiên cứu AI/vnstock-agent-guide/stock_news_bot/utils/logger.py) cấu hình RotatingFileHandler (tự tạo thư mục `logs/`, giới hạn 5MB, giữ 5 tệp backup).
    *   Tạo trình quản lý cấu hình [settings.py](file:///d:/Nghiên cứu AI/vnstock-agent-guide/stock_news_bot/config/settings.py) sử dụng `python-dotenv` để validate các biến môi trường bắt buộc.
    *   Tạo các tệp khởi chạy script nhanh [run.sh](file:///d:/Nghiên cứu AI/vnstock-agent-guide/stock_news_bot/run.sh) (cho Linux) và [run.bat](file:///d:/Nghiên cứu AI/vnstock-agent-guide/stock_news_bot/run.bat) (cho Windows).

### 2.2 Hoạt động của DataCrawlerAgent (Phân nhánh `a23d8404`)
*   **Tác vụ thực hiện**:
    *   Xây dựng lớp quản lý cache trạng thái gửi tin [state_cache.py](file:///d:/Nghiên cứu AI/vnstock-agent-guide/stock_news_bot/cache/state_cache.py) sử dụng cơ chế ghi đè nguyên tử (ghi ra file `.tmp` rồi đổi tên bằng `os.replace`), giúp đảm bảo cache không bị hỏng cấu trúc JSON khi bị dừng đột ngột.
    *   Khởi tạo phiên bản [news_crawler.py](file:///d:/Nghiên cứu AI/vnstock-agent-guide/stock_news_bot/crawlers/news_crawler.py) ban đầu, lấy tin tức thô từ RSS CafeF sitemap và lọc theo watchlist.

### 2.3 Hoạt động của AiAnalyzerAgent (Phân nhánh `f694b38a`)
*   **Tác vụ thực hiện**:
    *   Xây dựng [utils.py](file:///d:/Nghiên cứu AI/vnstock-agent-guide/stock_news_bot/analyzer/utils.py) chứa hàm convert kiểu dữ liệu `_to_native()` để lọc sạch các kiểu dữ liệu của numpy/pandas trước khi gửi lên Gemini.
    *   Khởi tạo [ai_analyzer.py](file:///d:/Nghiên cứu AI/vnstock-agent-guide/stock_news_bot/analyzer/ai_analyzer.py) kết nối API Gemini thông qua thư viện `google-genai` mới, tích hợp cơ chế tự động bắt lỗi `ResourceExhausted` (429) và ngủ chờ 65s.

### 2.4 Hoạt động của TelegramBotAgent (Phân nhánh `fbc83d27`)
*   **Tác vụ thực hiện**:
    *   Tạo lớp [telegram_bot.py](file:///d:/Nghiên cứu AI/vnstock-agent-guide/stock_news_bot/bot/telegram_bot.py) gọi API Telegram sendMessage bằng thư viện `requests` (hỗ trợ `parse_mode="HTML"`).
    *   Tích hợp hàm cắt nhỏ tin nhắn `_chunk_text()` để chia tin nhắn thành các phần dưới 4000 ký tự theo dòng để tránh lỗi độ dài của Telegram.
    *   Xây dựng hàm fallback plain-text bằng cách dùng regex loại bỏ thẻ HTML nếu Telegram trả về mã lỗi không thể parse thực thể.

### 2.5 Hoạt động điều phối và sửa lỗi của Orchestrator (Main Agent)
*   **Sửa lỗi Unicode trên Windows**: Bổ sung cấu hình `sys.stdout.reconfigure(encoding='utf-8')` để chống lỗi crash in ký tự tiếng Việt trên Console Windows.
*   **Khắc phục lỗi tham số Crawler**: Phát hiện và sửa lỗi gọi sai tham số `top_n` sang `max_articles` trong `EnhancedNewsCrawler` của thư viện `vnstock_news`.
*   **Tích hợp Lọc kép (Double Filter)**:
    *   Nâng cấp `news_crawler.py` để hỗ trợ cào đồng thời 10 feed RSS thuộc 4 danh mục chuyên biệt.
    *   Viết mã Python lọc thô các bài viết thuộc danh mục Ngành & Doanh nghiệp không chứa từ khóa tài chính/ngân hàng/watchlist để tối ưu token gửi cho AI.
*   **Khắc phục lỗi Telegram Parse HTML**:
    *   Chuyển đổi prompt AI trong [prompts.py](file:///d:/Nghiên cứu AI/vnstock-agent-guide/stock_news_bot/analyzer/prompts.py) sang yêu cầu xuất **Plain Text thuần túy** (không chứa HTML/Markdown).
    *   Trong `main.py`, Orchestrator thực hiện mã hóa ký tự đặc biệt (`html.escape()`) trước khi wrap thẻ HTML của Telegram. **Xử lý triệt để lỗi parse định dạng.**
*   **Cơ chế xoay vòng API Key**:
    *   Phát hiện lỗi cạn kiệt hạn ngạch ngày của tài khoản Free Tier (20 requests/ngày).
    *   Nâng cấp `AIAnalyzer` hỗ trợ danh sách API key dự phòng, tự động xoay key tiếp theo lập tức khi gặp lỗi 429 và thử lại ngay chu trình.
*   **Tách đôi bản tin**:
    *   Tách gộp tin gửi thành 2 tin nhắn riêng biệt: Bản tin Vĩ mô và Bản tin Ngành & Doanh nghiệp, giúp tối ưu hóa luồng hiển thị trên Telegram.

### 2.6 Hoạt động Refactoring và Tối ưu hóa (v1.4.0)
*   **Tác vụ thực hiện**:
    *   **Tuân thủ Data Contract**: Bổ sung hàm `_to_native(art)` vào `generate_category_summary` tại `ai_analyzer.py` nhằm ép kiểu dữ liệu từ Numpy/Pandas về kiểu Python thuần túy trước khi đẩy cho Gemini API.
    *   **State Caching**: Di chuyển khối lệnh ghi trạng thái `mark_as_processed` vào trong khối `finally` ở cuối chu kỳ chạy (`main.py`) nhằm đảm bảo tính nguyên tử, chỉ ghi log thành công thay vì ghi giữa chừng dễ lỗi.
    *   **Tối ưu hóa Tài nguyên**: Truyền đối tượng cấu hình `Settings()` xuyên suốt các hàm chạy vòng lặp thay vì đọc lại `.env` nhiều lần để tối ưu hóa truy xuất hệ thống (I/O).
    *   **Chuẩn hóa & Dọn dẹp**: Tạo thư mục đóng gói Python chuẩn (thêm file `__init__.py` cho các module), tạo tệp `.gitignore`, `.env.example`, và loại bỏ các file tạm/test rác dư thừa.

### 2.7 Hoạt động Tái cấu trúc Kiến trúc v2.0 (v2.0.0)
*   **Tác vụ thực hiện**:
    *   **Thiết lập Data Contracts End-to-End**:
        *   Tạo file [schemas.py](file:///d:/Nghiên cứu AI/vnstock-agent-guide/stock_news_bot/models/schemas.py) định nghĩa các cấu trúc dữ liệu Pydantic: `ArticleSchema`, `ArticleAnalysisSchema` và `CategorySummarySchema`.
        *   Nâng cấp [news_crawler.py](file:///d:/Nghiên cứu AI/vnstock-agent-guide/stock_news_bot/crawlers/news_crawler.py) để trả về trực tiếp danh sách `List[ArticleSchema]` thay vì `pd.DataFrame`. Loại bỏ hoàn toàn sự phụ thuộc vào Pandas trong ranh giới truyền tải dữ liệu giữa Crawler, Filters, và Orchestrator.
    *   **Tích hợp Instructor & Vòng lặp Tự sửa lỗi (Self-Correction)**:
        *   Nâng cấp `AIAnalyzer` kết hợp thư viện `instructor` bọc GenerativeModel của Gemini. Ép buộc LLM trả về đúng schema mong muốn (`CategorySummarySchema` và `ArticleAnalysisSchema`).
        *   Cấu hình `max_retries=3` trong instructor giúp chuyển giao trách nhiệm xử lý lỗi định dạng và nghiệp vụ hoàn toàn cho LLM. Khi Pydantic reject dữ liệu (chứa HTML rác, thiếu summary_points...), instructor sẽ tự gói thông tin lỗi gửi ngược lại để LLM tự sửa trước khi trả kết quả về Orchestrator.
    *   **Giải phóng Orchestrator (Tách biệt Trách nhiệm)**:
        *   Di chuyển logic lọc thô watchlist theo từ khóa từ Crawler sang [filters.py](file:///d:/Nghiên cứu AI/vnstock-agent-guide/stock_news_bot/utils/filters.py).
        *   Di chuyển logic render và định dạng báo cáo gửi Telegram (kèm `html.escape()`) từ `main.py` sang [formatters.py](file:///d:/Nghiên cứu AI/vnstock-agent-guide/stock_news_bot/utils/formatters.py).
        *   Refactor [main.py](file:///d:/Nghiên cứu AI/vnstock-agent-guide/stock_news_bot/main.py) cực kỳ tinh gọn, chỉ làm nhiệm vụ Pipeline Coordinator kết nối các module độc lập.
    *   **Ghi nhận Metrics hiệu năng của Subagent**:
        *   Tích hợp ghi nhận nhật ký hoạt động LLM chi tiết vào `logs/agent_metrics.jsonl`. Ghi lại các chỉ số: thời gian phản hồi, số lần retry, trạng thái thành công/thất bại, lỗi cụ thể và danh mục tin tức.
    *   **Xây dựng Test Suite và Ràng buộc Toàn cục**:
        *   Mở rộng file [test_contracts.py](file:///d:/Nghiên cứu AI/vnstock-agent-guide/stock_news_bot/tests/test_contracts.py) lên 7 unit tests kiểm tra toàn bộ luồng Schema Validation, Filtering và Formatting (đảm bảo 100% Passed).
        *   Ban hành bộ quy chuẩn [GLOBAL_CONSTRAINTS.md](file:///d:/Nghiên cứu AI/vnstock-agent-guide/docs/GLOBAL_CONSTRAINTS.md) áp đặt nguyên tắc code cho tất cả các subagent tham gia phát triển dự án sau này.

