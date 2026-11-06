"""Render a ~100s Korean narrated demo video for ZeroNotice.

Pipeline: PIL scene cards -> ffmpeg zoompan clips -> TTS (Google translate) -> concat.
"""

import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw, ImageFont

WS = r"D:\KUN_lswes"
TMP = os.path.join(WS, ".tmp", "video")
IMG = os.path.join(WS, ".tmp", "deckimg")
FF = r"D:\KUN_lswes\.tools\ffmpeg\ffmpeg-win-x86_64-v9.0.2.exe"
OUT = os.path.join(WS, "ZeroNotice_데모영상.mp4")

W, H, FPS = 1920, 1080, 25
INK = (11, 11, 15)
MUTED = (111, 111, 120)
FAINT = (161, 161, 170)
LINE = (230, 230, 234)
SOFT = (247, 247, 248)
WHITE = (255, 255, 255)
EMERALD = (16, 185, 129)

FONT_BOLD = r"C:\Windows\Fonts\malgunbd.ttf"
FONT_REG = r"C:\Windows\Fonts\malgun.ttf"


def font(size, bold=True):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def text(draw, xy, s, size=40, fill=INK, bold=True, anchor="la", spacing=1.25):
    f = font(size, bold)
    x, y = xy
    lines = s.split("\n")
    line_h = int(size * spacing)
    for i, line in enumerate(lines):
        draw.text((x, y + i * line_h), line, font=f, fill=fill, anchor=anchor)


def rounded(img, radius=28):
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, img.size[0] - 1, img.size[1] - 1], radius, fill=255)
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def paste_card(canvas, path, box, radius=24, border=LINE):
    """Paste a screenshot scaled into box, with rounded corners + hairline."""
    x, y, w, h = box
    src = Image.open(path).convert("RGB")
    scale = min(w / src.width, h / src.height)
    nw, nh = int(src.width * scale), int(src.height * scale)
    src = src.resize((nw, nh), Image.LANCZOS)
    card = rounded(src, radius)
    layer = Image.new("RGB", (nw + 2, nh + 2), WHITE)
    layer.paste(card.convert("RGB"), (1, 1), card)
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle([0, 0, nw + 1, nh + 1], radius, outline=border, width=2)
    canvas.paste(layer, (x, y))


def scene_cover():
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 18, H], fill=EMERALD)
    text(d, (140, 150), "2026 KNU AI HACKATHON · ZERO TO ONE", 26, (110, 110, 120))
    text(d, (140, 235), "공지의 숨은 비용을\n0으로 만드는 AI 비서", 92, WHITE, spacing=1.18)
    text(d, (140, 560), "ZeroNotice (제로노티스)", 42, (200, 200, 208), bold=False)
    text(d, (140, 625), "강원대 공지 탐색 · 첨부 판독 · 자격 판정 · 신청 링크 추출 · 마감 알림", 30, (150, 150, 160), bold=False)
    d.rectangle([140, 760, 300, 766], fill=EMERALD)
    text(d, (140, 800), "류위신 · 첨단AI공학부", 30, (170, 170, 180), bold=False)
    paste_card(img, os.path.join(IMG, "detail.png"), (1180, 150, 660, 800), radius=28)
    return img


def scene_problem():
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    text(d, (120, 110), "01 · 문제", 26, EMERALD)
    text(d, (120, 165), "공지 한 건에 6분, 학기마다 7시간", 66)
    text(d, (120, 280), "본문은 비어 있고, 자격요건은 HWP 첨부 2페이지에, 신청 경로는 제각각입니다.", 30, MUTED, bold=False)

    stats = [("6.1분", "공지 1건 확인"), ("주 5건", "확인 빈도"), ("6.8시간", "학기당 소모"), ("D-3", "평균 발견 시점")]
    x = 120
    for v, label in stats:
        d.rounded_rectangle([x, 380, x + 400, 620], 22, fill=SOFT)
        text(d, (x + 40, 420), v, 62)
        text(d, (x + 40, 520), label, 28, MUTED, bold=False)
        x += 420

    text(d, (120, 700), "탐색 3.5분 + 첨부 열람 1.5분 + 자격 대조 1.1분", 26, FAINT, bold=False)
    text(d, (120, 790), "확인이 안 되는 게 아니라, 확인·판단·신청 준비가 전부 사람 손입니다.", 34, INK)
    return img


