# Team Access Context

This context covers organizer access control, memberships, invitations, roles, and ownership invariants.

## Language

**Team Access**:
The organizer-owned access-control submodule for managing owner and operator memberships, invitations, and ownership invariants.
_Avoid_: Users, staff, account access

**Organizer Membership**:
The relationship that lets a user act for an organizer with a role.
_Avoid_: Account membership

**Organizer Invitation**:
An invitation sent to an email address that lets a person become a user with an owner or operator organizer membership.
_Avoid_: Direct user creation, staff invite

**Owner**:
A user role that can manage organizer profile, organizer settings UI actions, team access, organizer payments, and all trips for an organizer.
_Avoid_: Admin

**Operator**:
A user role that can manage trip operations, non-commercial trip profile content other than packages, booking confirmation, manual payment approvals, and closing bookings, but cannot manage organizer payments, team access, publication, opening bookings, trip capacity, post-booking trip dates, or packages.
_Avoid_: Staff, helper

## Relationships

- An **Organizer** has **Team Access**.
- **Team Access** manages **Organizer Memberships** and **Organizer Invitations**.
- A **User** has one **Organizer Membership** for each **Organizer** they act for.
- An **Organizer Membership** has an **Owner** or **Operator** role.
- An **Organizer Invitation** creates an **Organizer Membership** when accepted.
- An **Organizer** can have multiple **Owner** memberships.
- An **Organizer** must always have at least one **Owner** membership.
- **Organizer Settings** can link to **Team Access** in the user interface, but does not own **Team Access**.

## Flagged Ambiguities

- "users" was too broad for organizer-facing access management — resolved: use **Team Access** for memberships and invitations.
- "team access" could look like a generic settings preference — resolved: **Team Access** is its own organizer submodule; Settings may link to it in the UI but does not own it.
- "admin" was too broad for organizer access — resolved: MVP uses **Owner** and **Operator** roles.
