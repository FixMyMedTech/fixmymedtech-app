# features/devices/cmms_ui.py — shared pieces of the clinic CMMS screens
# (wave 2): the device ID card's tiles, the "Needs you today" list and the
# device wall grouped by ward. Classes use the design-system tokens only.

from fasthtml.common import *

from components import fmt_date

CMMS_CSS = """
.eyebrow{font-size:12px;line-height:1.4;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--text-muted);}
.id-card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-panel);box-shadow:var(--shadow-card);overflow:hidden;margin-bottom:16px;}
.id-head{display:flex;gap:16px;align-items:flex-start;padding:20px;}
.id-photo{width:88px;height:88px;flex-shrink:0;border-radius:var(--radius-card);object-fit:cover;background:var(--sunken);border:1px solid var(--border);}
.id-photo-empty{display:flex;align-items:center;justify-content:center;color:var(--text-muted);font-size:28px;font-weight:700;}
.id-main{flex:1;min-width:0;}
.id-main h1{margin:2px 0 4px;font-size:24px;line-height:1.2;}
.id-sub{color:var(--text-muted);font-size:14px;margin:0;}
.id-status{flex-shrink:0;}
.id-cta{display:flex;flex-wrap:wrap;align-items:center;gap:12px;padding:0 20px 20px;}
.id-cta .btn-primary{font-size:16px;padding:12px 22px;}
.id-tiles{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;background:var(--border);border-top:1px solid var(--border);}
.tile{display:block;background:var(--surface);padding:14px 16px;text-decoration:none;color:var(--text);border-top:3px solid transparent;}
.tile:hover{background:var(--sunken);}
.tile .tile-num{font-size:22px;font-weight:800;letter-spacing:-.01em;line-height:1.2;margin-top:2px;font-variant-numeric:tabular-nums;}
.tile .tile-sub{font-size:12px;color:var(--text-muted);margin-top:2px;}
.tile.is-ok{border-top-color:var(--ok);} .tile.is-warn{border-top-color:var(--warn);} .tile.is-danger{border-top-color:var(--danger);} .tile.is-neutral{border-top-color:var(--border-strong);}
.tile.is-warn .tile-num{color:var(--warn);} .tile.is-danger .tile-num{color:var(--danger);}
details.more{margin-bottom:16px;}
details.more>summary{cursor:pointer;list-style:none;display:flex;align-items:center;gap:10px;padding:12px 16px;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-card);font-weight:700;color:var(--primary);}
details.more>summary::-webkit-details-marker{display:none;}
details.more>summary::before{content:"+";width:22px;height:22px;border-radius:7px;background:var(--primary-tint);display:grid;place-items:center;font-size:16px;flex-shrink:0;}
details.more>summary>span:last-child{margin-left:auto;}
details.more[open]>summary{margin-bottom:16px;}
details.more[open]>summary::before{content:"\\2013";}
.needs{list-style:none;margin:0;padding:0;}
.needs li{display:flex;align-items:center;gap:12px;padding:10px 12px;border:1px solid var(--border);border-left:4px solid var(--border-strong);border-radius:12px;margin-bottom:8px;background:var(--surface);}
.needs li.is-danger{border-left-color:var(--danger);} .needs li.is-warn{border-left-color:var(--warn);}
.needs .n-main{flex:1;min-width:0;}
.needs .n-title{font-weight:600;color:var(--text);font-size:14px;}
.needs .n-sub{font-size:12px;color:var(--text-muted);}
.needs-empty{display:flex;align-items:center;gap:14px;padding:18px;border:1px dashed var(--border-strong);border-radius:var(--radius-card);color:var(--text-muted);}
.needs-empty .big{font-size:28px;font-weight:700;color:var(--ok);}
.wall{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px;}
.ward{background:var(--sunken);border:1px solid var(--border);border-radius:var(--radius-card);padding:14px;}
.ward-head{display:flex;justify-content:space-between;align-items:baseline;gap:8px;margin-bottom:10px;}
.ward-name{font-weight:600;color:var(--text);font-size:14px;}
.ward-count{font-size:12px;font-weight:600;color:var(--text-muted);background:var(--sunken);border-radius:var(--radius-pill);padding:1px 8px;}
.ward-devs{display:flex;flex-wrap:wrap;gap:6px;}
.dev{font-family:var(--font-sans);display:inline-flex;align-items:center;gap:6px;max-width:100%;padding:4px 10px;border-radius:var(--radius-pill);font-size:12px;font-weight:500;text-decoration:none;border:1px solid var(--border);background:var(--surface);color:var(--text);}
.dev:hover{border-color:var(--primary);}
.dev .dot{width:8px;height:8px;border-radius:50%;flex-shrink:0;background:var(--ok);}
.dev.is-warn .dot{background:var(--warn);} .dev.is-danger .dot{background:var(--danger);} .dev.is-neutral .dot{background:var(--border-strong);}
.dev .chip-name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.wall-legend{display:flex;flex-wrap:wrap;gap:14px;font-size:12px;color:var(--text-muted);margin:0 0 12px;}
.wall-legend span{display:inline-flex;align-items:center;gap:6px;}
.wall-legend i{width:8px;height:8px;border-radius:50%;display:inline-block;}
@media (max-width:600px){
  .id-head{padding:16px;gap:12px;} .id-photo{width:64px;height:64px;}
  .id-cta{padding:0 16px 16px;} .id-cta .btn-primary{width:100%;text-align:center;}
  .tile{padding:12px;} .tile .tile-num{font-size:16px;}
}
"""

