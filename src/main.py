from __future__ import annotations

import html
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

import feedparser
import requests


KST = timezone(timedelta(hours=9))
NOTION_VERSION = "2022-06-28"
OPENAI_URL = "https://api.openai.com/v1/responses"
NOTION_URL = "https://api.notion.com/v1"

RSS_QUERIES = [
    ("국내", "대한민국 주요 뉴스"),
    ("국제", "국제 주요 뉴스"),
    ("경제", "한국 경제 증시 환율"),
    ("해외시장", "미국 증시 반도체 금리 유가"),
]

MARKET_SYMBOLS = {
    "S&P 500": "^GSPC",
    "NASDAQ": "^IXIC",
    "Dow Jones": "^DJI",
    "KOSPI": "^KS11",
    "KOSDAQ": "^KQ11",
    "USD/KRW": "KRW=X",
    "WTI": "CL=F",
    "Gold": "GC=F",
}

NEWS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "overall_summary",
        "quick_market",
        "quick_world",
        "quick_korea",
        "top_news",
        "global_market",
        "korea_market",
    ],
    "properties": {
        "overall_summary": {"type": "string"},
        "quick_market": {"type": "string"},
        "quick_world": {"type": "string"},
        "quick_korea": {"type": "string"},
        "top_news": {
            "type": "array",
            "minItems": 10,
            "maxItems": 10,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title", "summary", "importance", "source_url"],
                "properties": {
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "importance": {"type": "string"},
                    "source_url": {"type": "string"},
                },
            },
        },
        "global_market": {
            "type": "object",
            "additionalProperties": False,
            "required": ["one_line", "briefing", "checkpoints", "source_urls"],
            "properties": {
                "one_line": {"type": "string"},
                "briefing": {"type": "array", "minItems": 5, "maxItems": 7, "items": {"type": "string"}},
                "checkpoints": {"type": "array", "minItems": 3, "maxItems": 5, "items": {"type": "string"}},
                "source_urls": {"type": "array", "minItems": 1, "maxItems": 5, "items": {"type": "string"}},
            },
        },
        "korea_market": {
            "type": "object",
            "additionalProperties": False,
            "required": ["one_line", "briefing", "checkpoints", "source_urls"],
            "properties": {
                "one_line": {"type": "string"},
                "briefing": {"type": "array", "minItems": 5, "maxItems": 7, "items": {"type": "string"}},
                "checkpoints": {"type": "array", "minItems": 3, "maxItems": 5, "items": {"type": "string"}},
                "source_urls": {"type": "array", "minItems": 1, "maxItems": 5, "items": {"type": "string"}},
            },
        },
    },
}


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Required environment variable is missing: {name}")
    return value


def fetch_rss_articles() -> list[dict[str, str]]:
    articles: list[dict[str, str]] = []
    seen: set[str] = set()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=42)

    for category, query in RSS_QUERIES:
        url = (
            "https://news.google.com/rss/search?"
            f"q={quote(query + ' when:1d')}&hl=ko&gl=KR&ceid=KR:ko"
        )
        feed = feedparser.parse(url)
        for entry in feed.entries[:18]:
            title = html.unescape(entry.get("title", "")).strip()
            link = entry.get("link", "").strip()
            published = entry.get("published_parsed")
            if not title or not link or title in seen:
                continue
            if published:
                published_at = datetime.fromtimestamp(time.mktime(published), tz=timezone.utc)
                if published_at < cutoff:
                    continue
            seen.add(title)
            source = entry.get("source", {}).get("title", "")
            articles.append(
                {
                    "category": category,
                    "title": title,
                    "source": source,
                    "url": link,
                    "published": entry.get("published", ""),
                }
            )
    if len(articles) < 10:
        raise RuntimeError(f"Not enough recent articles were collected: {len(articles)}")
    return articles[:60]


