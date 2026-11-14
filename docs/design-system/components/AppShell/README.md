# AppShell

Every signed-in page: a brand bar on top, a sidebar in three coloured sections, and the page in `main`.

- **Brand bar:** solid `brand-deep`, the white mark and the name in white, a 4px `--gradient-brand` rule underneath. The avatar sits on the right in a white ring. Public pages use the same bar with Library and Sign in as translucent white buttons.
- **Sidebar:** Home and Dashboard on top, then three sections with uppercase 11px headings: *Equipment* (`primary`), *Grow the network* (`accent`), *Community* (`lead`). Each link has a 30px icon tile in its section's tint; the active link fills the tile with the section colour and tints the row.
- Profile and Sign out live in the avatar menu, not the sidebar. Applicants see two links only (start, library): show less, unlock more.
- Phones: the sidebar becomes a drawer. Folded on desktop: tiles only, each link keeps a `title`.
