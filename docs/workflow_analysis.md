# Phân Tích Workflow Triển Khai Dự Án Stock News Bot

Tài liệu này tổng hợp và rà soát lại toàn bộ vòng đời phát triển dự án Stock News Bot (từ v1.0.0 đến v2.0.0), phân tích sâu vào các quyết định thiết kế kiến trúc Agentic, những điểm phải tái cấu trúc nhiều lần, và bài học rút ra cho các dự án Multi-Agent tương lai.

---

## 1. Những Điểm Hiệu Quả (Thành Công)

*   **Tư duy Phân rã Hệ thống (Separation of Concerns)**: Việc định hình dự án theo hướng Agentic (phân tách thành Crawler, Analyzer, Telegram Reporter, Orchestrator) ngay từ ban đầu giúp việc khoanh vùng lỗi trở nên cực kỳ dễ dàng. Khi có lỗi về Telegram parse HTML, hệ thống chỉ cần sửa đúng ở lớp Reporter/Formatter mà không làm sập lớp Crawler.
*   **Cơ chế Lọc kép (Double Filter)**: Giải pháp kết hợp "Lọc thô bằng Code" (Pre-filter bằng regex từ khóa) và "Lọc tinh bằng AI" mang lại hiệu suất vượt trội. Việc này giúp giảm tới 50% lượng token gửi cho LLM, ngăn chặn LLM bị "ảo giác" (hallucinate) và tăng tốc độ xử lý.
*   **Xoay vòng API (API Key Rotation) & Cơ chế Nguyên tử (Atomic)**: Tích hợp sớm cơ chế tự động xoay vòng API key khi gặp lỗi `429 RESOURCE_EXHAUSTED` và cơ chế ghi Cache ở khối `finally` đã giúp bot duy trì sự sống sót (resilience) ngay cả khi môi trường mạng và hạn ngạch API không ổn định.
*   **Ban hành "Luật Toàn cục" (GLOBAL_CONSTRAINTS)**: Giải pháp tạo một file Markdown lưu trữ bộ nguyên tắc hệ thống giúp đồng bộ hóa hành vi của các tác nhân AI ở các phiên chat khác nhau, tránh việc một Agent mới vào phá vỡ cấu trúc của Agent trước đó.

---

## 2. Những Điểm Chưa Hiệu Quả & Phải Chỉnh Sửa Nhiều Lần

Dự án đã trải qua nhiều "nỗi đau" (pain points) về mặt kỹ thuật, buộc phải đập đi xây lại (refactor) nhiều lần ở các khía cạnh sau:

### 2.1. Quản trị Data Contract (Lỗi dính dáng tới Pandas/Numpy)
*   **Vấn đề**: Ban đầu, hệ thống sử dụng Pandas DataFrame làm chuẩn giao tiếp giữa Crawler và Analyzer. Tuy nhiên, Pandas ngầm định các kiểu dữ liệu như `numpy.str_` hoặc `pd.Timestamp`. Khi ném các kiểu này vào prompt hoặc thư viện JSON, hệ thống liên tục văng lỗi serialize.
*   **Chắp vá**: Ban đầu phải viết hàm "rác" `_to_native()` để ép kiểu từng dòng dữ liệu một cách thủ công.
*   **Giải pháp cuối (v2.0)**: Bỏ hoàn toàn Pandas ở ranh giới giao tiếp. Thay bằng End-to-End Pydantic (`ArticleSchema`). Crawler sinh ra thẳng Object của Pydantic, giúp code gãy gọn và Type-Safe 100%.

