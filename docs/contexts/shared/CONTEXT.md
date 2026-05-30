# TripOS Shared Context

TripOS is a domain for operating group travel experiences, where organizers manage trips, travelers, bookings, payments, and trip operations in one place.

## Language

**Organizer**:
A business, community, brand, or group that operates trips and owns the related commercial and operational records.
_Avoid_: User, creator, host, account

**User**:
A person who signs in to TripOS and acts for one or more organizers.
_Avoid_: Organizer, traveler, customer

**Owner**:
A user role that can manage organizer profile, organizer settings UI actions, team access, organizer payments, and all trips for an organizer.
_Avoid_: Admin

**Operator**:
A user role that can manage trip operations, non-commercial trip profile content other than packages, booking confirmation, manual payment approvals, and closing bookings, but cannot manage organizer payments, team access, publication, opening bookings, trip capacity, post-booking trip dates, or packages.
_Avoid_: Staff, helper

**Operations Dashboard**:
The organizer-facing workspace for managing trip operations.
_Avoid_: Admin dashboard, organizer dashboard

**Trip Workspace**:
The private trip-scoped operations surface for managing one selected trip.
_Avoid_: Selected Trip mode, global workspace

**Internal Admin**:
The thin TripOS staff surface for orchestrating module-owned support and configuration actions during pilots.
_Avoid_: Internal CRM, support dashboard, business state owner

**Community-Led Organizer**:
An organizer that repeatedly sells paid trips to a creator audience, community, or affinity group.
_Avoid_: Travel agency, corporate planner, friend group

**Publication State**:
The visibility state of a public trip page.
_Avoid_: Booking availability, trip status

**Draft Publication**:
A public page that is not visible to travelers.
_Avoid_: Inactive trip

**Published Publication**:
A public page that is visible to travelers.
_Avoid_: Open booking

**Archived Publication**:
A public trip page hidden from normal public sharing while retained for records.
_Avoid_: Deleted trip

**Notification Channel**:
A delivery medium for notifications.
_Avoid_: Chat thread

**WhatsApp Channel**:
The notification channel used for WhatsApp delivery.
_Avoid_: WhatsApp group chat

**Email Channel**:
The notification channel used for email delivery.
_Avoid_: SMS

## Relationships

- An **Organizer** can have one or more **Users**.
- A **User** can act on behalf of one or more **Organizers**.
- **Owner** and **Operator** are organizer membership roles.
- **Internal Admin** is TripOS staff tooling and is not the same thing as organizer-facing **Operations Dashboard**.
- TripOS remains a modular monolith unless a future ADR explicitly changes deployment boundaries.

## Flagged Ambiguities

- "organizer" was used to mean both the operating entity and the person using the product — resolved: **Organizer** is the operating entity, **User** is the login identity.
- "admin" could mean organizer-facing operations or TripOS staff support — resolved: use **Operations Dashboard** for organizer-facing work and **Internal Admin** for TripOS staff support.
- "published" does not mean bookable — resolved: **Publication State** controls visibility, while booking ability is controlled separately.
