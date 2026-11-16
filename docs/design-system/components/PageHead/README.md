# PageHead

The top of a page: an icon tile in the audience colour, the title, one line under it, actions on the right. From the platform brief's chapter heads.

```python
page_head(_("device_list.title"), count_line, "devices", "",
          A(_("device_list.add"), href="/new_device", cls="btn btn-primary"))
```

| Tone | Tile | Use for |
| --- | --- | --- |
| `""` | `primary` | Equipment: devices, dashboard |
| `"eng"` | `accent` | Growing the network: groups, invite a clinic |
| `"lead"` | `lead` | Community: network, library, journey |
| `"brand"` | gradient | The person's own page: profile |
| `"danger"` | `danger` | Faults |

- Tile 52px, radius 16, white icon 26px (44px and 22px on phones). Title is `h1`; the line under it is `text-muted`, one sentence or a count.
- Classes: `.ph`, `.ph-ico.t-*`, `.ph-text`, `.ph-acts`.