def scene_solution():
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    text(d, (120, 110), "02 · 해결", 26, EMERALD)
    text(d, (120, 165), "읽고, 판정하고, 신청까지", 66)

    rows = [
        ("공지 통합", "5개 게시판을 한 화면에 · 모든 사용자가 같은 데이터"),
        ("첨부 5종 판독", "HWP · HWPX · PDF · XLSX · DOCX 를 서버에서 직접"),
        ("자격 자동 판정", "캠퍼스·신분·GPA·소득분위를 규칙 엔진으로 대조"),
        ("신청 정보 추출", "링크·접수 방법·서류·문의처를 출처와 함께"),
        ("마감 알림", "관심 등록하면 24시간 전에 메일 + 캘린더"),
    ]
    y = 300
    for i, (t, sub) in enumerate(rows):
        d.ellipse([120, y, 176, y + 56], fill=INK)
        text(d, (148, y + 28), str(i + 1), 28, WHITE, anchor="mm")
        text(d, (210, y + 2), t, 38)
        text(d, (210, y + 48), sub, 26, MUTED, bold=False)
        y += 130

    paste_card(img, os.path.join(IMG, "detail.png"), (1250, 300, 560, 680), radius=26)
    return img


def scene_apply():
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    text(d, (120, 110), "03 · 신청 정보", 26, EMERALD)
    text(d, (120, 165), "링크가 포스터 안에만 있어도 찾아냅니다", 58)
    paste_card(img, os.path.join(IMG, "apply.png"), (120, 300, 1000, 420), radius=22)
    text(d, (120, 780), "본문에 링크가 있는 공지는 7건뿐 · 1건은 포스터 OCR + HTTP 검증", 28, MUTED, bold=False)
    paste_card(img, os.path.join(IMG, "gallery.png"), (1180, 300, 620, 420), radius=22)
    text(d, (1180, 745), "포스터 안의 링크를 읽고,\n살아있는 주소만 노출합니다.", 26, MUTED, bold=False)
    return img


def scene_assistant():
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    text(d, (120, 110), "04 · AI 비서와 알림", 26, EMERALD)
    text(d, (120, 165), "말로 시키면, 대신 처리합니다", 58)
    paste_card(img, os.path.join(IMG, "assistant.png"), (150, 300, 520, 700), radius=24)
    paste_card(img, os.path.join(IMG, "sub.png"), (820, 300, 980, 330), radius=20)
    text(d, (820, 680), "관심 등록 → 마감 24시간 전 메일\n.ics 첨부로 캘린더 자동 등록", 28, MUTED, bold=False)
    return img


def scene_close():
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)
    text(d, (140, 190), "THANK YOU", 26, (110, 110, 120))
    text(d, (140, 250), "공지를 찾는 시간을 0으로,\n신청까지의 거리를 0으로.", 76, WHITE, spacing=1.2)

    stats = [("25", "공지"), ("45", "첨부"), ("23", "AI 추출"), ("24h", "마감 알림")]
    x = 140
    for v, label in stats:
        text(d, (x, 610), v, 56, WHITE)
        text(d, (x, 690), label, 26, (150, 150, 160), bold=False)
        x += 300

    text(d, (140, 830), "github.com/stewenmc-boop/ZeroNotice   ·   zero-notice.vercel.app", 28, (200, 200, 208), bold=False)
    text(d, (140, 890), "류위신 · 첨단AI공학부 · 2026 KNU AI Hackathon", 24, (140, 140, 150), bold=False)
    return img


SCENES = [
    {
        "img": scene_cover,
        "narration": "안녕하세요. 강원대 공지의 숨은 비용을 0으로 만드는, 제로노티스입니다.",
    },
    {
        "img": scene_problem,
        "narration": "학생들은 매주 장학 공지를 찾고, 본문이 비어 있어 첨부 파일을 열고, 자격 요건과 내 학점을 직접 대조합니다. 공지 한 건에 육 분, 학기마다 칠 시간이 사라집니다.",
    },
    {
        "img": scene_solution,
        "narration": "제로노티스는 공지를 모으고, 다섯 가지 형식의 첨부를 읽고, 내 조건과 대조해 지원 가능 여부를 즉시 판정합니다.",
    },
    {
        "img": scene_apply,
        "narration": "관심 있는 공지를 열면, 에이아이가 신청 링크와 제출 서류를 찾아냅니다. 링크가 포스터 이미지 안에만 있어도, 읽어서 검증합니다.",
    },
    {
        "img": scene_assistant,
        "narration": "궁금한 것은 비서에게 말로 물으면 되고, 관심 등록을 하면 마감 하루 전에 메일과 캘린더 알림이 도착합니다.",
    },
    {
        "img": scene_close,
        "narration": "공지 스물다섯 건과 첨부 마흔다섯 개를 실제로 처리했고, 없는 정보는 만들지 않습니다. 감사합니다.",
    },
]


