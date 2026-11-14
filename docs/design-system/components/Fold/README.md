# Fold

Progressive disclosure: everything that is not the main job of the screen goes in a fold. From the brief's "Build notes" toggle.

```python
Details(Summary(_("cmms.more_details"), Span(hint, cls="hint")), Div(..., cls="fold-body"), cls="fold")
```

- Summary in `primary`, 700, with a "+" in a 22px `primary-tint` square (becomes "–" when open); a muted hint on the right says what is inside.
- Tiles above a fold can open it and jump to a section (`onclick` sets `open`).
- `details.more` (dashboard "Numbers and map", device "More details") uses the same look.
