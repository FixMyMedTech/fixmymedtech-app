# Claims, task board and missing manuals

How members get recognised for work the app cannot see, how small community jobs are shared out with points, and how a missing manual becomes a task.

## Claim an achievement

Some achievements count by themselves (devices registered, clinics invited). Others can't: an event you organised, a clinic you introduced, someone you supported. Those are *recognised* achievements, and you claim them.

1. Open **Teams and achievements**, pick an achievement your team recognises and tap **Claim it** (or go straight to `/community/claims`).
2. Choose the achievement, how many times, and what happened (where, when, who was there). A photo helps the team say yes quickly.
3. Tap **Send to my team**. Under **My claims** you follow it: *Waiting for the team*, *They asked for more*, *Confirmed* or *Declined*.
4. If the team asks for more, answer under the claim (you can add a photo) and tap **Send again**.

Once confirmed, the achievement is recorded and your star level goes up.

## Validate claims (team members and leads)

Members of a team see **To validate** in the sidebar (`/lead`). It lists:

- **Claims to validate** for your team's achievements, with the note and the proof photo. A **lead** (or a superuser) confirms alone. Otherwise **two team members** must agree: the first **I agree** counts as one of two.
- **Ask for more** (with a short note) sends the claim back to its author. **Decline** closes it.
- **Tasks to check** from the task board.
- Shortcuts to **Talks** (for talk hosts), **Team admin** (for those who can see it) and the **Task board**.

You can't validate your own claim.

## The task board

**Task board** (`/community/tasks`) holds small jobs that grow the network:

| Kind | Example |
| --- | --- |
| Find a manual | Find the service manual of a Mindray BeneHeart D3 |
| Verify a clinic | Check that a newly registered clinic exists |
| Brands and models | Fill in the models a brand sells in the region |
| Other | Anything else the community needs |

1. **Post a task** (members): kind, what needs doing, details and points (10 by default).
2. **I'll do it** takes an open task; it moves to **Mine**. **Give it back** reopens it.
3. **Done**, with a note or link, sends it for a check.
4. The task's **author** or a **team lead** checks it: **Looks good** gives the points, **Send back** returns it. The person who did the task never checks it.

The top of the board shows your points and the top five.

## Missing manuals

- **On a device page**, when no manual is attached and none is in the library for that model, tap **Find this manual**. It posts a *Find a manual* task worth 20 points. If someone already asked for the same brand and model, the existing task is reused.
- **In the Library**, a search with no result offers **Can't find it?**: give the brand and model and tap **Find this manual**. Visitors are asked to log in first.
- **By brand and model.** Without a search, the Library lists FixMyMedTech's documents grouped by brand, then model. A device page also shows library manuals of the same brand and model, under *Also in the library for …*, even when they are not attached to it.

## Where the code is

| Piece | File |
| --- | --- |
| Claims and task board API (`/api/community/claims…`, `/api/community/tasks…`) | `backend/routers/community_work.py` |
| Tables `achievement_claims`, `community_tasks` | `infrastructure/migrations/033_claims_and_tasks.sql` |
| Pages `/lead`, `/community/claims`, `/community/tasks` | `frontend/features/community/pages/work.py` |
| Manuals of the same model on a device | `backend/routers/documents.py` `device_documents` |
| Text in three languages | `frontend/i18n.py`, keys `w5.*` |
