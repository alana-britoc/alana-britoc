import json
import os
import random
import sys
import urllib.request
from datetime import datetime

API_URL = "https://github-contributions-api.jogruber.de/v4/{user}?y=last"

FLOWER_EMOJIS = [
    "🌸", "🌷", "🌻", "🌺", "🌹",
    "🏵️", "🌼", "💐", "🪷", "🪻"
]

EMPTY_COLOR = "#161b22"

BG_COLOR = "#0d1117"
TEXT_COLOR = "#7d8590"

CELL = 10
GAP = 3
RADIUS = 2
PAD_LEFT = 26
PAD_TOP = 18

MONTH_ABBR = [
    "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
    "Jul", "Ago", "Set", "Out", "Nov", "Dez"
]


def fetch_contributions(username: str):
    url = API_URL.format(user=username)

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "commit-flower-garden"}
    )

    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode())

    return data["contributions"]


def build_weeks(contributions):
    if not contributions:
        return []

    first_date = datetime.strptime(
        contributions[0]["date"],
        "%Y-%m-%d"
    )

    lead_empty = (first_date.weekday() + 1) % 7

    days = [None] * lead_empty + contributions

    return [
        days[i:i + 7]
        for i in range(0, len(days), 7)
    ]


def month_labels_for(weeks):
    labels = {}

    last_month = None
    last_col_used = -999

    for col, week in enumerate(weeks):

        first_day = next(
            (d for d in week if d is not None),
            None
        )

        if first_day is None:
            continue

        month = datetime.strptime(
            first_day["date"],
            "%Y-%m-%d"
        ).month

        if month != last_month and (col - last_col_used) >= 2:
            labels[col] = MONTH_ABBR[month - 1]

            last_month = month
            last_col_used = col

    return labels


def pick_flower(date_str):
    return random.Random(date_str).choice(FLOWER_EMOJIS)


def build_svg(weeks, username):

    cols = len(weeks)

    width = PAD_LEFT + cols * (CELL + GAP)
    height = PAD_TOP + 7 * (CELL + GAP) + 6

    BLOOM = 1.5
    RESET = 1.0
    STEP = 1.8

    commit_days = [
        day
        for week in weeks
        for day in week
        if day is not None and day.get("level", 0) > 0
    ]

    flower_count = len(commit_days)

    if flower_count > 0:
        max_delay = (flower_count - 1) * STEP
    else:
        max_delay = 0

    DURATION = round(max_delay + BLOOM + RESET, 3)

    hold_end_pct = ((DURATION - RESET) / DURATION) * 100

    months = month_labels_for(weeks)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" '
        f'height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        f'font-family="-apple-system,\'Segoe UI\',Roboto,Helvetica,Arial,sans-serif">'
    ]

    flower_keyframes = []

    parts.append(
        f'<rect width="{width}" height="{height}" fill="{BG_COLOR}"/>'
    )

    for col, label in months.items():
        x = PAD_LEFT + col * (CELL + GAP)
        parts.append(
            f'<text '
            f'x="{x}" '
            f'y="12" '
            f'font-size="9" '
            f'fill="{TEXT_COLOR}">'
            f'{label}'
            f'</text>'
        )

    day_labels = ["", "Seg", "", "Qua", "", "Sex", ""]

    for row, label in enumerate(day_labels):
        if label:
            y = PAD_TOP + row * (CELL + GAP) + CELL - 2
            parts.append(
                f'<text '
                f'x="0" '
                f'y="{y}" '
                f'font-size="9" '
                f'fill="{TEXT_COLOR}">'
                f'{label}'
                f'</text>'
            )

    body_parts = []
    flower_index = 0

    for col, week in enumerate(weeks):
        x = PAD_LEFT + col * (CELL + GAP)

        for row, day in enumerate(week):
            y = PAD_TOP + row * (CELL + GAP)

            if day is None:
                continue

            level = day.get("level", 0)

            body_parts.append(
                f'<rect '
                f'x="{x}" '
                f'y="{y}" '
                f'width="{CELL}" '
                f'height="{CELL}" '
                f'rx="{RADIUS}" '
                f'ry="{RADIUS}" '
                f'fill="{EMPTY_COLOR}"/>'
            )

            if level > 0:

                emoji = pick_flower(day["date"])
                cx = x + CELL / 2
                cy = y + CELL / 2

                anim_name = f"bloom{flower_index}"

                start_pct = round((flower_index * STEP) / DURATION * 100, 3)
                grow_end_pct = round(
                    (flower_index * STEP + BLOOM) / DURATION * 100, 3
                )
                grow_end_pct = min(grow_end_pct, hold_end_pct)

                flower_keyframes.append(
                    f'''
                    @keyframes {anim_name} {{
                        0% {{ opacity: 0; transform: scale(0.2); }}
                        {start_pct}% {{ opacity: 0; transform: scale(0.2); }}
                        {grow_end_pct}% {{ opacity: 1; transform: scale(1); }}
                        {hold_end_pct:.3f}% {{ opacity: 1; transform: scale(1); }}
                        100% {{ opacity: 0; transform: scale(0.2); }}
                    }}
                    '''
                )

                body_parts.append(
                    f'<text '
                    f'style="'
                    f'transform-box:fill-box;'
                    f'transform-origin:center;'
                    f'animation:{anim_name} {DURATION}s ease-in-out infinite;" '
                    f'x="{cx}" '
                    f'y="{cy}" '
                    f'font-size="{CELL}" '
                    f'text-anchor="middle" '
                    f'dominant-baseline="central">'
                    f'{emoji}'
                    f'</text>'
                )

                flower_index += 1

    parts.append(f'<style>{"".join(flower_keyframes)}</style>')
    parts.extend(body_parts)
    parts.append("</svg>")

    return "".join(parts)


def main():

    username = (
        os.environ.get("GITHUB_USERNAME")
        or (sys.argv[1] if len(sys.argv) > 1 else None)
    )

    if not username:
        print(
            "Defina a variável de ambiente "
            "GITHUB_USERNAME ou passe o usuário "
            "como argumento."
        )
        sys.exit(1)

    contributions = fetch_contributions(username)
    weeks = build_weeks(contributions)
    svg = build_svg(weeks, username)

    os.makedirs("assets", exist_ok=True)

    with open("assets/flower-garden.svg", "w", encoding="utf-8") as f:
        f.write(svg)

    print(
        f"Jardim de flores gerado para "
        f"{username} em assets/flower-garden.svg"
    )


if __name__ == "__main__":
    main()