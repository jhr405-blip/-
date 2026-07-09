#!/usr/bin/env python3
"""3단계: 슬라이드 렌더링.

generate_script.py가 만든 video.json을 1920x1080 슬라이드 PNG로 렌더링한다.
새벽에온주호 스타일(크림 배경, 제목 바, 형광 하이라이트, 출처 푸터)의
HTML 템플릿을 Playwright(Chromium)로 스크린샷 찍는 방식.

썸네일(1280x720) 시안도 함께 생성한다 — 배경 이미지는 AI로 따로 뽑아서
thumbnail.html의 body background에 넣으면 된다.

사용법:
    python3 pipeline/build_slides.py video.json -o output_dir/
"""

import argparse
import html
import json
import os
import pathlib

from playwright.sync_api import sync_playwright

# 로컬에 크로미움이 이미 있으면 그 경로를 쓴다 (없으면 playwright install chromium).
CHROMIUM_PATH = next(
    (p for p in [os.environ.get("CHROMIUM_PATH", ""), "/opt/pw-browsers/chromium"]
     if p and os.path.exists(p)),
    None,
)

SLIDE_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  width: 1920px; height: 1080px;
  font-family: 'Pretendard', 'Noto Sans KR', 'Malgun Gothic', sans-serif;
  background: #f7f3ea;
  padding: 90px 110px;
  display: flex; flex-direction: column;
  position: relative;
}
.badge {
  position: absolute; top: 0; right: 0;
  background: #111; color: #fff;
  font-size: 34px; font-weight: 800;
  padding: 18px 44px;
  border-bottom-left-radius: 18px;
}
h1 {
  font-size: 74px; font-weight: 900; color: #1a1a1a;
  line-height: 1.25;
  padding-bottom: 36px; margin-bottom: 48px;
  border-bottom: 6px solid #1a1a1a;
}
ul { list-style: none; flex: 1; }
li {
  font-size: 46px; color: #2a2a2a; line-height: 1.5;
  margin-bottom: 34px; padding-left: 52px;
  position: relative;
}
li::before {
  content: '·'; position: absolute; left: 8px;
  font-weight: 900; color: #c0392b;
}
mark {
  background: linear-gradient(transparent 55%, #ffe66d 55%);
  font-weight: 800;
}
.sources {
  font-size: 28px; color: #8a8577;
  border-top: 2px solid #d8d2c2; padding-top: 22px;
}
.pagenum {
  position: absolute; bottom: 40px; right: 60px;
  font-size: 26px; color: #b5ae9c;
}
"""

THUMB_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  width: 1280px; height: 720px;
  font-family: 'Pretendard', 'Noto Sans KR', 'Malgun Gothic', sans-serif;
  /* AI로 생성한 배경 이미지를 아래 background에 넣으세요 */
  background: linear-gradient(135deg, #1b2735 0%, #090a0f 100%);
  background-size: cover;
  position: relative; overflow: hidden;
}
.badge {
  position: absolute; top: 18px; right: 18px;
  background: #4de1e6; color: #000;
  font-size: 30px; font-weight: 900;
  padding: 10px 26px; border-radius: 6px;
}
.hand {
  position: absolute; top: 200px; left: 60px; right: 60px;
  font-size: 46px; font-weight: 700; color: #fff;
  transform: rotate(-3deg);
  text-shadow: 0 0 12px rgba(0,0,0,.9);
}
.titles {
  position: absolute; bottom: 30px; left: 0; right: 0;
  text-align: center;
}
.line1 {
  font-size: 84px; font-weight: 900; color: #fff;
  text-shadow:
    -3px -3px 0 #000, 3px -3px 0 #000, -3px 3px 0 #000, 3px 3px 0 #000,
    6px 6px 0 rgba(0,0,0,.6);
}
.line2 {
  font-size: 78px; font-weight: 900; color: #ff3b30;
  text-shadow:
    -3px -3px 0 #fff, 3px -3px 0 #fff, -3px 3px 0 #fff, 3px 3px 0 #fff,
    6px 6px 10px rgba(0,0,0,.8);
}
"""


def render_bullet(b: dict) -> str:
    text = html.escape(b["text"])
    hl = html.escape(b.get("highlight", ""))
    if hl and hl in text:
        text = text.replace(hl, f"<mark>{hl}</mark>", 1)
    return f"<li>{text}</li>"


def slide_html(slide: dict, idx: int, total: int, badge: str) -> str:
    bullets = "\n".join(render_bullet(b) for b in slide["bullets"])
    sources = "  ·  ".join(slide.get("sources", []))
    return f"""<!doctype html><html><head><meta charset="utf-8">
<style>{SLIDE_CSS}</style></head><body>
<div class="badge">{html.escape(badge)}</div>
<h1>{html.escape(slide['title'])}</h1>
<ul>{bullets}</ul>
<div class="sources">{html.escape(sources)}</div>
<div class="pagenum">{idx}/{total}</div>
</body></html>"""


def thumbnail_html(thumb: dict) -> str:
    return f"""<!doctype html><html><head><meta charset="utf-8">
<style>{THUMB_CSS}</style></head><body>
<div class="badge">크립토 뉴스</div>
<div class="hand">{html.escape(thumb['handwriting'])}</div>
<div class="titles">
  <div class="line1">{html.escape(thumb['line1'])}</div>
  <div class="line2">{html.escape(thumb['line2'])}</div>
</div>
</body></html>"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video_json", help="generate_script.py 출력 파일")
    ap.add_argument("-o", "--output", default="slides")
    ap.add_argument("--badge", default="크립토 뉴스")
    args = ap.parse_args()

    with open(args.video_json, encoding="utf-8") as f:
        video = json.load(f)

    out = pathlib.Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    slides = video["slides"]

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROMIUM_PATH)
        page = browser.new_page(viewport={"width": 1920, "height": 1080})

        for i, slide in enumerate(slides, 1):
            html_doc = slide_html(slide, i, len(slides), args.badge)
            html_path = out / f"slide_{i:02d}.html"
            html_path.write_text(html_doc, encoding="utf-8")
            page.goto(html_path.as_uri())
            page.screenshot(path=str(out / f"slide_{i:02d}.png"))
            print(f"  slide_{i:02d}.png — {slide['title']}")

        thumb_doc = thumbnail_html(video["thumbnail"])
        (out / "thumbnail.html").write_text(thumb_doc, encoding="utf-8")
        page.set_viewport_size({"width": 1280, "height": 720})
        page.goto((out / "thumbnail.html").as_uri())
        page.screenshot(path=str(out / "thumbnail.png"))
        print("  thumbnail.png (배경은 AI 이미지로 교체 권장)")
        browser.close()

    # 나레이션 대본을 녹음용 텍스트로도 저장
    script_lines = [f"# {video['video_title']}", ""]
    for i, slide in enumerate(slides, 1):
        script_lines += [f"## 슬라이드 {i} — {slide['title']}", "", slide["narration"], ""]
    (out / "script.md").write_text("\n".join(script_lines), encoding="utf-8")
    print(f"  script.md — 녹음용 대본")
    print(f"완료: {out}/")


if __name__ == "__main__":
    main()
