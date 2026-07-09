# AI 영상 제작 파이프라인

"새벽에온주호" 스타일의 크립토 뉴스 영상을 만드는 3단계 파이프라인.
뉴스 수집 → AI 대본/슬라이드 생성 → 슬라이드 PNG 렌더링까지 자동화하고,
녹음(본인 목소리)과 편집만 사람이 한다.

```
[1] collect_news.py      RSS 6곳에서 최근 24시간 뉴스 수집 → news_today.json
[2] generate_script.py   Claude API로 대본+슬라이드+이미지 프롬프트 생성 → video.json
[3] build_slides.py      1920x1080 슬라이드 PNG + 썸네일 시안 + 녹음용 대본 렌더링
[4] (사람) 녹음           slides/script.md 를 읽으면서 녹음
[5] (사람) 편집           슬라이드 PNG를 나레이션에 맞춰 배치 (Vrew/CapCut/프리미어)
```

## 설치

```bash
pip install anthropic playwright
playwright install chromium   # 크로미움이 이미 있으면 생략
export ANTHROPIC_API_KEY=sk-ant-...   # platform.claude.com 에서 발급
```

## 매일 돌리는 명령 (전체 3줄)

```bash
python3 pipeline/collect_news.py -o news_today.json
python3 pipeline/generate_script.py news_today.json -o video.json
python3 pipeline/build_slides.py video.json -o today_slides/
```

결과물 (`today_slides/`):

| 파일 | 용도 |
|---|---|
| `slide_01.png` ~ `slide_NN.png` | 영상 본편 슬라이드 (1920x1080) |
| `thumbnail.png` | 썸네일 시안 (1280x720) — 배경만 AI 이미지로 교체 |
| `script.md` | 슬라이드별 녹음용 나레이션 대본 |
| `slide_*.html`, `thumbnail.html` | 문구 수정 후 재렌더링용 원본 |

`video.json` 안에는 추가로 다음이 들어 있다:

- `youtube_description` — 설명란에 붙여넣을 텍스트 (출처 링크 포함)
- `thumbnail.image_prompt` — ChatGPT/Midjourney에 넣을 썸네일 배경 프롬프트
- `slides[].infographic_prompt` — 손그림 인포그래픽 생성용 프롬프트 (선택)

## 뉴스 소스

`collect_news.py`의 `FEEDS` 목록을 수정해서 소스를 추가/교체한다.
기본: CoinDesk, Cointelegraph, Decrypt, The Block, Bitcoin Magazine, 연준(1차 소스).

## 주제를 직접 정하고 싶을 때

```bash
python3 pipeline/generate_script.py news_today.json --topic "이더리움 ETF"
```

## 예시

`examples/2026-07-09/` 에 실제 수집 뉴스(news.json), 생성물 샘플(video.json),
렌더링된 슬라이드/썸네일이 들어 있다.

## 비용 (대략)

- Claude API (Opus 4.8): 영상 1편당 입력 ~1.5만 토큰 + 출력 ~8천 토큰 ≈ $0.3 내외
- 이미지 생성: ChatGPT Plus 구독으로 커버 가능
- 나머지는 무료 (RSS, Playwright)

## 주의

- 슬라이드에 들어간 숫자·날짜는 업로드 전 반드시 원문 기사와 대조할 것 (AI 환각 방지)
- 영상 설명란에 출처 링크를 유지할 것 — 유튜브 재사용 콘텐츠 정책 대응에 유리
- 나레이션은 본인 목소리 녹음 유지 (AI 음성 대량생산은 수익화 제한 리스크)
