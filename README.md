# Daily News to Notion

평일 오전 9시 30분(한국시간)에 주요 뉴스와 국내외 증시 브리핑을
Notion의 `오늘의 뉴스` 페이지 아래에 기록합니다.

## 생성 구조

- `YYYY-MM-DD 오늘의 뉴스`
  - `오늘의 대표 뉴스 10개`
  - `해외 주식 동향`
  - `국내 주식 동향`

같은 날짜의 페이지가 이미 있으면 중복 생성하지 않습니다.

## GitHub Secrets

저장소의 `Settings > Secrets and variables > Actions`에서 아래 값을
`Repository secrets`로 등록해야 합니다.

| 이름 | 설명 |
| --- | --- |
| `OPENAI_API_KEY` | OpenAI API 키 |
| `NOTION_TOKEN` | Notion Integration 비밀 키 |
| `NOTION_PARENT_PAGE_ID` | `오늘의 뉴스` 페이지 ID |

현재 사용 중인 Notion 상위 페이지 ID:

```text
3792dc2fc79981dd84c2c6fc883a7ec4
```

Notion Integration에는 해당 `오늘의 뉴스` 페이지의 편집 권한을
공유해야 합니다.

## 수동 테스트

GitHub 저장소의 `Actions` 탭에서 `Daily News to Notion`을 선택하고
`Run workflow`를 누르면 예약 시간을 기다리지 않고 테스트할 수 있습니다.

## 환경 변수

선택적으로 다음 저장소 변수를 설정할 수 있습니다.

| 이름 | 기본값 |
| --- | --- |
| `OPENAI_MODEL` | `gpt-5.5` |