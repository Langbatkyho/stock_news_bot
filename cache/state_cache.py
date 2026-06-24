import json
import os
import time
from utils.logger import get_logger

logger = get_logger(__name__)

def load_alert_cache(path: str = "logs/.alert_cache") -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Lỗi đọc file cache {path}, tạo cache mới: {e}")
        return {}

def save_alert_cache(cache: dict, path: str = "logs/.alert_cache") -> None:
    tmp_path = f"{path}.tmp"
    try:
        os.makedirs(os.path.dirname(os.path.dirname(os.path.abspath(path))), exist_ok=True)
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
    except Exception as e:
        logger.error(f"Lỗi ghi cache ra {path}: {e}")

def is_new_article(article_url: str, cache: dict) -> bool:
    return article_url not in cache

def mark_as_processed(article_url: str, cache: dict, ttl_days: int = 7) -> dict:
    current_time = time.time()
    cache[article_url] = current_time
    
    # Dọn entry cũ
    keys_to_delete = []
    ttl_seconds = ttl_days * 24 * 3600
    for k, v in cache.items():
        if current_time - v > ttl_seconds:
            keys_to_delete.append(k)
            
    for k in keys_to_delete:
        del cache[k]
        
    return cache
