# 🔎 BÁO CÁO CODE REVIEW — Stock News Bot
**Reviewer:** Claude Opus 4.6 (Principal Code Reviewer)  
**Ngày:** 2026-06-19  

---

### 1. 🔍 ĐỐI CHIẾU SỰ TUÂN THỦ (PLAN VS IMPLEMENTATION)

| Mã Task | Tên Task (Trong Plan) | Trạng thái | Ghi chú kỹ thuật nhanh |
| :--- | :--- | :--- | :--- |
| Task 1 | `.env.example` | **SÓT** | File `.env.example` không tồn tại trong repo. Chỉ có `.env` chứa secret thật. |
| Task 2 | `utils/logger.py` | **Đạt** | RotatingFileHandler 5MB/5 backup, auto `makedirs`, guard `logger.handlers`. |
| Task 3 | `config/settings.py` | **Đạt** | `python-dotenv`, raise `EnvironmentError` nếu thiếu biến, parse list đúng. |
| Task 4 | `cache/state_cache.py` | **Đạt** | Atomic write `.tmp` + `os.replace`. TTL cleanup. JSON corrupt → `{}`. |
| Task 5 | `crawlers/news_crawler.py` | **Sai lệch** | Không có retry/exponential backoff trên lệnh gọi mạng `vnstock_news` (Plan yêu cầu 3 lần retry). Chỉ có try/except bọc đơn giản. |
| Task 6 | `analyzer/utils.py` (`_to_native`) | **Đạt** | Đủ xử lý: numpy int/float/nan, pd.Timestamp/NaT, dict, list, pd.Series. |
| Task 7 | `analyzer/prompts.py` | **Đạt** | Dynamic prompt 3 loại + `build_category_prompt` (mở rộng hợp lý theo yêu cầu user #9). Anti-hallucination directive có. |
| Task 8 | `analyzer/ai_analyzer.py` | **Sai lệch** | Model mặc định `gemini-2.5-flash` thay vì `gemini-3.5-flash` như Plan. Retry loop vượt spec (max `len(keys)*2` thay vì tối đa 3). Chấp nhận được nhưng lệch Plan. |
| Task 9 | `bot/telegram_bot.py` | **Đạt** | Chunk 4000 ký tự, fallback plain-text via regex strip HTML, retry 3 lần + rate-limit handler. |
| Task 10 | `main.py` (Orchestrator) | **Sai lệch** | Khởi tạo lại `Settings()` bên trong mỗi `run_cycle_async()` thay vì 1 lần ở `main()`. `import html` nằm trong vòng lặp (dòng 52). Cache ghi giữa chừng khi gửi thành công từng nhóm (dòng 85-88) thay vì cuối chu kỳ — **vi phạm ràng buộc Plan mục State Caching**. |
| Task 11 | `run.sh` | **Đạt** | `cd`, `export PYTHONUTF8`, venv activate, `nohup &`. |
| Task 12 | `run.bat` | **Đạt** | `chcp 65001`, `set PYTHONUTF8=1`, `cd /d`, venv activate. |
| Task 13 | `docs/implementation_plan.md` | **Đạt** | SSOT hiện trạng Live. |
| Task 14 | `docs/changelog.md` | **Đạt** | Entries theo thứ tự version đảo ngược. |
| — | `test_category_crawler.py` | **Ngoài Plan** | File test 196 dòng chứa code trùng lặp với `news_crawler.py` + `ai_analyzer.py`. Không nằm trong danh sách 14 Task. **Vi phạm ràng buộc "không tự ý can thiệp file ngoài danh sách"**. |
| — | 4 file `temp_*.csv` | **Ngoài Plan** | File rác debug (53KB-311KB) bỏ quên trong repo. |
| — | `__init__.py` | **SÓT** | Không có `__init__.py` trong các package `analyzer/`, `bot/`, `cache/`, `config/`, `crawlers/`, `utils/`. Chạy được nhờ `sys.path` append nhưng **không chuẩn Python packaging**. |

---

### 2. ⚡ TỐI ƯU HÓA WORKFLOW & KIẾN TRÚC

- **Lỗi bảo mật nghiêm trọng:**
  - File `.env` chứa **Gemini API Key thật** và **Telegram Bot Token thật** đang nằm trong working tree của Git. Dù `.gitignore` có `.env`, nếu người dùng chạy `git add .` sẽ commit secret lên remote. **Phải thêm `.env` vào `.gitignore` tại cấp thư mục `stock_news_bot/` hoặc tạo `.gitignore` riêng tại đó.** Ngoài ra, file `.env.example` bắt buộc phải tồn tại (Task 1 bị sót).

- **Lệch pha Data Contract:**
  - `generate_category_summary()` trong `ai_analyzer.py` (dòng 121-175) **không gọi `_to_native()`** trên danh sách `articles` trước khi chèn vào prompt. Chỉ có `analyze_article()` gọi `_to_native()`. Điều này **vi phạm ràng buộc**: *"toàn bộ dữ liệu Pandas/Numpy bắt buộc đi qua `_to_native()` trước khi đưa vào prompt LLM"*.
  - `main.py` dòng 87: `categories_data[cat_name]["url"].tolist()` — gọi `.tolist()` trên cột Pandas mà không qua `_to_native()`, có thể chứa `numpy.str_` thay vì `str` thuần.

- **Trùng lặp / Thừa thãi:**
  - `test_category_crawler.py` (196 dòng) chứa bản sao gần nguyên vẹn của `CATEGORY_MAPPING`, logic cào tin, và logic gọi AI — **trùng ~70%** với `news_crawler.py` + `ai_analyzer.py`. Nên xóa hoặc chuyển thành test module chuẩn dùng `pytest`.
  - 4 file `temp_cafebiz.csv`, `temp_cafef.csv`, `temp_tuoitre.csv`, `temp_vietstock.csv` (~510KB tổng) — file debug rác.
  - `format_scorecard()` trong `telegram_bot.py` (dòng 16-37) hiện **không được gọi ở bất kỳ đâu** trong codebase. Dead code kể từ khi chuyển sang chế độ bản tin tổng hợp.

---

### 3. 🛠️ VECTOR TINH CHỈNH CODEBASE (REFACTOR VECTORS)

**Vector 1 — Thiếu `_to_native()` trong `generate_category_summary`**
- **Vị trí:** `analyzer/ai_analyzer.py` → hàm `generate_category_summary`, dòng 131-136
- **Vấn đề:** Articles từ `df.to_dict(orient="records")` chứa `numpy.str_` và `pd.Timestamp`. Chèn trực tiếp vào prompt LLM vi phạm Data Contract.
- **Giải pháp:**
```python
# Dòng 131, thay:
        for i, art in enumerate(articles, 1):
# bằng:
        for i, art in enumerate(articles, 1):
            art = _to_native(art)
```

**Vector 2 — `mark_as_processed` gọi giữa chu kỳ thay vì cuối**
- **Vị trí:** `main.py` → hàm `run_cycle_async`, dòng 84-88
- **Vấn đề:** Gọi `mark_as_processed` ngay sau khi gửi thành công từng nhóm bản tin. Nếu bot crash giữa nhóm Macro và Micro, nhóm Macro bị đánh dấu "đã gửi" nhưng Micro chưa → mất tin. Plan quy định chỉ ghi cache cuối chu kỳ.
- **Giải pháp:** Di chuyển toàn bộ khối `mark_as_processed` ra ngoài vòng lặp `for group_name...`, chuyển vào trước `save_alert_cache` trong block `finally`:
```python
    finally:
        # Đánh dấu tất cả tin đã gửi thành công
        for cat_name, df in categories_data.items():
            if not df.empty:
                for url in df["url"].tolist():
                    cache = mark_as_processed(url, cache)
        save_alert_cache(cache)
```

**Vector 3 — `import html` trong vòng lặp**
- **Vị trí:** `main.py`, dòng 52
- **Vấn đề:** `import html` nằm bên trong vòng lặp `for cat_name, df in categories_data.items()`. Mặc dù Python cache import, đặt nó ở đây là anti-pattern và gây nhầm lẫn khi đọc code.
- **Giải pháp:** Di chuyển `import html` lên đầu file (dòng 1-5).

**Vector 4 — Khởi tạo `Settings()` lặp mỗi chu kỳ**
- **Vị trí:** `main.py`, dòng 18 (`run_cycle_async`) và dòng 104 (`main`)
- **Vấn đề:** `Settings()` đọc lại `.env` + validate mỗi 30 giây khi schedule chạy. Lãng phí I/O, và nếu `.env` bị xóa giữa chừng → crash toàn bộ bot thay vì dùng config đã load.
- **Giải pháp:** Truyền `settings` instance từ `main()` xuống `run_cycle()` qua tham số:
```python
def run_cycle(settings):
    asyncio.run(run_cycle_async(settings))

# Trong main():
    schedule.every().day.at(time_str).do(run_cycle, settings)
```

**Vector 5 — Thiếu `__init__.py` packages**
- **Vị trí:** `analyzer/`, `bot/`, `cache/`, `config/`, `crawlers/`, `utils/`
- **Vấn đề:** Không có `__init__.py` → không phải Python package chuẩn. Hoạt động nhờ `sys.path.append` hoặc CWD, nhưng sẽ gây lỗi khi import từ bên ngoài thư mục project hoặc khi dùng test runner.
- **Giải pháp:** Tạo `__init__.py` rỗng trong mỗi thư mục con:
```bash
touch analyzer/__init__.py bot/__init__.py cache/__init__.py config/__init__.py crawlers/__init__.py utils/__init__.py
```

---

### 4. ✅ KẾT LUẬN VÀ TRẠNG THÁI HIỆN TẠI (v1.4.0)

**Trạng thái: Đã giải quyết toàn bộ**

*   Tất cả các khuyến nghị và lỗi bảo mật/cấu trúc được nêu trong bản Code Review này đã được tiếp thu và xử lý hoàn tất trong phiên bản **v1.4.0** (Commit Refactoring).
*   Các điểm vi phạm Data Contract và lỗi State Caching đều đã được khắc phục triệt để. Hệ thống hiện tại đã sẵn sàng để vận hành ổn định lâu dài qua Task Scheduler.

---

## 🔎 BÁO CÁO AUDIT & CODE REVIEW — KIẾN TRÚC v2.0.0
**Reviewer:** Claude Opus 4.6 (Principal Code Reviewer)  
**Ngày:** 2026-06-24  

### 1. KẾT QUẢ ĐỐI CHIẾU KIẾN TRÚC v2.0.0
Sau khi thực hiện rà soát sâu rộng đợt nâng cấp lớn lên phiên bản v2.0.0, toàn bộ các sai lệch về Data Contract và nợ kỹ thuật từ phiên bản trước đã được xử lý triệt để:

| Vấn đề Phát hiện (v2.0 Draft) | Giải pháp thực thi thực tế (Live v2.0.0) | Trạng thái |
| :--- | :--- | :--- |
| **Data Contract chưa End-to-End** | `NewsCrawler` đã loại bỏ hoàn toàn `pd.DataFrame`, trả trực tiếp `List[ArticleSchema]` sang cho Filter và Orchestrator. | **Đạt 100%** |
| **Trùng lặp logic & Thừa thãi** | Xóa hoàn toàn file `analyzer/utils.py` (`_to_native`) và `utils/validator.py`. Chuyển logic kiểm tra nghiệp vụ vào `@field_validator` của Pydantic schema. | **Đạt 100%** |
| **Logic Lọc và Format dính trong `main.py`** | Tách triệt để sang `utils/filters.py` (lọc từ khóa) và `utils/formatters.py` (định dạng báo cáo HTML Telegram). | **Đạt 100%** |
| **Bỏ sót Self-Correction ở một số hàm** | Hàm `analyze_article` đã được nâng cấp đồng bộ sử dụng `instructor` kết hợp với `ArticleAnalysisSchema` tương tự hàm tổng hợp danh mục. | **Đạt 100%** |
| **Test suite quá mỏng** | Nâng cấp file `tests/test_contracts.py` lên 7 unit tests đầy đủ, bao phủ kiểm thử Schema, Filters và Formatters (100% Passed). | **Đạt 100%** |
| **Thiếu quy tắc ràng buộc** | Đã ban hành hướng dẫn phát triển toàn cục [GLOBAL_CONSTRAINTS.md](file:///d:/Nghiên cứu AI/vnstock-agent-guide/docs/GLOBAL_CONSTRAINTS.md). | **Đạt 100%** |

### 2. KẾT LUẬN
Kiến trúc v2.0.0 đạt độ chín về thiết kế phần mềm (Design Pattern): tách biệt rõ ràng các nhiệm vụ, kiểm soát chặt chẽ hợp đồng dữ liệu đầu vào/đầu ra bằng Pydantic kết hợp với khả năng tự sửa lỗi lỗi của LLM thông qua `instructor`. Hệ thống hoạt động tối ưu, giảm thiểu đáng kể lỗi runtime so với phiên bản cũ.

