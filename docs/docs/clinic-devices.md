# Look after your clinic's devices

What a clinic sees once its devices are registered: what needs someone today, every device by ward, when each one is next due for a service, and what engineers may show about the clinic on their profiles.

## Needs you today

The **Dashboard** opens with **Needs you today**, one short list for the clinic:

- **Open faults**, red when the severity is high or critical. **Open** goes to the fault.
- **Overdue services**, in red. **Log service** opens the maintenance log for that device.
- **Services due in the next 14 days**, in orange.

When nothing is waiting, the card says **All clear**. Only the first items show; the rest are on the device list (**Devices → Needs attention**).

## Your devices by ward

Under the list, **Your devices by ward** groups every device by the first part of its location ("Ward 3 / Room 7" goes under *Ward 3*). Each device is a chip with a coloured dot:

| Dot | Means |
| --- | --- |
| Green | Working, service on time |
| Orange | In maintenance, or its service is overdue |
| Red | Has an open fault |
| Grey | Decommissioned |

Devices that need someone come first in each ward. Tap a chip to open the device.

## The device ID card

Each device page starts with an ID card: photo, type, brand and model, location and status, then the main actions (**Report a problem**, **Call an engineer**, **Start maintenance log**, **Ask for a spare part**, **Show QR**) and three tiles:

- **Next service**: the date, and whether it is on track, due soon or overdue.
- **Manuals**: how many are attached. Library manuals for the same brand and model show too. With none, anyone can tap **Find this manual** to ask the community (see [Claims, task board and missing manuals](community-work.md)).
- **Repairs**: how many faults are still open.

Owners, location, history and the QR code are folded under **More details**.

## Service intervals and reminders

Every device category has a service interval in months (for example 6 months). A device can override it on its edit page (**Service every**). When a maintenance log is closed, the next service date moves forward by that interval, or to the date written in the log.

The admins of the clinic and of the organization that maintains the device get one email when a service is due within 14 days and one when it is overdue, once per due date. Set `MAINTENANCE_REMINDERS=off` in `.env` to stop the emails.

## Privacy: your devices on engineer profiles

Engineers who register a clinic's devices get a line on their public profile for each one ("Ventilator · Mulago Hospital"). On the clinic's page, the **Privacy** tab lets its admins:

- **Show our devices on engineer profiles** (on by default), and
- **Hide our name there**, so the line reads "Ventilator · a clinic".

A preview shows what an engineer's profile will display.
