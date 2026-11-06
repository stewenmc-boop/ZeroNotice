"""Generate Korean narration clips + durations.json used by the recorder and muxer."""

import json
import os
import subprocess
import urllib.parse
import urllib.request

WS = r"D:\KUN_lswes"
REC = os.path.join(WS, ".tmp", "rec3")
FF = r"D:\KUN_lswes\.tools\ffmpeg\ffmpeg-win-x86_64-v9.0.2.exe"

# order matters: the recorder walks the same labels
SCRIPT = [
    ("intro", "제로노티스. 강원대 공지의 숨은 비용을 0으로 만드는 AI 비서입니다."),
    ("list", "다섯 개 게시판의 공지를 한 화면에 모으고, 내 조건에 맞는 것만 보여줍니다."),
    ("filter", "신청 링크가 있는 공지만 따로 볼 수 있습니다."),
    ("search", "검색은 제목뿐 아니라 첨부 본문과 추출된 신청 정보까지 찾습니다."),
    ("detail", "공지를 열면 가장 먼저 자격 판정이 나옵니다. LLM이 아니라 규칙 엔진이 계산합니다."),
    ("apply", "AI가 뽑은 신청 정보입니다. 링크와 접수 방법, 제출 서류, 문의처까지 한 번에 보입니다."),
    ("attachments", "첨부 파일과 포스터도 이 자리에서 확인합니다."),
    ("agent", "이제 담당 부서에 보낼 문의 메일을 만들어 보겠습니다."),
    ("email", "딥시크 모델이 몇 초 만에 정중한 한국어 행정 메일을 작성했습니다."),
    ("assistant", "궁금한 것은 오른쪽 아래 비서에게 말로 물으면 됩니다."),
    ("assistant-answer", "이번 주 마감 공지를 정리하고, 지원 가능한지까지 알려줍니다."),
    ("subscription", "관심 있는 공지는 알림을 켜두면 마감 하루 전에 메일로 알려줍니다."),
    ("subscribed", "알림은 제가 입력한 프로필 이메일로 발송됩니다."),
    ("profile", "왼쪽에는 제 학적 정보가 저장되어 있고, 판정과 메일에 그대로 쓰입니다."),
    ("repo", "이제 이 프로젝트를 어떻게 만들었는지 보여드리겠습니다. 코드와 문서는 깃허브에 있습니다."),
    ("agents-md", "에이전츠 문서에는 구조와 API, 금지 사항, 디자인 규칙을 고정했습니다."),
    ("commits", "커밋 메시지에는 무엇을 왜 바꿨고, 실제로 검증했는지를 남겼습니다."),
    ("summary", "빈 본문과 첨부, 자격 대조, 흩어진 신청 경로, 마감 망각. 네 가지를 하나의 흐름으로 해결했습니다."),
]


def tts(text, path):
    chunks, buf = [], ""
    for ch in text:
        buf += ch
        if len(buf) >= 170 and ch in ".!?":
            chunks.append(buf.strip())
            buf = ""
    if buf.strip():
        chunks.append(buf.strip())
    parts = []
    for i, chunk in enumerate(chunks):
        url = ("https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl=ko&q="
               + urllib.parse.quote(chunk))
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        data = urllib.request.urlopen(req, timeout=30).read()
        part = f"{path}.{i}.mp3"
        open(part, "wb").write(data)
        parts.append(part)
    if len(parts) == 1:
        os.replace(parts[0], path)
        return
    lst = path + ".txt"
    with open(lst, "w", encoding="utf-8") as fh:
        for p in parts:
            fh.write(f"file '{p.replace(os.sep, '/')}'\n")
    subprocess.run([FF, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat",
                    "-safe", "0", "-i", lst, "-c", "copy", path], check=True)


def duration(path):
    out = subprocess.run([FF, "-i", path], capture_output=True, text=True,
                         encoding="utf-8", errors="ignore")
    for line in out.stderr.splitlines():
        if "Duration:" in line:
            h, m, s = line.split("Duration:")[1].split(",")[0].strip().split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    return 3.0


def main():
    os.makedirs(REC, exist_ok=True)
    meta = []
    for label, text in SCRIPT:
        path = os.path.join(REC, f"{label}.mp3")
        if not os.path.exists(path):
            tts(text, path)
        dur = duration(path)
        meta.append({"label": label, "text": text, "file": path, "seconds": round(dur, 2)})
        print(f"{label:18s} {dur:5.2f}s  {text[:24]}")

    with open(os.path.join(REC, "durations.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
    print("total speech:", round(sum(m["seconds"] for m in meta), 1), "s")


if __name__ == "__main__":
    main()
