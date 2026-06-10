from datetime import datetime

from main import (
    KST,
    NotionClient,
    bullet,
    divider,
    heading,
    link_paragraph,
    paragraph,
    require_env,
)

IHG_URL = "https://www.ihg.com/voco/hotels/us/en/nha-trang/nhasb/hoteldetail"
AMENITIES_URL = "https://www.ihg.com/voco/hotels/vn/vi/nha-trang/nhasb/hoteldetail/amenities"
OPENING_URL = "https://thoibaotaichinhvietnam.vn/ihg-ra-mat-voco-scenia-bay-nha-trang-nhip-dieu-moi-noi-vung-vinh-mien-trung-195072.html"


def run() -> None:
    notion = NotionClient(require_env("NOTION_TOKEN"))
    parent_id = require_env("NOTION_PARENT_PAGE_ID").replace("-", "")
    now = datetime.now(KST)
    title = f"예약 자동화 테스트 - voco Scenia Bay Nha Trang - {now:%Y-%m-%d %H:%M}"
    blocks = [
        heading("호텔 한눈에 보기"),
        paragraph(
            "voco Scenia Bay Nha Trang by IHG는 나트랑 북부 해안의 팜반동 거리에 자리한 신축 5성급 라이프스타일 호텔입니다. "
            "2026년 3월 31일 공식 개장했으며, 나트랑 베이와 꼬띠엔 산 전망을 강조합니다."
        ),
        bullet("주소: Tower A, 25-26 Pham Van Dong, Bac Nha Trang Ward, Nha Trang, Vietnam"),
        bullet("객실: 전용 발코니, 바다 전망, 욕조를 갖춘 현대적인 객실·스위트 250개"),
        bullet("체크인 오후 3시 / 체크아웃 정오 / 최소 체크인 연령 18세"),
        bullet("깜란 국제공항에서 약 35km"),
        divider(),
        heading("주요 시설과 매력"),
        bullet("5층 인피니티 풀: Scenia Bay와 꼬띠엔 산을 바라보며 일출과 일몰 전망을 즐길 수 있음"),
        bullet("피트니스센터, 스파, 무료 Wi-Fi, 투숙객 무료 주차, 매일 객실 정비"),
        bullet("The Show 올데이다이닝과 지중해식 La Bonita를 포함한 레스토랑·바 시설"),
        bullet("조식 운영 시간은 매일 오전 6시 30분부터 10시 30분까지"),
        bullet("그랜드 볼룸과 오션뷰 회의실 등 행사·MICE 시설"),
        divider(),
        heading("주변과 여행 동선"),
        paragraph(
            "혼총 곶과 포나가르 참탑에 접근하기 좋고, 나트랑 중심부의 야시장과 주요 관광지는 차량 이동이 편리합니다. "
            "중심가 한복판보다 조용한 해안 휴양 분위기를 선호하는 여행자에게 잘 맞습니다."
        ),
        heading("예약 전 확인할 점"),
        bullet("무료 지역 셔틀은 제공되지 않으므로 공항·시내 이동 수단을 별도로 준비해야 합니다."),
        bullet("반려동물은 동반할 수 없습니다."),
        bullet("조식 포함 여부와 취소 조건은 예약 요금제마다 달라 결제 전에 다시 확인해야 합니다."),
        bullet("신규 호텔이라 장기간 누적된 후기 수가 아직 많지 않을 수 있습니다."),
        divider(),
        heading("출처 및 공식 정보"),
        link_paragraph("IHG 공식 호텔 안내", IHG_URL),
        link_paragraph("IHG 공식 편의시설 안내", AMENITIES_URL),
        link_paragraph("2026년 개장 관련 현지 보도", OPENING_URL),
        paragraph(f"정보 확인 기준: 한국시간 {now:%Y-%m-%d %H:%M}"),
    ]
    page = notion.create_page(parent_id, title, blocks, icon="🏨")
    print(f"SUCCESS: Hotel test page created at {page['url']}")


if __name__ == "__main__":
    run()
