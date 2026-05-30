# Organizer Profile Context

This context covers public organizer profile content, publication state, readiness, and Organizer Public Page content ownership.

## Language

**Organizer Profile**:
The organizer-owned public facts used to generate organizer discovery and trust surfaces, including public name, logo, description, and contact channel.
_Avoid_: Organizer settings, user profile, public trip page, marketplace seller profile

**Organizer Profile Publication State**:
The visibility state of an organizer profile.
_Avoid_: Trip publication state, organizer status, onboarding state

**Organizer Profile Readiness**:
Whether an organizer profile has enough public content and required organizer policies to publish.
_Avoid_: Organizer onboarding, trip profile publication readiness, payment readiness

**Draft Organizer Profile**:
An organizer profile that is not publicly listed.
_Avoid_: Draft trip, inactive organizer

**Published Organizer Profile**:
An organizer profile that can appear in public discovery.
_Avoid_: Published trip, verified organizer

**Archived Organizer Profile**:
An organizer profile hidden from normal public discovery while retained for records.
_Avoid_: Deleted organizer, archived trip

**Public Organizer Description**:
The organizer-authored public description shown on organizer discovery and trust surfaces.
_Avoid_: Internal notes, organizer onboarding text

**Organizer Public Page**:
The public page for an organizer that composes organizer profile content, public organizer media, organizer policies, and published offered trips.
_Avoid_: Organizer dashboard, organizer settings, public trip page

**Organizer Public URL**:
The TripOS-hosted URL for an organizer public page.
_Avoid_: Organizer dashboard URL, custom domain

## Relationships

- **Organizer Profile** owns public organizer name, logo, description, and contact channel.
- **Organizer Profile** may include one **Organizer Logo**.
- **Organizer Profile** owns **Organizer Public Page** content and publication state.
- **Organizer Profile** provides public profile content to an **Organizer Public Page**.
- **Organizer Profile** has one **Organizer Profile Publication State**.
- Publishing **Organizer Profile** requires **Organizer Profile Readiness**.
- **Organizer Profile Readiness** requires **Public Organizer Description** and required **Organizer Policies**.
- **Public Organizer Media** is encouraged but not required for **Organizer Profile Readiness**.
- A public contact channel is encouraged but not required for **Organizer Profile Readiness**.
- **Owners** can edit and publish **Organizer Profile**.
- **Operators** can view **Organizer Profile** but cannot publish it in the first version.
- **Organizer Profile** does not include **Organizer Policies**, **Payment Setup**, **Team Access**, provider credentials, traveler documents, bookings, or operational metrics.

## Flagged Ambiguities

- "organizer public profile" could mix private setup and public discovery content — resolved: use **Organizer Profile** for public profile content and module-owned organizer setup for private configuration.
- "organizer profile" could mean private organizer setup or public discovery content — resolved: use **Organizer Profile** for public discovery content.
- "white-label" would expand the SaaS surface too early — resolved: MVP supports **Organizer Profile** branding only.
