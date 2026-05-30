# Internal Admin Context

This context covers TripOS staff-facing orchestration for module-owned support and configuration actions.

## Language

**Internal Admin**:
The thin TripOS staff surface for orchestrating module-owned support and configuration actions during pilots.
_Avoid_: Internal CRM, support dashboard, business state owner

**Configured Demand Page**:
A staff-configured demand page with public copy, SEO metadata, demand pattern, and selected or rule-matched organizer and trip links.
_Avoid_: Auto-generated thin page, booking page

**Platform Fee Statement**:
A periodic statement of platform fees owed by an organizer.
_Avoid_: Payment setup billing

**Platform Fee**:
The organizer-absorbed fee TripOS records on successful provider payments and collects from the organizer later.
_Avoid_: Payment provider fee, traveler fee

## Relationships

- **Internal Admin** orchestrates module-owned staff actions and does not own **Organizer**, **Trip**, **Public Discovery**, **Booking**, **Traveler**, or **Payment** business state.
- **Internal Admin** provides the staff workflow for configuring **Configured Demand Pages** in the first version.
- A **Configured Demand Page** belongs to **Public Discovery Catalog**.
- **Internal Admin** can manage the staff workflow for **Platform Fee Statements** in the MVP.
- **Trip Payments** provides **Platform Fee** facts for **Platform Fee Statements**.
- **Organizer Payments** does not manage **Platform Fee Statements** in the MVP.

## Flagged Ambiguities

- "internal admin" could become the real owner of staff-managed records — resolved: **Internal Admin** is a thin orchestration surface for module-owned actions, not a business state owner.
- "admin" could mean either organizer-facing operations or TripOS staff support — resolved: use **Operations Dashboard** for organizer-facing work and **Internal Admin** only for TripOS staff support.
