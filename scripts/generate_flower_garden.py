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


def pick_flower(date_str):
    return random.Random(date_str).choice(FLOWER_EMOJIS)


def count_flowers(weeks):
    """
    Conta quantos dias possuem pelo menos um commit.

    Cada dia com level > 0 será representado
    por uma flor na animação.
    """

    return sum(
        1
        for week in weeks
        for day in week
        if day is not None and day.get("level", 0) > 0
    )


def build_svg(weeks, username):

    cols = len(weeks)

    width = PAD_LEFT + cols * (CELL + GAP)

    height = PAD_TOP + 7 * (CELL + GAP) + 6

    # ---------------------------------------------------------
    # CONFIGURAÇÃO DA ANIMAÇÃO
    # ---------------------------------------------------------

    # Tempo para uma flor surgir completamente
    BLOOM = 1.5

    # Tempo que a flor permanece visível depois de surgir
    HOLD = 1.5

    # Tempo para desaparecer
    RESET = 1.0

    # Intervalo entre o início de uma flor e o início da próxima.
    #
    # Como BLOOM = 1.5 e STEP = 1.8,
    # a próxima flor só começa depois que a anterior
    # terminou de surgir.
    STEP = 1.8

    # Quantidade REAL de dias com commits.
    #
    # Antes o código utilizava "cols", que representa
    # semanas. Agora cada commit/dia é uma flor.
    flower_count = count_flowers(weeks)

    # Delay da última flor
    max_delay = (
        max(0, flower_count - 1) * STEP
    )

    # Duração total da animação
    DURATION = round(
        max_delay + BLOOM + HOLD + RESET,
        3
    )

    # Percentuais utilizados pelo CSS
    bloom_pct = round(
        (BLOOM / DURATION) * 100,
        3
    )

    reset_start_pct = round(
        ((DURATION - RESET) / DURATION) * 100,
        3
    )

    months = month_labels_for(weeks)

    # ---------------------------------------------------------
    # SVG
    # ---------------------------------------------------------

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        f'font-family="-apple-system,\'Segoe UI\',Roboto,Helvetica,Arial,sans-serif">'
    ]

    # ---------------------------------------------------------
    # CSS DA ANIMAÇÃO
    # ---------------------------------------------------------

    parts.append(
        f'''
        <style>

          .flower {{
            opacity: 0;

            animation-name: appear;

            animation-duration: {DURATION}s;

            animation-timing-function: ease-in-out;

            animation-iteration-count: infinite;
          }}

          @keyframes appear {{

            /* Flor começa invisível */
            0% {{
              opacity: 0;
            }}

            /* Flor terminou de surgir */
            {bloom_pct}% {{
              opacity: 1;
            }}

            /* Flor permanece visível */
            {reset_start_pct}% {{
              opacity: 1;
            }}

            /* Flor desaparece */
            100% {{
              opacity: 0;
            }}

          }}

        </style>

        <rect
          width="{width}"
          height="{height}"
          fill="{BG_COLOR}"
        />
        '''
    )

    # ---------------------------------------------------------
    # MESES
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # DIAS DA SEMANA
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # FLORES
    # ---------------------------------------------------------

    # Este contador é GLOBAL.
    #
    # Diferente do código anterior, ele não reinicia
    # a cada coluna/semana.
    #
    # Portanto:
    #
    # commit 1 -> delay 0
    # commit 2 -> delay 1.8
    # commit 3 -> delay 3.6
    # commit 4 -> delay 5.4
    #
    # etc.
    flower_index = 0

    for col, week in enumerate(weeks):

        x = PAD_LEFT + col * (CELL + GAP)

        for row, day in enumerate(week):

            y = PAD_TOP + row * (CELL + GAP)

            if day is None:
                continue

            level = day.get("level", 0)

            # -------------------------------------------------
            # QUADRADO VAZIO
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
            # DIA COM COMMIT
            # -------------------------------------------------

            if level > 0:

                emoji = pick_flower(day["date"])

                cx = x + CELL / 2
                cy = y + CELL / 2

                # Cada commit recebe seu próprio delay.
                #
                # NÃO usamos mais "col * STEP",
                # porque "col" representa semanas.
                delay = round(
                    flower_index * STEP,
                    3
                )

                parts.append(
                    f'<text '
                    f'class="flower" '
                    f'style="animation-delay:{delay}s" '
                    f'x="{cx}" '
                    f'y="{cy}" '
                    f'font-size="{CELL}" '
                    f'text-anchor="middle" '
                    f'dominant-baseline="central">'
                    f'{emoji}'
                    f'</text>'
                )

                # Próximo commit = próxima flor
                flower_index += 1

    # ---------------------------------------------------------
    # FINALIZA SVG
    # ---------------------------------------------------------

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