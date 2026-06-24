import time
import json
import os
import re
import pandas as pd
from typing import List, Dict
from utils.logger import get_logger
from cache.state_cache import is_new_article
from models.schemas import ArticleSchema

try:
    from vnstock_news import EnhancedNewsCrawler
except ImportError:
    EnhancedNewsCrawler = None

logger = get_logger(__name__)

CATEGORY_MAPPING = {
    "Vĩ mô Việt Nam": {
        "sources": [
            "https://vietstock.vn/761/kinh-te/vi-mo.rss",
            "https://cafebiz.vn/rss/vi-mo.rss"
        ],
        "site_names": ["vietstock", "cafebiz"]
    },
    "Vĩ mô Thế giới": {
        "sources": [
            "https://vietstock.vn/772/the-gioi/tai-chinh-quoc-te.rss",
            "https://vietstock.vn/773/the-gioi/chung-khoan-the-gioi.rss",
            "https://tuoitre.vn/rss/the-gioi.rss"
        ],
        "site_names": ["vietstock", "vietstock", "tuoitre"]
    },
    "Kinh tế Ngành": {
        "sources": [
            "https://vietstock.vn/775/the-gioi/kinh-te-nganh.rss"
        ],
        "site_names": ["vietstock"]
    },
    "Doanh nghiệp & Đầu tư": {
        "sources": [
            "https://vietstock.vn/768/kinh-te/kinh-te-dau-tu.rss",
            "https://cafebiz.vn/rss/cau-chuyen-kinh-doanh.rss",
            "https://tuoitre.vn/rss/kinh-doanh.rss"
        ],
        "site_names": ["vietstock", "cafebiz", "tuoitre"]
    }
}

class NewsCrawler:
    def __init__(self, watchlist: List[str], use_cache: bool = True):
        self.watchlist = watchlist
        self.use_cache = use_cache
        self.cache_path = "cache/local_news_cache.json"
        
        if EnhancedNewsCrawler:
            self.crawler = EnhancedNewsCrawler(cache_enabled=True, cache_ttl=3600)
        else:
            self.crawler = None

    def _pre_filter_keywords(self, articles: List[ArticleSchema]) -> List[ArticleSchema]:
        """Lọc tin theo từ khóa liên quan đến watchlist (Ngân hàng, Chứng khoán, SHB, VND...)"""
        from utils.filters import filter_by_keywords
        keywords = ['shb', 'vnd', 'ngân hàng', 'chứng khoán', 'finance', 'cổ phiếu', 'tín dụng', 'lãi suất', 'sáp nhập', 'banking', 'securities', 'bank']
        return filter_by_keywords(articles, keywords)

    async def fetch_articles_for_category_async(self, category_name: str, config: dict, time_frame: str = "24h") -> List[ArticleSchema]:
        """Cào tin tức cho một danh mục từ các nguồn RSS tương ứng"""
        articles_list = []
        
        for url, site in zip(config["sources"], config["site_names"]):
            try:
                logger.info(f"Đang lấy tin từ: {url} (Báo: {site}) cho danh mục {category_name}")
                if self.crawler:
                    # Cào bằng EnhancedNewsCrawler (hỗ trợ async)
                    # max_articles=10 để lấy đủ tin tức trước khi lọc
                    df = await self.crawler.fetch_articles_async(
                        sources=[url], 
                        max_articles=10, 
                        site_name=site, 
                        time_frame=time_frame
                    )
                    if not df.empty:
                        for _, row in df.iterrows():
                            try:
                                art = ArticleSchema(
                                    url=str(row.get("url", "")),
                                    title=str(row.get("title", "")),
                                    short_description=str(row.get("short_description", "")),
                                    content=str(row.get("content", "")),
                                    publish_time=str(row.get("publish_time", "")),
                                    category=category_name
                                )
                                articles_list.append(art)
                            except Exception as e:
                                logger.warning(f"Bỏ qua bài báo do lỗi schema: {e}")
                else:
                    logger.warning("EnhancedNewsCrawler không khả dụng, không thể cào tin.")
            except Exception as e:
                logger.error(f"Lỗi khi cào nguồn {url} cho {category_name}: {e}")
                
        # Lọc trùng theo URL
        unique_articles = {}
        for art in articles_list:
            if art.url and art.url not in unique_articles:
                unique_articles[art.url] = art
                
        return list(unique_articles.values())

    async def fetch_all_categories_async(self, cache: dict, time_frame: str = "24h") -> Dict[str, List[ArticleSchema]]:
        """Cào tin cho cả 4 danh mục, áp dụng Pre-filter và lọc trùng/lọc tin mới"""
        result = {}
        
        # Thử lấy tin từ API
        try:
            raw_data = {}
            for cat_name, config in CATEGORY_MAPPING.items():
                articles = await self.fetch_articles_for_category_async(cat_name, config, time_frame)
                
                # Áp dụng Pre-filter cho Kinh tế Ngành và Doanh nghiệp & Đầu tư
                if cat_name in ["Kinh tế Ngành", "Doanh nghiệp & Đầu tư"]:
                    articles_filtered = self._pre_filter_keywords(articles)
                    logger.info(f"Danh mục [{cat_name}]: Pre-filter lọc từ {len(articles)} bài xuống còn {len(articles_filtered)} bài.")
                    articles = articles_filtered
                
                raw_data[cat_name] = articles
                
            # Lưu local cache thô (sau khi đã pre-filter từ khóa)
            if self.use_cache:
                os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
                cache_to_save = {cat: [art.model_dump() for art in arts] for cat, arts in raw_data.items()}
                with open(self.cache_path, "w", encoding="utf-8") as f:
                    json.dump(cache_to_save, f, ensure_ascii=False, indent=2)
                    
        except Exception as e:
            logger.error(f"Lỗi hệ thống khi cào tin các danh mục: {e}. Đang chuyển sang sử dụng Local Cache...")
            raw_data = {}
            if self.use_cache and os.path.exists(self.cache_path):
                try:
                    with open(self.cache_path, "r", encoding="utf-8") as f:
                        cache_data = json.load(f)
                    for cat, articles in cache_data.items():
                        raw_data[cat] = [ArticleSchema(**art) for art in articles]
                except Exception as cache_err:
                    logger.error(f"Lỗi đọc Local Cache: {cache_err}")
            
            # Điền list rỗng cho các danh mục thiếu
            for cat_name in CATEGORY_MAPPING.keys():
                if cat_name not in raw_data:
                    raw_data[cat_name] = []

        # Lọc tin mới (chưa có trong alert_cache)
        for cat_name, articles in raw_data.items():
            if not articles:
                result[cat_name] = []
                continue
                
            new_rows = []
            for art in articles:
                if art.url and is_new_article(art.url, cache):
                    new_rows.append(art)
            
            result[cat_name] = new_rows
            logger.info(f"Danh mục [{cat_name}]: Tìm thấy {len(result[cat_name])} tin mới chưa gửi.")
            
        return result