### 2.2. Kiểm soát Output của LLM (JSON rác và Lỗi Telegram HTML)
*   **Vấn đề**: Việc dựa vào prompt text để "ép" LLM trả về JSON thuần cực kỳ rủi ro. AI thường xuyên chèn thêm Markdown (` ```json `) hoặc các thẻ HTML vào kết quả, làm hàm regex `_extract_json` bị gãy, đồng thời khiến API của Telegram từ chối gửi tin vì lỗi Parse HTML.
*   **Chắp vá**: Yêu cầu AI chỉ xuất "Plain text", dùng `html.escape()` và cắt gọt chuỗi.
*   **Giải pháp cuối (v2.0)**: Tích hợp thư viện `instructor`. Đây là "vũ khí tối thượng" ép LLM sinh ra đúng cấu trúc Pydantic (`CategorySummarySchema`). Nếu LLM sinh sai hoặc có thẻ HTML rác, `@field_validator` của Pydantic sẽ bắt lỗi, và `instructor` tự động gửi lỗi đó lại cho LLM để AI **tự sửa (Self-Correction)** với `max_retries=3`.

### 2.3. Tổ chức Orchestrator (Bệnh "God Object")
*   **Vấn đề**: File `main.py` (Orchestrator) ban đầu ôm đồm quá nhiều việc: từ khởi tạo vòng lặp, chứa logic lọc từ khóa (chèn `import html` ở giữa), đến trực tiếp render text cho Telegram.
*   **Giải pháp cuối (v2.0)**: Bóc tách logic ra các file tiện ích chuyên biệt (`utils/filters.py` và `utils/formatters.py`). `main.py` lúc này chỉ còn làm đúng vai trò của một Pipeline Coordinator: Giao việc -> Nhận kết quả -> Giao việc tiếp theo.

---

## 3. Bài Học Rút Ra (Lessons Learned)

1. **"Đừng dùng Prompt để giải quyết vấn đề của Code"**:
   * Việc cố gắng viết prompt dài để van nài AI trả về đúng JSON, không có Markdown, không có HTML... là một hướng đi kém bền vững.
   * *Thực tiễn tốt nhất*: Hãy dùng **Code (Pydantic + Instructor)** để thiết lập "hàng rào thép" cho cấu trúc dữ liệu. Bất cứ thứ gì vượt rào sẽ bị code reject và ép AI sinh lại.

2. **Dịch chuyển triết lý từ "God Agent" sang "Autonomous Subagents"**:
   * Orchestrator không nên và không được phép đi sửa lỗi lặt vặt (như parse định dạng, ép kiểu) thay cho các tác nhân con.
   * *Thực tiễn tốt nhất*: Cấp quyền tự kiểm tra và tự sửa lỗi (Self-verification & Self-correction loop) ngay tại lớp Subagent (`ai_analyzer.py` tự lo liệu lỗi định dạng với `max_retries`). Orchestrator chỉ quan tâm đến kết quả cuối cùng đạt chuẩn Data Contract.

3. **Data Contract phải được áp dụng End-to-End**:
   * Việc chỉ áp dụng Schema cho dữ liệu đầu ra của LLM là không đủ. Dữ liệu mộc từ lúc vừa cào (Crawler) cũng cần được đóng gói vào Schema ngay lập tức. Việc này giúp luồng dữ liệu xuyên suốt dự án được bảo vệ khỏi các lỗi Type ẩn (Hidden Type Errors) như trường hợp của Pandas.

4. **Kế hoạch tốt cần đi kèm Test Coverage sớm**:
   * Trong giai đoạn v1, việc thay đổi code rất rủi ro vì thiếu Unit Tests. Khi sang v2.0, việc chuẩn hóa `test_contracts.py` với 7 unit tests giúp quá trình Refactoring diễn ra tự tin và không phá vỡ logic cũ. Đưa TDD (Test-Driven Development) vào sớm sẽ làm giảm thời gian debug ở các giai đoạn sau.

---

## 4. Đánh Giá Hiệu Quả Quá Trình Chuyển Giao: Planning -> Execution

Quá trình chuyển đổi từ Bản thiết kế (Plan) sang Mã nguồn thực tế (Implementation) trong dự án này bộc lộ rõ bản chất của một hệ thống AI Multi-Agent, với cả những điểm sáng và những sai lệch cần rút kinh nghiệm.

### 4.1. Những điểm hiệu quả khiến Plan và Implementation khớp
*   **Tài liệu hóa Single Source of Truth (SSOT)**: Việc duy trì file `implementation_plan.md` làm bản thiết kế chuẩn mực giúp các Agent (cả Agent lập trình và Agent Reviewer) luôn có một cột mốc cố định để đối chiếu.
*   **Vòng lặp Code Review độc lập**: Việc sử dụng một Agent đóng vai trò "Principal Code Reviewer" (như ở phiên bản v1.4.0 và v2.0.0 draft) cầm bản Plan đi rà soát từng dòng code đã giúp phát hiện ngay lập tức các sai lệch (ví dụ: phát hiện lỗi ghi Cache sai vị trí vòng lặp, phát hiện file `.env.example` bị sót).
*   **Phân chia Task rõ ràng, có Checklist**: Khi bản Plan được chia thành các Task nhỏ (Task 1: `.env.example`, Task 2: `logger.py`...), Agent lập trình dễ dàng hoàn thiện từng tệp một cách cô lập, tỷ lệ bám sát kiến trúc thư mục là 100%.

### 4.2. Những điểm chưa hiệu quả khiến Plan và Implementation không khớp
*   **Hội chứng "Đường tắt" của AI (Tunnel Vision / Shortcut)**: Khi gặp khó khăn trong quá trình chuyển đổi dữ liệu, AI lập trình thường tự ý chọn đường dễ nhất thay vì tuân thủ cấu trúc của Plan. 
    *   *Ví dụ*: Ở bản v2.0 Draft, Plan quy định Crawler phải trả về `List[ArticleSchema]`. Nhưng Agent lập trình thấy việc giữ lại Pandas DataFrame dễ thao tác hơn nên đã phớt lờ thiết kế, dẫn đến Data Contract bị gãy ở đầu vào.
*   **Bỏ quên "Dọn dẹp" (Cleanup Amnesia)**: Agent thường chỉ tập trung viết code mới cho chạy được, nhưng lại quên xóa code thừa hoặc file rác.
    *   *Ví dụ*: Để lại hàm rác `_to_native()`, import thừa `import html`, file debug `temp_cafebiz.csv`, hay tạo một module rỗng `validator.py` không có logic bên trong.
*   **Mất bối cảnh khi xử lý logic hẹp**: Khi đang mải mê fix một bug nhỏ (như parse HTML), Agent dễ vô tình phá vỡ một ràng buộc lớn (Constraint) của hệ thống đã được chốt ở Plan (như việc ghi file trạng thái phải là thao tác "Atomic").

### 4.3. Bài học rút ra cho quá trình Planning -> Execution
1.  **Code Review Agent là bắt buộc**: Tuyệt đối không tin tưởng hoàn toàn vào Agent thực thi (Executor). Luôn cần một Agent thứ hai làm nhiệm vụ Audit/Review, mang theo nguyên bản Plan để "chấm điểm" và bắt Executor sửa lại trước khi merge.
2.  **Ràng buộc bằng Code (TDD) thay vì Văn bản**: Nếu Plan chỉ ghi bằng chữ "Hàm này phải trả về kiểu X", Agent rất dễ làm sai. Phải viết file Unit Test trước (Test-Driven Development), và yêu cầu Agent thực thi phải viết code sao cho pass 100% Test, lúc đó ranh giới giữa Plan và Code sẽ không thể bị phá vỡ.
3.  **Hệ thống hóa Rule/Constraint (GLOBAL_CONSTRAINTS)**: Các nguyên tắc thiết kế tối quan trọng không được để rải rác trong Plan. Cần tổng hợp thành file cấu hình như `GLOBAL_CONSTRAINTS.md` (hoặc `.cursorrules`, `AGENTS.md`) và ép vào System Prompt của mọi tác nhân AI để chúng luôn bị nhắc nhở mỗi khi gõ code.

---

## 5. Đánh Giá Đối Chiếu (Cross-Project Analysis) với Stock Bot và Stock Hunt

Dựa trên việc rà soát các tài liệu `workflow_analysis.md` từ 2 dự án tiền nhiệm là **Stock Bot** (bot_app) và **Stock Hunt**, dưới đây là đánh giá về việc kế thừa tri thức trong dự án **Stock News Bot**:

### 5.1. Bài học nào đã được áp dụng hiệu quả
*   **Thiết lập Data Contract ngay từ đầu (Từ Stock Hunt)**: Bài học xương máu về sự bất đồng bộ dữ liệu giữa các Subagent ở dự án Stock Hunt đã được áp dụng cực kỳ triệt để. Stock News Bot đã vươn lên một tầm cao mới khi áp dụng Pydantic Schema xuyên suốt (End-to-End) thay vì chỉ dùng Dictionary lỏng lẻo.
*   **Tách biệt Living Plan và Changelog (Từ Stock Hunt)**: Dự án này duy trì rất tốt sự trong sáng của tài liệu. `implementation_plan.md` luôn gọn gàng (chỉ chứa kiến trúc hiện tại), còn mọi lịch sử rườm rà được đẩy sang `changelog.md`.
*   **Resilient Design & Rate-limit Safe (Từ Stock Bot)**: Bài học về vòng lặp Retry khi gọi API và việc thêm độ trễ (`time.sleep`) được kế thừa hoàn hảo. Thậm chí, việc tích hợp thư viện `instructor` (tự động retry và self-correction 3 lần) là một bước tiến vượt bậc so với việc dùng vòng lặp `while` thủ công ở Stock Bot.
*   **State Caching nguyên tử (Từ Stock Bot)**: Kinh nghiệm lưu cache để tránh Spam Telegram và bảo vệ tính nguyên tử của dữ liệu (chỉ lưu trong khối `finally`) đã được sao chép và hoạt động ổn định.

### 5.2. Bài học nào không áp dụng hoặc áp dụng không hiệu quả
*   **Đồng bộ Tài liệu Tức thì / Iterative Prompting (Từ Stock Hunt)**: Bài học này yêu cầu "cập nhật code đến đâu, cập nhật docs đến đó". Tuy nhiên, ở Stock News Bot, các tác nhân AI vẫn mắc bệnh "Cleanup Amnesia" — mải mê sửa code mà quên mất việc cập nhật tài liệu. Hệ quả là phải có một Task rà soát toàn diện ở cuối Phase 6 mới có thể đồng bộ lại toàn bộ log.
*   **Hàm tiện ích Serialization `_to_native` (Từ Stock Bot)**: Bài học từ Stock Bot khuyên nên viết sẵn hàm `_to_native` để ép kiểu dữ liệu Pandas/Numpy. Trong Phase 1 của dự án này, Agent đã "học vẹt" bài học đó một cách máy móc. Nhưng đến v2.0, công nghệ Pydantic đã chứng minh hàm `_to_native` là một cục nợ kỹ thuật (Tech Debt). Điều này cho thấy việc áp dụng cứng nhắc một bài học cũ có thể cản trở việc tiếp cận giải pháp công nghệ mới tốt hơn.

### 5.3. Điều có thể cải thiện tiếp về thủ tục Workflow Analysis
1.  **Biến Bài Học Thành Ràng Buộc Mã Máy (Automated Constraints)**: Thủ tục Workflow Analysis hiện tại kết thúc bằng việc xuất ra một tệp Markdown để "con người hoặc AI đọc lại sau này". Điều này phụ thuộc vào trí nhớ của Agent. Cải tiến tiếp theo bắt buộc phải là: **Mỗi bài học mới rút ra phải được tự động compile thành một rule trong `GLOBAL_CONSTRAINTS.md` hoặc `.cursorrules`**. Ràng buộc phải nằm trong System Prompt chứ không chỉ nằm trên giấy.
2.  **Đánh giá Chéo Chủ Động (Proactive Cross-Project Knowledge Sharing)**: Hiện tại, AI chỉ đọc lại bài học của dự án cũ khi User có lệnh yêu cầu. Thủ tục chuẩn hóa tiếp theo nên là: Ở Phase 0 (Planning) của bất kỳ dự án mới nào, Agent Kiến trúc sư (Orchestrator) **bắt buộc phải tự động gọi lệnh tìm kiếm và đọc các file `workflow_analysis.md` của tất cả các dự án trong Workspace** trước khi đặt bút viết Plan.


