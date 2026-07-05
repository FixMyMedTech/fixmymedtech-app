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


BASE_URL = "https://fixmymedtech-dev.careagain.org"
OUTPUT_DIR = "qr_codes"


def generate_qr(device_id: str, base_url: str = BASE_URL) -> str:
    """
    Generate a QR code PNG for a device URL.
    Returns the path to the saved file.
    """
    url = f"{base_url}/d/{device_id}"

    # Create output directory if it doesn't exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,  # 15% error correction
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    # Create styled image with rounded modules
    img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=RoundedModuleDrawer(),
        fill_color="#104f84",   # FixMyMedTech dark blue
        back_color="#ffffff",
    )

    # Convert to standard PIL Image before adding label
    img = img.convert("RGB")

    # Add label below QR code
    img = add_label(img, device_id, url)

    # Save
    filename = f"{OUTPUT_DIR}/qr_{device_id}.png"
    img.save(filename)
    print(f"✓ Saved: {filename}")
    print(f"  URL:    {url}")
    return filename


def add_label(img: Image.Image, device_id: str, url: str) -> Image.Image:
    """Add device ID label below the QR code."""
    qr_width, qr_height = img.size
    label_height = 60
    padding = 10

    # Create new image with space for label
    new_img = Image.new("RGB", (qr_width, qr_height + label_height), "#ffffff")
    new_img.paste(img, (0, 0))

    draw = ImageDraw.Draw(new_img)

    # Try to use a nice font, fall back to default
    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 11)
    except Exception:
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
        except Exception:
            font_large = ImageFont.load_default()
            font_small = font_large

    # Draw "FixMyMedTech QR" header
    header = "FixMyMedTech QR"
    draw.text((qr_width // 2, qr_height + padding), header,
              fill="#104f84", font=font_large, anchor="mt")

    # Draw short device ID
    short_id = device_id[:8] + "..."
    draw.text((qr_width // 2, qr_height + padding + 22), short_id,
              fill="#8a8780", font=font_small, anchor="mt")

    return new_img


def main():
    parser = argparse.ArgumentParser(description="Generate QR codes for FixMyMedTech devices")
    parser.add_argument("--device-id", type=str, default=None,
                        help="Specific device UUID (default: random)")
    parser.add_argument("--count", type=int, default=1,
                        help="Number of QR codes to generate (default: 1)")
    parser.add_argument("--base-url", type=str, default=BASE_URL,
                        help=f"Base URL (default: {BASE_URL})")
    args = parser.parse_args()

    if args.device_id:
        # Generate for specific ID
        generate_qr(args.device_id, args.base_url)
    else:
        # Generate with random UUIDs
        for i in range(args.count):
            device_id = str(uuid.uuid4())
            generate_qr(device_id, args.base_url)

    print(f"\nQR codes saved to ./{OUTPUT_DIR}/")


if __name__ == "__main__":
    main()