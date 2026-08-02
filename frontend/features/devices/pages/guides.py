from fasthtml.common import *
from starlette.responses import HTMLResponse

from components import pub_shell
from features.devices.static.guides import GUIDES
from i18n import t as make_t

rt = APIRouter()

# ══════════════════════════════════════════════════════════════
# MAINTENANCE GUIDES (public)
# Content source: "Medical Equipment Maintenance Manual —
# First line maintenance for end users" — Ministry of Health and
# Family Welfare, New Delhi.
# ══════════════════════════════════════════════════════════════

GUIDE_INDEX = {g["slug"]: g for g in GUIDES}


def _checklist(list_items):
    return Div(
        *[Div(
            Span("•", style="color:var(--c-primary);margin-right:8px;"),
            Span(item, style="font-size:0.875rem;color:var(--c-text);"),
            style="display:flex;padding:7px 0;border-bottom:1px solid var(--c-border);"
        ) for item in list_items],
    ) if list_items else P("—", style="color:var(--c-text-3);")


def _fault_table(faults, _):
    rows = []
    for fault in faults:
        cases = fault["cases"]
        for i, (cause, solution) in enumerate(cases):
            if i == 0:
                rows.append(Tr(
                    Td(fault["fault"], rowspan=len(cases),
                       style="font-weight:500;font-size:0.875rem;vertical-align:top;"),
                    Td(cause, style="font-size:0.875rem;vertical-align:top;"),
                    Td(solution, style="font-size:0.875rem;vertical-align:top;"),
                ))
            else:
                rows.append(Tr(
                    Td(cause, style="font-size:0.875rem;vertical-align:top;"),
                    Td(solution, style="font-size:0.875rem;vertical-align:top;"),
                ))
    return Div(
        Table(
            Thead(Tr(
                Th(_("guide.fault"), style="text-align:left;"),
                Th(_("guide.cause"), style="text-align:left;"),
                Th(_("guide.solution"), style="text-align:left;"),
            )),
            Tbody(*rows),
        ),
        style="overflow-x:auto;"
    )


def _guide_page(guide, lang):
    _ = make_t(lang)
    content = guide.get(lang) or guide
    cards = []

    if content.get("function"):
        cards.append(Div(
            H3(_("guide.function"), style="font-size:1rem;margin-bottom:10px;color:var(--c-text-2);"),
            P(content["function"], style="font-size:0.9rem;line-height:1.55;margin:0;"),
            cls="card", style="margin-bottom:14px;"
        ))

    if content.get("how_it_works"):
        cards.append(Div(
            H3(_("guide.how_it_works"), style="font-size:1rem;margin-bottom:10px;color:var(--c-text-2);"),
            P(content["how_it_works"], style="font-size:0.9rem;line-height:1.55;margin:0;"),
            cls="card", style="margin-bottom:14px;"
        ))

    cards.append(Div(
        H3(_("guide.troubleshooting"), style="font-size:1rem;margin-bottom:10px;color:var(--c-text-2);"),
        _fault_table(content.get("faults", []), _),
        cls="card", style="margin-bottom:14px;"
    ))

    six_months = content.get("six_months") or _("guide.six_months_default")
    cards.append(Div(
        H3(_("guide.checklist"), style="font-size:1rem;margin-bottom:4px;color:var(--c-text-2);"),
        Div(
            H4(_("guide.daily"), style="font-size:0.875rem;margin:14px 0 6px;color:var(--c-text-3);text-transform:uppercase;letter-spacing:.03em;"),
            _checklist(content.get("daily", [])),
            H4(_("guide.weekly"), style="font-size:0.875rem;margin:14px 0 6px;color:var(--c-text-3);text-transform:uppercase;letter-spacing:.03em;"),
            _checklist(content.get("weekly", [])),
            H4(_("guide.six_months"), style="font-size:0.875rem;margin:14px 0 6px;color:var(--c-text-3);text-transform:uppercase;letter-spacing:.03em;"),
            P(six_months, style="font-size:0.875rem;color:var(--c-text);margin:0;"),
        ),
        cls="card"
    ))

    page = Div(
        Div(Div(Span("✚", cls="pub-cross"), f" {_('brand')}", cls="pub-logo"), cls="pub-header"),
        Div(
            Div("🔧", style="width:52px;height:52px;background:var(--c-primary-lt);color:var(--c-primary);border-radius:12px;font-size:1.5rem;display:flex;align-items:center;justify-content:center;margin-bottom:12px;"),
            H1(content["title"], style="margin-bottom:4px;"),
            P(_("guide.first_line"),
              style="color:var(--c-text-3);font-size:0.85rem;margin-bottom:20px;"),
            *cards,
            style="max-width:860px;margin:0 auto;padding:24px 16px 60px;"
        ),
        cls="pub-page"
    )

    return pub_shell(page, title=f"{content['title']} — {_('guide.maint_title')}", lang=lang)


@rt("/device/maintenace_guide/{slug}")
async def get(req, slug: str):
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    guide = GUIDE_INDEX.get(slug)
    if not guide:
        return HTMLResponse(str(pub_shell(
            Div(
                Div(Div(Span("✚", cls="pub-cross"), f" {_('brand')}", cls="pub-logo"), cls="pub-header"),
                Div(
                    Div("⚠", style="width:52px;height:52px;background:var(--c-amber-lt);color:var(--c-amber);border-radius:12px;font-size:1.5rem;display:flex;align-items:center;justify-content:center;margin-bottom:12px;"),
                    H2(_("guide.not_found")),
                    P(_("guide.not_found_msg"), style="margin-bottom:16px;"),
                    A(_("guide.back"), href="/devices", cls="btn btn-primary",
                      style="text-decoration:none;"),
                    style="text-align:center;padding:60px 24px;"
                ),
                cls="pub-page"
            ),
            lang=lang
        )), status_code=404)
    return _guide_page(guide, lang)
