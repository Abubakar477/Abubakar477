#!/usr/bin/env python3
"""
radar.py - render a spider / radar chart as a standalone SVG. Stdlib only.

Two sources of data:

  1. a JSON file you control (default)
        python scripts/radar.py --data assets/skills.json -o assets/radar

  2. live language stats from the GitHub API
        python scripts/radar.py --github YOUR_USERNAME -o assets/radar-langs

Writes <out>-dark.svg and <out>-light.svg so the README can swap them with
<picture> + prefers-color-scheme.

skills.json shape:
    {
      "title": "Skill Radar",
      "axes": [ {"label": "Python", "value": 88}, ... ]      // value 0-100
    }
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

THEMES = {
    "dark": {
        "bg": "#0d1117",
        "grid": "#30363d",
        "spoke": "#21262d",
        "label": "#c9d1d9",
        "value": "#8b949e",
        "title": "#e6edf3",
        "stroke": "#38bdf8",
        "fill": "#38bdf8",
        "vertex": "#7dd3fc",
    },
    "light": {
        "bg": "#ffffff",
        "grid": "#d0d7de",
        "spoke": "#e1e4e8",
        "label": "#24292f",
        "value": "#57606a",
        "title": "#24292f",
        "stroke": "#0284c7",
        "fill": "#0284c7",
        "vertex": "#0369a1",
    },
}


def from_json(path: Path) -> tuple[str, list[tuple[str, float]]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    title = raw.get("title", "")
    axes = [(a["label"], float(a["value"])) for a in raw["axes"]]
    return title, axes


def from_github(user: str, token: str | None, limit: int, excl: set[str],
                curve: float) -> tuple[str, list[tuple[str, float]]]:
    req = urllib.request.Request(
        f"https://api.github.com/users/{user}/repos?per_page=100&type=owner",
        headers={"User-Agent": "radar.py"},
    )
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            repos = json.loads(res.read())
    except urllib.error.URLError as e:
        sys.exit(f"GitHub API error: {e}")

    totals: dict[str, int] = {}
    for r in repos:
        if r.get("fork"):
            continue
        l_req = urllib.request.Request(
            r["languages_url"], headers={"User-Agent": "radar.py"}
        )
        if token:
            l_req.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(l_req, timeout=15) as res:
                for lang, bytes_ in json.loads(res.read()).items():
                    if lang.lower() not in excl:
                        totals[lang] = totals.get(lang, 0) + bytes_
        except urllib.error.URLError:
            pass

    top = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    if not top:
        sys.exit(f"no language bytes found for {user}")

    peak = top[0][1]
    axes = [(n, round(100 * (c / peak) ** curve, 1)) for n, c in top]
    return f"{user} · language mix", axes


# --------------------------------------------------------------------------- #
# rendering
# --------------------------------------------------------------------------- #


FONT = "ui-sans-serif,-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif"
LBL, VAL, TTL = 13, 11, 15  # font sizes: axis label, axis value, title


def ring(radius, n, start=-math.pi / 2):
    """Vertices of a regular n-gon centred on (0, 0), first one straight up."""
    return [
        (radius * math.cos(start + i * 2 * math.pi / n),
         radius * math.sin(start + i * 2 * math.pi / n))
        for i in range(n)
    ]


def text_width(s: str, font_size: float) -> float:
    return len(s) * font_size * 0.62


def render(title: str, axes: list[tuple[str, float]], theme: str, size: int,
           rings: int, show_values: bool, animate: bool) -> str:
    c = THEMES[theme]
    n = len(axes)
    r = size / 2 - 8
    gap = 20

    vals = [max(0.0, min(100.0, v)) for _, v in axes]
    outer = ring(r, n)

    labels = []
    for i, (label, _) in enumerate(axes):
        ang = -math.pi / 2 + i * 2 * math.pi / n
        cosv, sinv = math.cos(ang), math.sin(ang)
        lx, ly = (r + gap) * cosv, (r + gap) * sinv
        anchor = "middle" if abs(cosv) < 0.25 else ("start" if cosv > 0 else "end")
        dy = 4 if abs(sinv) < 0.25 else (14 if sinv > 0 else -5)
        labels.append((lx, ly + dy, anchor, label, vals[i]))

    minx, maxx, miny, maxy = -r, r, -r, r
    for lx, ly, anchor, label, v in labels:
        w = max(text_width(label, LBL),
                text_width(f"{v:g}", VAL) if show_values else 0.0)
        if anchor == "start":
            x0, x1 = lx, lx + w
        elif anchor == "end":
            x0, x1 = lx - w, lx
        else:
            x0, x1 = lx - w / 2, lx + w / 2
        y0 = ly - LBL
        y1 = ly + 4 + (VAL + 4 if show_values else 0)
        minx, maxx = min(minx, x0), max(maxx, x1)
        miny, maxy = min(miny, y0), max(maxy, y1)

    pad = 14
    title_h = TTL + 14 if title else 0
    W = round((maxx - minx) + 2 * pad)
    H = round((maxy - miny) + 2 * pad + title_h)
    ox, oy = -minx + pad, -miny + pad + title_h

    if title:
        need = round(text_width(title, TTL) + 2 * pad)
        if need > W:
            ox += (need - W) / 2
            W = need

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}" role="img" '
        f'aria-label="{esc(title) or "radar chart"}" font-family="{FONT}">'
    ]
    if c["bg"] != "none":
        parts.append(
            f'<rect width="100%" height="100%" rx="10" fill="{c["bg"]}" '
            f'stroke="{c["grid"]}" stroke-width="1"/>'
        )
    if title:
        parts.append(
            f'<text x="{W / 2:.1f}" y="{pad + TTL:.0f}" text-anchor="middle" '
            f'font-size="{TTL}" font-weight="700" fill="{c["title"]}">'
            f'{esc(title)}</text>'
        )
    parts.append(f'<g transform="translate({ox:.1f},{oy:.1f})">')

    # Concentric rings
    for k in range(rings, 0, -1):
        d = " ".join(f"{x:.1f},{y:.1f}" for x, y in ring(r * k / rings, n))
        parts.append(
            f'<polygon points="{d}" fill="none" stroke="{c["grid"]}" '
            f'stroke-width="1" opacity="{0.35 + 0.5 * k / rings:.2f}"/>'
        )

    # Spokes
    for x, y in outer:
        parts.append(
            f'<line x1="0" y1="0" x2="{x:.1f}" y2="{y:.1f}" '
            f'stroke="{c["spoke"]}" stroke-width="1"/>'
        )

    # Data shape
    shape = [(px * v / 100, py * v / 100) for (px, py), v in zip(outer, vals)]
    d = " ".join(f"{x:.1f},{y:.1f}" for x, y in shape)
    parts.append("<g>")
    if animate:
        parts.append(
            '<animateTransform attributeName="transform" type="scale" '
            'values="0.04;1" dur="1.1s" calcMode="spline" keyTimes="0;1" '
            'keySplines="0.22 1 0.36 1" fill="freeze"/>'
        )
    parts.append(
        f'<polygon points="{d}" fill="{c["fill"]}" fill-opacity="0.25" '
        f'stroke="{c["stroke"]}" stroke-width="2.5" stroke-linejoin="round"/>'
    )
    for x, y in shape:
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.6" fill="{c["vertex"]}" '
            f'stroke="{c["stroke"]}" stroke-width="1.2"/>'
        )
    parts.append("</g>")

    # Axis labels
    for lx, ly, anchor, label, v in labels:
        parts.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" '
            f'font-size="{LBL}" font-weight="600" fill="{c["label"]}">'
            f'{esc(label)}</text>'
        )
        if show_values:
            parts.append(
                f'<text x="{lx:.1f}" y="{ly + VAL + 4:.1f}" text-anchor="{anchor}" '
                f'font-size="{VAL}" fill="{c["value"]}">{v:g}%</text>'
            )

    parts.append("</g></svg>")
    return "".join(parts)


def esc(s: str) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    src = p.add_mutually_exclusive_group()
    src.add_argument("--data", type=Path, default=Path("assets/skills.json"))
    src.add_argument("--github", metavar="USER",
                     help="build the radar from GitHub language stats instead")
    p.add_argument("-o", "--out", type=Path, default=Path("assets/radar"),
                   help="output path WITHOUT extension")
    p.add_argument("--title", help="override the chart title ('' for none)")
    p.add_argument("--size", type=int, default=420)
    p.add_argument("--rings", type=int, default=4)
    p.add_argument("--limit", type=int, default=7,
                   help="max axes when using --github")
    p.add_argument("--exclude", default="html,css,shell,makefile,dockerfile,batchfile",
                   help="comma-separated languages to skip in --github mode")
    p.add_argument("--curve", type=float, default=0.5,
                   help="--github axis scaling: 1.0 linear, 0.5 sqrt (default)")
    p.add_argument("--values", action="store_true", help="print the number per axis")
    p.add_argument("--no-animate", dest="animate", action="store_false",
                   help="disable the grow-in animation")
    args = p.parse_args(argv)

    if args.github:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        excl = {s.strip().lower() for s in args.exclude.split(",") if s.strip()}
        title, axes = from_github(args.github, token, args.limit, excl, args.curve)
    else:
        if not args.data.exists():
            sys.exit(f"no data file: {args.data}")
        title, axes = from_json(args.data)

    if args.title is not None:
        title = args.title
    if len(axes) < 3:
        sys.exit("a radar chart needs at least 3 axes")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    for theme in ("dark", "light"):
        svg = render(title, axes, theme, args.size, args.rings, args.values,
                     args.animate)
        dest = args.out.with_name(f"{args.out.name}-{theme}.svg")
        dest.write_text(svg, encoding="utf-8")
        print(f"wrote {dest} ({len(axes)} axes)")


if __name__ == "__main__":
    main()
