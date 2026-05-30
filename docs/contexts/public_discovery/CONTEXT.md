# Public Discovery Context

This context covers Public Discovery Catalog, Demand Pages, discovery SEO metadata, discovery routing, and listing rules.

## Language

**Public Discovery Catalog**:
The TripOS public discovery domain for demand pages, SEO metadata, discovery routing, and listing rules that compose published organizer and trip pages.
_Avoid_: Marketplace, travel marketplace, booking marketplace

**Demand Page**:
An SEO-focused public discovery page that distributes traveler demand for a specific travel pattern to relevant published organizer and trip pages.
_Avoid_: Distribution page, trip, public trip page, booking request, waitlist

**Configured Demand Page**:
A staff-configured demand page with public copy, SEO metadata, demand pattern, and selected or rule-matched organizer and trip links.
_Avoid_: Auto-generated thin page, booking page

**Discovery SEO Metadata**:
The search-facing title, description, canonical URL, structured metadata, and indexability settings for public discovery pages.
_Avoid_: Trip profile content, organizer profile content, ad copy

**Discovery Routing**:
The public URL and route ownership for discovery pages such as demand pages and catalog pages.
_Avoid_: Public trip URL ownership, booking route, operations route

**Discovery Listing Rule**:
A configured or rule-based selection that decides which published organizer or trip pages appear on a discovery page.
_Avoid_: Booking rule, payment rule, manual curation only

**TripOS Marketing Site**:
The public TripOS-owned site that explains TripOS to prospective organizers.
_Avoid_: Public trip page, organizer public page, operations dashboard

**Organizer Public Page**:
The public page for an organizer that composes organizer profile content, public organizer media, organizer policies, and published offered trips.
_Avoid_: Organizer dashboard, organizer settings, public trip page

**Organizer Public URL**:
The TripOS-hosted URL for an organizer public page.
_Avoid_: Organizer dashboard URL, custom domain

**Public Trip Page**:
The shareable traveler-facing page for a trip.
_Avoid_: Microsite, landing page

**Public Trip URL**:
The TripOS-hosted URL for a public trip page.
_Avoid_: Custom domain

**Demand Page URL**:
The TripOS-hosted URL for a demand page.
_Avoid_: Trip URL, public trip URL, booking URL

## Relationships

- The **Public Discovery Catalog** can list **Organizer Public Pages** and published **Public Trip Pages**.
- The **Public Discovery Catalog** owns **Demand Pages**, **Discovery SEO Metadata**, **Discovery Routing**, and **Discovery Listing Rules**.
- The **Public Discovery Catalog** composes **Published Organizer Profile** and published **Public Trip Pages**.
- **Public Discovery Catalog** owns **Discovery Routing** and **Discovery Listing Rules** for **Organizer Public Pages**.
- **Public Discovery Catalog** can own **Discovery Routing** and **Discovery Listing Rules** around published **Public Trip Pages**.
- **Public Discovery Catalog** can host and link to **Organizer Public Pages** and **Public Trip Pages**, but does not own their source content or booking rules.
- An **Organizer Public URL** lives in **Public Discovery Catalog** routing.
- An **Organizer Public Page** content comes from **Organizer Profile**, **Organizer Media**, **Organizer Policies**, and published **Public Trip Pages**.
- The **Public Discovery Catalog** lists only **Published Organizer Profile** and published **Public Trip Pages**.
- **Demand Pages** should link only to published **Public Trip Pages** whose **Organizer** has **Published Organizer Profile**.
- A first-version **Demand Page** is a **Configured Demand Page**.
- A **Configured Demand Page** uses **Discovery Listing Rules** to select relevant organizer and trip links.
- A **Configured Demand Page** belongs to **Public Discovery Catalog**.
- A **Demand Page** does not create **Bookings** or **Booking Requests**.
- A **Demand Page** does not own checkout, payment, booking rules, or trip operations.
- The **TripOS Marketing Site** is distinct from **Public Discovery Catalog**, **Organizer Public Pages**, and **Public Trip Pages**.

## Flagged Ambiguities

- "marketplace" could imply TripOS-owned checkout, split settlement, reviews, and marketplace policies — resolved: use **Public Discovery Catalog** for SEO-friendly discovery of organizers and published trips while booking remains on **Public Trip Pages**.
- "demand page" could imply a trip, waitlist, or booking request — resolved: a **Demand Page** is SEO-focused public discovery and does not create bookings by itself.
- "public discovery" could become a second owner of organizer or trip pages — resolved: **Public Discovery Catalog** owns demand pages, SEO metadata, discovery routing, and listing rules, but composes published organizer and trip pages from their owning domains.
- "public trip page route" could make discovery own checkout behavior — resolved: **Public Discovery Catalog** may own discovery routing/listing around public trip pages, while **Trips**, **Trip Bookings**, and **Trip Payments** own content, publication, booking gates, booking URLs, and checkout behavior.
