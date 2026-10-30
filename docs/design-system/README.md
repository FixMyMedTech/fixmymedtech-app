FixMyMedTech helps biomedical engineers and clinics tag, track, report faults on and maintain medical equipment, starting in Africa. The whole identity is one idea: **the mark on the shape of a place, in one teal-to-deep-blue gradient.** Everything here is the smallest set of parts that carries that idea through the app, the printed QR tag and community material.

## The system on one page

| Part | What there is |
| --- | --- |
| Brand | One mark in three renderings (colour, black, white); one gradient (`brand-teal` → `brand-deep`, 135°); one name, FixMyMedTech |
| Colour | 22 tokens named by role: 4 brand, 3 grounds, 2 lines, 2 text, 4 action, 1 accent, 6 status |
| Type | System fonts. 7 styles: `display`, `h1`, `h2`, `h3`, `body`, `small`, `code` on 12/14/16/20/24/32px |
| Space and shape | Spacing 4, 8, 12, 16, 24, 32, 48. Radius 8 (controls), 12 (cards), pill. Two shadows |
| Components | Button, Badge, Field, Card, Table, Alert, FilterPills, QRTag |
| Patterns | AppShell, PublicDevicePage, SignIn |

## Voice

- Write for a busy engineer or nurse holding a phone: short sentences, the device's real name, "you".
- Sentence case everywhere: "Report fault", "Assign this fault". Uppercase only for eyebrows.
- Use hospital words (device, fault, clinic, engineer, maintenance log, QR tag), not system words (org, entity, healthsite id).
- Buttons say what happens; empty states say what is missing ("No devices found.").
- Every string in English, French and Spanish. No emoji in the product.

## Brand

- **Mark:** health cross, heartbeat line turning into a wrench, gear. Colour rendering on light grounds, white on dark grounds and the gradient, black for print and QR tags.
- **Name:** FixMyMedTech, one word, mixed case, `brand-navy` with "My" in `accent`. Always part of the logo image; never retyped in another font. No other spelling anywhere, including file names and docs.
- **Gradient:** `brand-teal` at top-left to `brand-deep` at bottom-right, 135°, exposed as `--gradient-brand`. Use it for country logos, the sign-in panel, slide and social backgrounds, and as a 4px rule under brand bars. Never on buttons, cards, charts or behind small text; text goes only on its darker half or on solid `brand-deep`.
- **Country logos:** the place's shape in the gradient with the white mark at 55–60% of its width (see CountryLogo). 64px and larger only; below that, the mark alone.

## Colour

- Brand tokens (`brand-*`, `on-brand`) are for the logo and brand surfaces; they never change with the theme.
- `primary` is the only action colour: buttons, links, active nav, focus ring. `accent` is teal for emphasis text only.
- `text` for headings and body, `text-muted` for everything secondary. Both pass WCAG AA on `bg`, `surface` and `sunken` in both themes.
- Status colours follow one rule, who has to act: `danger` someone must act, `warn` someone is on it, `ok` it works or is done, neutral (`sunken` + `text-muted`) not in play. Always with a word.
- Dark theme uses the same names; nothing is styled per theme.

## Type

- System sans (`font-sans`): fast on slow connections and native on every phone. Mono (`font-mono`) only for serials, asset tags and device ids.
- `display` 32/700 dashboard numbers, `h1` 24/700 page title, `h2` 20/700 sections and device names, `h3` 16/600 card titles, `body` 14/400 (500 for buttons and nav), `small` 12/500 labels, captions, badges and uppercase eyebrows, `code` 12 mono.

## Space, shape and icons

- Spacing on a 4px base: `space-1` 4 to `space-12` 48. Phones use `space-4` gutters, desktop `space-6`.
- `radius-control` for buttons and inputs, `radius-card` for cards, tables and tags, `radius-pill` for badges and pills; the rounded corners echo the cross.
- Edges are 1px `border` hairlines; `shadow-card` at rest, `shadow-float` for menus and modals.
- Focus: 2px solid `primary` ring, 2px offset, on every interactive element.
- Icons: Lucide, 18px in navigation, 16px in buttons, 2px stroke, `currentColor`.

## Outside the app

- Discord and social avatars: the colour mark on white.
- Slides, posters, social cards: the gradient as a background band, the white mark or country logo, titles in the system sans on the darker half.
- Docs and printed forms: black mark, `text` and `primary` only.

## Moving the app onto this system

- Replace the `:root` block in `frontend/components.py` with these tokens; keep the old `--c-*` names as aliases for one release (`--c-text-3: var(--text-muted)`, `--c-green: var(--ok)` …), then remove them.
- Switch badge classes to `badge-ok`, `badge-warn`, `badge-danger`, `badge-neutral` in `status_badge()`; merge `btn-outline` and `btn-warning` into `btn-secondary`.
- Move the most repeated of the app's inline `style="…"` attributes into classes; a token change does not reach them.
- Make `scripts/generate_qr.py` output the QRTag layout.
