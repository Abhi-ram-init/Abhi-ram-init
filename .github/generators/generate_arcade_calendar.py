#!/usr/bin/env python3
"""Generate an animated retro arcade falling-block SVG from live GitHub contributions.

- Fetches real public contribution cells from https://github.com/users/<user>/contributions
  (matching GitHub's exact 53x7 matrix: week column, day row, date, level, commit count).
- Starts with an empty matrix (all recessed grid slots empty), then drops each active
  commit day one-by-one in strict chronological order into its exact calendar coordinate.
- Computes RGB brick colours mathematically using the Golden Angle (-137.508 deg) and
  Golden Ratio (phi = 1.618) WCAG luminance contrast progression on a dark cabinet canvas.
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
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple


PHI = (1.0 + math.sqrt(5.0)) / 2.0
GOLDEN_ANGLE = 360.0 * (1.0 - 1.0 / PHI)  # ~137.50776 deg
BG_HEX = "#070B12"
BG_RGB = (7, 11, 18)


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


def _solve_rgb_for_contrast(hue_deg: float, target_contrast: float, bg_rgb: Tuple[int, int, int], sat: float = 0.96) -> Tuple[int, int, int]:
    """Find vivid RGB at hue_deg whose relative luminance meets target_contrast against bg_rgb."""
    bg_l = _rel_luminance(*bg_rgb)
    target_l = target_contrast * (bg_l + 0.05) - 0.05
    lo, hi = 0.18, 0.92
    best = (0, 0, 0)
    for _ in range(36):
        mid = 0.5 * (lo + hi)
        rgb = tuple(int(round(c * 255)) for c in colorsys.hls_to_rgb((hue_deg % 360.0) / 360.0, mid, sat))
        if _rel_luminance(*rgb) < target_l:
            lo = mid
        else:
            hi = mid
        best = rgb  # type: ignore[assignment]
    return best


def _brighten_bevel(rgb: Tuple[int, int, int], factor: float = 0.45) -> str:
    r, g, b = (min(255, int(round(c + (255 - c) * factor))) for c in rgb)
    return f"#{r:02X}{g:02X}{b:02X}"


def build_golden_ratio_palette() -> Dict[int, Tuple[str, str]]:
    """Build 4 RGB commit-density tiers via Golden Angle hues & phi-scaled contrast."""
    # Start near pure Green (115 deg) with reverse golden angle:
    # Tier 1: Green, Tier 2: Neon Crimson-Red, Tier 3: Electric Cyan-Blue, Tier 4: Arcade Gold
    base_hue = 115.0
    base_contrast = 3.25
    palette: Dict[int, Tuple[str, str]] = {}
    for tier in range(1, 5):
        hue = (base_hue - (tier - 1) * GOLDEN_ANGLE) % 360.0
        target_cr = base_contrast * (PHI ** (tier - 1))
        rgb = _solve_rgb_for_contrast(hue, target_cr, BG_RGB, sat=0.96)
        fill_hex = f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
        bevel_hex = _brighten_bevel(rgb, 0.42)
        palette[tier] = (fill_hex, bevel_hex)
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

    # Match <td ... data-date="YYYY-MM-DD" id="contribution-day-component-R-C" data-level="L" ...></td>
    # followed closely by <tool-tip ...>TEXT</tool-tip>
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
            # Fallback if tooltip text format ever changes
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
                # If col 0 partial month would collide with month starting at col 1 or 2, replace col 0 edge label
                if labels and (col - labels[-1][0]) < 3:
                    if labels[-1][0] == 0:
                        labels.pop()
                    else:
                        continue
                labels.append((col, chosen_dt.strftime("%b")))
                last_month_key = key
    return labels


def render_svg(username: str, days: List[ContributionDay], total_header: Optional[int]) -> str:
    palette = build_golden_ratio_palette()
    max_col = max(d.col for d in days)
    num_cols = max_col + 1

    cell = 11.5
    gap = 3.0
    step = cell + gap  # 14.5 px per week column

    margin_left = 36.0
    grid_y = 66.0
    grid_w = num_cols * step - gap
    grid_h = 7 * step - gap  # ~98.5 px

    svg_w = int(math.ceil(margin_left + grid_w + 22))  # ~825 -> clean ~825..840px
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

    # CSS keyframes for chronological brick drops starting from an EMPTY calendar
    # Timeline in % of cycle_s:
    #   0% .. 3%   -> Calendar completely EMPTY (all bricks opacity: 0 above chute)
    #   3% .. 64%  -> Bricks drop sequentially in chronological order (oldest -> latest)
    #   64% .. 92% -> Complete real contribution calendar stays seated & visible
    #   92% .. 97% -> Clean arcade board reset fade back to empty
    #   97% .. 100%-> Empty baseline before next loop
    css_keyframes: List[str] = []
    drop_span_start = 3.0
    drop_span_end = 62.0
    drop_dur_pct = 8.5  # single brick fall duration as % of total loop

    if n_active > 0:
        stagger = (drop_span_end - drop_span_start - drop_dur_pct) / max(1, n_active - 1) if n_active > 1 else 0.0
    else:
        stagger = 0.0

    for idx, day in enumerate(active_days):
        t0 = drop_span_start + idx * stagger
        t_enter = t0 + 0.5
        t_land = min(drop_span_end + drop_dur_pct, t0 + drop_dur_pct)
        t_bounce = min(90.0, t_land + 1.1)
        t_settle = min(91.5, t_bounce + 1.0)
        # Drop from right under the top chute line above row 0 down into target row
        dy = -(day.row * step + 22.0)
        css_keyframes.append(
            f"""      @keyframes drop_{idx} {{
        0%, {t0:.2f}% {{ transform: translateY({dy:.1f}px); opacity: 0; }}
        {t_enter:.2f}% {{ opacity: 1; }}
        {t_land:.2f}% {{ transform: translateY(0px); opacity: 1; }}
        {t_bounce:.2f}% {{ transform: translateY(-2.5px); opacity: 1; }}
        {t_settle:.2f}%, 91.50% {{ transform: translateY(0px); opacity: 1; }}
        96.50%, 100% {{ transform: translateY(0px); opacity: 0; }}
      }}
      .b_{idx} {{ animation: drop_{idx} {cycle_s:.2f}s cubic-bezier(0.22, 0.85, 0.35, 1) infinite; }}"""
        )

    # Active chute scanning tracer bar tracking roughly above active chronological waves
    empty_slots_svg: List[str] = []
    for d in days:
        cx = margin_left + d.col * step
        cy = grid_y + d.row * step
        empty_slots_svg.append(
            f'    <rect x="{cx:.1f}" y="{cy:.1f}" width="{cell:.1f}" height="{cell:.1f}" rx="2.2" fill="#0F172A" stroke="#1E293B" stroke-width="0.8"/>'
        )

    falling_bricks_svg: List[str] = []
    for idx, d in enumerate(active_days):
        t = tier_from_count(d.count)
        fill_hex, bevel_hex = palette[t]
        cx = margin_left + d.col * step
        cy = grid_y + d.row * step
        glow_attr = ' filter="url(#brickGlow)"' if t >= 3 else ""
        # Each brick is a mini 3D arcade brick (main block + bright top edge bevel)
        falling_bricks_svg.append(
            f'    <g class="b_{idx}"{glow_attr}>\n'
            f'      <title>{d.date}: {d.count} commit{"s" if d.count != 1 else ""}</title>\n'
            f'      <rect x="{cx:.1f}" y="{cy:.1f}" width="{cell:.1f}" height="{cell:.1f}" rx="2.2" fill="{fill_hex}"/>\n'
            f'      <rect x="{cx + 1.2:.1f}" y="{cy + 1.0:.1f}" width="{cell - 2.4:.1f}" height="2.2" rx="1" fill="{bevel_hex}" opacity="0.85"/>\n'
            f'    </g>'
        )

    months_svg = [
        f'    <text x="{margin_left + col * step:.1f}" y="58" class="mono m-lbl">{lbl}</text>'
        for col, lbl in month_labels
    ]

    # Day labels on Sun/Mon/Wed/Fri rows matching GitHub calendar orientation (Row 0 = Sun .. Row 6 = Sat)
    day_rows = [(1, "Mon"), (3, "Wed"), (5, "Fri")]
    days_lbl_svg = [
        f'    <text x="12" y="{grid_y + r * step + 8.5:.1f}" class="mono d-lbl">{name}</text>'
        for r, name in day_rows
    ]

    # Legend swatches from golden-ratio palette
    legend_x = 36
    legend_y = 204
    c1, b1 = palette[1]
    c2, b2 = palette[2]
    c3, b3 = palette[3]
    c4, b4 = palette[4]

    footer_note = f"REALTIME GITHUB COMMITS  ·  {start_lbl} – {end_lbl}  ·  BLOCKS FALL CHRONOLOGICALLY  ·  RGB φ-CONTRAST"

    svg_doc = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" width="100%" role="img" aria-label="Retro Arcade Block Contribution Calendar for {username}">
  <defs>
    <linearGradient id="cabBg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#090E18"/>
      <stop offset="100%" stop-color="{BG_HEX}"/>
    </linearGradient>

    <linearGradient id="cabBorder" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{c1}"/>
      <stop offset="33%" stop-color="{c2}"/>
      <stop offset="66%" stop-color="{c3}"/>
      <stop offset="100%" stop-color="{c4}"/>
    </linearGradient>

    <filter id="brickGlow" x="-35%" y="-35%" width="170%" height="170%">
      <feGaussianBlur stdDeviation="1.8" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>

    <!-- Clip falling bricks neatly to calendar playfield below month header -->
    <clipPath id="playfieldClip">
      <rect x="{margin_left - 2:.1f}" y="{grid_y - 12:.1f}" width="{grid_w + 4:.1f}" height="{grid_h + 16:.1f}"/>
    </clipPath>

    <style><![CDATA[
      .mono {{ font-family: 'Courier New', Consolas, monospace; }}
      .hud-title {{ font-size: 10.5px; font-weight: 700; fill: #F8D905; letter-spacing: 1.2px; }}
      .hud-chip  {{ font-size: 9.5px;  font-weight: 700; fill: {c3}; letter-spacing: 0.8px; }}
      .hud-sub   {{ font-size: 8.5px;  fill: #94A3B8; letter-spacing: 0.6px; }}
      .m-lbl     {{ font-size: 8.5px;  fill: #94A3B8; }}
      .d-lbl     {{ font-size: 7.5px;  fill: #64748B; }}
      .leg-lbl   {{ font-size: 8.2px;  fill: #94A3B8; }}
      .foot-note {{ font-size: 8.0px;  fill: #64748B; letter-spacing: 0.7px; }}

      @keyframes livePulse {{
        0%, 100% {{ opacity: 1; }}
        50%      {{ opacity: 0.35; }}
      }}
      .live-ind {{ animation: livePulse 1.8s ease-in-out infinite; }}

{os.linesep.join(css_keyframes)}
    ]]></style>
  </defs>

  <!-- Arcade Cabinet Frame -->
  <rect x="0" y="0" width="{svg_w}" height="{svg_h}" rx="10" fill="url(#cabBg)"/>
  <rect x="1" y="1" width="{svg_w - 2}" height="{svg_h - 2}" rx="9.2" fill="none" stroke="url(#cabBorder)" stroke-width="1.5" stroke-opacity="0.75"/>

  <!-- Subtle Arcade Screen Scanlines -->
  <g stroke="#FFFFFF" stroke-opacity="0.022" stroke-width="1">
    <line x1="8" y1="48"  x2="{svg_w - 8}" y2="48"/>
    <line x1="8" y1="74"  x2="{svg_w - 8}" y2="74"/>
    <line x1="8" y1="100" x2="{svg_w - 8}" y2="100"/>
    <line x1="8" y1="126" x2="{svg_w - 8}" y2="126"/>
    <line x1="8" y1="152" x2="{svg_w - 8}" y2="152"/>
    <line x1="8" y1="178" x2="{svg_w - 8}" y2="178"/>
  </g>

  <!-- HUD Scoreboard Top Strip -->
  <circle cx="18" cy="18" r="3.5" fill="{c1}" class="live-ind"/>
  <text x="27" y="21.5" class="mono hud-title">ARCADE CONTRIBUTION MATRIX // {username}</text>
  <text x="{svg_w - 16}" y="21.5" text-anchor="end" class="mono hud-chip">COMMITS: {total_commits}  ·  ACTIVE DAYS: {n_active}</text>

  <text x="16" y="36" class="mono hud-sub">EMPTY GRID → CHRONOLOGICAL BRICK DROP  ·  GOLDEN-RATIO RGB INTENSITY (φ ≈ 1.618)</text>
  <text x="{svg_w - 16}" y="36" text-anchor="end" class="mono hud-sub">GRID: {num_cols} WKS × 7 DAYS</text>
  <line x1="14" y1="44" x2="{svg_w - 14}" y2="44" stroke="#1E293B" stroke-width="1"/>

  <!-- Month Headers -->
  <g>
{os.linesep.join(months_svg)}
  </g>

  <!-- Weekday Labels -->
  <g>
{os.linesep.join(days_lbl_svg)}
  </g>

  <!-- Empty Contribution Calendar Base Grid (always visible cleanly beneath falling blocks) -->
  <g id="empty-calendar-grid">
{os.linesep.join(empty_slots_svg)}
  </g>

  <!-- Falling & Locking Real Commit Bricks (sorted oldest -> newest) -->
  <g id="commit-bricks" clip-path="url(#playfieldClip)">
{os.linesep.join(falling_bricks_svg)}
  </g>

  <!-- Footer Divider & Dynamic Legend / Real-Data Note -->
  <line x1="14" y1="184" x2="{svg_w - 14}" y2="184" stroke="#1E293B" stroke-width="1"/>

  <g class="mono">
    <!-- RGB Commit Density Legend -->
    <text x="{legend_x}" y="{legend_y}" class="leg-lbl">0</text>
    <rect x="{legend_x + 12}" y="{legend_y - 9}" width="11" height="11" rx="2.2" fill="#0F172A" stroke="#1E293B" stroke-width="0.9"/>

    <rect x="{legend_x + 34}" y="{legend_y - 9}" width="11" height="11" rx="2.2" fill="{c1}"/>
    <rect x="{legend_x + 35}" y="{legend_y - 8}" width="9"  height="2"  rx="1"   fill="{b1}"/>
    <text x="{legend_x + 49}" y="{legend_y}" class="leg-lbl">1–2</text>

    <rect x="{legend_x + 76}" y="{legend_y - 9}" width="11" height="11" rx="2.2" fill="{c2}"/>
    <rect x="{legend_x + 77}" y="{legend_y - 8}" width="9"  height="2"  rx="1"   fill="{b2}"/>
    <text x="{legend_x + 91}" y="{legend_y}" class="leg-lbl">3–5</text>

    <rect x="{legend_x + 118}" y="{legend_y - 9}" width="11" height="11" rx="2.2" fill="{c3}"/>
    <rect x="{legend_x + 119}" y="{legend_y - 8}" width="9"  height="2"  rx="1"   fill="{b3}"/>
    <text x="{legend_x + 133}" y="{legend_y}" class="leg-lbl">6–10</text>

    <rect x="{legend_x + 166}" y="{legend_y - 9}" width="11" height="11" rx="2.2" fill="{c4}"/>
    <rect x="{legend_x + 167}" y="{legend_y - 8}" width="9"  height="2"  rx="1"   fill="{b4}"/>
    <text x="{legend_x + 181}" y="{legend_y}" class="leg-lbl">11+</text>

    <!-- Right side: Live stats -->
    <text x="{svg_w - 16}" y="{legend_y}" text-anchor="end" class="leg-lbl" fill="#E2E8F0">
      SEQUENCE: OLDEST → LATEST  ·  TOTAL: <tspan fill="{c4}" font-weight="700">{total_commits}</tspan>
    </text>

    <!-- Bottom Real-Time Note -->
    <text x="{svg_w / 2:.1f}" y="227" text-anchor="middle" class="foot-note">{footer_note}</text>
  </g>
</svg>
"""
    return svg_doc


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate retro arcade block contribution calendar SVG.")
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
