
import json
import os
import sys
import urllib.request
from datetime import datetime

API_URL = "https://github-contributions-api.jogruber.de/v4/{user}?y=last"

LEVEL_EMOJI = {
    0: None,   # sem commit -> só um pontinho de terra
    1: "🌱",
    2: "🌿",
    3: "🌷",
    4: "🌸",
}

CELL = 15
GAP = 3
PAD_LEFT = 30
PAD_TOP = 32


def fetch_contributions(username: str):
    url = API_URL.format(user=username)
    req = urllib.request.Request(url, headers={"User-Agent": "commit-flower-garden"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode())
    return data["contributions"]


def build_weeks(contributions):
    """Agrupa os dias (lista ordenada) em semanas de 7 dias (dom-sáb),
    preenchendo o início com None para alinhar com o dia da semana certo."""
    if not contributions:
        return []
    first_date = datetime.strptime(contributions[0]["date"], "%Y-%m-%d")
    lead_empty = (first_date.weekday() + 1) % 7  # 0 = domingo
    days = [None] * lead_empty + contributions
    return [days[i:i + 7] for i in range(0, len(days), 7)]


def build_svg(weeks, username):
    cols = len(weeks)
    width = PAD_LEFT + cols * (CELL + GAP)
    height = PAD_TOP + 7 * (CELL + GAP) + 10

    STEP = 0.08
    FADE_IN = 0.35  

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        f'font-family="-apple-system,\'Segoe UI\',Roboto,Helvetica,Arial,sans-serif">'
    ]

    parts.append(f'''
    <defs>
      <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#f6fff4"/>
        <stop offset="100%" stop-color="#eafbe6"/>
      </linearGradient>
      <style>
        .cell {{
          opacity: 0;
          animation-name: appear;
          animation-duration: {FADE_IN}s;
          animation-timing-function: ease-out;
          animation-iteration-count: 1;
          animation-fill-mode: forwards;
        }}
        @keyframes appear {{
          from {{ opacity: 0; }}
          to   {{ opacity: 1; }}
        }}
      </style>
    </defs>
    <rect width="{width}" height="{height}" rx="12" fill="url(#bg)"/>
    <text x="{PAD_LEFT}" y="20" font-size="13" fill="#2f4f2f" font-weight="bold">
      🌼 {username} — jardim de contribuições
    </text>
    ''')

    day_labels = ["", "Seg", "", "Qua", "", "Sex", ""]
    for row, label in enumerate(day_labels):
        if label:
            y = PAD_TOP + row * (CELL + GAP) + CELL - 3
            parts.append(f'<text x="4" y="{y}" font-size="9" fill="#7a7a7a">{label}</text>')

    for col, week in enumerate(weeks):
        x = PAD_LEFT + col * (CELL + GAP)
        delay = round(col * STEP, 3)  # aparece da esquerda pra direita, uma vez só
        style = f'style="animation-delay:{delay}s"'
        for row, day in enumerate(week):
            y = PAD_TOP + row * (CELL + GAP)
            if day is None:
                continue
            level = day.get("level", 0)
            emoji = LEVEL_EMOJI.get(level)
            cx, cy = x + CELL / 2, y + CELL / 2

            if emoji is None:
                parts.append(
                    f'<circle class="cell" {style} cx="{cx}" cy="{cy}" r="2.3" fill="#d9d0c3"/>'
                )
            else:
                size = 10 + level * 2  # flores maiores em dias mais cheios de commits
                parts.append(
                    f'<text class="cell" {style} x="{cx}" y="{cy}" font-size="{size}" '
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