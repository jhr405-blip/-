#!/usr/bin/env python3
"""2단계: 대본 + 슬라이드 생성.

collect_news.py가 만든 뉴스 JSON을 Claude API에 넣어
영상 1편 분량의 대본, 슬라이드 구성, 썸네일/인포그래픽 이미지 프롬프트를
한 번에 JSON으로 생성한다.

필요: ANTHROPIC_API_KEY 환경변수 (https://platform.claude.com 에서 발급)

사용법:
    python3 pipeline/generate_script.py news_today.json -o video.json
    python3 pipeline/generate_script.py news_today.json --topic "비트코인 ETF"
"""

import argparse
import json
import sys

import anthropic

MODEL = "claude-opus-4-8"

SYSTEM_PROMPT = """\
너는 한국어 크립토 뉴스 유튜브 채널의 작가다. 매일 그날의 뉴스 중 가장 흥미로운
주제 하나를 골라 8~10분 분량(나레이션 기준 1,800~2,200자)의 영상을 만든다.

스타일 가이드:
- 시청자는 크립토에 관심 있는 일반인. 전문용어는 반드시 한 줄로 풀어서 설명.
- 나레이션은 구어체("~인데요", "~거든요"). 낭독했을 때 자연스러워야 한다.
- 각 슬라이드의 나레이션은 그 슬라이드 불릿 내용을 확장해서 설명하는 구조.
- 숫자와 날짜는 구체적으로. 출처가 불분명한 주장은 하지 않는다.
- 제목과 썸네일은 호기심을 자극하되 낚시성 과장은 금지.
- 슬라이드 불릿의 highlight에는 그 줄에서 가장 중요한 표현을 그대로 복사해 넣는다.
- sources에는 해당 슬라이드 내용의 근거가 된 기사의 도메인만 적는다 (예: coindesk.com).
"""

# 슬라이드 JSON 스키마 — build_slides.py가 이 구조를 그대로 렌더링한다.
OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "video_title": {"type": "string", "description": "유튜브 영상 제목 (40자 이내)"},
        "youtube_description": {"type": "string", "description": "영상 설명란 텍스트 (출처 링크 포함)"},
        "thumbnail": {
            "type": "object",
            "properties": {
                "line1": {"type": "string", "description": "썸네일 첫 줄 (흰색 큰 글씨)"},
                "line2": {"type": "string", "description": "썸네일 둘째 줄 (빨간색 강조)"},
                "handwriting": {"type": "string", "description": "손글씨 후킹 문구 한 줄"},
                "image_prompt": {"type": "string", "description": "배경 이미지 생성용 영어 프롬프트 (photorealistic, cinematic)"},
            },
            "required": ["line1", "line2", "handwriting", "image_prompt"],
            "additionalProperties": False,
        },
        "slides": {
            "type": "array",
            "description": "6~9장의 슬라이드. 첫 장은 오프닝 훅, 마지막 장은 정리/전망.",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "bullets": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string"},
                                "highlight": {"type": "string", "description": "text 안에서 강조할 부분 (부분 문자열). 없으면 빈 문자열"},
                            },
                            "required": ["text", "highlight"],
                            "additionalProperties": False,
                        },
                    },
                    "sources": {"type": "array", "items": {"type": "string"}},
                    "narration": {"type": "string", "description": "이 슬라이드를 띄운 상태에서 읽을 나레이션 (250~350자)"},
                    "infographic_prompt": {"type": "string", "description": "이 슬라이드를 손그림 인포그래픽으로 만들 때 쓸 이미지 생성 프롬프트 (한국어 텍스트 포함 지시). 불필요하면 빈 문자열"},
                },
                "required": ["title", "bullets", "sources", "narration", "infographic_prompt"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["video_title", "youtube_description", "thumbnail", "slides"],
    "additionalProperties": False,
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("news_json", help="collect_news.py 출력 파일")
    ap.add_argument("-o", "--output", default="video.json")
    ap.add_argument("--topic", default="", help="주제를 지정하고 싶을 때 (없으면 AI가 선정)")
    args = ap.parse_args()

    with open(args.news_json, encoding="utf-8") as f:
        news = json.load(f)

    articles = news["articles"]
    if not articles:
        sys.exit("뉴스가 비어 있습니다. collect_news.py를 먼저 실행하세요.")

    article_block = "\n".join(
        f"- [{a['source']}] {a['title']} — {a['summary'][:200]} ({a['link']})"
        for a in articles[:60]
    )
    topic_line = (
        f"오늘의 주제는 '{args.topic}'로 정해져 있다. 이 주제와 관련된 기사들만 사용하라."
        if args.topic
        else "아래 기사 중 조회수가 가장 잘 나올 만한 주제 하나를 골라라. 여러 기사가 겹치는 이슈일수록 좋다."
    )

    client = anthropic.Anthropic()

    with client.messages.stream(
        model=MODEL,
        max_tokens=32000,
        thinking={"type": "adaptive"},
        system=SYSTEM_PROMPT,
        output_config={"format": {"type": "json_schema", "schema": OUTPUT_SCHEMA}},
        messages=[{
            "role": "user",
            "content": (
                f"{topic_line}\n\n"
                f"오늘({news['collected_at'][:10]}) 수집된 뉴스 {len(articles)}건:\n"
                f"{article_block}\n\n"
                "위 뉴스로 영상 1편의 대본과 슬라이드를 JSON으로 작성하라."
            ),
        }],
    ) as stream:
        print("대본 생성 중...", file=sys.stderr)
        response = stream.get_final_message()

    if response.stop_reason == "refusal":
        sys.exit("모델이 요청을 거부했습니다. 뉴스 내용을 확인하세요.")

    text = next(b.text for b in response.content if b.type == "text")
    video = json.loads(text)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(video, f, ensure_ascii=False, indent=2)

    total_chars = sum(len(s["narration"]) for s in video["slides"])
    print(f"제목: {video['video_title']}")
    print(f"슬라이드 {len(video['slides'])}장, 나레이션 {total_chars}자 → {args.output}")
    print(f"토큰 사용: 입력 {response.usage.input_tokens} / 출력 {response.usage.output_tokens}")


if __name__ == "__main__":
    main()
