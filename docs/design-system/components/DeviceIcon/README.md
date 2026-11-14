# DeviceIcon

A device's picture: a rounded tile with the Lucide icon of its category, tinted with its status colour. Replaces the emoji and the initial letter.

```python
device_icon(category, tone="danger")        # 44px, in lists
device_icon(category, tone="ok", size="lg") # 88px, on the device ID card
```

- Tones follow the badge rule: `ok`, `warn`, `danger`, `neutral` (tint background, solid icon). No tone = `primary-tint`.
- Category → icon: ventilators and oxygen `wind`, monitors and ECG `activity`, infusion `droplet`, defibrillators `zap`, imaging `scan`, incubators `heart`, autoclaves `flame`, blood-pressure and flowmeters `gauge`; unknown → `devices`.
- A photo, when there is one, replaces the tile at the same size.
