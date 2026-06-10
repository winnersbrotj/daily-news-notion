from datetime import datetime

from main import (
    KST,
    NotionClient,
    build_news_blocks,
    fetch_market_snapshot,
    fetch_rss_articles,
    generate_digest,
    heading,
    paragraph,
    require_env,
)


def run() -> None:
    articles = fetch_rss_articles()
    digest = generate_digest(articles, fetch_market_snapshot())
    notion = NotionClient(require_env("NOTION_TOKEN"))
    parent_id = require_env("NOTION_PARENT_PAGE_ID").replace("-", "")
    now = datetime.now(KST)
    title = f"자동화 테스트 - {now:%Y-%m-%d %H:%M}"
    blocks = [
        heading("현시간 대표 뉴스 5가지"),
        paragraph(f"확인 기준: 한국시간 {now:%Y-%m-%d %H:%M}"),
        *build_news_blocks(digest["top_news"][:5]),
    ]
    page = notion.create_page(parent_id, title, blocks, icon="🧪")
    print(f"SUCCESS: Test page created at {page['url']}")


if __name__ == "__main__":
    run()
