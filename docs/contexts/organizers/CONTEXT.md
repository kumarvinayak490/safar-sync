# Organizers Context

This context covers the Organizer root, organizer onboarding, setup checklist, and organizer-level ownership. Read with the specific organizer sub-contexts for profile, media, policies, team access, payments, or creative setup work.

## Language

**Organizer**:
A business, community, brand, or group that operates trips and owns the related commercial and operational records.
_Avoid_: User, creator, host, account

**Organizer Logo**:
The optional uploaded logo image shown as part of an organizer's profile on traveler-facing surfaces.
_Avoid_: Logo URL, external logo

**Organizer Settings**:
The organizer-facing UI grouping for organizer-level setup links and preferences.
_Avoid_: Backend domain owner, organizer profile, global settings, trip setup

**Organizer Setup Checklist**:
A post-onboarding organizer-level readiness view for completing shared setup before and alongside trip creation.
_Avoid_: Onboarding gate, trip launch checklist; UI may call this Setup guide

**Organizer Onboarding**:
The initial setup in which a user creates an organizer, becomes its first owner, and establishes initial organizer profile basics to enter the operations dashboard.
_Avoid_: Trip setup, launch setup

**Operations Dashboard**:
The organizer-facing workspace for managing trip operations.
_Avoid_: Admin dashboard, organizer dashboard

**Community-Led Organizer**:
An organizer that repeatedly sells paid trips to a creator audience, community, or affinity group.
_Avoid_: Travel agency, corporate planner, friend group

## Relationships

- **Organizer Onboarding** creates one **Organizer** and one first **Owner** membership.
- An **Organizer** has one **Operations Dashboard**.
- **Organizer Onboarding** leads to the **Organizer Setup Checklist**.
- **Organizer Settings** is a UI grouping, not a domain owner.
- **Organizer Settings** can link to module-owned setup areas, but does not own them.
- An **Organizer** has **Organizer Profile**, **Organizer Media**, **Organizer Policies**, **Team Access**, **Organizer Payments**, and **Creative Setup**.
- An **Organizer** can offer one or more **Trips**.
- A **Trip** is owned by an **Organizer** but is not part of **Organizer Profile**, **Organizer Settings**, **Organizer Media**, **Organizer Policies**, **Organizer Payments**, or **Team Access**.

## Flagged Ambiguities

- "organizer identity" sounded like a separate product module and overlapped with **Organizer Profile** — resolved: retire Organizer Identity as a domain term.
- "global settings" was too broad — resolved: **Organizer Settings** is only a UI grouping for organizer-level setup links and preferences, not a backend domain owner.
- "organizer settings" could become a backend junk drawer — resolved: real domain ownership belongs to Profile, Media, Policies, Team Access, Organizer Payments, Creative Setup, Trips, and Public Discovery.
