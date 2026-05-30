# Product

## Register

product

## Users

TripOS serves repeat community-led trip organizers in India who run paid group trips with roughly 10-80 travelers per trip. Primary users are Owners and Operators inside an Organizer, which is the business, community, or brand operating trips.

Users are usually managing payments, traveler readiness, documents, reminders, capacity, cancellations, and operational exports while coordinating across WhatsApp, bank/payment records, and vendor handoffs. They need fast confidence about who is reserved, who is ready, who owes money, and what needs action.

Owners manage Organizer setup, Organizer Identity, Team Access, Payment Setup, and Trip creation. Operators manage Trip operations after an Owner has created Trips, while still needing an Organizer-level entry point that explains setup and launch blockers without exposing Owner-only controls.

## Product Purpose

TripOS helps trip organizers stop managing paid group trips on WhatsApp and Excel. It centralizes payment collection and reconciliation, reserved and confirmed booking states, traveler documents and readiness, reminders, and operational export.

The product is not a travel marketplace, discovery app, itinerary generator, or social platform. The Public Trip Page is the entry point into an operations system, not the main category.

Success means an organizer can confidently run a paid group trip from public booking through reservation, confirmation, readiness review, reminders, cancellation handling, and export without fragmented manual tracking.

## Product Structure

TripOS is Organizer-first. Organizer onboarding creates a User, one Organizer, the first Owner membership, and enough Organizer Identity to enter the Operations Dashboard. Creating the first Trip is not part of onboarding and is never required for onboarding to be complete.

The Operations Dashboard has two layers and two shell modes:

- Organizer layer: Home, Organizer Identity, Team Access, Payment Setup, and Trips.
- Trip workspace layer: Overview, Trip Profile, Launch, Bookings, Payments, Travelers, Communications, and Exports.

These layers are not nested in the app shell. Organizer routes use the Organizer shell and Trip routes use a dedicated Trip workspace shell. When a Trip is opened, the Organizer sidebar is hidden completely, the Trip sidebar becomes the primary navigation, and the user exits through Back to Trips or Home.

Organizer Home is the default landing page for Owners and Operators, whether the Organizer has zero Trips or many Trips. It should show the Organizer Setup Checklist as a helpful Setup guide, summarize active Trips and cross-trip needs attention, and make Create Trip prominent for Owners. Operators can see Trip choices and blockers, but Owner-only setup actions should be hidden, read-only, or explained.

Trips are created from the Trips area, not from onboarding. Trip creation should be a short draft step that collects title, dates, capacity, and a starter Package before opening the Trip workspace. After a Trip is created, the Owner lands on Trip Overview. Trip Overview is the root of the selected Trip workspace and summarizes dates, capacity, packages, booking progress, payment readiness, traveler readiness, and recent operational activity. Trip Profile is the editable trip-facing workspace area for Trip Description, Itinerary Days, Trip Media Gallery, Packages, Payment Schedule, and Confirmation Requirements before publication. Packages and Payment Schedule are Owner-only profile sections. Launch remains the separate Trip-level surface for Publication State, Booking Availability, public booking readiness, Trip Profile Publication Readiness, and the Public Trip Page share link.

Publishing the Public Trip Page creates a Published Trip Profile Lock. The lock prevents normal edits to Trip Profile content and core trip facts, while Bookings, Payments, Travelers, Communications, Exports, booking closure, cancellation, and completion remain normal Trip operations.

Organizer Identity and Team Access belong to the Organizer layer. Organizer Logo is optional and should be editable after onboarding with a text fallback when absent. Team Access manages Owner and Operator memberships and Organizer Invitations, not direct creation of other Users.

Payment Setup is Organizer-level configuration owned by Owners. It includes Provider Payment Setup for provider-confirmed payments and Manual Payment Instructions for review-gated manual payments. Trip-level Payments are for collected, approved, due, overdue, adjusted, refunded, and reconciliation state inside a selected Trip. Provider Payment Setup blocks provider-confirmed payments, but does not block draft Trip creation or publishing a Public Trip Page. Public booking can open when at least one payment method is ready for the Trip.

