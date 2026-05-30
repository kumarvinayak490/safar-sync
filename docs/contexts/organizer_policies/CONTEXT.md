# Organizer Policies Context

This context covers organizer-owned public legal and trust policy content.

## Language

**Organizer Policies**:
The organizer-owned legal and trust policy content reused by public organizer and trip surfaces.
_Avoid_: Organizer profile identity, platform policies, payment setup, trip operations

**Organizer Public Policy**:
Organizer-owned public policy text shown on public organizer and trip surfaces.
_Avoid_: Platform terms, payment setup, internal SOP

**Organizer Privacy Policy**:
The organizer-owned public policy describing how the organizer handles traveler privacy.
_Avoid_: Platform privacy policy, internal data policy

**Organizer Refund Policy**:
The organizer-owned public policy describing refund expectations for the organizer's trips.
_Avoid_: Platform refund policy, payment setup

**Organizer Cancellation Policy**:
The organizer-owned public policy describing cancellation expectations for the organizer's trips.
_Avoid_: Trip cancellation action, booking cancellation action

## Relationships

- An **Organizer** has **Organizer Policies**.
- **Organizer Policies** includes **Organizer Privacy Policy**, **Organizer Refund Policy**, and **Organizer Cancellation Policy** in the first version.
- **Organizer Policies** provides policy content for an **Organizer Public Page** and **Public Trip Pages**.
- **Organizer Profile Readiness** requires required **Organizer Policies**.
- **Owners** can edit **Organizer Policies** in the first version.
- **Operators** can view **Organizer Policies** but cannot edit policies in the first version.

## Flagged Ambiguities

- "policies" could be mistaken for organizer profile identity fields — resolved: **Organizer Policies** is its own organizer submodule, required for publishing **Organizer Profile**.
- "marketplace policies" could imply TripOS owns trip fulfillment terms — resolved: organizer public policies are organizer-owned, not platform-owned marketplace policies.
