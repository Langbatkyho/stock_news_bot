# GLOBAL CONSTRAINTS - STOCK NEWS BOT

Tài liệu này đóng vai trò là "Bộ Luật Bất Biến" (System Constraints) cho toàn bộ dự án. Tất cả các tác nhân AI (Orchestrator, Coder, Reviewer) hoặc lập trình viên con người khi tham gia phát triển, bảo trì dự án này **BẮT BUỘC PHẢI** tuân thủ các nguyên tắc dưới đây. 

Tuyệt đối không được phá vỡ các quy tắc này vì bất kỳ lý do gì (kể cả khi fix bug khẩn cấp hay tìm đường tắt).

---

## 1. Data Contract (Hợp Đồng Dữ Liệu End-to-End)
*   **KHÔNG DÙNG PANDAS:** Tuyệt đối không dùng Pandas DataFrame hay Dictionary tự do ở các ranh giới giao tiếp giữa Crawler, Filter, AI và Formatter.
*   **PYDANTIC LÀ CHUẨN MỰC:** Mọi dữ liệu luân chuyển phải được đóng gói vào Pydantic Schema (được định nghĩa tại `models/schemas.py`).
    *   *Crawler* bắt buộc sinh ra `List[ArticleSchema]`.
    *   *AI Analyzer* bắt buộc sinh ra `CategorySummarySchema`.

## 2. No "God Object" (Tách Biệt Trách Nhiệm)
*   **Orchestrator Thuần Túy:** File `main.py` chỉ được phép đóng vai trò Pipeline Coordinator (Điều phối luồng: Giao việc -> Nhận kết quả).
*   **Cấm chèn logic rác:** Tuyệt đối không được phép chèn logic lọc dữ liệu (Filter), không xử lý Escape chuỗi/HTML (Formatter), và không khởi tạo Prompt (Analyzer) trực tiếp vào bên trong `main.py`.

## 3. Self-Correction & Resilient Design (Kháng Lỗi & Tự Sửa Sai)
*   **Uỷ quyền sửa lỗi cho Subagent:** Orchestrator không tự đi sửa lỗi định dạng rác (HTML/Markdown) của LLM. Mọi giao tiếp với LLM bắt buộc phải được bọc qua thư viện `instructor` để kích hoạt vòng lặp Tự sửa lỗi (Self-correction) với tham số `max_retries=3`.
*   **Chống Spam API:** Bắt buộc duy trì độ trễ `time.sleep(2)` giữa các request gọi AI.
*   **Bền bỉ (Resilience):** Phải duy trì cơ chế xoay vòng API Key dự phòng khi gặp lỗi `429 RESOURCE_EXHAUSTED`.

## 4. Atomic State Caching (Ghi Trạng Thái Nguyên Tử)
*   **Ghi một lần duy nhất:** Trạng thái các bài báo đã được xử lý (`sent_urls`) CHỈ ĐƯỢC PHÉP ghi (dump) xuống hệ thống lưu trữ ở khối lệnh `finally` vào cuối chu kỳ chạy của `main.py`.
*   **Cấm ghi giữa chừng:** Tuyệt đối không được ghi đè trạng thái trong lúc vòng lặp xử lý tin tức đang diễn ra dở dang, để tránh rò rỉ trạng thái khi script bị crash hoặc bị dừng đột ngột.

## 5. Dọn Dẹp và Đồng Bộ Tài Liệu (Cleanup & Sync)
*   **SSOT (Single Source of Truth):** Khi thay đổi bất kỳ logic kiến trúc nào, bắt buộc phải cập nhật bản thiết kế gốc tại `docs/implementation_plan.md` VÀ ghi nhận lịch sử vào `docs/changelog.md`.
*   **Zero Trash:** Tuyệt đối không để lại file rác debug (ví dụ: `temp_*.csv`), các lệnh import bị thừa, hoặc code tạm bợ sau khi hoàn thành Task. Cần tự dọn dẹp (Cleanup) sau mỗi đợt chỉnh sửa.
