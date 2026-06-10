import importlib.util
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "src" / "main.py"
SPEC = importlib.util.spec_from_file_location("daily_news_main", MODULE_PATH)
main = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(main)


def test_main_blocks_do_not_repeat_page_title():
    digest = {
        "overall_summary": "총평",
        "quick_market": "시장",
        "quick_world": "국제",
        "quick_korea": "국내",
    }
    blocks = main.build_main_blocks(digest)
    serialized = str(blocks)
    assert "오늘의 뉴스" not in serialized
    assert "총평" in serialized


def test_news_blocks_include_all_items_and_sources():
    items = [
        {
            "title": f"뉴스 {index}",
            "summary": "요약",
            "importance": "중요성",
            "source_url": f"https://example.com/{index}",
        }
        for index in range(1, 11)
    ]
    blocks = main.build_news_blocks(items)
    serialized = str(blocks)
    assert "10. 뉴스 10" in serialized
    assert "https://example.com/1" in serialized
    assert "https://example.com/10" in serialized


def test_market_blocks_include_checkpoints():
    section = {
        "one_line": "한 줄",
        "briefing": ["문장 1", "문장 2", "문장 3", "문장 4", "문장 5"],
        "checkpoints": ["지표 1", "지표 2", "지표 3"],
        "source_urls": ["https://example.com/source"],
    }
    serialized = str(main.build_market_blocks(section))
    assert "체크할 지표" in serialized
    assert "지표 3" in serialized
