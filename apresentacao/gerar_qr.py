"""QR codes do slide final. Uso: uv run --with "qrcode[pil]" python apresentacao/gerar_qr.py"""

from pathlib import Path

import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.colormasks import SolidFillColorMask
from qrcode.image.styles.moduledrawers.pil import RoundedModuleDrawer

URLS = {
    "github": "https://github.com/Gabriel-Marques-tech/Stone-Content-Guide",
    "linkedin": "https://www.linkedin.com/in/gabrielmarquesinteli",
}
for nome, url in URLS.items():
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=20, border=2)
    qr.add_data(url)
    qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=RoundedModuleDrawer(),
        color_mask=SolidFillColorMask(front_color=(21, 32, 26), back_color=(255, 255, 255)),
    ).save(Path(__file__).parent / f"qr-{nome}.png")
