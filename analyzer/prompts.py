from typing import List

def _build_base_prompt(article: dict) -> str:
    title = article.get("title", "")
    content = article.get("content", "")
    publish_time = article.get("publish_time", "")
    
    return f"""
Vui lòng phân tích bài báo tài chính sau.
CHỈ SỬ DỤNG thông tin được cung cấp trong bài báo này, không tự suy diễn hoặc sử dụng kiến thức bên ngoài.

Tiêu đề: {title}
Thời gian xuất bản: {publish_time}
Nội dung:
{content}
"""

def build_company_prompt(article: dict, ticker: str = "") -> str:
    base = _build_base_prompt(article)
    target = f" cho cổ phiếu {ticker}" if ticker else " cho doanh nghiệp được nhắc đến"
    return base + f"""
Yêu cầu phân tích{target}:
1. Tóm tắt ngắn gọn các điểm chính.
2. Đánh giá tác động (Tích cực, Tiêu cực, Trung tính, Không rõ).
3. Đánh giá tâm lý thị trường (Sentiment).

Hãy trả về kết quả KHÔNG có markdown wrap, chỉ ở định dạng JSON với các trường sau:
{{
    "summary": "tóm tắt ngắn gọn",
    "impact": "Tích cực / Tiêu cực / Trung tính / Không rõ",
    "sentiment": "tâm lý thị trường",
    "ticker": "{ticker}"
}}
"""

def build_industry_prompt(article: dict, industry: str = "") -> str:
    base = _build_base_prompt(article)
    return base + f"""
Yêu cầu phân tích tác động đối với ngành {industry}:
1. Tóm tắt ngắn gọn các điểm chính ảnh hưởng đến ngành.
2. Đánh giá tác động (Tích cực, Tiêu cực, Trung tính, Không rõ).
3. Đánh giá tâm lý thị trường (Sentiment).

Hãy trả về kết quả KHÔNG có markdown wrap, chỉ ở định dạng JSON với các trường sau:
{{
    "summary": "tóm tắt ngắn gọn",
    "impact": "Tích cực / Tiêu cực / Trung tính / Không rõ",
    "sentiment": "tâm lý thị trường",
    "ticker": null
}}
"""

def build_macro_prompt(article: dict) -> str:
    base = _build_base_prompt(article)
    return base + """
Yêu cầu phân tích tác động vĩ mô:
1. Tóm tắt ngắn gọn các sự kiện vĩ mô chính.
2. Đánh giá tác động (Tích cực, Tiêu cực, Trung tính, Không rõ) đến thị trường chứng khoán chung.
3. Đánh giá tâm lý thị trường (Sentiment).

Hãy trả về kết quả KHÔNG có markdown wrap, chỉ ở định dạng JSON với các trường sau:
{{
    "summary": "tóm tắt ngắn gọn",
    "impact": "Tích cực / Tiêu cực / Trung tính / Không rõ",
    "sentiment": "tâm lý thị trường",
    "ticker": null
}}
"""

def build_category_prompt(category_name: str, articles_text: str, watchlist: List[str]) -> str:
    watchlist_str = ", ".join(watchlist)
    
    if category_name == "Vĩ mô Việt Nam" or category_name == "Vĩ mô Thế giới":
        return f"""
Bạn là chuyên gia phân tích tài chính cao cấp. Hãy đọc các bài viết thuộc danh mục [{category_name}] dưới đây và trích xuất dữ liệu.

Yêu cầu báo cáo:
1. Trích xuất các sự kiện vĩ mô chính một cách ngắn gọn, độc lập thành các điểm tin (summary_points).
2. Đánh giá TÁC ĐỘNG TRỰC TIẾP đối với các cổ phiếu trong danh mục theo dõi: {watchlist_str}. 
   - Giải thích xem tin tức vĩ mô này ảnh hưởng như thế nào (Tích cực, Tiêu cực hay Trung lập).
   - Nếu không có tác động đáng kể, hãy ghi rõ 'Không có tác động đáng kể'.

Dữ liệu tin tức:
{articles_text}
"""
    elif category_name == "Kinh tế Ngành":
        return f"""
Bạn là chuyên gia phân tích ngành tài chính. Hãy đọc các bài viết thuộc danh mục [{category_name}] dưới đây và trích xuất dữ liệu.

Yêu cầu báo cáo:
1. Đóng vai trò là bộ lọc AI: Chỉ tổng hợp những thông tin liên quan đến các ngành của cổ phiếu theo dõi: {watchlist_str} (ngành Ngân hàng và Chứng khoán).
2. HOÀN TOÀN LOẠI BỎ các tin tức ngành khác.
3. Trích xuất các điểm cốt lõi ảnh hưởng trực tiếp đến ngành Ngân hàng/Chứng khoán thành các điểm tin độc lập (summary_points).
4. Đánh giá tác động đến watchlist vào mục impacts.

Dữ liệu tin tức:
{articles_text}
"""
    elif category_name == "Doanh nghiệp & Đầu tư":
        return f"""
Bạn là chuyên gia phân tích doanh nghiệp. Hãy đọc các bài viết thuộc danh mục [{category_name}] dưới đây và trích xuất dữ liệu.

Yêu cầu báo cáo:
1. Đóng vai trò là bộ lọc AI: Chỉ tổng hợp tin tức của chính các cổ phiếu trong watchlist: {watchlist_str} hoặc đối thủ cạnh tranh trực tiếp.
2. HOÀN TOÀN LOẠI BỎ bài viết về các doanh nghiệp khác.
3. Trích xuất ngắn gọn các tin tức doanh nghiệp được giữ lại (summary_points).
4. Đánh giá tác động đến watchlist (impacts).

Dữ liệu tin tức:
{articles_text}
"""
    else:
        return f"""
Hãy tóm tắt ngắn gọn các bài viết thuộc danh mục [{category_name}] dưới đây bằng tiếng Việt thành các điểm tin độc lập.

Dữ liệu tin tức:
{articles_text}
"""