def fetch_market_snapshot() -> dict[str, dict[str, float | str]]:
    snapshot: dict[str, dict[str, float | str]] = {}
    headers = {"User-Agent": "daily-news-notion/1.0"}
    for name, symbol in MARKET_SYMBOLS.items():
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol)}"
        try:
            response = requests.get(
                url,
                params={"range": "5d", "interval": "1d"},
                headers=headers,
                timeout=15,
            )
            response.raise_for_status()
            result = response.json()["chart"]["result"][0]
            closes = [value for value in result["indicators"]["quote"][0]["close"] if value is not None]
            if len(closes) < 2:
                continue
            current, previous = closes[-1], closes[-2]
            snapshot[name] = {
                "symbol": symbol,
                "value": round(current, 2),
                "change_percent": round((current / previous - 1) * 100, 2),
            }
        except (requests.RequestException, KeyError, IndexError, TypeError, ZeroDivisionError):
            continue
    return snapshot


def generate_digest(
    articles: list[dict[str, str]],
    market_snapshot: dict[str, dict[str, float | str]],
) -> dict[str, Any]:
    api_key = require_env("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-5.5")
    today = datetime.now(KST).strftime("%Y-%m-%d")
    allowed_urls = [article["url"] for article in articles]

    prompt = f"""
오늘은 한국시간 {today}입니다.
아래 RSS 기사 후보와 시장 스냅샷만 근거로 한국어 데일리 브리핑을 작성하세요.

요구사항:
- 국내외 중요도를 균형 있게 고려하고 중복 사건은 하나로 합칩니다.
- 대표 뉴스는 정확히 10개입니다.
- 사실과 수치를 과장하거나 추측하지 않습니다.
- source_url과 source_urls는 반드시 제공된 기사 URL 중에서만 선택합니다.
- 시장 스냅샷은 데이터 시차가 있을 수 있으므로 단정하지 말고 확인 기준을 밝혀 표현합니다.
- 투자 권유가 아닌 정보 요약으로 작성합니다.
- 간결하고 자연스러운 한국어를 사용합니다.

시장 스냅샷:
{json.dumps(market_snapshot, ensure_ascii=False)}

기사 후보:
{json.dumps(articles, ensure_ascii=False)}

허용된 출처 URL:
{json.dumps(allowed_urls, ensure_ascii=False)}
""".strip()

    response = requests.post(
        OPENAI_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "input": prompt,
            "reasoning": {"effort": "low"},
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "daily_news",
                    "strict": True,
                    "schema": NEWS_SCHEMA,
                }
            },
        },
        timeout=180,
    )
    response.raise_for_status()
    payload = response.json()
    output_text = payload.get("output_text")
    if not output_text:
        for item in payload.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    output_text = content.get("text")
                    break
    if not output_text:
        raise RuntimeError("OpenAI response did not include output text")
    digest = json.loads(output_text)

    allowed = set(allowed_urls)
    used_urls = [item["source_url"] for item in digest["top_news"]]
    used_urls += digest["global_market"]["source_urls"]
    used_urls += digest["korea_market"]["source_urls"]
    invalid_urls = [url for url in used_urls if url not in allowed]
    if invalid_urls:
        raise RuntimeError(f"Model returned unapproved source URLs: {invalid_urls}")
    return digest


class NotionClient:
    def __init__(self, token: str) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            }
        )

    def request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = self.session.request(
            method,
            f"{NOTION_URL}{path}",
            timeout=60,
            **kwargs,
        )
        response.raise_for_status()
        return response.json()

    def find_child_page(self, parent_page_id: str, title: str) -> str | None:
        cursor: str | None = None
        while True:
            params: dict[str, Any] = {"page_size": 100}
            if cursor:
                params["start_cursor"] = cursor
            data = self.request("GET", f"/blocks/{parent_page_id}/children", params=params)
            for block in data.get("results", []):
                if block.get("type") == "child_page" and block["child_page"].get("title") == title:
                    return block["id"]
            if not data.get("has_more"):
                return None
            cursor = data.get("next_cursor")

    def create_page(
        self,
        parent_page_id: str,
        title: str,
        blocks: list[dict[str, Any]],
        *,
        icon: str | None = None,
        cover_url: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "parent": {"type": "page_id", "page_id": parent_page_id},
            "properties": {
                "title": {
                    "type": "title",
                    "title": [{"type": "text", "text": {"content": title}}],
                }
            },
            "children": blocks[:100],
        }
        if icon:
            body["icon"] = {"type": "emoji", "emoji": icon}
        if cover_url:
            body["cover"] = {"type": "external", "external": {"url": cover_url}}
        page = self.request("POST", "/pages", json=body)
        if len(blocks) > 100:
            self.append_blocks(page["id"], blocks[100:])
        return page

    def append_blocks(self, page_id: str, blocks: list[dict[str, Any]]) -> None:
        for start in range(0, len(blocks), 100):
            self.request(
                "PATCH",
                f"/blocks/{page_id}/children",
                json={"children": blocks[start : start + 100]},
            )


