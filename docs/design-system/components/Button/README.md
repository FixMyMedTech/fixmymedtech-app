# Button

Three variants and one size modifier. The label says what happens: "Report fault", "Assign this fault".

- `btn-primary`: the main action of the view. One per view.
- `btn-secondary`: every other action, including cancel, back, edit and row actions.
- `btn-danger`: delete, leave, decommission, always behind a confirmation.
- `btn-sm`: in table rows and dense toolbars.

A 16px Lucide icon before the label only when it speeds up scanning. An icon-only button needs an `aria-label`.

**What the consumer provides:** label (i18n key) and an `href` or a form submit.