## MVP Scope Boundaries

Organizer Settings stay intentionally small in the MVP: Organizer Identity, Team Access, and Payment Setup. Do not introduce Organizer-level default requirements, communication templates, policy templates, report templates, inherited Trip settings, Reports or Analytics, or Vendor management. Vendor and field-team handoffs are handled through Trip-scoped Operational Exports and operational notes.

Bookings, Payments, Travelers, Communications, and Operational Exports remain Trip-scoped workflows. Organizer Home may summarize cross-trip counts, alerts, and blockers, but it should not become a cross-trip booking management table or reporting module.

## Brand Personality

Calm, exacting, field-ready.

TripOS should feel trustworthy with money, practical with operations, and specific to group travel. It should have the discipline of financial tooling, the clarity of operations software, and a little warmth from community travel without becoming decorative or touristy.

## Design System Commitment

TripOS uses a soft premium glass product system for the full app: authenticated operations, public Trip pages, auth, onboarding, booking, and traveler portal surfaces. The system is light, pastel, glassy, and operationally precise, with dark navy command actions, muted blue and lavender attention states, warm off-white depth, rounded shell geometry, subtle shadows, and scan-first dense rows.

This direction is intentional and should not be reverted by future redesign work. Preserve the active token vocabulary in `apps/web/src/app/styles.css`, especially the later `:root` block with `--surface-card`, `--surface-raised`, `--glass`, `--primary`, `--attention`, `--radius-panel`, `--radius-control`, `--shadow-card`, `--shadow-lift`, and `--shadow-button`.

Do not bring back discarded visual directions: beige or gold warning systems, dark-mode-first Trip workspaces, hard outlined enterprise panels, full-card status color washes, marketing-style dashboard heroes, decorative travel imagery, centered framed Trip workspaces, or generic purple SaaS gradients. Status should live in chips, icons, markers, and concise text, while panels and rows keep a calm shared surface system.

## Anti-references

- Generic travel booking sites focused on discovery, hotel inventory, or inspirational destinations
- Startup SaaS pages with oversized heroes, purple gradients, vague automation claims, and decorative card grids
- Spreadsheet clones that expose raw complexity without workflow guidance
- WhatsApp-like chat surfaces that imply TripOS owns group conversation
- Consumer travel aesthetics that use scenic imagery as decoration instead of operational clarity
- Beige or gold finance dashboards, yellow warning-heavy interfaces, or amber attention palettes
- Dark, boxed, command-center Trip workspaces that feel separate from the Organizer shell
- Status-heavy surfaces where entire cards turn red, green, or yellow instead of using compact state markers

## Design Principles

1. Operations first: every screen should help the organizer answer what is paid, reserved, ready, overdue, missing, or blocked.
2. Financial trust: payment states, ledger entries, adjustments, refunds, and acknowledgements must feel precise and auditable.
3. Group clarity: Booking Contact, Travelers, Traveler Slots, cancellations, replacements, and active travelers must remain visually distinct.
4. Calm density: the dashboard should support repeated work for 10-80 travelers without feeling cramped or theatrical.
5. Structured communication: reminders, announcements, notices, and acknowledgements should feel deliberate, not like a chat replacement.
6. Layer clarity: Home belongs to the Organizer layer; Overview belongs to the Trip workspace layer.
7. Visual continuity: Organizer, Trip, public, booking, and traveler surfaces should share the same soft premium glass system, with workflow context changed through navigation and copy rather than unrelated visual themes.

## Accessibility & Inclusion

Aim for WCAG 2.2 AA for product surfaces. Do not rely on color alone for statuses. Support keyboard navigation, visible focus states, reduced motion, responsive layouts, and readable table/list alternatives on smaller screens.