def tts(text_str: str, path: str) -> bool:
    """Google translate TTS; split long text into <=180 char chunks."""
    chunks, buf = [], ""
    for ch in text_str:
        buf += ch
        if len(buf) >= 170 and ch in ".!?":
            chunks.append(buf.strip())
            buf = ""
    if buf.strip():
        chunks.append(buf.strip())
    if not chunks:
        chunks = [text_str]

    parts = []
    for i, chunk in enumerate(chunks):
        url = (
            "https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl=ko&q="
            + urllib.parse.quote(chunk)
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            data = urllib.request.urlopen(req, timeout=30).read()
        except Exception as exc:  # noqa: BLE001
            print("tts failed:", exc)
            return False
        part = f"{path}.{i}.mp3"
        with open(part, "wb") as fh:
            fh.write(data)
        parts.append(part)

    if len(parts) == 1:
        os.replace(parts[0], path)
        return True

    listfile = path + ".txt"
    with open(listfile, "w", encoding="utf-8") as fh:
        for p in parts:
            fh.write(f"file '{p.replace(os.sep, '/')}'\n")
    subprocess.run(
        [FF, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", listfile, "-c", "copy", path],
        check=True,
    )
    return True


def duration(path: str) -> float:
    out = subprocess.run([FF, "-i", path], capture_output=True, text=True, encoding="utf-8", errors="ignore")
    for line in out.stderr.splitlines():
        if "Duration:" in line:
            hh, mm, ss = line.split("Duration:")[1].split(",")[0].strip().split(":")
            return int(hh) * 3600 + int(mm) * 60 + float(ss)
    return 3.0


def main() -> int:
    os.makedirs(TMP, exist_ok=True)
    segments, audio_parts = [], []

    for i, scene in enumerate(SCENES, 1):
        png = os.path.join(TMP, f"scene{i}.png")
        mp3 = os.path.join(TMP, f"scene{i}.mp3")
        scene["img"]().save(png)
        if not tts(scene["narration"], mp3):
            return 2
        dur = max(duration(mp3) + 1.0, 5.0)
        seg = os.path.join(TMP, f"seg{i}.mp4")
        fade_out = max(dur - 0.7, 0)
        vf = (
            f"zoompan=z='min(zoom+0.0006,1.06)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":s={W}x{H}:fps={FPS},format=yuv420p"
        )
        if i == 1:
            vf += ",fade=t=in:st=0:d=0.6"
        if i == len(SCENES):
            vf += f",fade=t=out:st={fade_out:.2f}:d=0.7"

        subprocess.run(
            [FF, "-y", "-hide_banner", "-loglevel", "error",
             "-loop", "1", "-i", png, "-i", mp3,
             "-t", f"{dur:.2f}",
             "-filter_complex",
             f"[0:v]{vf}[v];[1:a]adelay=400|400,apad,atrim=0:{dur:.2f},aformat=sample_rates=48000:channel_layouts=stereo[a]",
             "-map", "[v]", "-map", "[a]",
             "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", str(FPS),
             "-c:a", "aac", "-b:a", "160k", "-shortest", seg],
            check=True,
        )
        segments.append(seg)
        print(f"scene {i}: {dur:.1f}s")

    listfile = os.path.join(TMP, "concat.txt")
    with open(listfile, "w", encoding="utf-8") as fh:
        for seg in segments:
            fh.write(f"file '{seg.replace(os.sep, '/')}'\n")

    subprocess.run(
        [FF, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", listfile, "-c", "copy", "-movflags", "+faststart", OUT],
        check=True,
    )
    print("saved", OUT, f"{duration(OUT):.1f}s", f"{os.path.getsize(OUT) // 1024}KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
