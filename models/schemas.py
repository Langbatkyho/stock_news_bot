from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
import re

class ArticleSchema(BaseModel):
    url: str
    title: str
    short_description: str
    content: str
    publish_time: str
    category: str

class ArticleAnalysisSchema(BaseModel):
    summary: str = Field(description="Tóm tắt ngắn gọn các điểm chính.")
    impact: str = Field(description="Đánh giá tác động (Tích cực, Tiêu cực, Trung tính, Không rõ).")
    sentiment: str = Field(description="Đánh giá tâm lý thị trường.")
    ticker: Optional[str] = Field(default=None, description="Mã cổ phiếu được nhắc đến (nếu có).")
    source_url: str = Field(description="URL nguồn của bài báo.")

class CategorySummarySchema(BaseModel):
    category_name: str = Field(description="Tên danh mục tin tức (VD: Vĩ mô Việt Nam, Kinh tế Ngành,...)")
    summary_points: List[str] = Field(description="Các điểm tin chính ảnh hưởng tới thị trường hoặc watchlist, được tóm tắt ngắn gọn thành các câu đơn giản độc lập.")
    impacts: List[str] = Field(description="Đánh giá tác động đến các cổ phiếu trong watchlist (nếu có). Nêu rõ tích cực, tiêu cực hay trung lập, hoặc ghi 'Không có tác động đáng kể'.")

    @field_validator('summary_points', 'impacts')
    @classmethod
    def check_html_and_empty(cls, v, info):
        if info.field_name == 'summary_points' and not v:
            raise ValueError("Phải có ít nhất 1 điểm tin (summary_points không được rỗng).")
        
        # Kiểm tra thẻ HTML (chỉ chấp nhận b, i, code nếu cần, nhưng tốt nhất là cấm HTML để formatters lo)
        html_pattern = re.compile(r'<[^>]+>')
        for item in v:
            if html_pattern.search(item):
                raise ValueError(f"Chuỗi không được chứa thẻ HTML: {item}")
        return v

