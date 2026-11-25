"""QR codes do slide final, no estilo da Lapida: módulos lapidados e o logo no meio.

uv run --with qrcode python apresentacao/gerar_qr.py
"""

import re
from pathlib import Path

import qrcode

URLS = {
    "github": "https://github.com/Gabriel-Marques-tech/Stone-Content-Guide",
    "linkedin": "https://www.linkedin.com/in/gabrielmarquesinteli",
}
PASTA = Path(__file__).parent
MARGEM = 4
LOGO = re.search(r"<polygon.*</svg>", (PASTA / "logo.svg").read_text()).group()[:-6]


def faceta(x, y, lado, cortes):
    """Quadrado com cantos cortados (cima-esq., cima-dir., baixo-dir., baixo-esq.), como lapidado."""
    a, b, c, d = cortes
    x2, y2 = x + lado, y + lado
    return (
        f"M{x + a} {y}H{x2 - b}L{x2} {y + b}V{y2 - c}L{x2 - c} {y2}H{x + d}L{x} {y2 - d}V{y + a}Z"
    )


def desenhar(url: str) -> str:
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=0)
    qr.add_data(url)
    qr.make(fit=True)
    m = qr.get_matrix()
    n = len(m)
    # o logo cobre 5x5 módulos, 2% do código; a correção M aguenta 15%
    meio, raio = n / 2, 2.5

    def livre(x, y):
        canto = (x < 7 or x >= n - 7) and y < 7 or (x < 7 and y >= n - 7)
        no_logo = abs(x + 0.5 - meio) < raio and abs(y + 0.5 - meio) < raio
        return m[y][x] and not canto and not no_logo

    def modulo(x, y):
        """Só corta a ponta que não encosta em outro módulo: o bloco fica contínuo."""
        viz = {
            (dx, dy): 0 <= x + dx < n and 0 <= y + dy < n and livre(x + dx, y + dy)
            for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0))
        }
        cima, dir_, baixo, esq = viz.values()
        pares = ((cima, esq), (cima, dir_), (baixo, dir_), (baixo, esq))
        return faceta(x, y, 1, [0 if a or b else 0.3 for a, b in pares])

    modulos = "".join(modulo(x, y) for y in range(n) for x in range(n) if livre(x, y))
    # olhos retos: com cantos cortados os leitores deixam de achar o código
    olhos = "".join(
        f'<path fill-rule="evenodd" d="{faceta(x, y, 7, [0] * 4)}{faceta(x + 1, y + 1, 5, [0] * 4)}" '
        f'fill="url(#g)"/><path d="{faceta(x + 2, y + 2, 3, [0] * 4)}" fill="#00663A"/>'
        for x, y in ((0, 0), (n - 7, 0), (0, n - 7))
    )
    lado, total = raio * 1.75, n + 2 * MARGEM
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-MARGEM} {-MARGEM} {total} {total}">'
        f'<defs><linearGradient id="g" gradientUnits="userSpaceOnUse" x2="{n}" y2="{n}">'
        '<stop stop-color="#15201A"/><stop offset="1" stop-color="#00663A"/>'
        f'</linearGradient></defs><rect x="{-MARGEM}" y="{-MARGEM}" width="{total}" '
        f'height="{total}" fill="#fff"/><path d="{modulos}" fill="url(#g)" stroke="url(#g)" stroke-width=".04"/>{olhos}'
        f'<svg x="{meio - lado / 2}" y="{meio - lado / 2}" width="{lado}" height="{lado}" '
        f'viewBox="8 6 192 188">{LOGO}</svg></svg>'
    )


for nome, url in URLS.items():
    (PASTA / f"qr-{nome}.svg").write_text(desenhar(url))
