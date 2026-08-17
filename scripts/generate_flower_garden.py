import json
import os
import sys
import urllib.request
from datetime import datetime

API_URL = "https://github-contributions-api.jogruber.de/v4/{user}?y=last"

LEVEL_EMOJI = {
    0: None,
    1: "🪻",
    2: "🌼",
    3: "🌷",
    4: "🌸",
}

LEVEL_COLOR = {
    0: "#161b22",
    1: "#0e4429",
    2: "#006d32",
    3: "#26a641",
    4: "#39d353",
}

BG_COLOR = "#0d1117"
TEXT_COLOR = "#7d8590"

CELL = 10
GAP = 3
RADIUS = 2
PAD_LEFT = 26
PAD_TOP = 18

MONTH_ABBR = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
              "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def fetch_contributions(username: str):
    url = API_URL.format(user=username)
    req = urllib.request.Request(url, headers={"User-Agent": "commit-flower-garden"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode())
    return data["contributions"]


def build_weeks(contributions):
    if not contributions:
        return []
    first_date = datetime.strptime(contributions[0]["date"], "%Y-%m-%d")
    lead_empty = (first_date.weekday() + 1) % 7
    days = [None] * lead_empty + contributions
    return [days[i:i + 7] for i in range(0, len(days), 7)]


def month_labels_for(weeks):
    labels = {}
    last_month = None
    last_col_used = -999
    for col, week in enumerate(weeks):
        first_day = next((d for d in week if d is not None), None)
        if first_day is None:
            continue
        month = datetime.strptime(first_day["date"], "%Y-%m-%d").month
        if month != last_month and (col - last_col_used) >= 3:
            labels[col] = MONTH_ABBR[month - 1]
            last_month = month
            last_col_used = col
    return labels


def build_svg(weeks, username):
    cols = len(weeks)
    width = PAD_LEFT + cols * (CELL + GAP)
    height = PAD_TOP + 7 * (CELL + GAP) + 6

    STEP = 0.5
    BLOOM = 1.5
    HOLD = 6.0
    RESET = 3.0

    max_delay = (cols - 1) * STEP if cols > 1 else 0
    DURATION = round(max_delay + BLOOM + HOLD + RESET, 3)

    bloom_pct = round((BLOOM / DURATION) * 100, 3)
    reset_start_pct = round(((DURATION - RESET) / DURATION) * 100, 3)

    months = month_labels_for(weeks)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        f'font-family="-apple-system,\'Segoe UI\',Roboto,Helvetica,Arial,sans-serif">'
    ]

    parts.append(f'''
    <style>
      .flower {{
        opacity: 0;
        animation-name: appear;
        animation-duration: {DURATION}s;
        animation-timing-function: ease-in-out;
        animation-iteration-count: infinite;
      }}
      @keyframes appear {{
        0% {{ opacity: 0; }}
        {bloom_pct}% {{ opacity: 1; }}
        {reset_start_pct}% {{ opacity: 1; }}
        100% {{ opacity: 0; }}
      }}
    </style>
    <rect width="{width}" height="{height}" fill="{BG_COLOR}"/>
    ''')

    for col, label in months.items():
        x = PAD_LEFT + col * (CELL + GAP)
        parts.append(f'<text x="{x}" y="12" font-size="9" fill="{TEXT_COLOR}">{label}</text>')

    day_labels = ["", "Seg", "", "Qua", "", "Sex", ""]
    for row, label in enumerate(day_labels):
        if label:
            y = PAD_TOP + row * (CELL + GAP) + CELL - 2
            parts.append(f'<text x="0" y="{y}" font-size="9" fill="{TEXT_COLOR}">{label}</text>')

    for col, week in enumerate(weeks):
        x = PAD_LEFT + col * (CELL + GAP)
        delay = round(col * STEP, 3)
        for row, day in enumerate(week):
            y = PAD_TOP + row * (CELL + GAP)
            if day is None:
                continue
            level = day.get("level", 0)
            color = LEVEL_COLOR.get(level, LEVEL_COLOR[0])

            parts.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                f'rx="{RADIUS}" ry="{RADIUS}" fill="{color}"/>'
            )

            emoji = LEVEL_EMOJI.get(level)
            if emoji:
                cx, cy = x + CELL / 2, y + CELL / 2
                parts.append(
                    f'<text class="flower" style="animation-delay:{delay}s" '
                    f'x="{cx}" y="{cy}" font-size="{CELL}" '
                    f'text-anchor="middle" dominant-baseline="central">{emoji}</text>'
                )

    parts.append("</svg>")
    return "".join(parts)


def main():
    username = os.environ.get("GITHUB_USERNAME") or (sys.argv[1] if len(sys.argv) > 1 else None)
    if not username:
        print("Defina a variável de ambiente GITHUB_USERNAME ou passe o usuário como argumento.")
        sys.exit(1)

    contributions = fetch_contributions(username)
    weeks = build_weeks(contributions)
    svg = build_svg(weeks, username)

    os.makedirs("assets", exist_ok=True)
    with open("assets/flower-garden.svg", "w", encoding="utf-8") as f:
        f.write(svg)

    print(f"Jardim de flores gerado para {username} em assets/flower-garden.svg")


if __name__ == "__main__":
    main()