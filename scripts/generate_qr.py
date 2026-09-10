#!/usr/bin/env python3
"""
generate_qr.py — Generate a QR code PNG for a device URL.

Usage:
    # Generate with a random UUID
    python generate_qr.py

    # Generate for a specific device ID
    python generate_qr.py --device-id abc123-your-uuid-here

    # Generate multiple QR codes at once
    python generate_qr.py --count 5

    # Use a different base URL (e.g. production)
    python generate_qr.py --base-url https://yourdomain.com

    # Choose environment: prod (logo + qr.fixmymedtech.org) or dev (no logo + dev.fixmymedtech.org)
    python generate_qr.py --env dev
    python generate_qr.py --env prod

Install dependencies first:
    pip install qrcode[pil]
"""

import argparse
import uuid
import os
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
from PIL import Image, ImageDraw, ImageFont


BASE_URL = "https://qr.fixmymedtech.org"
OUTPUT_DIR = "qr/qr_dom_codes"
LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "frontend", "static", "logo_BW_black.png")

# Per-environment QR settings
ENVS = {
    "dev":  {"base_url": "https://dev.fixmymedtech.org",  "logo": None},
    "prod": {"base_url": "https://qr.fixmymedtech.org",   "logo": LOGO_PATH},
}


def generate_qr(device_id: str, base_url: str = BASE_URL,
                logo_path: str = LOGO_PATH) -> str:
    """
    Generate a QR code PNG for a device URL.
    Returns the path to the saved file.
    """
    url = f"{base_url}/d/{device_id}"

    if not logo_path:
        print("ℹ Dev environment (no logo)")
    else:
        print(f"ℹ Prod-like environment — logo at: {logo_path}")

    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # 30% error correction (logo in center)
        box_size=14,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    # Create styled image with rounded modules
    img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=RoundedModuleDrawer(),
        fill_color="#434c53",   # grey
        back_color="#ffffff",
    )

    # Convert to standard PIL Image before adding label
    img = img.convert("RGB")

    # Overlay logo in the centre of the QR code
    if logo_path:
        img = add_logo(img, logo_path)

    # Add label below QR code
    img = add_label(img, device_id, url)

    # Save
    filename = f"{OUTPUT_DIR}/qr_{device_id}.png"
    img.save(filename)
    print(f"✓ Saved: {filename}")
    print(f"  Device: {device_id}")
    print(f"  URL:    {url}")
    return filename


def add_logo(img: Image.Image, logo_path: str) -> Image.Image:
    """Overlay the FixMyMedTech logo in the center of the QR code."""
    if not os.path.exists(logo_path):
        print(f"⚠ Logo not found at {logo_path} — skipping logo")
        return img
    try:
        logo = Image.open(logo_path).convert("RGB")
    except Exception as e:
        print(f"⚠ Could not load logo ({e}) — skipping logo")
        return img

    qr_w, qr_h = img.size
    max_size = int(qr_w * 0.22)
    logo.thumbnail((max_size, max_size), Image.LANCZOS)

    # White padding around the logo keeps a clean quiet zone
    pad = max(4, int(max_size * 0.08))
    bg = Image.new("RGB", (logo.width + pad * 2, logo.height + pad * 2), "#ffffff")
    bg.paste(logo, (pad, pad))

    x = (qr_w - bg.width) // 2
    y = (qr_h - bg.height) // 2
    img.paste(bg, (x, y))
    return img


def add_label(img: Image.Image, device_id: str, url: str) -> Image.Image:
    """Add device ID label below the QR code."""
    qr_width, qr_height = img.size
    label_height = 84
    padding = 4

    # Create new image with space for label
    new_img = Image.new("RGB", (qr_width, qr_height + label_height), "#ffffff")
    new_img.paste(img, (0, 0))

    draw = ImageDraw.Draw(new_img)

    # Try to use a nice font, fall back to default
    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 17)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
    except Exception:
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 17)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
        except Exception:
            font_large = ImageFont.load_default()
            font_small = font_large

    # Draw "FixMyMedTech QR" header
    header = "FixMyMedTech QR"
    draw.text((qr_width // 2, qr_height + padding), header,
              fill="#000000", font=font_large, anchor="mt")

    # # Draw short device ID
    # short_id = device_id[:8] + "..."
    # draw.text((qr_width // 2, qr_height + padding + 22), short_id,
    #           fill="#8a8780", font=font_small, anchor="mt")

    # Draw full device UID
    draw.text((qr_width // 2, qr_height + padding + 20), device_id,
              fill="#8a8780", font=font_small, anchor="mt")

    return new_img


def main():
    parser = argparse.ArgumentParser(description="Generate QR codes for FixMyMedTech devices")
    parser.add_argument("--device-id", type=str, default=None,
                        help="Specific device UUID (default: random)")
    parser.add_argument("--count", type=int, default=1,
                        help="Number of QR codes to generate (default: 1)")
    parser.add_argument("--env", type=str, choices=list(ENVS), default="prod",
                        help="Environment: 'dev' (no logo, dev.fixmymedtech.org) or 'prod' (logo, qr.fixmymedtech.org). Default: prod")
    parser.add_argument("--base-url", type=str, default=None,
                        help=f"Base URL override (default: per --env: qr/dev.fixmymedtech.org)")
    parser.add_argument("--logo", type=str, default=None,
                        help="Logo image to embed in the center (default: per --env, prod uses frontend/static/logo_BW_black.png, dev uses none)")
    args = parser.parse_args()

    env = ENVS[args.env]
    base_url = args.base_url or env["base_url"]
    logo_path = args.logo if args.logo is not None else env["logo"]

    if args.device_id:
        # Generate for specific ID
        generate_qr(args.device_id, base_url, logo_path)
    else:
        # Generate with random UUIDs
        for i in range(args.count):
            device_id = str(uuid.uuid4())
            generate_qr(device_id, base_url, logo_path)

    print(f"\nQR codes saved to ./{OUTPUT_DIR}/")


if __name__ == "__main__":
    main()