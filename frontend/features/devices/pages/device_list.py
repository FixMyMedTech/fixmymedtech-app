from fasthtml.common import *
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
import os, json, httpx
from dotenv import load_dotenv

load_dotenv()

from i18n import t as make_t

# __ API imports __
import features.auth.helper as auth_helper
import features.auth.api as auth_api
import features.dashboard.api as dashboard_api
import features.devices.api as devices_api
import features.faults.api as faults_api

from components import page_shell, status_badge, fmt_date
from features.devices.static.guides import category_label
rt = APIRouter()


def _js_json(value) -> str:
    r"""json.dumps output that is safe inside a <script> element.

    JSON itself doesn't forbid '</script>', and FastHTML's Script() doesn't
    escape it either, so an HTML parser would end the block at a device name
    containing that sequence. Encoding <, > and & as \u escapes keeps the JSON
    byte-identical after parsing while making that impossible.
    """
    return (json.dumps(value, ensure_ascii=False)
            .replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e"))

# Client-side search over the already-loaded, org-scoped device rows.
DEV_SEARCH_JS = """
function devSearch() {
  var input = document.getElementById('dev-search');
  var q = ((input && input.value) || '').trim().toLowerCase();
  var rows = document.querySelectorAll('tr[data-m]');
  var shown = 0;
  for (var i = 0; i < rows.length; i++) {
    var hit = !q || rows[i].getAttribute('data-m').indexOf(q) !== -1;
    rows[i].style.display = hit ? '' : 'none';
    if (hit) shown++;
  }

  var table = document.getElementById('dev-table');
  var empty = document.getElementById('dev-empty');
  if (table) table.style.display = shown ? '' : 'none';
  if (empty) empty.style.display = shown ? 'none' : '';

  var count = document.getElementById('dev-count');
  if (count) {
    count.textContent = shown + ' ' +
      (shown === 1 ? count.dataset.one : count.dataset.many) + ' ' + count.dataset.tail;
  }

  var box = document.getElementById('dev-sugg');
  if (!box) return;
  box.textContent = '';
  if (!q) { box.hidden = true; return; }

  var hits = DEV_INDEX.filter(function (d) { return d.m.indexOf(q) !== -1; }).slice(0, 8);
  box.hidden = false;
  if (!hits.length) {
    var none = document.createElement('div');
    none.className = 'sugg-empty';
    none.textContent = DEV_NONE;
    box.appendChild(none);
    return;
  }
  hits.forEach(function (d) {
    var a = document.createElement('a');
    a.className = 'sugg-item';
    a.href = '/device/' + encodeURIComponent(d.id);
    var name = document.createElement('span');
    name.className = 'sugg-name';
    name.textContent = d.name;
    var sub = document.createElement('span');
    sub.className = 'sugg-sub';
    sub.textContent = d.sub;
    a.appendChild(name);
    a.appendChild(sub);
    box.appendChild(a);
  });
}

function devSearchClose() {
  var box = document.getElementById('dev-sugg');
  if (box) box.hidden = true;
}

document.addEventListener('click', function (e) {
  var wrap = document.querySelector('.dev-search');
  if (wrap && !wrap.contains(e.target)) devSearchClose();
});
document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') devSearchClose();
});
"""

# In-app delete confirmation. The name comes from DEV_INDEX, so the device
# name is never interpolated into markup — only textContent can touch it.
DEL_DIALOG_JS = """
function delAsk(id) {
  var d = DEV_INDEX.filter(function (x) { return x.id === id; })[0];
  document.getElementById('del-name').textContent = d ? d.name : '';
  document.getElementById('del-dialog-form').action =
    '/devices/' + encodeURIComponent(id) + '/delete';
  document.getElementById('del-dialog').showModal();
}
"""

# ══════════════════════════════════════════════════════════════
# DEVICES LIST
# ══════════════════════════════════════════════════════════════

@rt("/devices")
async def get(req, status: str = "", healthsite_id: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect: return redirect

    lang = req.session.get("lang", "en")
    _ = make_t(lang)

    try:
        devices = await devices_api.get_devices(token, status or None, healthsite_id or None)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            auth_helper.clear_session(req)
            return RedirectResponse("/login?expired=1", status_code=302)
        if e.response.status_code == 403:
            return page_shell(
                Div(
                    Div("⚠", style="font-size:2rem;display:block;margin-bottom:10px;"),
                    H2(_("device_list.access_denied")),
                    P(_("device_list.access_msg")),
                    style="text-align:center;padding:60px 24px;"
                ),
                lang=lang
            )
        devices = []
    except Exception:
        devices = []

    all_devices = devices
    if status or healthsite_id:
        try:
            all_devices = await devices_api.get_devices(token)
        except Exception:
            all_devices = devices

    status_filters = [
        ("", _("device_list.filter_all")),
        ("operational", _("device_list.filter_operational")),
        ("maintenance", _("device_list.filter_maintenance")),
        ("fault", _("device_list.filter_fault")),
        ("decommissioned", _("device_list.filter_decommissioned")),
    ]

    my_admin_org_ids = set()
    my_id = None
    try:
        me = await auth_api.get_me(token)
        my_id = str(me.get("id") or "") or None
        my_admin_org_ids = {str(o["id"]) for o in me.get("organizations", []) if o.get("role") == "admin"}
    except Exception:
        my_admin_org_ids = set()

    def can_manage(d):
        """Edit/delete allowed: admin of the owning org, admin of the
        device's healthsite, or the user who registered the device."""
        if my_id and str(d.get("registered_by") or "") == my_id:
            return True
        if str(d.get("organization_id") or "") in my_admin_org_ids:
            return True
        healthsite = d.get("healthsite") or {}
        hs_id = str(d.get("healthsite_id") or healthsite.get("id") or "")
        return hs_id in my_admin_org_ids

    pills = [
        A(label, href=f"/devices?status={val}&healthsite_id={healthsite_id}" if healthsite_id else f"/devices?status={val}",
        cls=f"pill {'active' if status == val else ''}")
        for val, label in status_filters
    ]

    device_healthsites = {}
    for device in all_devices:
        healthsite = device.get("healthsite") or {}
        if healthsite.get("id"):
            device_healthsites[str(healthsite["id"])] = healthsite
    healthsites = sorted(device_healthsites.values(), key=lambda site: site.get("name", "").lower())

    healthsite_options = [
        Option(_("device_list.filter_healthsite_all"), value="", selected=not healthsite_id),
        *[
            Option(f"{o['name']} ({o['country']})", value=o["id"], selected=(o["id"] == healthsite_id))
            for o in healthsites
        ],
    ]
    healthsite_filter = Form(
        Label(_("device_list.filter_healthsite"), for_="healthsite_id", style="font-size:0.8rem;color:var(--c-text-3);"),
        Select(*healthsite_options, name="healthsite_id", id="healthsite_id",
               onchange="this.form.submit()",
               style="padding:6px 8px;border:1px solid var(--c-border);border-radius:var(--r-md);font-size:0.8rem;"),
        Input(type="hidden", name="status", value=status),
        method="get", action="/devices",
        style="display:flex;align-items:center;gap:8px;margin-left:auto;",
    )

    rows = []
    search_index = []
    for d in devices:
        cat = d.get("category") or {}
        healthsite = d.get("healthsite") or {}
        hs_name = healthsite.get("name", "")
        loc_name = d.get("location", "")
        cat_text = f"{cat.get('icon','🏥')} {category_label(cat, lang)}"
        nm = d.get("next_maintenance", "")
        overdue = nm and nm < __import__("datetime").datetime.now().isoformat()

        # Free-text index behind the search bar: every field a user might type.
        match = " ".join(filter(None, [
            d.get("name", ""), d.get("manufacturer", ""), d.get("model", ""),
            cat_text, hs_name, loc_name,
        ])).lower()
        search_index.append({
            "id": str(d["id"]),
            "name": d.get("name", "") or _("common.fallback"),
            "sub": " · ".join(filter(None, [cat_text, hs_name or loc_name])),
            "m": match,
        })

        actions = Div(
            A(_("device_list.view"), href=f"/device/{d['id']}", cls="btn btn-secondary btn-sm"),
            A(_("groups.edit"), href=f"/devices/{d['id']}/edit", cls="btn btn-secondary btn-sm") if can_manage(d) else "",
            Button(_("groups.delete"), type="button", cls="btn btn-danger btn-sm",
                   onclick=f"delAsk({json.dumps(str(d['id']))})") if can_manage(d) else "",
            cls="actions",
        )

        loc_children = []
        if hs_name:
            loc_children.append(Div(hs_name, style="font-weight:500;font-size:0.875rem;color:var(--c-text);"))
        loc_children.append(Div(loc_name or _("common.fallback"),
                                style="font-size:0.8rem;color:var(--c-text-3);"))

        rows.append(Tr(
            Td(
                Div(d.get("name", ""), style="font-weight:500;font-size:0.875rem;color:var(--c-text);"),
                Div(cat_text, style="font-size:0.75rem;color:var(--c-text-2);margin-top:2px;"),
                Div(f"{d.get('manufacturer','')} {d.get('model','')}".strip(),
                    style="font-size:0.75rem;color:var(--c-text-3);"),
            ),
            Td(*loc_children, **{"data-label": _("device_list.col_location")}),
            Td(status_badge(d.get("status", "operational"), lang=lang),
               **{"data-label": _("device_list.col_status")}),
            Td(
                Span(fmt_date(nm), cls="overdue" if overdue else ""),
                Span(_("device_list.overdue"), cls="overdue-tag") if overdue else "",
                **{"data-label": _("device_list.col_next")},
            ),
            Td(actions),
            **{"data-m": match},
        ))

    table = Div(
        Table(
            Thead(Tr(Th(_("device_list.col_device")), Th(_("device_list.col_location")),
                    Th(_("device_list.col_status")), Th(_("device_list.col_next")), Th("", style="text-align:right;"))),
            Tbody(*rows) if rows else Tbody()
        ),
        id="dev-table",
        cls="table-wrap has-cards",
        style="" if rows else "display:none;",
    )

    # Shown instead of the table when there is nothing at all, or when the
    # search filter leaves no rows.
    empty_msg = Div(_("device_list.empty"),
        id="dev-empty",
        style="text-align:center;padding:32px;color:var(--c-text-3);border:1px dashed "
              "var(--c-border);border-radius:var(--r-lg);" + ("" if not rows else "display:none;"))

    search_bar = Div(
        Input(id="dev-search", type="search", cls="input",
              placeholder=_("device_list.search_placeholder"),
              autocomplete="off", oninput="devSearch()",
              **{"aria-label": _("device_list.search_placeholder")}),
        Div(id="dev-sugg", cls="dev-sugg", hidden=True),
        cls="dev-search",
    )

    # In-app confirmation instead of the browser's native confirm() box.
    delete_dialog = Dialog(
        Form(
            H3(_("device_list.delete_confirm"),
               style="margin:0 0 6px 0;font-size:1.05rem;"),
            P(Span("", id="del-name"),
              style="color:var(--c-text-2);font-size:0.875rem;margin:0 0 18px;"
                    "word-break:break-word;overflow-wrap:anywhere;"),
            Div(
                Button(_("groups.cancel"), type="button", cls="btn btn-secondary",
                       onclick="document.getElementById('del-dialog').close()"),
                Button(_("groups.delete"), type="submit", cls="btn btn-danger"),
                style="display:flex;gap:8px;justify-content:flex-end;",
            ),
            method="post", action="/devices", id="del-dialog-form",
            style="padding:20px;max-width:440px;width:90%;",
        ),
        id="del-dialog",
        style="border:none;border-radius:12px;box-shadow:0 10px 40px rgba(0,0,0,.2);",
    )

    n = len(devices)
    one, many = _("device_list.device"), _("device_list.device") + _("device_list.devices_plural")
    tail = _("device_list.registered")
    count_line = P(
        Span(f"{n} {one if n == 1 else many} {tail}", id="dev-count",
             **{"data-one": one, "data-many": many, "data-tail": tail}),
        style="color:var(--c-text-3);",
    )

    page_script = Script(
        "const DEV_INDEX = " + _js_json(search_index) + ";\n"
        "const DEV_NONE = " + _js_json(_("device_list.search_none")) + ";\n"
        + DEV_SEARCH_JS
        + DEL_DIALOG_JS
    )

    content = Div(
        Div(
            Div(H1(_("device_list.title")), count_line),
            A(_("device_list.add"), href="/new_device", cls="btn btn-primary"),
            cls="page-header"
        ),
        Div(*pills, healthsite_filter, cls="toolbar"),
        search_bar,
        table,
        empty_msg,
        delete_dialog,
        page_script,
    )

    return page_shell(content, current="/devices", title=_("title.devices"), lang=lang)


@rt("/devices/{device_id}/delete")
async def post_delete(req, device_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect: return redirect

    try:
        await devices_api.delete_device(token, device_id)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            auth_helper.clear_session(req)
            return RedirectResponse("/login?expired=1", status_code=302)
    return RedirectResponse("/devices", status_code=303)
