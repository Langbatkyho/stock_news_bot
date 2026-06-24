from typing import List
from models.schemas import ArticleSchema

def filter_by_keywords(articles: List[ArticleSchema], keywords: List[str]) -> List[ArticleSchema]:
    """Lọc tin theo danh sách từ khóa"""
    if not articles:
        return []
        
    filtered_articles = []
    for art in articles:
        text = f"{art.title} {art.short_description} {art.content}".lower()
        
        # Kiểm tra xem có chứa bất kỳ từ khóa nào không
        match_found = any(kw.lower() in text for kw in keywords)
        
        if match_found:
            filtered_articles.append(art)
            
    return filtered_articles
