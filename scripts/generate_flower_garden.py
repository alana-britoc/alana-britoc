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

        if month != last_month and (col - last_col_used) >= 3:
            labels[col] = MONTH_ABBR[month - 1]

            last_month = month
            last_col_used = col

    return labels


def pick_flower(date_str, commit_index):
    """
    Escolhe uma flor de forma determinística.

    O índice do commit também participa da escolha,
    para que vários commits possam gerar flores diferentes.
    """

    seed = f"{date_str}-{commit_index}"

    return random.Random(seed).choice(FLOWER_EMOJIS)


def count_total_commits(contributions):
    """
    Soma todos os commits do período.
    """

    return sum(
        day.get("count", 0)
        for day in contributions
    )


def build_svg(weeks, username):

    cols = len(weeks)

    width = PAD_LEFT + cols * (CELL + GAP)

    height = PAD_TOP + 7 * (CELL + GAP) + 6

    # =========================================================
    # CONFIGURAÇÃO DA ANIMAÇÃO
    # =========================================================

    # Quanto tempo uma flor leva para aparecer.
    BLOOM = 1.5

    # Quanto tempo ela permanece completamente visível.
    HOLD = 1.0

    # Quanto tempo leva para desaparecer.
    RESET = 1.0

    # Intervalo entre uma flor e outra.
    #
    # É maior que BLOOM, portanto:
    #
    # Flor 1 termina de aparecer
    # ↓
    # pequena pausa
    # ↓
    # Flor 2 começa
    STEP = 1.8

    # =========================================================
    # CONTA OS COMMITS
    # =========================================================

    all_days = [
        day
        for week in weeks
        for day in week
        if day is not None
    ]

    total_commits = count_total_commits(all_days)

    # =========================================================
    # DURAÇÃO TOTAL
    # =========================================================

    if total_commits > 0:

        max_delay = (
            (total_commits - 1) * STEP
        )

        DURATION = (
            max_delay
            + BLOOM
            + HOLD
            + RESET
        )

    else:

        DURATION = BLOOM + HOLD + RESET

    DURATION = round(DURATION, 3)

    months = month_labels_for(weeks)

    # =========================================================
    # SVG
    # =========================================================

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" '
        f'height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        f'font-family="-apple-system,\'Segoe UI\',Roboto,Helvetica,Arial,sans-serif">'
    ]

    # =========================================================
    # FUNDO
    # =========================================================

    parts.append(
        f'''
        <rect
            width="{width}"
            height="{height}"
            fill="{BG_COLOR}"
        />
        '''
    )

    # =========================================================
    # MESES
    # =========================================================

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

    # =========================================================
    # DIAS DA SEMANA
    # =========================================================

    day_labels = [
        "",
        "Seg",
        "",
        "Qua",
        "",
        "Sex",
        ""
    ]

    for row, label in enumerate(day_labels):

        if label:

            y = (
                PAD_TOP
                + row * (CELL + GAP)
                + CELL
                - 2
            )

            parts.append(
                f'<text '
                f'x="0" '
                f'y="{y}" '
                f'font-size="9" '
                f'fill="{TEXT_COLOR}">'
                f'{label}'
                f'</text>'
            )

    # =========================================================
    # FLORES
    # =========================================================

    commit_index = 0

    for col, week in enumerate(weeks):

        x = PAD_LEFT + col * (CELL + GAP)

        for row, day in enumerate(week):

            y = PAD_TOP + row * (CELL + GAP)

            if day is None:
                continue

            # -------------------------------------------------
            # QUADRADO DE FUNDO
            # -------------------------------------------------

            parts.append(
                f'<rect '
                f'x="{x}" '
                f'y="{y}" '
                f'width="{CELL}" '
                f'height="{CELL}" '
                f'rx="{RADIUS}" '
                f'ry="{RADIUS}" '
                f'fill="{EMPTY_COLOR}"/>'
            )

            # -------------------------------------------------
            # QUANTIDADE DE COMMITS NESSE DIA
            # -------------------------------------------------

            count = day.get("count", 0)

            if count <= 0:
                continue

            cx = x + CELL / 2
            cy = y + CELL / 2

            # -------------------------------------------------
            # UMA FLOR PARA CADA COMMIT
            # -------------------------------------------------

            for commit_number in range(count):

                emoji = pick_flower(
                    day["date"],
                    commit_number
                )

                # Delay baseado no COMMIT,
                # e não na semana.
                delay = round(
                    commit_index * STEP,
                    3
                )

                # -------------------------------------------------
                # CADA FLOR TEM SUA PRÓPRIA ANIMAÇÃO
                # -------------------------------------------------

                parts.append(
                    f'''
                    <text
                        x="{cx}"
                        y="{cy}"
                        font-size="{CELL}"
                        text-anchor="middle"
                        dominant-baseline="central"
                        opacity="0"
                        style="
                            animation-name: bloom;
                            animation-duration: {DURATION}s;
                            animation-delay: {delay}s;
                            animation-timing-function: ease-in-out;
                            animation-iteration-count: infinite;
                            animation-fill-mode: both;
                        "
                    >{emoji}</text>
                    '''
                )

                commit_index += 1

    # =========================================================
    # ANIMAÇÃO
    # =========================================================

    bloom_pct = (
        BLOOM / DURATION
    ) * 100

    hold_start_pct = (
        (BLOOM + HOLD) / DURATION
    ) * 100

    reset_start_pct = (
        (BLOOM + HOLD) / DURATION
    ) * 100

    parts.insert(
        1,
        f'''
        <style>

            /*
             * Cada flor possui a MESMA animação,
             * mas um animation-delay diferente.
             *
             * Exemplo:
             *
             * Flor 1 = 0s
             * Flor 2 = 1.8s
             * Flor 3 = 3.6s
             * Flor 4 = 5.4s
             *
             * Portanto elas não surgem em uma linha.
             */

            @keyframes bloom {{

                0% {{
                    opacity: 0;
                    transform: scale(0.2);
                }}

                {bloom_pct:.3f}% {{
                    opacity: 1;
                    transform: scale(1);
                }}

                {hold_start_pct:.3f}% {{
                    opacity: 1;
                    transform: scale(1);
                }}

                100% {{
                    opacity: 0;
                    transform: scale(0.2);
                }}

            }}

        </style>
        '''
    )

    parts.append("</svg>")

    return "".join(parts)


def main():

    username = (
        os.environ.get("GITHUB_USERNAME")
        or (
            sys.argv[1]
            if len(sys.argv) > 1
            else None
        )
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

    svg = build_svg(
        weeks,
        username
    )

    os.makedirs(
        "assets",
        exist_ok=True
    )

    with open(
        "assets/flower-garden.svg",
        "w",
        encoding="utf-8"
    ) as f:

        f.write(svg)

    print(
        f"Jardim de flores gerado para "
        f"{username} em assets/flower-garden.svg"
    )


if __name__ == "__main__":
    main()