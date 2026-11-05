# Badge

A badge names a state in one or two words. Its colour follows one rule: who has to act.

| Colour | Meaning | States |
| --- | --- | --- |
| `danger` | Someone must act, nobody has yet | open, fault, high, critical |
| `warn` | Someone is on it | assigned, diagnosed, approved, in progress, maintenance, medium |
| `ok` | It works or is done | operational, resolved, closed |
| `neutral` | Not in play | decommissioned, low |

The word is always there, so colour is never the only signal. Render through `status_badge()` so the mapping lives in one place.

**What the consumer provides:** the status key; the label comes from i18n.
