"""Mux the recording with narration using a numpy mix (robust for many clips)."""

import json
import os
import subprocess
import wave

import numpy as np

WS = r"D:\KUN_lswes"
REC = os.path.join(WS, ".tmp", "rec3")
FF = r"D:\KUN_lswes\.tools\ffmpeg\ffmpeg-win-x86_64-v9.0.2.exe"
OUT = os.path.join(WS, "ZeroNotice_데모영상.mp4")
SR = 48000


def duration(path):
    out = subprocess.run([FF, "-i", path], capture_output=True, text=True,
                         encoding="utf-8", errors="ignore")
    for line in out.stderr.splitlines():
        if "Duration:" in line:
            h, m, s = line.split("Duration:")[1].split(",")[0].strip().split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    return 0.0


def decode(path):
    raw = subprocess.run(
        [FF, "-v", "error", "-i", path, "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
        capture_output=True, check=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2)


def main():
    meta = json.load(open(os.path.join(REC, "timeline.json"), encoding="utf-8"))
    timeline, video = meta["timeline"], meta["video"]
    total = duration(video)
    bed = np.zeros((int(total * SR) + SR, 2), dtype=np.float32)

    placed = 0
    for item in timeline:
        mp3 = os.path.join(REC, f"{item['label']}.mp3")
        if not os.path.exists(mp3):
            continue
        clip = decode(mp3)
        start = int((item["t"] + 0.12) * SR)
        end = min(start + len(clip), len(bed))
        bed[start:end] += clip[: end - start]
        placed += 1

    peak = float(np.max(np.abs(bed))) or 1.0
    target = 10 ** (-1.5 / 20)  # -1.5 dBFS
    bed = bed * (target / peak)
    pcm = np.clip(bed, -1.0, 1.0)
    wav_path = os.path.join(REC, "narration.wav")
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes((pcm * 32767).astype(np.int16).tobytes())

    cmd = [FF, "-y", "-hide_banner", "-loglevel", "error",
           "-i", video, "-i", wav_path,
           "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "25",
           "-c:a", "aac", "-b:a", "192k",
           "-shortest", "-movflags", "+faststart", OUT]
    subprocess.run(cmd, check=True)
    print(f"placed {placed} clips; saved {OUT} {duration(OUT):.1f}s "
          f"{os.path.getsize(OUT) // 1024}KB")


if __name__ == "__main__":
    main()