def rich_text(text: str, *, bold: bool = False, url: str | None = None) -> list[dict[str, Any]]:
    item: dict[str, Any] = {
        "type": "text",
        "text": {"content": text[:2000]},
        "annotations": {"bold": bold},
    }
    if url:
        item["text"]["link"] = {"url": url}
    return [item]


def heading(text: str, level: int = 2) -> dict[str, Any]:
    key = f"heading_{level}"
    return {"object": "block", "type": key, key: {"rich_text": rich_text(text)}}


def paragraph(text: str, *, bold: bool = False) -> dict[str, Any]:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": rich_text(text, bold=bold)},
    }


def bullet(text: str) -> dict[str, Any]:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": rich_text(text)},
    }


def divider() -> dict[str, Any]:
    return {"object": "block", "type": "divider", "divider": {}}


def link_paragraph(label: str, url: str) -> dict[str, Any]:
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": rich_text(label, url=url)},
    }


def build_main_blocks(digest: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        heading("한 줄 총평"),
        paragraph(digest["overall_summary"]),
        heading("빠른 요약"),
        paragraph(f"시장: {digest['quick_market']}"),
        paragraph(f"국제: {digest['quick_world']}"),
        paragraph(f"국내: {digest['quick_korea']}"),
    ]


def build_news_blocks(items: list[dict[str, str]]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        if blocks:
            blocks.append(divider())
        blocks.extend(
            [
                heading(f"{index}. {item['title']}"),
                paragraph(f"핵심 요약: {item['summary']}"),
                paragraph(f"왜 중요한가: {item['importance']}"),
                link_paragraph("출처/참고", item["source_url"]),
            ]
        )
    return blocks


def build_market_blocks(section: dict[str, Any]) -> list[dict[str, Any]]:
    blocks = [
        heading("한 줄 요약"),
        paragraph(section["one_line"]),
        heading("브리핑"),
    ]
    blocks.extend(paragraph(sentence) for sentence in section["briefing"])
    blocks.append(heading("체크할 지표"))
    blocks.extend(bullet(item) for item in section["checkpoints"])
    blocks.append(heading("출처/참고"))
    blocks.extend(link_paragraph(f"출처 {index}", url) for index, url in enumerate(section["source_urls"], 1))
    return blocks


def publish_to_notion(digest: dict[str, Any]) -> str:
    token = require_env("NOTION_TOKEN")
    parent_page_id = require_env("NOTION_PARENT_PAGE_ID").replace("-", "")
    notion = NotionClient(token)
    date_text = datetime.now(KST).strftime("%Y-%m-%d")
    title = f"{date_text} 오늘의 뉴스"

    existing = notion.find_child_page(parent_page_id, title)
    if existing:
        return f"https://www.notion.so/{existing.replace('-', '')}"

    main = notion.create_page(
        parent_page_id,
        title,
        build_main_blocks(digest),
        icon="🗞️",
        cover_url=(
            "https://images.unsplash.com/photo-1504711434969-e33886168f5c"
            "?auto=format&fit=crop&w=1800&q=80"
        ),
    )
    notion.create_page(
        main["id"],
        "오늘의 대표 뉴스 10개",
        build_news_blocks(digest["top_news"]),
        icon="📰",
    )
    notion.create_page(
        main["id"],
        "해외 주식 동향",
        build_market_blocks(digest["global_market"]),
        icon="🌐",
    )
    notion.create_page(
        main["id"],
        "국내 주식 동향",
        build_market_blocks(digest["korea_market"]),
        icon="📈",
    )
    return main["url"]


def main() -> int:
    try:
        articles = fetch_rss_articles()
        market_snapshot = fetch_market_snapshot()
        digest = generate_digest(articles, market_snapshot)
        notion_url = publish_to_notion(digest)
        print(f"SUCCESS: Daily news was published to {notion_url}")
        return 0
    except Exception as exc:
        print(f"FAILURE: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
