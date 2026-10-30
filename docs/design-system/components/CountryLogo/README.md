# CountryLogo

A country or continent logo is the mark in white on the shape of the place, filled with the brand gradient. The shape tells the country; the colours never change.

**Build one**
1. Take the outline from Natural Earth with its main islands. Simplify until it reads at 64px.
2. Fill it with the brand gradient at 135°: `brand-teal` top-left, `brand-deep` bottom-right. Two stops, no others.
3. Place the white one-colour mark at 55–60% of the shape's width, centred on the heaviest part of the land, not the bounding box. For thin countries, size it on the widest part and let it overhang the coast.
4. Fill the mark white; do not cut it out of the shape.
5. Export colour, black and white, each as SVG and 1024px PNG, named `fixmymedtech-<country>-<rendering>`.

**Use it** on sign-in screens (the deployment's `LOGO_URL`), country pages, slides and posters. Never below 64px, never on the gradient itself, never in national flag colours.

**What the consumer provides:** the outline and the country name for `alt` ("FixMyMedTech Cameroon").
