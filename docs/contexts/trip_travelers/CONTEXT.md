# Trip Travelers Context

This context covers traveler slots, traveler identity details, traveler documents, readiness, check-in, and traveler-level changes.

## Language

**Trip Travelers**:
The trip-scoped traveler readiness domain for traveler slots, traveler identity details, traveler documents, traveler check-in, and traveler-level changes.
_Avoid_: Booking contact, user account, customer profile

**Traveler**:
A person attending a trip.
_Avoid_: Booking contact, customer, user

**Traveler Slot**:
A place in a booking intended for one traveler before identity details are complete.
_Avoid_: Empty traveler

**Traveler Identity Details**:
The basic details that identify the person attending a trip.
_Avoid_: Traveler documents, confirmation requirements

**Active Traveler**:
A traveler inside a reserved or confirmed booking who has not been cancelled or replaced.
_Avoid_: Paid traveler

**No-Show Traveler**:
A traveler marked as not having joined the trip without cancelling their place.
_Avoid_: Cancelled traveler

**Traveler Check-In**:
The organizer action of marking that a traveler has arrived or joined the trip.
_Avoid_: QR check-in, attendance app

**Traveler Cancellation**:
The organizer-controlled removal of one traveler from a booking.
_Avoid_: Booking cancellation, drop-out

**Traveler Replacement**:
Replacing one traveler in a booking with another person while preserving the seat.
_Avoid_: Traveler addition

**Traveler Addition**:
Adding another traveler to an existing booking.
_Avoid_: Traveler replacement, new booking

**Traveler Document**:
An identity or eligibility document collected for a traveler.
_Avoid_: Booking document, upload

**Travel Logistics**:
Traveler-specific arrival, departure, and operational details relevant to a trip.
_Avoid_: Itinerary

**Emergency Contact**:
Traveler-provided emergency contact information requested by the organizer.
_Avoid_: Booking contact

**Medical Disclosure**:
Traveler-provided health information requested by the organizer for trip readiness.
_Avoid_: Medical record

**Sensitive Traveler Information**:
Traveler information that should be handled with restricted visibility and explicit export choice.
_Avoid_: Routine export field

**Traveler Data Request**:
An organizer-mediated request for traveler readiness information.
_Avoid_: Self-serve traveler profile

**Document State**:
The review state of a traveler document.
_Avoid_: Traveler state

**Missing Document**:
A required traveler document that has not been submitted.
_Avoid_: Rejected document

**Submitted Document**:
A traveler document submitted for organizer review.
_Avoid_: Approved document

**Approved Document**:
A traveler document accepted by the organizer.
_Avoid_: Verified identity

**Rejected Document**:
A traveler document rejected by the organizer.
_Avoid_: Missing document

**Confirmation Requirements**:
The trip-level requirements that determine what traveler readiness information is needed.
_Avoid_: Organizer default requirements, policy

## Relationships

- A **Traveler Slot** may become a **Traveler** when **Traveler Identity Details** are complete.
- An **Active Traveler** belongs to a **Reserved Booking** or **Confirmed Booking**.
- **Traveler Check-In** applies to one **Active Traveler**.
- **Traveler Check-In** is performed by an **Owner** or **Operator** in the MVP.
- Traveler changes after reservation are organizer-controlled.
- **Traveler Cancellation** releases the seat by default.
- **Traveler Replacement** preserves seat count.
- **Traveler Addition** increases the booking's traveler count and requires enough available seats.
- **Traveler Documents** belong to the specific **Traveler**, not the booking.
- **Medical Disclosure** is **Sensitive Traveler Information**.
- **Confirmation Requirements** can change after bookings exist without automatically changing **Booking State**.

## Flagged Ambiguities

- "traveler" was used to mean both the attendee and the person managing the purchase — resolved: **Traveler** attends the trip, while **Booking Contact** manages communication and payment coordination.
- "traveler with no name" was semantically awkward — resolved: use **Traveler Slot** until identity details are complete.
- "traveler identity" could be confused with readiness requirements — resolved: **Traveler Identity Details** identify the person, while **Confirmation Requirements** cover additional readiness data.
- "document" could have belonged to a booking or a traveler — resolved: identity and eligibility documents are **Traveler Documents**.
