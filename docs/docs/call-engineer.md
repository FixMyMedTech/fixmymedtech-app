# Call an engineer

When a device breaks, a clinic can call an engineer from the device page, much like calling a ride. Engineers nearby send a visit offer; the clinic picks one; the repair then follows the usual fault steps. Payment stays outside the app: fees are written down, nothing is charged.

## For the clinic

1. On the device page (or its QR page, or an open fault), tap **Call an engineer**.
2. Say what is happening and how urgent it is: **Device stopped** or **This week**.
3. The call page shows each step: *Call → Match → Offer → Agree → Diagnose → Repair → Sign off*. While it looks, a radar shows who has been told.
4. Engineers are told in order:
    1. the clinic's own responsible engineers,
    2. the engineer who registered the device,
    3. then, if nobody has offered after 20 minutes (*Device stopped*) or 4 hours (*This week*), Contributors who live in the clinic's city.
5. Each offer shows the engineer, their rating, a **visit fee** and an **arrival time**. Tap **Accept**, or **Ask once for less** with your price. You can counter each offer once; the engineer then accepts or declines.
6. Accepting an offer assigns the fault to that engineer and closes the other offers.
7. After the repair, answer **Does it work now?** **It works** closes the request and lets you rate the repair (1 to 5 stars). **It still doesn’t work** reopens the fault.

## For engineers

- **Requests** (sidebar) lists the requests near you and your offers. A badge says why you see it: *Your clinic*, *You registered it* or *Nearby*.
- Open one to send an offer (visit fee and arrival time) or to pass. If the clinic counters, accept or decline its price.
- Once your offer is accepted, the fault is yours: diagnose, repair and close it as in [Report a fault and get it repaired](report-fault.md).
- Requests also show on **My Tasks**, next to your assigned repairs.

Only members who finished their welcome steps can send offers.

## Settings

| Variable | Default | What it does |
| --- | --- | --- |
| `CALL_OFFER_POOL` | `city` | Who may offer after the call widens: `city` (Contributors whose city is in the clinic's address or region) |
| `CALL_CURRENCY` | `XAF` | Currency shown next to visit fees |

The proposals here (visit fee and arrival time only, one counter-offer) are still to be confirmed with the community.
