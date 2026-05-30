# Trip Bookings Context

This context covers booking lifecycle, manual bookings, booking imports, booking contact, booking access, and booking state.

## Language

**Trip Bookings**:
The trip-scoped booking domain for reservations, manual bookings, booking imports, booking state, access links, and booking contact coordination.
_Avoid_: Trip profile, traveler account, payment setup

**Public Booking**:
A traveler-initiated booking created from a public trip page.
_Avoid_: Manual booking, unpaid booking request

**No-Login Public Booking**:
A public booking flow where the traveler or booking contact does not create a user account.
_Avoid_: Traveler account, customer login

**Bookings Opening Soon**:
The public trip page message shown when the page is visible but public booking is not available yet.
_Avoid_: Waitlist, booking request, manual payment instructions

**Booking Contact**:
The person responsible for a booking's communication and payment coordination.
_Avoid_: Traveler, customer, payer

**Booking Contact Details**:
The name and phone number required to contact a booking contact, with email optional in the MVP.
_Avoid_: Traveler details

**Booking**:
A reservation for one trip that groups one or more travelers under one booking contact.
_Avoid_: Order, registration, purchase

**Manual Booking**:
A booking created by a user from the organizer dashboard rather than by a booking contact from the public trip page.
_Avoid_: Offline booking

**Booking Import**:
An organizer-uploaded import of existing booking, traveler, and payment records into a trip.
_Avoid_: Generic import, ETL

**Booking Access Link**:
A time-limited link that lets a booking contact or traveler access booking information without creating a user account.
_Avoid_: Traveler account, login

**Traveler Portal**:
The no-login booking access surface reached through booking access links.
_Avoid_: Booking access link, traveler account

**Access Link Expiry**:
The time after which a booking access link no longer grants access.
_Avoid_: Login expiry

**Booking-Level Access Link**:
A booking access link for the booking contact.
_Avoid_: Traveler link

**Traveler-Level Access Link**:
A booking access link for one traveler.
_Avoid_: Booking link

**Booking State**:
The operational reservation lifecycle state of a booking.
_Avoid_: Payment status, booking status

**Draft Booking**:
A booking intent that has not yet reserved seats.
_Avoid_: Lead, booking request

**Draft Expiry**:
The time after which a draft booking is no longer recoverable.
_Avoid_: Seat hold expiry

**Reserved Booking**:
A booking whose seats are reserved after required reservation money is collected.
_Avoid_: Confirmed booking

**Confirmed Booking**:
A reserved booking that the organizer has accepted as ready for the trip.
_Avoid_: Paid booking

**Unconfirm Booking**:
The organizer action of moving a confirmed booking back to reserved without cancelling it.
_Avoid_: Cancellation

**Cancelled Booking**:
A booking that is no longer active.
_Avoid_: Traveler cancellation

**Completed Booking**:
A booking completed by organizer action when the trip is complete.
_Avoid_: Fully paid booking

## Relationships

- A **Trip** can have one or more **Bookings**.
- A **Booking** belongs to exactly one **Trip**.
- A **Manual Booking** is a type of **Booking**.
- A **Manual Booking** is created from the **Operations Dashboard**, not the **Public Trip Page**.
- A **Booking Import** creates or updates bookings for exactly one **Trip**.
- A **Booking** has exactly one **Booking Contact**.
- A **Booking Contact** has **Booking Contact Details** before payment starts.
- Public booking requires booking contact details, traveler count, package selection, and pricing inputs before payment starts.
- Public booking does not require full traveler identity details before payment starts in the MVP.
- A **Booking** has one or more **Booking Access Links**.
- The **Traveler Portal** is accessed through **Booking Access Links**.
- **Booking-Level Access Link** is sent to the **Booking Contact** by default after reservation.
- A **Booking** contains one or more **Traveler Slots**.
- A **Booking** reserves all of its travelers' seats only after its **Booking Reservation Amount** is paid.
- **Draft Booking** does not reserve seats.
- **Manual Bookings** do not require **Provider Payment Setup**.

## Flagged Ambiguities

- "booking" was considered as either one reservation per traveler or one reservation containing travelers — resolved: a **Booking** can contain one or more **Traveler Slots**.
- "offline booking" could imply bypassing the model — resolved: use **Manual Booking**, which follows the same reservation rules as other bookings.
- "traveler account" would add customer-side auth friction — resolved: travelers and booking contacts use **Booking Access Links** in the MVP.
- "booking request" could create an unpaid public flow while payments are not ready — resolved: **Public Booking** requires at least one ready payment method; unpaid public booking requests are out of scope.
