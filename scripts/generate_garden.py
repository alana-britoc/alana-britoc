#!/usr/bin/env python3
"""
Commit Garden - gera um jardim em SVG a partir do histórico de commits do repositório.

Regras:
- Cada branch remota vira uma "espécie" de planta (definida por um hash do nome).
- O número de commits na branch define o estágio de crescimento:
    1-2 commits   -> 🌱 semente
    3-6 commits   -> 🌿 broto
    7-15 commits  -> espécie da branch, em tamanho "jovem"
    16+ commits   -> espécie da branch, "florescendo"
- Branches sem commit novo há mais de 60 dias murcham (🥀).
"""
import subprocess
import hashlib
import datetime
import os

# Espécies "maduras" possíveis. Cada branch recebe uma com base num hash do nome,
# então a mesma branch sempre gera a mesma planta.
SPECIES = ["🌳", "🌷", "🌻", "🌵", "🍀", "🌸", "🍄", "🌲"]


def run(cmd: str) -> str:
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()


def get_branches():
    raw = run("git for-each-ref --format='%(refname:short)' refs/remotes/origin")
    branches = [b.strip("'") for b in raw.splitlines() if b and "HEAD" not in b]
    return [b.replace("origin/", "", 1) for b in branches]


def commit_count(branch: str) -> int:
    out = run(f"git rev-list --count origin/{branch}")
    try:
        return int(out)
    except ValueError:
        return 0


def last_commit_days_ago(branch: str) -> int:
    out = run(f"git log -1 --format=%ct origin/{branch}")
    if not out:
        return 999
    ts = int(out)
    dt = datetime.datetime.utcfromtimestamp(ts)
    return (datetime.datetime.utcnow() - dt).days


def species_for(branch: str) -> str:
    h = int(hashlib.sha256(branch.encode()).hexdigest(), 16)
    return SPECIES[h % len(SPECIES)]


def growth_stage(n_commits: int, species_emoji: str):
    if n_commits <= 2:
        return "🌱", "semente"
    elif n_commits <= 6:
        return "🌿", "broto"
    elif n_commits <= 15:
        return species_emoji, "jovem"
    else:
        return species_emoji, "florescendo"


def build_svg(plants):
    width = 900
    cols = 6
    cell_w = width // cols
    rows = max(1, (len(plants) + cols - 1) // cols)
    ground_y = 60
    height = ground_y + rows * 140 + 40

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        f'font-family="Segoe UI Emoji, Apple Color Emoji, Noto Color Emoji, sans-serif">'
    ]

    parts.append(f'''
    <defs>
      <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#bfe9ff"/>
        <stop offset="100%" stop-color="#eaf9ff"/>
      </linearGradient>
      <linearGradient id="soil" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#8b5a2b"/>
        <stop offset="100%" stop-color="#5c3a1e"/>
      </linearGradient>
    </defs>
    <rect width="{width}" height="{height}" fill="url(#sky)"/>
    <circle cx="{width-70}" cy="55" r="30" fill="#ffd93d"/>
    ''')

    for i, p in enumerate(plants):
        col = i % cols
        row = i // cols
        x = col * cell_w + cell_w // 2
        y_ground = ground_y + row * 140 + 120

        parts.append(
            f'<rect x="{col*cell_w+10}" y="{y_ground-10}" width="{cell_w-20}" '
            f'height="18" rx="6" fill="url(#soil)"/>'
        )
        parts.append(
            f'<text x="{x}" y="{y_ground-30}" font-size="42" '
            f'text-anchor="middle">{p["emoji"]}</text>'
        )
        parts.append(
            f'<text x="{x}" y="{y_ground+22}" font-size="12" text-anchor="middle" '
            f'fill="#2f4f2f" font-weight="bold">{p["branch"]}</text>'
        )
        parts.append(
            f'<text x="{x}" y="{y_ground+38}" font-size="10" text-anchor="middle" '
            f'fill="#5c5c5c">{p["commits"]} commits · {p["stage_name"]}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)


def main():
    branches = get_branches()
    if not branches:
        branches = ["main"]

    plants = []
    for b in branches:
        n = commit_count(b)
        species = species_for(b)
        emoji, stage_name = growth_stage(n, species)
        days_ago = last_commit_days_ago(b)

        if days_ago > 60:
            emoji = "🥀"
            stage_name = "murchando (sem commits recentes)"

        plants.append({
            "branch": b,
            "commits": n,
            "emoji": emoji,
            "stage_name": stage_name,
        })

    # branches com mais commits aparecem primeiro
    plants.sort(key=lambda p: -p["commits"])

    svg = build_svg(plants)
    os.makedirs("assets", exist_ok=True)
    with open("assets/garden.svg", "w", encoding="utf-8") as f:
        f.write(svg)

    print(f"Jardim gerado com {len(plants)} planta(s) em assets/garden.svg")


if __name__ == "__main__":
    main()