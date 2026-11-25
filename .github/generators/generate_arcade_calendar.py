#!/usr/bin/env python3
"""Generate an animated 2D retro arcade falling-block SVG from live GitHub contributions.

- Fetches real public contribution cells from https://github.com/users/<user>/contributions
  (matching GitHub's exact 53x7 matrix: week column, day row, date, level, commit count).
- Starts with an empty 2D matrix, then drops each active commit day's flat 2D block
  one-by-one in strict chronological order into its exact calendar coordinate.
- Uses a single cohesive Electric Ice-Cyan hue (196 deg) on Midnight Obsidian (#070B14)
  where each commit tier varies cleanly in saturation, gradient stops, and Golden-Ratio
  (phi = 1.618) WCAG luminance contrast — zero multi-color or orange clutter.
"""

from __future__ import annotations

import argparse
import colorsys
import html
import math
import os
import re
import sys
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


PHI = (1.0 + math.sqrt(5.0)) / 2.0
BG_HEX = "#070B14"
BG_RGB = (7, 11, 20)
ACCENT_HEX = "#38BDF8"
SINGLE_HUE_DEG = 196.0  # Clean Ice-Cyan monochrome palette on Midnight Slate


@dataclass(frozen=True)
class ContributionDay:
    date: str
    col: int
    row: int
    level: int
    count: int


def _rel_luminance(r: int, g: int, b: int) -> float:
    def ch(c: int) -> float:
        v = c / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def _solve_monochrome_rgb(hue_deg: float, sat: float, target_contrast: float, bg_rgb: Tuple[int, int, int]) -> Tuple[int, int, int]:
    """Find RGB at fixed single hue & saturation matching Golden-Ratio WCAG contrast on bg_rgb."""
    bg_l = _rel_luminance(*bg_rgb)
    target_l = target_contrast * (bg_l + 0.05) - 0.05
    lo, hi = 0.12, 0.95
    best = (0, 0, 0)
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        rgb = tuple(int(round(c * 255)) for c in colorsys.hls_to_rgb((hue_deg % 360.0) / 360.0, mid, sat))
        if _rel_luminance(*rgb) < target_l:
            lo = mid
        else:
            hi = mid
        best = rgb  # type: ignore[assignment]
    return best


def _darken(rgb: Tuple[int, int, int], factor: float) -> str:
    r, g, b = (max(0, int(round(c * factor))) for c in rgb)
    return f"#{r:02X}{g:02X}{b:02X}"


def build_monochrome_cyan_palette() -> Dict[int, Tuple[str, str]]:
    """Build 4 pure 2D single-hue tiers varying by saturation, gradient, and phi-luminance."""
    base_contrast = 2.60
    saturations = {1: 0.78, 2: 0.88, 3: 0.96, 4: 1.00}
    palette: Dict[int, Tuple[str, str]] = {}
    for tier in range(1, 5):
        target_cr = base_contrast * (PHI ** (tier - 1))
        rgb = _solve_monochrome_rgb(SINGLE_HUE_DEG, saturations[tier], target_cr, BG_RGB)
        start_hex = f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
        end_hex = _darken(rgb, 0.82)
        palette[tier] = (start_hex, end_hex)
    return palette


def tier_from_count(count: int) -> int:
    if count <= 0:
        return 0
    if count <= 2:
        return 1
    if count <= 5:
        return 2
    if count <= 10:
        return 3
    return 4


def fetch_contributions_html(username: str) -> str:
    url = f"https://github.com/users/{username}/contributions"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; AbhiRamArcadeCalendar/1.0)",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_contributions(raw_html: str) -> Tuple[List[ContributionDay], Optional[int]]:
    total_header: Optional[int] = None
    m_hdr = re.search(r"([\d,]+)\s+contributions?\s+in the last year", raw_html)
    if m_hdr:
        total_header = int(m_hdr.group(1).replace(",", ""))

    cell_pattern = re.compile(
        r'<td\b([^>]*data-date="(\d{4}-\d{2}-\d{2})"[^>]*)>\s*</td>\s*(?:<tool-tip[^>]*>(.*?)</tool-tip>)?',
        re.DOTALL,
    )

    days: List[ContributionDay] = []
    for match in cell_pattern.finditer(raw_html):
        attrs = match.group(1)
        date_str = match.group(2)
        tooltip = html.unescape(match.group(3) or "").strip()

        id_match = re.search(r'id="contribution-day-component-(\d+)-(\d+)"', attrs)
        lvl_match = re.search(r'data-level="(\d+)"', attrs)
        if not id_match or not lvl_match:
            continue

        row = int(id_match.group(1))
        col = int(id_match.group(2))
        level = int(lvl_match.group(1))

        count = 0
        cnt_match = re.search(r"(\d+)\s+contributions?", tooltip)
        if cnt_match:
            count = int(cnt_match.group(1))
        elif level > 0:
            count = level

        days.append(ContributionDay(date=date_str, col=col, row=row, level=level, count=count))

    if not days:
        raise RuntimeError("Failed to parse any contribution calendar cells from GitHub HTML.")

    days.sort(key=lambda d: (d.col, d.row))
    return days, total_header


