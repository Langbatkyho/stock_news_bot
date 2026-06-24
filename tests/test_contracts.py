import pytest
from pydantic import ValidationError
from models.schemas import ArticleSchema, CategorySummarySchema
from utils.filters import filter_by_keywords
from utils.formatters import build_telegram_report

def test_article_schema_valid():
    data = {
        "url": "http://example.com/1",
        "title": "Test",
        "short_description": "Desc",
        "content": "Content",
        "publish_time": "2024-01-01",
        "category": "Vĩ mô"
    }
    article = ArticleSchema.model_validate(data)
    assert article.url == data["url"]

def test_article_schema_invalid():
    data = {
        "url": "http://example.com/1",
        # missing title
    }
    with pytest.raises(ValidationError):
        ArticleSchema.model_validate(data)

def test_category_summary_schema_valid():
    data = {
        "category_name": "Kinh tế Ngành",
        "summary_points": ["Điểm 1", "Điểm 2"],
        "impacts": ["Tích cực đến VCB"]
    }
    summary = CategorySummarySchema.model_validate(data)
    assert summary.category_name == "Kinh tế Ngành"
    assert len(summary.summary_points) == 2
    assert len(summary.impacts) == 1

def test_category_summary_schema_no_html():
    data = {
        "category_name": "Kinh tế Ngành",
        "summary_points": ["Điểm 1", "<b>Lỗi HTML</b>"],
        "impacts": ["Tích cực đến VCB"]
    }
    with pytest.raises(ValidationError, match="Chuỗi không được chứa thẻ HTML"):
        CategorySummarySchema.model_validate(data)

def test_filter_by_keywords():
    art1 = ArticleSchema(url="1", title="Bank", short_description="", content="", publish_time="", category="")
    art2 = ArticleSchema(url="2", title="Tech", short_description="", content="", publish_time="", category="")
    
    res = filter_by_keywords([art1, art2], ["bank", "shb"])
    assert len(res) == 1
    assert res[0].url == "1"

def test_filter_empty():
    assert filter_by_keywords([], ["bank"]) == []

def test_build_telegram_report():
    summary = CategorySummarySchema(
        category_name="Kinh tế Ngành",
        summary_points=["Point 1 & 2", "Point 3"],
        impacts=["Tích cực <3"]
    )
    report = build_telegram_report("TEST", "🔥", {"Kinh tế Ngành": summary}, ["VCB"])
    assert "TEST" in report
    assert "Point 1 &amp; 2" in report
    assert "Tích cực &lt;3" in report

