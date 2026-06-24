import html
import pandas as pd
from typing import Dict, List
from models.schemas import CategorySummarySchema

def build_telegram_report(
    title_text: str,
    header_icon: str,
    summaries: Dict[str, CategorySummarySchema],
    watchlist: List[str]
) -> str:
    """Xây dựng nội dung HTML cho Telegram Report dựa trên kết quả JSON"""
    if not summaries:
        return ""
        
    report_text = (
        f"{header_icon} <b>{title_text}</b>\n"
        f"<i>Thời gian: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</i>\n"
        f"<i>Watchlist: {', '.join(watchlist)}</i>\n\n"
        f"====================================\n\n"
    )
    
    for cat_name, summary in summaries.items():
        report_text += f"📌 <b>{cat_name.upper()}</b>\n\n"
        
        for point in summary.summary_points:
            report_text += f"• {html.escape(point)}\n"
            
        report_text += "\n"
        
        # Impacts 
        if summary.impacts:
            report_text += f"<b>TÁC ĐỘNG ĐẾN WATCHLIST:</b>\n"
            for impact in summary.impacts:
                report_text += f"- {html.escape(impact)}\n"
        
        report_text += f"\n------------------------------------\n\n"
        
    return report_text
