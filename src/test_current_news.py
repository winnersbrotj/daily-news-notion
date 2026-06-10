from datetime import datetime, timedelta

import requests

from main import KST, NotionClient, bullet, heading, link_paragraph, paragraph, require_env

WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_CODES = {
    0: "맑음",
    1: "대체로 맑음",
    2: "부분적으로 흐림",
    3: "흐림",
    45: "안개",
    48: "서리 안개",
    51: "약한 이슬비",
    53: "이슬비",
    55: "강한 이슬비",
    61: "약한 비",
    63: "비",
    65: "강한 비",
    71: "약한 눈",
    73: "눈",
    75: "강한 눈",
    80: "약한 소나기",
    81: "소나기",
    82: "강한 소나기",
    95: "뇌우",
    96: "우박을 동반한 뇌우",
    99: "강한 우박을 동반한 뇌우",
}


def fetch_tomorrow_weather() -> dict[str, object]:
    response = requests.get(
        WEATHER_URL,
        params={
            "latitude": 37.5665,
            "longitude": 126.9780,
            "daily": ",".join(
                [
                    "weather_code",
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "precipitation_probability_max",
                    "precipitation_sum",
                    "wind_speed_10m_max",
                    "sunrise",
                    "sunset",
                ]
            ),
            "timezone": "Asia/Seoul",
            "forecast_days": 3,
        },
        timeout=30,
    )
    response.raise_for_status()
    daily = response.json()["daily"]
    tomorrow = (datetime.now(KST) + timedelta(days=1)).strftime("%Y-%m-%d")
    index = daily["time"].index(tomorrow)
    return {key: values[index] for key, values in daily.items() if key != "time"} | {"date": tomorrow}


def run() -> None:
    weather = fetch_tomorrow_weather()
    notion = NotionClient(require_env("NOTION_TOKEN"))
    parent_id = require_env("NOTION_PARENT_PAGE_ID").replace("-", "")
    now = datetime.now(KST)
    description = WEATHER_CODES.get(int(weather["weather_code"]), "날씨 변화 가능")
    title = f"예약 자동화 테스트 - 내일 서울 날씨 - {now:%Y-%m-%d %H:%M}"
    blocks = [
        heading(f"{weather['date']} 서울 날씨"),
        paragraph(f"예상 날씨: {description}", bold=True),
        bullet(f"최저·최고기온: {weather['temperature_2m_min']}°C / {weather['temperature_2m_max']}°C"),
        bullet(f"최대 강수확률: {weather['precipitation_probability_max']}%"),
        bullet(f"예상 강수량: {weather['precipitation_sum']}mm"),
        bullet(f"최대 풍속: {weather['wind_speed_10m_max']}km/h"),
        bullet(f"일출: {str(weather['sunrise']).split('T')[-1]} / 일몰: {str(weather['sunset']).split('T')[-1]}"),
        heading("외출 참고"),
        paragraph(
            "강수확률과 기온은 최신 예보에 따라 달라질 수 있습니다. 외출 직전에 기상청 등에서 한 번 더 확인하세요."
        ),
        link_paragraph("실행 시점에 조회한 Open-Meteo 예보", "https://open-meteo.com/"),
        paragraph(f"자동 조회·페이지 생성 시각: 한국시간 {now:%Y-%m-%d %H:%M:%S}"),
    ]
    page = notion.create_page(parent_id, title, blocks, icon="🌤️")
    print(f"SUCCESS: Weather test page created at {page['url']}")


if __name__ == "__main__":
    run()