# Device status → wall tone. "Who has to act": fault = someone must act,
# maintenance = someone is on it, decommissioned = not in play.
STATUS_TONE = {"operational": "ok", "maintenance": "warn", "fault": "danger", "decommissioned": "neutral"}


def ward_of(location: str | None, fallback: str) -> str:
    """The ward is the first part of the free-text location ("Ward 3 / Room 7"
    → "Ward 3"). Locations are typed by hand, so "/", "," and "-" all split."""
    loc = (location or "").strip()
    if not loc:
        return fallback
    for sep in ("/", ",", " - ", "·"):
        if sep in loc:
            loc = loc.split(sep, 1)[0].strip()
            break
    return loc or fallback


def device_tone(d: dict, today_iso: str) -> str:
    tone = STATUS_TONE.get(d.get("status") or "operational", "ok")
    nm = str(d.get("next_maintenance") or "")
    if tone == "ok" and nm and nm < today_iso:
        return "warn"
    return tone


def device_wall(_, devices: list, today_iso: str):
    if not devices:
        return P(_("cmms.wall_empty"), style="color:var(--text-muted);")
    wards: dict[str, list] = {}
    for d in devices:
        wards.setdefault(ward_of(d.get("location"), _("cmms.no_ward")), []).append(d)
    order = {"danger": 0, "warn": 1, "ok": 2, "neutral": 3}
    cards = []
    for name in sorted(wards, key=lambda w: (w == _("cmms.no_ward"), w.lower())):
        devs = sorted(wards[name], key=lambda d: (order[device_tone(d, today_iso)], (d.get("name") or "").lower()))
        cards.append(Div(
            Div(Span(name, cls="ward-name"),
                Span(_("cmms.ward_count").format(n=len(devs)), cls="ward-count"), cls="ward-head"),
            Div(*[A(Span(cls="dot"), Span(d.get("name") or "", cls="chip-name"),
                    href=f"/device/{d['id']}", title=d.get("location") or "",
                    cls=f"dev is-{device_tone(d, today_iso)}") for d in devs], cls="ward-devs"),
            cls="ward",
        ))
    legend = Div(
        Span(I(style="background:var(--ok);"), _("cmms.legend_ok")),
        Span(I(style="background:var(--warn);"), _("cmms.legend_warn")),
        Span(I(style="background:var(--danger);"), _("cmms.legend_danger")),
        cls="wall-legend",
    )
    return Div(legend, Div(*cards, cls="wall"))