def compute_month_labels(days: List[ContributionDay]) -> List[Tuple[int, str]]:
    """Place month abbreviations aligned with GitHub's calendar columns without overlap."""
    by_col: Dict[int, List[ContributionDay]] = {}
    for d in days:
        by_col.setdefault(d.col, []).append(d)

    labels: List[Tuple[int, str]] = []
    last_month_key = ""
    for col in sorted(by_col):
        col_days = sorted(by_col[col], key=lambda x: x.date)
        chosen_dt: Optional[datetime] = None
        for d in col_days:
            dt = datetime.strptime(d.date, "%Y-%m-%d")
            if dt.day <= 7:
                key = dt.strftime("%Y-%m")
                if key != last_month_key:
                    chosen_dt = dt
                    break
        if chosen_dt is None and col == 0:
            chosen_dt = datetime.strptime(col_days[0].date, "%Y-%m-%d")

        if chosen_dt is not None:
            key = chosen_dt.strftime("%Y-%m")
            if key != last_month_key:
                if labels and (col - labels[-1][0]) < 3:
                    if labels[-1][0] == 0:
                        labels.pop()
                    else:
                        continue
                labels.append((col, chosen_dt.strftime("%b")))
                last_month_key = key
    return labels


def render_svg(username: str, days: List[ContributionDay], total_header: Optional[int]) -> str:
    palette = build_monochrome_cyan_palette()
    max_col = max(d.col for d in days)
    num_cols = max_col + 1

    cell = 11.5
    gap = 3.0
    step = cell + gap

    margin_left = 36.0
    grid_y = 66.0
    grid_w = num_cols * step - gap
    grid_h = 7 * step - gap

    svg_w = int(math.ceil(margin_left + grid_w + 22))
    svg_h = 242

    active_days = sorted([d for d in days if d.count > 0], key=lambda d: d.date)
    total_commits = sum(d.count for d in days)
    if total_header is not None and total_header >= total_commits:
        total_commits = total_header

    start_date = min(d.date for d in days)
    end_date = max(d.date for d in days)
    start_lbl = datetime.strptime(start_date, "%Y-%m-%d").strftime("%b '%y").upper()
    end_lbl = datetime.strptime(end_date, "%Y-%m-%d").strftime("%b '%y").upper()

    n_active = len(active_days)
    cycle_s = round(max(10.0, min(20.0, 5.2 + n_active * 0.24)), 2)
    month_labels = compute_month_labels(days)

    css_keyframes: List[str] = []
    drop_span_start = 3.0
    drop_span_end = 60.0
    drop_dur_pct = 8.5

    stagger = (drop_span_end - drop_span_start - drop_dur_pct) / max(1, n_active - 1) if n_active > 1 else 0.0
    clear_span_start = 82.0
    clear_fade_dur = 5.5
    clear_stagger = (96.5 - clear_span_start - clear_fade_dur) / max(1, n_active - 1) if n_active > 1 else 0.0

    for idx, day in enumerate(active_days):
        t0 = drop_span_start + idx * stagger
        dy = -(day.row * step + 20.0)

        # Smooth cubic ease-out deceleration directly to translateY(0px) — zero bounce/overlap
        p1 = t0 + drop_dur_pct * 0.14
        p2 = t0 + drop_dur_pct * 0.42
        p3 = t0 + drop_dur_pct * 0.72
        t_land = t0 + drop_dur_pct

        dy1 = dy * ((1.0 - 0.14) ** 3)
        dy2 = dy * ((1.0 - 0.42) ** 3)
        dy3 = dy * ((1.0 - 0.72) ** 3)

        # Smooth ending wave dissolve back to the empty grid (stays locked at translateY(0))
        tc0 = clear_span_start + idx * clear_stagger
        tc_mid = tc0 + clear_fade_dur * 0.50
        tc1 = min(97.5, tc0 + clear_fade_dur)

        css_keyframes.append(
            f"""      @keyframes drop_{idx} {{
        0%, {t0:.2f}% {{ transform: translateY({dy:.1f}px); opacity: 0; }}
        {p1:.2f}% {{ transform: translateY({dy1:.1f}px); opacity: 1; }}
        {p2:.2f}% {{ transform: translateY({dy2:.1f}px); opacity: 1; }}
        {p3:.2f}% {{ transform: translateY({dy3:.1f}px); opacity: 1; }}
        {t_land:.2f}%, {tc0:.2f}% {{ transform: translateY(0px); opacity: 1; }}
        {tc_mid:.2f}% {{ transform: translateY(0px); opacity: 0.50; }}
        {tc1:.2f}%, 100% {{ transform: translateY(0px); opacity: 0; }}
      }}
      .b_{idx} {{ animation: drop_{idx} {cycle_s:.2f}s linear infinite; }}"""
        )

    # Pure flat 2D empty grid squares
    empty_slots_svg: List[str] = []
    for d in days:
        cx = margin_left + d.col * step
        cy = grid_y + d.row * step
        empty_slots_svg.append(
            f'    <rect x="{cx:.1f}" y="{cy:.1f}" width="{cell:.1f}" height="{cell:.1f}" rx="1.2" fill="#0C1322" stroke="#162238" stroke-width="0.8"/>'
        )

    # Pure flat 2D falling arcade blocks (no 3D bevels, no glow shadows)
    falling_bricks_svg: List[str] = []
    for idx, d in enumerate(active_days):
        t = tier_from_count(d.count)
        cx = margin_left + d.col * step
        cy = grid_y + d.row * step
        falling_bricks_svg.append(
            f'    <g class="b_{idx}">\n'
            f'      <title>{d.date}: {d.count} commit{"s" if d.count != 1 else ""}</title>\n'
            f'      <rect x="{cx:.1f}" y="{cy:.1f}" width="{cell:.1f}" height="{cell:.1f}" rx="1.2" fill="url(#tier{t}Grad)"/>\n'
            f'    </g>'
        )

    months_svg = [
        f'    <text x="{margin_left + col * step:.1f}" y="58" class="mono m-lbl">{lbl}</text>'
        for col, lbl in month_labels
    ]

    day_rows = [(1, "Mon"), (3, "Wed"), (5, "Fri")]
    days_lbl_svg = [
        f'    <text x="12" y="{grid_y + r * step + 8.5:.1f}" class="mono d-lbl">{name}</text>'
        for r, name in day_rows
    ]

    tier_defs = []
    for tier in range(1, 5):
        start_hex, end_hex = palette[tier]
        tier_defs.append(
            f"""    <linearGradient id="tier{tier}Grad" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="{start_hex}"/>
      <stop offset="100%" stop-color="{end_hex}"/>
    </linearGradient>"""
        )

    legend_x = 36
    legend_y = 204
    t4_hex = palette[4][0]
    t3_hex = palette[3][0]

    footer_note = f"REALTIME GITHUB COMMITS  ·  {start_lbl} – {end_lbl}  ·  2D BLOCKS FALL IN CHRONOLOGICAL ORDER"

    svg_doc = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" width="100%" role="img" aria-label="2D Arcade Block Contribution Calendar for {username}">
  <defs>
    <!-- Single dark slate background -->
    <linearGradient id="cabBg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#080E1A"/>
      <stop offset="100%" stop-color="{BG_HEX}"/>
    </linearGradient>

    <!-- Single-hue Electric Cyan top border accent -->
    <linearGradient id="cyanEdge" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{ACCENT_HEX}" stop-opacity="0.08"/>
      <stop offset="50%" stop-color="{ACCENT_HEX}" stop-opacity="0.60"/>
      <stop offset="100%" stop-color="{ACCENT_HEX}" stop-opacity="0.08"/>
    </linearGradient>

    <!-- Pure 2D single-hue saturation and phi-luminance gradients -->
{os.linesep.join(tier_defs)}

    <clipPath id="playfieldClip">
      <rect x="{margin_left - 2:.1f}" y="{grid_y - 12:.1f}" width="{grid_w + 4:.1f}" height="{grid_h + 16:.1f}"/>
    </clipPath>

    <style><![CDATA[
      .mono {{ font-family: 'Courier New', Consolas, monospace; }}
      .hud-title {{ font-size: 10.5px; font-weight: 700; fill: #F1F5F9; letter-spacing: 1.2px; }}
      .hud-chip  {{ font-size: 9.5px;  font-weight: 700; fill: {t4_hex}; letter-spacing: 0.8px; }}
      .hud-sub   {{ font-size: 8.5px;  fill: #7C93B0; letter-spacing: 0.6px; }}
      .m-lbl     {{ font-size: 8.5px;  fill: #94A3B8; }}
      .d-lbl     {{ font-size: 7.5px;  fill: #64748B; }}
      .leg-lbl   {{ font-size: 8.2px;  fill: #94A3B8; }}
      .foot-note {{ font-size: 8.0px;  fill: #64748B; letter-spacing: 0.7px; }}

      @keyframes livePulse {{
        0%, 100% {{ opacity: 1; }}
        50%      {{ opacity: 0.3; }}
      }}
      .live-ind {{ animation: livePulse 1.8s ease-in-out infinite; }}

{os.linesep.join(css_keyframes)}
    ]]></style>
  </defs>

  <!-- Single-tone Midnight Slate Frame (No orange, clean cyan edge) -->
  <rect x="0" y="0" width="{svg_w}" height="{svg_h}" rx="10" fill="url(#cabBg)"/>
  <rect x="0.75" y="0.75" width="{svg_w - 1.5}" height="{svg_h - 1.5}" rx="9.5" fill="none" stroke="#17253B" stroke-width="1.2"/>
  <rect x="1" y="1" width="{svg_w - 2}" height="2" rx="1" fill="url(#cyanEdge)"/>

  <!-- HUD Header -->
  <rect x="15" y="15" width="7" height="7" rx="1" fill="{t4_hex}" class="live-ind"/>
  <text x="29" y="21.5" class="mono hud-title">ARCADE CONTRIBUTION MATRIX // ABHIRAM B S</text>
  <text x="{svg_w - 16}" y="21.5" text-anchor="end" class="mono hud-chip">COMMITS: {total_commits}  ·  ACTIVE DAYS: {n_active}</text>

  <text x="16" y="36" class="mono hud-sub">EMPTY 2D GRID → CHRONOLOGICAL BLOCK DROP  ·  SINGLE-HUE φ-CONTRAST LUMINANCE</text>
  <text x="{svg_w - 16}" y="36" text-anchor="end" class="mono hud-sub">GRID: {num_cols} WKS × 7 DAYS</text>
  <line x1="14" y1="44" x2="{svg_w - 14}" y2="44" stroke="#17253B" stroke-width="1"/>

  <!-- Month Headers -->
  <g>
{os.linesep.join(months_svg)}
  </g>

  <!-- Weekday Labels -->
  <g>
{os.linesep.join(days_lbl_svg)}
  </g>

  <!-- Empty 2D Base Matrix -->
  <g id="empty-calendar-grid">
{os.linesep.join(empty_slots_svg)}
  </g>

  <!-- 2D Chronological Falling Commit Blocks -->
  <g id="commit-bricks" clip-path="url(#playfieldClip)">
{os.linesep.join(falling_bricks_svg)}
  </g>

  <!-- Footer Legend & Note -->
  <line x1="14" y1="184" x2="{svg_w - 14}" y2="184" stroke="#17253B" stroke-width="1"/>

  <g class="mono">
    <text x="{legend_x}" y="{legend_y}" class="leg-lbl">0</text>
    <rect x="{legend_x + 12}" y="{legend_y - 9}" width="11" height="11" rx="1.2" fill="#0C1322" stroke="#162238" stroke-width="0.9"/>

    <rect x="{legend_x + 34}" y="{legend_y - 9}" width="11" height="11" rx="1.2" fill="url(#tier1Grad)"/>
    <text x="{legend_x + 49}" y="{legend_y}" class="leg-lbl">1–2</text>

    <rect x="{legend_x + 76}" y="{legend_y - 9}" width="11" height="11" rx="1.2" fill="url(#tier2Grad)"/>
    <text x="{legend_x + 91}" y="{legend_y}" class="leg-lbl">3–5</text>

    <rect x="{legend_x + 118}" y="{legend_y - 9}" width="11" height="11" rx="1.2" fill="url(#tier3Grad)"/>
    <text x="{legend_x + 133}" y="{legend_y}" class="leg-lbl">6–10</text>

    <rect x="{legend_x + 166}" y="{legend_y - 9}" width="11" height="11" rx="1.2" fill="url(#tier4Grad)"/>
    <text x="{legend_x + 181}" y="{legend_y}" class="leg-lbl">11+</text>

    <text x="{svg_w - 16}" y="{legend_y}" text-anchor="end" class="leg-lbl">
      ORDER: OLDEST → LATEST  ·  TOTAL: <tspan fill="{t3_hex}" font-weight="700">{total_commits}</tspan>
    </text>

    <text x="{svg_w / 2:.1f}" y="227" text-anchor="middle" class="foot-note">{footer_note}</text>
  </g>
</svg>
"""
    return svg_doc


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate 2D single-hue golden-ratio arcade contribution calendar SVG.")
    parser.add_argument("--user", default="Abhi-ram-init", help="GitHub username")
    parser.add_argument("--out", default="assets/arcade-contributions.svg", help="Output SVG file path")
    args = parser.parse_args()

    raw_html = fetch_contributions_html(args.user)
    days, total_hdr = parse_contributions(raw_html)
    svg_text = render_svg(args.user, days, total_hdr)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(svg_text, encoding="utf-8", newline="\n")

    active_count = sum(1 for d in days if d.count > 0)
    total = total_hdr if total_hdr is not None else sum(d.count for d in days)
    print(f"Generated {out_path}: {len(days)} calendar days, {active_count} active days, {total} total contributions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
