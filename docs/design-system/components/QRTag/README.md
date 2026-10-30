# QRTag

The label stuck on every tagged device: the brand's most-seen object. It must scan in a dim ward from a cheap phone and survive a thermal printer.

**Layout (70 × 30 mm)**
- Left: the QR code, 24 mm square, black on white, with its quiet zone. No logo inside the code.
- Right, top to bottom: the black mark (6 mm high), "Scan to report a fault" bold, the same line in the deployment's second language, the short device id in `code`, and `qr.fixmymedtech.org`.

**Rules**
- One ink, black `#000000` on white. Never grey, never the gradient: contrast decides whether it scans.
- The QR encodes `https://qr.fixmymedtech.org/d/<device id>`; the short id is the first 8 characters, for when the code is damaged.
- Use the black core mark, never a country logo (unreadable at 6 mm).
- `scripts/generate_qr.py` should produce exactly this layout.

**What the consumer provides:** device id and the two languages of the deployment.
