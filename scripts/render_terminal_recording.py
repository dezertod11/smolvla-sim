"""Render a util-linux script(1) timing/output pair as a compact MP4 proof."""

import argparse
import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ANSI = re.compile(rb"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")


def snapshots(timing, typescript):
    payload = Path(typescript).read_bytes()
    offset = 0
    elapsed = 0.0
    text = ""
    result = []
    for row in Path(timing).read_text(encoding="utf-8").splitlines():
        delay, size = row.split()
        elapsed += float(delay)
        size = int(size)
        chunk = ANSI.sub(b"", payload[offset : offset + size]).decode(
            "utf-8", errors="replace"
        )
        offset += size
        text += chunk.replace("\r", "\n")
        result.append((elapsed, text))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("timing")
    parser.add_argument("typescript")
    parser.add_argument("output")
    parser.add_argument("--speed", type=float, default=1.5)
    args = parser.parse_args()
    states = snapshots(args.timing, args.typescript)
    duration = states[-1][0] / args.speed
    font = ImageFont.truetype("DejaVuSansMono.ttf", 20)
    title_font = ImageFont.truetype("DejaVuSansMono-Bold.ttf", 23)
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        state_index = 0
        for second in range(int(duration) + 2):
            source_time = second * args.speed
            while state_index + 1 < len(states) and states[state_index + 1][0] <= source_time:
                state_index += 1
            lines = [line for line in states[state_index][1].splitlines() if line.strip()]
            image = Image.new("RGB", (1280, 720), "#111827")
            draw = ImageDraw.Draw(image)
            draw.rectangle((0, 0, 1280, 58), fill="#0b1220")
            draw.text(
                (24, 16),
                "docker compose up — ROS2 closed loop",
                font=title_font,
                fill="#e5e7eb",
            )
            draw.text(
                (1010, 19),
                f"{min(source_time, states[-1][0]):6.1f}s",
                font=font,
                fill="#93c5fd",
            )
            visible = lines[-25:]
            y = 78
            for line in visible:
                color = "#86efac" if "ROS2_EPISODE_RESULT" in line else "#d1d5db"
                draw.text((22, y), line[:105], font=font, fill=color)
                y += 24
            image.save(directory / f"frame-{second:04d}.png")
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error", "-framerate", "1",
                "-i", str(directory / "frame-%04d.png"), "-vf", "fps=30",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", args.output,
            ],
            check=True,
        )
    print(f"Rendered {duration:.1f}s to {args.output}")


if __name__ == "__main__":
    main()
