import time
import schedule
import traceback
import asyncio
import pandas as pd

from config.settings import Settings
from utils.logger import get_logger
from cache.state_cache import load_alert_cache, save_alert_cache, mark_as_processed
from crawlers.news_crawler import NewsCrawler
from analyzer.ai_analyzer import AIAnalyzer
from bot.telegram_bot import TelegramReporter

logger = get_logger("main")

async def run_cycle_async(settings):
    logger.info("Bắt đầu chu kỳ quét và tổng hợp tin tức mới...")
    
    crawler = NewsCrawler(watchlist=settings.STOCK_WATCHLIST, use_cache=True)
    analyzer = AIAnalyzer(api_key=settings.GEMINI_API_KEY)
    reporter = TelegramReporter(bot_token=settings.TELEGRAM_BOT_TOKEN, chat_id=settings.TELEGRAM_CHAT_ID)
    
    cache = load_alert_cache()
    sent_urls = []
    
    try:
        # Cào tin theo 4 danh mục và lọc tin mới
        categories_data = await crawler.fetch_all_categories_async(cache, time_frame="24h")
        
        # Kiểm tra xem có bất kỳ tin mới nào không
        total_new_articles = sum(len(articles) for articles in categories_data.values())
        if total_new_articles == 0:
            logger.info("Không có tin tức mới nào trong chu kỳ này.")
            return
            
        logger.info(f"Tổng cộng có {total_new_articles} tin mới trên tất cả danh mục. Tiến hành tổng hợp...")
        
        # Tổng hợp bằng AI cho từng danh mục
        summaries = {}
        
        for cat_name, articles in categories_data.items():
            if not articles:
                continue
                
            logger.info(f"Tổng hợp danh mục [{cat_name}] với {len(articles)} tin mới...")
            
            # Gửi cho AI tổng hợp
            # Chuyển ArticleSchema objects về dict cho AIAnalyzer (hoặc cập nhật AIAnalyzer để nhận ArticleSchema)
            articles_dicts = [art.model_dump() for art in articles]
            summary = analyzer.generate_category_summary(cat_name, articles_dicts, settings.STOCK_WATCHLIST)
            
            # Lưu lại đối tượng CategorySummarySchema
            summaries[cat_name] = summary
            
            # Tránh over rate limit Gemini API (TPM/RPM)
            time.sleep(2)

        if not summaries:
            logger.info("Không tạo được bản tóm tắt nào.")
            return

        # Tách tin nhắn thành 2 bản tin độc lập (Vĩ mô & Vi mô/Doanh nghiệp)
        from utils.formatters import build_telegram_report
        for group_name, cats_list, header_icon, title_text in [
            ("Macro", ["Vĩ mô Việt Nam", "Vĩ mô Thế giới"], "📊", "BẢN TIN VĨ MÔ & THỊ TRƯỜNG"),
            ("Micro", ["Kinh tế Ngành", "Doanh nghiệp & Đầu tư"], "🏢", "BẢN TIN NGÀNH & DOANH NGHIỆP")
        ]:
            group_summaries = {k: v for k, v in summaries.items() if k in cats_list}
            if not group_summaries:
                continue
                
            report_text = build_telegram_report(
                title_text=title_text,
                header_icon=header_icon,
                summaries=group_summaries,
                watchlist=settings.STOCK_WATCHLIST
            )
                
            logger.info(f"Đang gửi {title_text} qua Telegram...")
            if reporter.send_report(report_text):
                logger.info(f"Gửi {title_text} thành công.")
                # Tích lũy các URL đã gửi thành công để đánh dấu sau
                for cat_name in cats_list:
                    if cat_name in categories_data:
                        sent_urls.extend([art.url for art in categories_data[cat_name]])
            else:
                logger.warning(f"Gửi {title_text} thất bại.")
            
    except Exception as e:
        logger.error(f"Lỗi hệ thống trong chu kỳ chạy: {e}")
        logger.debug(traceback.format_exc())
    finally:
        # Đánh dấu các tin đã gửi thành công ở cuối chu kỳ
        if sent_urls:
            for url in sent_urls:
                cache = mark_as_processed(url, cache)
            save_alert_cache(cache)
            logger.info(f"Đã cập nhật trạng thái cache cho {len(sent_urls)} bài viết thành công.")
        else:
            logger.info("Không có bài viết mới nào được cập nhật trạng thái cache.")

def run_cycle(settings):
    asyncio.run(run_cycle_async(settings))

def main():
    try:
        settings = Settings()
        logger.info(f"Khởi động Stock News Bot. Lịch trình: {settings.SCHEDULE_TIMES}")
        
        # Đăng ký lịch trình
        for time_str in settings.SCHEDULE_TIMES:
            schedule.every().day.at(time_str).do(run_cycle, settings)
            logger.info(f"Đã đăng ký tác vụ lúc {time_str}")
        
        # Chạy chu kỳ đầu tiên ngay lập tức khi khởi động
        logger.info("Chạy chu kỳ đầu tiên ngay lập tức...")
        run_cycle(settings)
        
        logger.info("Đang chờ đến lịch trình tiếp theo. Nhấn Ctrl+C để thoát.")
        while True:
            schedule.run_pending()
            time.sleep(30)
            
    except KeyboardInterrupt:
        logger.info("Nhận được tín hiệu dừng. Đang tắt Stock News Bot một cách an toàn (Graceful Shutdown).")
    except Exception as e:
        logger.error(f"Lỗi không mong muốn làm gián đoạn bot: {e}")
        logger.debug(traceback.format_exc())

if __name__ == "__main__":
    main()
