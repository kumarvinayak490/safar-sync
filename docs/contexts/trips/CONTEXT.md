# Trips Context

This context covers Trips, Trip Profile, public trip page content, publication, packages, itinerary, confirmation requirements, booking availability, and capacity.

## Language

**Trip**:
A sellable group travel offering presented by an organizer to travelers; before departures are introduced, a trip represents one scheduled run.
_Avoid_: Experience, package, tour

**Trip Overview**:
The private trip workspace summary for one selected trip.
_Avoid_: Trip profile, public trip page

**Trip Profile**:
The editable traveler-facing trip content and commercial terms used to publish a public trip page.
_Avoid_: Trip overview, operations dashboard

**Published Trip Profile Lock**:
The lock created when a public trip page is published, preventing normal edits to launch-critical trip profile content.
_Avoid_: Archive, payment lock, trip status

**Trip Profile Publication Readiness**:
Whether a trip profile has enough reviewed content and commercial terms to publish a public trip page.
_Avoid_: Payment readiness, booking availability, organizer readiness

**Trip Description**:
The rich text description of a trip shown on the public trip page.
_Avoid_: Internal notes, itinerary

**Trip Rich Text**:
Structured rich text used for trip profile copy.
_Avoid_: Markdown string, raw HTML

**Trip Media Gallery**:
The ordered media gallery for a trip profile.
_Avoid_: Operational files, traveler documents, social feed

**Trip Media Item**:
An uploaded media asset in a trip media gallery.
_Avoid_: External URL, document

**Package**:
A selectable commercial option for a traveler within a trip.
_Avoid_: Booking, room, ticket

**Withdrawn Package**:
A package no longer selectable for new bookings while retained for historical booking context.
_Avoid_: Deleted package

**Payment Schedule**:
The trip-level payment terms that define reservation and balance milestones.
_Avoid_: Installment plan

**Payment Milestone**:
A required payment point in a trip payment schedule.
_Avoid_: Invoice

**Reservation Milestone**:
The first payment milestone required to reserve seats.
_Avoid_: Deposit deadline

**Balance Milestone**:
The later payment milestone for the remaining booking balance.
_Avoid_: Installment

**Itinerary**:
The trip's planned sequence of itinerary days.
_Avoid_: Operations checklist

**Itinerary Day**:
A day entry in a trip itinerary.
_Avoid_: Schedule item

**Trip Start Date**:
The first scheduled date of a trip.
_Avoid_: Departure date

**Trip Date Change**:
An organizer-controlled change to a trip's scheduled date range after trip setup.
_Avoid_: Itinerary edit

**Trip Capacity**:
The maximum number of travelers that can be reserved for a trip.
_Avoid_: Available seats

**Available Seats**:
The number of seats remaining after active reserved travelers are counted.
_Avoid_: Manually edited inventory

**Bookable Seats**:
The seats available to a new booking attempt after current active holds and reservations are considered.
_Avoid_: Available seats

**Booking Availability**:
Whether travelers can create and reserve bookings for a trip.
_Avoid_: Publication state, trip status

**Open Booking Availability**:
A trip state in which travelers can start and reserve bookings.
_Avoid_: Live booking

**Closed Booking Availability**:
A trip state in which travelers cannot create or reserve new bookings because the organizer has closed booking.
_Avoid_: Sold out

**Sold Out Booking Availability**:
A derived trip state in which travelers cannot reserve because capacity is unavailable.
_Avoid_: Closed booking

**Availability Band**:
The public availability label shown instead of exact available seat counts.
_Avoid_: Exact seats left

**Public Trip Page**:
The shareable traveler-facing page for a trip.
_Avoid_: Microsite, landing page

**Public Trip URL**:
The TripOS-hosted URL for a public trip page.
_Avoid_: Custom domain

**Public Booking Gate**:
The trip-owned rule that determines whether a traveler can start public booking from a public trip page.
_Avoid_: Discovery listing rule, demand page rule, publication state

**Completed Trip**:
A trip marked complete by the organizer after operations are done.
_Avoid_: Archived trip

**Trip Cancellation**:
The owner-controlled cancellation of an entire trip.
_Avoid_: Archived trip, booking cancellation

**Trip Duplicate**:
A new trip created by copying setup from an existing trip.
_Avoid_: Departure, clone

**Paid Trip**:
A trip whose bookings require a payable booking total greater than zero.
_Avoid_: Free event, RSVP

**Departure**:
A future scheduled run of a reusable trip template.
_Avoid_: Current trip

## Relationships

- An **Organizer** can offer one or more **Trips**.
- A **Trip** is owned by an **Organizer**.
- **Trips** own trip profile, packages, itinerary, confirmation requirements, booking availability, trip profile publication readiness, public trip pages, and trip publication state.
- **Trip Bookings**, **Trip Travelers**, **Trip Payments**, and **Trip Operations** belong to a **Trip** but are separate trip-scoped domains.
- **Trips** are managed from a **Trip Workspace** inside the **Operations Dashboard**.
- A **Trip Workspace** has exactly one selected **Trip**.
- A **Trip** has one **Trip Profile**.
- A **Trip Profile** includes one **Trip Description**, one **Trip Media Gallery**, one or more **Packages**, one **Payment Schedule**, one **Itinerary**, and **Confirmation Requirements**.
- Publishing a **Public Trip Page** requires **Trip Profile Publication Readiness**.
- Publishing a **Public Trip Page** creates a **Published Trip Profile Lock**.
- A **Published Trip Profile Lock** blocks normal edits to launch-critical profile and commercial content but does not block trip operations after publication.
- **Trips** own **Public Trip Page** content, **Publication State**, **Booking Availability**, and the **Public Booking Gate**.
- Public booking URLs and checkout behavior are owned by **Trips**, **Trip Bookings**, and **Trip Payments**, not **Public Discovery Catalog**.
- A **Public Booking Gate** allows **Public Booking** only when the **Public Trip Page** is published, **Booking Availability** is open, at least one payment method is ready, and **Bookable Seats** are sufficient.
- **Available Seats** are derived from **Trip Capacity** minus active reserved travelers.
- **Sold Out Booking Availability** is derived from **Available Seats**.

## Flagged Ambiguities

- "trip" was used to mean both a reusable travel template and a scheduled run — resolved: **Trip** currently means one scheduled offering; **Departure** is reserved for future repeated runs.
- "trip overview" could mean either the workspace summary or editable traveler-facing details — resolved: **Trip Overview** is the workspace summary, while **Trip Profile** is the editable trip-facing record.
- "trips module" could become a large catch-all for every trip-scoped concern — resolved: **Trips** owns core profile/publication/availability, while **Trip Bookings**, **Trip Travelers**, **Trip Payments**, and **Trip Operations** remain separate trip-scoped domains.
- "payment readiness" could block public page publication — resolved: payment method readiness gates **Public Booking**, not **Public Trip Page** publication.
- "public availability" could expose exact seat counts — resolved: the **Public Trip Page** shows **Availability Bands** instead.
