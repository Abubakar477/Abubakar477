#!/usr/bin/env python3
"""
patch_banner.py - updates the text info panel in banner-dark.v9.svg and banner-light.v9.svg
for Abubakar477.
"""

from __future__ import annotations
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

ROWS = [
    ("Subject", "Abubakar"),
    ("Role", "Software Developer · CS Student"),
    ("Origin", "Islamabad · Pakistan"),
    ("Education", "BS Computer Science · IST"),
    ("Status", "Building + Learning + Shipping"),
    ("ToolChain", "VS Code · Git · Figma"),
    ("Core.Lang", "Python · C++ · TypeScript · JS"),
    ("Core.Frontend", "React · Next.js · Three.js · Tailwind"),
    ("Core.Backend", "Node · Python · REST APIs"),
    ("Core.Database", "Postgres · SQL"),
    ("Core.Infra", "Vercel · Docker · GitHub Actions"),
    ("Grid.Mail", "abubakar2pp@gmail.com"),
    ("Grid.LinkedIn", "/in/abubakar"),
    ("Grid.GitHub", "Abubakar477"),
    ("Grid.Portfolio", "my-3d-portfolio-snowy-eight"),
]

THEMES = {
    "dark": {
        "line": "#25344C",
        "muted": "#8291A8",
        "text": "#DDE7F5",
        "chrome": "#22D3EE",
        "accent": "#10B981",
        "node": "UTC+5 · PK NODE",
    },
    "light": {
        "line": "#CBD7E1",
        "muted": "#64748B",
        "text": "#172033",
        "chrome": "#0891B2",
        "accent": "#10B981",
        "node": "UTC+5 · PK NODE",
    },
}

def num(v: float) -> str:
    s = f"{v:.2f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s

def text_width(text: str, font_size: float = 14) -> float:
    return len(text) * font_size * 0.605

def dotted_leader(x1: float, x2: float, y: float) -> str:
    if x2 <= x1:
        return ""
    cur = x1
    pts = []
    while cur < x2:
        pts.append(f"M{num(cur)} {num(y)}h1")
        cur += 5.0
    return "".join(pts)

def patch_banner(theme: str):
    file_path = ASSETS / f"banner-{theme}.v9.svg"
    if not file_path.exists():
        print(f"Skipping {file_path}, does not exist")
        return

    content = file_path.read_text(encoding="utf-8")
    t = THEMES[theme]

    # Replace handle pill text
    content = re.sub(
        r'<text x="1055" y="111"[^>]*>.*?</text>',
        f'<text x="1055" y="111" text-anchor="middle" fill="{t["chrome"]}" '
        'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" '
        'font-size="14" font-weight="700">@Abubakar477</text>',
        content,
    )

    # Build new rows
    value_right = 1127.0
    row_y = 153.0
    rows_svg = []
    for label, value in ROWS:
        val_w = round(text_width(value, 14), 1)
        lbl_w = round(text_width(label, 14), 1)
        leader_start = 491 + lbl_w + 12
        leader_end = value_right - val_w - 12
        
        row_str = (
            f'<text x="491" y="{num(row_y)}" fill="{t["muted"]}" '
            'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="14">'
            f'{html.escape(label)}</text>'
            f'<path d="{dotted_leader(leader_start, leader_end, row_y - 4)}" '
            f'fill="none" stroke="{t["line"]}" stroke-width="1" shape-rendering="crispEdges"/>'
            f'<text x="{num(value_right)}" y="{num(row_y)}" text-anchor="end" '
            f'fill="{t["text"]}" font-family="ui-monospace,SFMono-Regular,Consolas,monospace" '
            f'font-size="14" textLength="{num(val_w)}" lengthAdjust="spacingAndGlyphs">'
            f'{html.escape(value)}</text>'
        )
        rows_svg.append(row_str)
        row_y += 23

    new_rows_content = "".join(rows_svg)

    # Replace the rows block: starts with <text x="491" y="153" up to <path d="M490 530H1130"
    pattern = r'<text x="491" y="153".*?(?=<path d="M490 530H1130")'
    content = re.sub(pattern, new_rows_content, content, flags=re.DOTALL)

    # Replace node location string
    content = re.sub(
        r'<text x="1128" y="548"[^>]*>.*?</text>',
        f'<text x="1128" y="548" text-anchor="end" fill="{t["muted"]}" '
        'font-family="ui-monospace,SFMono-Regular,Consolas,monospace" font-size="11">'
        f'{t["node"]}</text>',
        content,
    )

    file_path.write_text(content, encoding="utf-8")
    print(f"Successfully patched {file_path.name}")

if __name__ == "__main__":
    patch_banner("dark")
    patch_banner("light")