def needs_list(_, items: list, total: int, lang: str):
    if not items:
        return Div(Span("0", cls="big"), Div(Strong(_("cmms.needs_none")), Div(_("cmms.needs_none_sub"))),
                   cls="needs-empty")
    rows = []
    for it in items:
        kind = it.get("kind")
        where = it.get("location") or ""
        if kind == "fault":
            tone = "danger" if it.get("severity") in ("critical", "high") else "warn"
            title = _("cmms.need_fault").format(device=it.get("device_name", ""))
            sub = _(f"badge.{it.get('severity') or 'medium'}") + " · " + fmt_date(it.get("date") or "")
            href = f"/device/{it['device_id']}/fault/{it['fault_id']}"
            action = _("cmms.open")
        elif kind == "overdue":
            tone = "danger"
            title = _("cmms.need_overdue").format(device=it.get("device_name", ""))
            sub = _("cmms.was_due").format(date=fmt_date(it.get("date") or ""))
            href = f"/d/{it['device_id']}/maintenance-log"
            action = _("cmms.log_service")
        else:
            tone = "warn"
            title = _("cmms.need_due_soon").format(device=it.get("device_name", ""))
            sub = _("cmms.due_on").format(date=fmt_date(it.get("date") or ""))
            href = f"/d/{it['device_id']}/maintenance-log"
            action = _("cmms.log_service")
        rows.append(Li(
            Div(Div(title, cls="n-title"), Div(" · ".join(p for p in (where, sub) if p), cls="n-sub"), cls="n-main"),
            A(action, href=href, cls="btn btn-secondary btn-sm"),
            cls=f"is-{tone}",
        ))
    more = P(_("cmms.needs_more").format(n=total - len(items)), style="color:var(--text-muted);font-size:12px;") \
        if total > len(items) else ""
    return Div(Ul(*rows, cls="needs"), more)


def clinic_of(d: dict) -> dict:
    """The clinic a device sits in: its healthsite, else its owning org."""
    return d.get("healthsite") or d.get("organization") or {}


def clinic_groups(_, devices: list, today_iso: str):
    """Wave 3, "my devices by clinic": one card per clinic, the devices that
    need someone first, coloured like the ward wall."""
    if not devices:
        return P(_("device_list.empty"), style="color:var(--text-muted);")
    groups: dict = {}
    for d in devices:
        c = clinic_of(d)
        key = str(c.get("id") or "")
        groups.setdefault(key, {"clinic": c, "devices": []})["devices"].append(d)
    order = {"danger": 0, "warn": 1, "ok": 2, "neutral": 3}
    cards = []
    for key, g in sorted(groups.items(), key=lambda kv: (kv[1]["clinic"].get("name") or "~").lower()):
        devs = sorted(g["devices"], key=lambda d: (order[device_tone(d, today_iso)], (d.get("name") or "").lower()))
        needing = sum(1 for d in devs if device_tone(d, today_iso) in ("danger", "warn"))
        c = g["clinic"]
        name = c.get("name") or _("cmms.no_ward")
        cards.append(Div(
            Div(A(name, href=f"/groups/{c['id']}/view", cls="ward-name", style="text-decoration:none;") if c.get("id")
                else Span(name, cls="ward-name"),
                Span(str(len(devs)), cls="ward-count"), cls="ward-head"),
            P(_("wave3.clinic_needs").format(n=needing) if needing else _("wave3.clinic_ok"),
              style=f"font-size:12px;margin:-4px 0 10px;color:var(--{'warn' if needing else 'ok'});font-weight:600;"),
            Div(*[A(Span(cls="dot"), Span(d.get("name") or "", cls="chip-name"),
                    href=f"/device/{d['id']}", title=d.get("location") or "",
                    cls=f"dev is-{device_tone(d, today_iso)}") for d in devs], cls="ward-devs"),
            cls="ward",
        ))
    return Div(*cards, cls="wall")
