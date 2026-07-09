# AI 대본 파이프라인

크립토 뉴스를 자동 수집해서 **녹음용 대본 + 썸네일 프롬프트**까지 만들어주는
2단계 파이프라인. 영상 화면·편집은 기존 방식대로, 대본 작성만 자동화한다.

```
[1] collect_news.py      RSS 6곳에서 최근 24시간 뉴스 수집 → news_today.json
[2] generate_script.py   Claude API로 대본 생성 → script.md
[3] (사람) 녹음·편집      script.md 읽으면서 녹음, 썸네일 프롬프트로 배경 이미지 생성
```

## 설치

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...   # platform.claude.com 에서 발급
```

## 매일 돌리는 명령 (2줄)

```bash
python3 pipeline/collect_news.py -o news_today.json
python3 pipeline/generate_script.py news_today.json -o script.md
```

`script.md` 하나에 전부 들어 있다:

| 항목 | 내용 |
|---|---|
| 영상 제목 | 유튜브 제목 (40자 이내) |
| 썸네일 | 첫 줄/둘째 줄/손글씨 문구 + **배경 이미지 생성 프롬프트** (ChatGPT/Midjourney에 붙여넣기) |
| 대본 | 섹션 5~8개, 섹션마다 나레이션 + 출처 도메인 |
| 유튜브 설명란 | 참고 기사 출처 포함, 그대로 복붙 |

## 주제를 직접 정하고 싶을 때

```bash
python3 pipeline/generate_script.py news_today.json --topic "이더리움 ETF"
```

지정하지 않으면 그날 기사 중 여러 매체가 겹치는 이슈를 AI가 골라준다.

## 뉴스 소스

`collect_news.py`의 `FEEDS` 목록을 수정해서 소스를 추가/교체.
기본: CoinDesk, Cointelegraph, Decrypt, The Block, Bitcoin Magazine, 연준(1차 소스).

## 예시

`examples/2026-07-09/` — 실제 수집 뉴스(news.json)와 출력 샘플(script.md).

## 비용

Claude API (Opus 4.8) 기준 영상 1편당 약 $0.3 내외.

## 주의

- 대본의 숫자·날짜는 업로드 전 원문 기사와 대조할 것 (AI 환각 방지)
- 설명란의 출처 링크 유지 권장 — 유튜브 재사용 콘텐츠 정책 대응에 유리
- 나레이션은 본인 목소리 녹음 유지 (AI 음성 대량생산은 수익화 제한 리스크)
