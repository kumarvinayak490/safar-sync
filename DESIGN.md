# Design

## Design System

TripOS is a product UI for paid group-trip operations in India. It helps repeat community-led Organizers run trips with roughly 10-80 travelers without stitching together WhatsApp, Excel, payment screenshots, Google Forms, and bank records.

The interface should feel calm, exacting, field-ready, and premium without becoming flashy. It should carry the trust of payment software, the clarity of operations tooling, and enough warmth to fit community-led travel. TripOS is not a travel marketplace, itinerary inspiration site, hotel/flight booking engine, AI itinerary planner, social feed, or chat replacement.

The current committed visual system is soft premium glass for the full app: muted lavender, blue, cream, and off-white canvas tones; frosted major surfaces; dark navy text and command actions; subtle shadows; clean modern typography; rounded shell geometry; and compact, scan-first operational rows. This applies to authenticated operations, Trip workspaces, public Trip pages, auth, onboarding, booking, and traveler portal surfaces. Glass is structural, not decorative: it belongs to shells, headers, panels, summaries, and empty states. Rows, tables, ledgers, queues, and chips stay crisp, compact, high contrast, and easy to scan.

The source of truth for live visual tokens is `apps/web/src/app/styles.css`, especially the later `:root` block that defines `--surface-card`, `--surface-raised`, `--glass`, `--primary`, `--attention`, radii, shadows, and semantic state colors. Future agents should update this document when those tokens intentionally change. They should not reintroduce discarded directions from earlier passes.

Discarded directions that must stay discarded:

- Beige, gold, yellow, or amber attention systems. Attention uses muted blue/lavender.
- Dark-mode-first or boxed Trip workspaces. Trip routes share the Organizer shell aesthetic.
- Hard outlined enterprise panels. Current depth uses soft glass, faint borders, and layered shadows.
- Full-card status color washes. Status lives in chips, icons, markers, concise text, and small surface accents.
- Marketing-style dashboard heroes, hero metrics, decorative card grids, scenic travel decoration, or generic purple SaaS gradients.

## Product Position

TripOS is operations and payments infrastructure for group travel experiences.

Primary promise:

- Help Organizers stop managing paid trips on WhatsApp and Excel.
- Centralize payment collection, reconciliation, reserved and confirmed booking states, traveler documents, readiness, reminders, and operational exports.
- Give travelers a professional Public Trip Page and focused portals for payment and document completion.

## Design Intent

TripOS should feel like a control room for travel operators: structured, confident, fast, and calm under pressure. Use that as a visual metaphor only, not as product copy. The product UI should communicate three things immediately:

- Clarity: the organizer knows what is happening.
- Control: the organizer knows what needs action.
- Trust: travelers, payments, readiness, and operations are safely managed.

The reference mood is warm SaaS for serious travel operators: Linear-style clarity, Shopify-style operational structure, Airbnb-style warmth, Stripe-style trust and polish, and Notion-style workspace calm.

TripOS should feel:

- Operational, not chaotic
- Premium, not flashy
- Human, not robotic
- Warm, not cold enterprise software
- Modern, not over-designed
- Trustworthy, not playful to the point of losing seriousness

Every major surface should answer: what changed, what matters, and what next.

UI copy should be terse. Prefer labels, short status phrases, and concrete actions over explanatory paragraphs. Remove copy that restates headings or explains how the interface works.

## Target Users

### Organizer Users

Owners and Operators work on behalf of an Organizer, which is the business, community, brand, or group operating trips.

Design for:

- Travel creators
- Trek organizers
- Yoga retreat hosts
- Startup and alumni communities
- Biker groups
- Small repeat trip operators

They are often coordinating while on the move, across phone calls, WhatsApp, UPI, vendor spreadsheets, and field teams. The UI must help them answer: who is reserved, who is confirmed, who owes money, who is missing documents, what changed, and what can be exported.

### Booking Contacts

The Booking Contact is responsible for the booking and communication. They may or may not be one of the Travelers. They need clear payment progress, reservation status, requirements, acknowledgements, and access links.

### Travelers

Travelers attend the trip. They need a narrow, low-friction way to view trip details, upload documents, provide travel logistics, add emergency contact information, and see operational announcements.

## Core Surfaces

### Signup and Organizer Onboarding

Purpose: create a User, then create the Organizer they operate under.

Design requirements:

- Make the User vs Organizer distinction clear.
- Signup creates the User; Organizer onboarding asks only for Organizer name.
- Create the Organizer, create the first Owner membership, and default Organizer Identity name from the Organizer name.
- End onboarding at Organizer Home inside the Operations Dashboard.
- Do not require Organizer Logo, Team Access, Payment Setup, or Trip creation during onboarding.
- Avoid internal admin language.
- Make Create Trip a prominent Owner action after onboarding, not an onboarding gate.

### Organizer Home

Purpose: give Owners and Operators a durable Organizer-level landing page before they choose or create a Trip.

Design requirements:

- Organizer Home is the default Operations Dashboard landing page for Organizers with zero Trips or many Trips.
- Use Home only for the Organizer layer. Use Overview only for a selected Trip workspace.
- Show a role-aware Setup guide for Organizer Identity, Team Access, Payment Setup, and Create Trip.
- Owners can act on setup items and create Trips. Operators can see blockers and explanations without Owner-only controls.
- In a zero-Trip Organizer, Owners see a prominent Create Trip action and Operators see a clear message that an Owner must create a Trip.
- Summarize active Trips, launch blockers, payment approvals, overdue balances, missing Confirmation Requirements, and other cross-trip needs attention.
- Keep summaries lightweight. Do not turn Home into a cross-trip booking management table, Reports module, or Analytics surface.
- Payment Setup status may appear as a blocker, but the configuration lives in Organizer-level Payment Setup.

### Organizer Setup Surfaces

Purpose: manage shared Organizer configuration outside any selected Trip.

Design requirements:

- Organizer Identity manages traveler-facing name, optional Organizer Logo, replacement, removal, and fallback display metadata.
- Missing Organizer Logo is a soft warning, not a blocker for Home, Trip creation, Public Trip Page publication, or opening public booking.
- Team Access manages Owner and Operator memberships and Organizer Invitations. Do not label this area Users or Staff.
- Owner invitations need clearer confirmation than Operator invitations. Operator is the default invite role.
- Payment Setup is Owner-managed Organizer configuration. Operators can see relevant status when it blocks Launch, but cannot edit it.
- Payment Setup includes Provider Payment Setup for Razorpay online payments and Manual Payment Instructions for QR-based manual payments.
- Manual Payment Instructions should support a Payment QR and concise optional UPI or bank transfer details. Do not label this as offline payment.
- Keep these surfaces practical and narrow. Do not add default requirements, communication templates, policy templates, report templates, or inherited Trip settings in the MVP.

### Trips

Purpose: manage the Organizer's Trip list and start Trip creation.

Design requirements:

- Keep Trips separate from Organizer Home.
- Use Trips for creating, finding, filtering, duplicating, completing, and managing Trips.
- Create Trip is visible to Owners and unavailable to Operators.
- Do not duplicate Organizer Home's cross-trip needs-attention summary as a management table.
- Trip Duplicate copies Trip Profile content into an unlocked draft with draft publication and closed booking availability.

### Trip Draft Creation

Purpose: let an Owner create a draft paid Trip from the Trips area, with one active scheduled run in the MVP.

Design requirements:

- A Trip is a sellable offering with date range, capacity, packages, Reservation Amounts, Trip Description, Itinerary Days, Trip Media Gallery, payment schedule, and Confirmation Requirements.
- Multiple date ranges are separate Trips in the MVP, not Departures.
- Trip creation is Owner-only and is separate from Organizer onboarding.
- Keep draft creation short: collect title, start date, end date, capacity, and a starter Package.
- Use a compact single-screen draft form rather than a multi-step wizard.
- Payment Setup does not block draft Trip creation.
- Completing Trip creation should open Trip Overview.
- Trip Profile is where Owners and Operators complete profile content before publication.
- Keep draft creation practical, not marketing-heavy.

### Trip Overview

Purpose: summarize the selected Trip before the Owner or Operator moves into specific Trip workflows.

Design requirements:

- Trip Overview is the root of the Trip workspace and the landing page after Trip creation.
- Summarize Trip dates, capacity, packages, booking progress, payment readiness, traveler readiness, and recent operational activity.
- Show enough launch and payment readiness context to explain blockers, but keep publication and booking controls in Launch.
- Link to Bookings, Payments, Travelers, Communications, and Exports when those queues need attention.
- Do not use Trip Overview as the Organizer-level Home or as a replacement for Launch.

### Trip Profile

Purpose: edit the trip-facing profile that shapes the Public Trip Page and booking readiness inputs before publication.

Design requirements:

- Put Trip Profile in the Trip workspace, separate from Trip Overview and Launch.
- Place Trip Profile in the Trip workspace navigation between Overview and Launch.
- Include Trip Description, structured Itinerary Days, Trip Media Gallery, Packages, Payment Schedule, and Confirmation Requirements.
- Use top-level tabs or segmented section navigation for Trip Profile sections, with accordions inside dense sections such as Itinerary Days, Packages, and Confirmation Requirements.
- Show inline section readiness while editing, including which items block publication and which are encouraged.
- Use section-level Save actions rather than one global Trip Profile save.
- Do not autosave Trip Profile edits in the MVP. Warn about unsaved section changes when switching sections or leaving the page.
- Use constrained rich text for Trip Description and Itinerary Day descriptions. Do not insert images or arbitrary page styling inside rich text.
- Trip Media Gallery supports ordered images, one cover item, public/private visibility, alt text, and captions. Do not add video support in the first implementation.
- Package and Payment Schedule editing should use section-level editing with an explicit Save, so multiple local changes can be validated together before persistence.
- Once the Public Trip Page is published, keep Trip Profile visible as read-only, show the Published Trip Profile Lock, and keep normal profile edits disabled.
- Operators can edit unlocked non-commercial profile content except Packages and Payment Schedule. Owners can edit unlocked Packages, Payment Schedule, and publish the Public Trip Page.

### Launch

Purpose: prepare a Trip for public sharing and booking.

Design requirements:

- Use a Trip Launch Checklist.
- Keep Launch Trip-scoped and distinct from Trip Overview.
- Separate Publication State from Booking Availability.
- Show a compact Trip Profile Publication Readiness checklist before publishing.
- Require Owner acknowledgement that publishing creates the Published Trip Profile Lock.
- Show the Public Trip Page share link immediately after publishing.
- Let Owners publish the Public Trip Page before Provider Payment Setup is complete.
- Keep public booking disabled until Booking Availability is open, capacity is available, and at least one payment method is ready.
- Link Owners to Organizer-level Payment Setup when no payment method is ready.
- Let Owners open or close Manual Payment Availability per Trip after Manual Payment Instructions exist.
- Operators can view launch readiness, but only Owners can publish or open public booking.

Launch language:

- Draft: not publicly visible
- Published: publicly visible
- Archived: hidden from normal public sharing, retained for records
- Open: travelers can start and reserve bookings
- Closed: organizer has disabled new bookings
- Sold out: derived from available seats

### Public Trip Page

Purpose: professional entry point into the operations system.

Design requirements:

- Display Organizer Identity prominently.
- Show itinerary, dates, packages, inclusions or operational notes where available.
- Use availability bands, not exact public seat counts: Available, Few seats left, Sold out.
- Make the booking CTA state obvious.
- Do not make the page feel like a marketplace listing or travel inspiration blog.

Public booking is allowed only when:

- Public Trip Page is published
- Booking Availability is open
- At least one payment method is ready
- Available Seats are sufficient

Payment method readiness:

- Razorpay online payments require Online Payment Readiness.
- QR-based manual payments require Manual Payment Instructions and open Manual Payment Availability.

### Booking Flow

Purpose: let a Booking Contact create a paid booking for one or more Travelers.

Design requirements:

- One Booking can contain one or more Travelers.
- Before identity details are known, use Traveler Slot language.
- Traveler count and package selection are required before payment.
- Full traveler names can be collected before confirmation rather than before payment.
- The Booking Reservation Amount is all-or-nothing for seat reservation.
- Block payment before collecting money if there are not enough seats.
- When Razorpay online payments are ready, the primary public path is provider checkout.
- When QR-based manual payments are ready, the public page can show "Scan QR code to pay" after Booking Contact Details, traveler count, and Package selection.
- QR-based manual payment submission creates a Draft Booking and a Submitted Manual Payment on the same public flow.
- The traveler submits Payment Proof after scanning the Payment QR. The action label should be "Submit Payment Proof."
- Submitted Manual Payments do not create Seat Holds and do not reserve seats until approved.
- If Razorpay is not ready, hide it from the traveler flow rather than showing a blocked Razorpay action.

Booking states:

- draft: booking details started, no seat reserved
- reserved: Booking Reservation Amount paid, seats held
- confirmed: organizer accepted the booking as operationally good to travel
- cancelled: booking no longer active
- completed: trip has finished for this booking

Payment states:

- unpaid
- reservation_paid
- partially_paid
- fully_paid
- overdue
- refund_due
- refunded

### Payments

Purpose: make collected money and outstanding balance auditable inside a selected Trip.

Design requirements:

- Label Organizer-level configuration as Payment Setup and Trip-level money operations as Payments.
- Treat payments at the Booking level.
- Show Booking Total, Booking Reservation Amount, collected amount, due amount, overdue amount, and refund due.
- Distinguish Provider Payments, Manual Payments, Opening Payment Records, Booking Adjustments, Refund Records, Platform Fee, and Ledger Entries.
- Use Payment Acknowledgement language, not invoices or receipts.
- Manual payment proof is required for traveler-submitted manual payments and optional for organizer-entered manual payments.
- Traveler-submitted manual payments remain submitted until approved.
- Only confirmed Provider Payments and approved Manual Payments count toward collected balance.
- Manual payment approvals should make the capacity consequence explicit: approving a reservation payment can reserve seats only when Bookable Seats are still sufficient.

### Traveler Readiness

Purpose: help Owners and Operators know who is ready to travel inside a selected Trip.

Design requirements:

- Confirmation Requirements are configured per Trip.
- Surface readiness inside Travelers and Trip Overview. Do not add a separate Trip-level Requirements navigation item in the MVP.
- Required categories: Traveler Documents, Traveler Identity Details, Travel Logistics, Emergency Contact, Medical Disclosure, full payment before confirmation.
- Document states are missing, submitted, approved, rejected.
- Medical disclosure and Traveler Documents are sensitive traveler information.
- Sensitive traveler information appears in Operational Exports only when explicitly selected.

### Notifications

Purpose: send structured Trip-scoped updates without recreating WhatsApp.

Design requirements:

- Use Notification as the parent concept.
- Reminder prompts action on an existing obligation.
- Announcement broadcasts trip operations updates.
- Use Communications as a Trip workspace label only when the surface includes Reminders and Announcements.
- Do not introduce Organizer-level communication defaults or templates in the MVP.
- Channels for MVP: WhatsApp and email.
- TripOS sends structured notifications through WhatsApp but does not own or mirror WhatsApp group chat.

Default recipients:

- Reminders go to the Booking Contact.
- Document reminders may go to the specific Traveler if contact details exist, while the Booking Contact remains responsible.
- Announcements go to active Travelers and the Booking Contact.
- Operational notifications exclude Draft and Cancelled Bookings.

### Operational Export

Purpose: produce Trip-scoped organizer-generated CSV files for offline, vendor, or team use.

Design requirements:

- CSV first, not PDF.
- Include operational metrics and records, not full financial accounting reports.
- Exclude sensitive traveler and payment information by default.
- Log export/download actions, especially when sensitive information is included.
- Support vendor and field-team handoffs here instead of adding a Vendors module in the MVP.

## Visual Direction

### Scene

An Operator is reviewing payments and traveler readiness on a laptop in a trip office or cafe, while WhatsApp messages and payment updates keep coming in. The product should reduce noise and restore control.

### Theme

Use a light, warm-neutral product theme by default. It should feel clear in daytime operational environments, on ordinary laptops, and on phones. Avoid dark-mode-first styling for MVP operations surfaces.

The overall aesthetic is soft premium operations glass:

- Light pastel canvas with lavender, muted blue, cream, and off-white depth
- Faint ledger/grid texture on the page canvas only, never inside operational data rows
- Frosted shells, headers, panels, summaries, public heroes, auth panels, and empty states
- Dark navy command actions, selected navigation, primary text, and high-contrast emphasis
- Muted blue/lavender attention states, not amber or gold
- Subtle translucent borders and layered shadows rather than hard enterprise outlines
- Rounded shell geometry with tighter controls and dense rows
- High whitespace around command surfaces and compact spacing inside queues
- Readable tables, ledgers, and approval queues with tabular numbers

### Color

Use OKLCH tokens. Prefer tinted neutrals, glassy raised surfaces, one dark navy command color, muted blue/lavender attention, and semantic green/red only when the state requires it.

Current active token direction from `apps/web/src/app/styles.css`:

```css
:root {
  --background: oklch(0.978 0.017 278);
  --foreground: oklch(0.2 0.055 264);
  --surface-shell: oklch(0.992 0.006 260 / 58%);
  --surface-base: oklch(0.992 0.006 260 / 56%);
  --surface-card: oklch(0.992 0.006 260 / 76%);
  --surface-raised: oklch(0.996 0.004 260 / 88%);
  --primary: oklch(0.24 0.075 264);
  --primary-hover: oklch(0.19 0.07 264);
  --primary-foreground: oklch(0.986 0.008 260);
  --secondary: oklch(0.93 0.03 276);
  --secondary-foreground: oklch(0.24 0.06 264);
  --muted-surface: oklch(0.947 0.023 274 / 72%);
  --muted-foreground: oklch(0.44 0.04 264);
  --accent: oklch(0.93 0.038 252);
  --accent-foreground: oklch(0.26 0.07 264);
  --destructive: oklch(0.54 0.14 28);
  --border: oklch(0.68 0.034 267 / 24%);
  --border-soft: oklch(0.68 0.034 267 / 18%);
  --input: oklch(0.66 0.035 267 / 34%);
  --ring: oklch(0.54 0.105 252);
  --glass: var(--surface-card);
  --glass-strong: var(--surface-raised);
  --lavender-soft: oklch(0.94 0.036 294);
  --blue-soft: oklch(0.935 0.04 250);
  --cream-soft: oklch(0.967 0.027 88);
  --attention: oklch(0.54 0.095 252);
  --attention-soft: oklch(0.942 0.034 252);
  --attention-border: oklch(0.76 0.055 252);
  --attention-text: oklch(0.3 0.074 258);
  --success: oklch(0.48 0.095 150);
  --danger: var(--destructive);
  --info: oklch(0.55 0.095 248);
  --neutral-chip: oklch(0.948 0.024 274);
  --neutral-chip-border: oklch(0.82 0.033 267);
  --neutral-chip-text: oklch(0.43 0.04 264);
}
```

Use color for:

- Primary action
- Current navigation selection
- State chips
- Payment, readiness, warning, and danger states
- Focus outlines and selected rows
- Trip context and execution state

Color role split:

- Dark navy carries primary actions, selected navigation, high-contrast text, and important command surfaces.
- Muted blue carries informational emphasis, links, focus, active attention, and low-risk highlights.
- Lavender carries soft grouping, secondary background depth, inactive neutral chips, and quiet workspace structure.
- Cream and off-white carry warmth in the canvas and empty-state surfaces.
- Semantic green and red are reserved for success and danger. Do not use amber/gold/yellow for the default attention system.
- Do not let status colors become the primary brand system.

Shell identity:

- Organizer Shell and Trip Workspace Shell use the same soft premium glass system.
- The rail dimensions, icon treatment, active state, text hierarchy, and spacing should stay consistent between shells.
- Trip context changes the navigation labels and selected Trip metadata, not the product aesthetic.
- Muted pastel canvas and frosted raised operational surfaces are the default authenticated app treatment.
- Dark navy carries primary actions and high-contrast navigation emphasis. Muted lavender, blue, cream, and off-white support depth and grouping, not decoration.

Avoid:

- Pure black or pure white
- Saturated purple startup gradients
- Decorative travel blues without operational purpose
- Beige-only palettes
- Beige, gold, yellow, or amber attention palettes
- Loud or high-contrast grid backgrounds
- Saturated inactive states
- Scenic imagery as decoration in operational tools
- Neon colors
- Heavy or low-contrast gradients
- Decorative glassmorphism that makes operational data harder to scan
- Low-contrast beige text
- Full-card red, yellow, green, or blue status washes on summaries, setup items, and attention rows

### Typography

Use the current product-grade sans stack:

```css
font-family: Inter, Geist, "SF Pro Display", -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
```

Guidelines:

- Fixed rem sizes, not viewport-scaled type.
- Tight but legible hierarchy.
- Use tabular numbers for money, capacity, traveler counts, and ledger rows.
- Body copy should usually stay under 65-75 characters per line.
- Operations Dashboard headings should be compact, including Organizer Home and Trip Overview. Reserve large type for onboarding and public pages only.
- Use zero or positive letter spacing only. Eyebrows may use modest uppercase tracking around `0.045em` to `0.075em`; labels, headings, and buttons should keep tracking normal.
- Current command headings sit around `1.875rem` to `1.9rem` at `740` weight. Workspace headings sit around `1.125rem` at `740` weight. Dense row text generally stays between `0.75rem` and `0.94rem`.

### Layout

Authenticated product surfaces use two separate shell modes. They are not nested.

Canvas texture:

- Use a faint ledger/grid texture on the global app canvas.
- Keep the texture subtle enough that cards, tables, and status states remain dominant.
- Grid opacity must stay extremely low, roughly the current `2%` canvas-line treatment.
- Do not use the grid as decoration inside cards or panels.

Organizer Shell:

- Left sidebar: Organizer navigation
- Top bar: Organizer name, Create Trip where appropriate, notifications, profile
- Main area: Organizer-wide Home, setup, Team Access, Payment Setup, and Trips list
- Works with zero Trips
- Current desktop shell uses a 272px left rail, a sticky rounded `authenticated-rail`, and a frosted `product-topbar`.

Trip Workspace Shell:

- Left sidebar: Trip navigation only
- Top bar: Trip name, dates, publication or booking status, Trip Actions
- Main area: Trip-specific operations
- Escape actions: Back to Trips and Home
- Shows selected Trip context and optional Trip switcher when multiple Trips exist
- Does not show the Organizer sidebar
- Uses the same visual system, rail dimensions, spacing rhythm, canvas treatment, and component vocabulary as the Organizer Shell
- Current Trip workspace uses the `trip-control-room` and `trip-control-rail` model. Keep it full-surface and operational, not a centered preview frame.

This hard mode switch prevents users from confusing Organizer-level setup with Trip-level execution. It should not make the Trip workspace feel like a separate product; the difference is navigation context, not visual identity.

Authenticated work areas should remain dense but readable:

- Tables and queues for repeated operational work
- Detail panels for booking, traveler, and payment records
- Inline actions for review and approval
- Cards for summaries, setup prompts, and compact status groupings
- Flatter lists or tables for operational queues where users review many records

Public and traveler surfaces should be simpler:

- Mobile-safe layout
- Clear next action
- Minimal navigation
- Strong Organizer Identity
- No marketplace discovery patterns

Avoid:

- Cards inside cards
- Oversized dashboard hero sections
- Decorative card grids
- Walls of equal cards for Bookings, Payments, Travelers, or other queue-heavy workflows
- Explainer copy that describes how UI works instead of making the control obvious
- Replacing the two-shell app model with a blended Organizer and Trip sidebar
- Returning Trip workspace routes to a dark, framed, presentation-like layout
- Turning Organizer Home into a reports dashboard or cross-trip management table

### Shape And Radius

Authenticated operations surfaces should be soft but still field-ready:

- Shells and major panels: use the current large rounded geometry, usually `24px` to `28px`.
- Repeated cards and summary tiles: usually `20px` to `24px` when they are standalone surfaces.
- Dense rows, tables, ledger lines, and action controls: use tighter radii, usually `14px` or less where scanning matters.
- Buttons and inputs: `--radius-control` (`14px`) with strong contrast and clear focus states.
- Status chips: `--radius-chip` (`999px`) when they are compact labels.

Avoid making the operations app feel like a soft consumer travel product. Roundness should support clarity, not decoration.

## Components

### Surface Hierarchy

Use the current surface hierarchy consistently:

- App canvas: pastel gradient plus very faint ledger grid.
- Shell rails and headers: frosted glass, large radius, soft shadows, dark navy active navigation.
- Page panels and summaries: `--surface-card` or `--surface-raised`, subtle border, `--shadow-card`.
- Command surfaces: navy primary action, muted blue/lavender secondary action, concise text.
- Dense operational rows: raised but crisp surfaces, subtle dividers, compact typography, no heavy glass blur per row.

Do not return to hard outlined cards everywhere. Do not use decorative glass layers where the user is reading money, readiness, traveler, or ledger records.

### Navigation

Organizer-level navigation:

- Home
- Organizer Identity
- Team Access
- Payment Setup
- Trips

Trip workspace navigation:

- Overview
- Launch
- Bookings
- Payments
- Travelers
- Communications
- Exports

Use stable navigation labels. Preserve Organizer context across authenticated routes, but selected Trip context appears only inside Trip Workspace routes. The shell must not assume a selected Trip exists.

Rules:

- Organizer Shell and Trip Workspace Shell are separate modes.
- Redesign work may restyle both shells, but must preserve the two-shell navigation model and ADR-0016 route behavior.
- The Organizer sidebar is hidden completely inside Trip Workspace routes.
- Trip Workspace routes use private operations URLs, not query-string selected Trip state.
- Trip Workspace should span the available app surface rather than sitting inside a centered frame.
- Trip Workspace uses the same shell aesthetic as Organizer routes. Avoid switching to a dark, framed, or presentation-style layout only for Trip routes.
- Do not replace authenticated navigation with a marketing-style top nav, chat-like layout, or single blended workspace.
- Opening a Trip from the Trips page enters Trip Overview.
- Creating a Trip ends at Trip Overview.
- Back to Trips returns to the Organizer-level Trip list.
- Home returns to Organizer Home.
- Avoid "Back to Workspace" because workspace is ambiguous.
- Active navigation is dark navy with high-contrast foreground and a soft shadow. Hover states may use the same family. Inactive states stay quiet and must not use saturated color.
- The Organizer rail and Trip rail both use the `authenticated-rail` system. The difference is information architecture, not visual theme.

Navigation states should distinguish:

- Owner actions available
- Operator-visible read-only blockers
- Disabled items caused by missing selected Trip
- Trip-scoped queues that need attention

### Status Chips

Use chips for:

- Booking State
- Payment State
- Publication State
- Booking Availability
- Document State
- Manual Payment status
- Traveler attendance
- Payout Status

Chips must use text and color together. Do not rely on color alone.

Current chip rules:

- Neutral or draft states use lavender-gray neutral chips.
- Attention, reserved, partially paid, submitted, and few seats left use muted blue/lavender, not yellow.
- Success states use restrained green.
- Blocked, sold out, rejected, refund due, and destructive states use restrained red.
- Never turn an entire card or list row into a saturated state color when a chip, icon, or compact marker can carry the state.

### Tables and Lists

Use tables or dense list views for:

- Bookings
- Traveler Slots
- Payments
- Ledger Entries
- Manual payment approvals
- Documents
- Exports

Tables should support scan-first behavior:

- Left side: identity and state
- Middle: obligations and requirements
- Right side: amount, due date, action

Operational queue rule:

- Use flatter table/list surfaces for Bookings, Payments, Travelers, and approval queues.
- Reserve cards for summaries, setup prompts, exception callouts, and individual detail panels.
- A queue row may have hover, focus, status badges, and compact row actions, but should not feel like a standalone marketing card.
- Keep dense operational rows compact and scan-first. Frosted glass belongs to the app canvas, shells, page panels, summaries, and empty states; rows, ledger lines, and reconciliation lists stay crisp with subtle hover states, tighter radius, strong text contrast, tabular numbers, and clear chips.
- Hover rows with muted lavender/blue surface changes. Do not use full-card warning washes for attention rows.
- Keep money, due dates, reconciliation references, and traveler names aligned for scanning. Decorative layout should never break queue comparison.

### Financial Ledger Rows

Ledger rows should show:

- Entry type
- Amount
- Source
- Reference
- Approval state where relevant
- Reason or description
- Timestamp

Money should align using tabular figures.

### Forms

Use inline or page-level forms where possible. Avoid modals as the default.

Controls:

- Inputs for text and dates
- Steppers or numeric inputs for capacity and amount
- Toggles or checkboxes for required confirmation categories
- Menus for finite state changes
- File upload controls for documents and proofs

Every control needs default, hover, focus, active, disabled, loading, and error states where applicable.

### Empty States

Empty states should be operationally useful. They should explain the next task, not market the product.

Examples:

- Zero Trips for Owner: make Create Trip the primary next action and show setup context.
- Zero Trips for Operator: explain that an Owner must create a Trip before Trip operations can begin.
- No bookings yet: point to the Public Trip Page and booking availability.
- No manual payments submitted: show that approval queue is clear.
- No missing requirements: show readiness is clear.
- No cross-trip attention needed: show the Organizer Home queue is clear without implying there is a Reports module.

### Access Links

Booking-level and Traveler-level access links should be visibly scoped.

- Booking Access Link: Booking Contact controls payment progress, traveler slots, manual payment proof, announcements.
- Traveler Access Link: specific Traveler uploads documents and views their own trip details.

Links expire and can be regenerated.

## Motion

Use short 150-250 ms transitions. The current app mostly uses 180-200 ms ease-out transitions for:

- Button feedback
- Row expansion
- Panel reveal
- Status changes
- Loading to loaded states

Motion should clarify state, not decorate the interface. Respect reduced motion.

Current motion rules:

- Hover lift may use `translateY(-1px)` on panels and buttons.
- Active controls may use a tiny scale or down-press treatment.
- Animate color, shadow, opacity, and transform. Do not animate layout properties.
- Avoid page-load choreography in authenticated product surfaces. Users are there to operate trips, not watch a presentation.

## Accessibility

Aim for WCAG 2.2 AA.

Requirements:

- Keyboard navigation for every control
- Visible focus states
- Labels for form inputs
- Color plus text for status
- Sufficient contrast for muted text
- Mobile layouts without text overlap
- Responsive tables or list alternatives
- Reduced motion support

## UX Copy

Use TripOS domain language from `CONTEXT.md`.

Preferred terms:

- Organizer
- Operations Dashboard
- Organizer Home
- Organizer Identity
- Organizer Logo
- User
- Owner
- Operator
- Team Access
- Payment Setup
- Provider Payment Setup
- Trip
- Trip Overview
- Public Trip Page
- Public Trip URL
- Booking Availability
- Booking
- Booking Contact
- Traveler
- Traveler Slot
- Package
- Reservation Amount
- Booking Reservation Amount
- Payment Schedule
- Financial Ledger
- Ledger Entry
- Provider Payment
- Manual Payment
- Manual Payment Instructions
- Manual Payment Availability
- Payment QR
- Payment Proof
- Payment Acknowledgement
- Booking Adjustment
- Refund Record
- Confirmation Requirements
- Travel Logistics
- Emergency Contact
- Medical Disclosure
- Reminder
- Announcement
- Operational Export

Avoid:

- Organization, Control Room, Admin dashboard, Users for access management, Staff, Finance for Organizer setup, Reports, Analytics, Vendor Management, Logo URL, guest, customer, attendee, user account, host, campaign, checkout funnel, receipt, invoice, deposit, microsite, white-label, marketplace, chat, offline payment, manual pay, QR checkout

Use direct labels:

- "Home"
- "Overview"
- "Create Trip"
- "Setup guide"
- "Team Access"
- "Payment Setup"
- "Scan QR code to pay"
- "Submit Payment Proof"
- "Bookings opening soon."
- "Open Public Booking"
- "Publish Public Trip Page"
- "Reservation Amount"
- "Payment Acknowledgement"
- "Missing Confirmation Requirements"

## MVP Boundaries

Do not design MVP screens for:

- Marketplace discovery
- Hotel APIs
- Flight booking
- AI itinerary planning
- Social feed
- Native mobile app
- Full white-label custom domains
- Arbitrary custom fields
- Full tax or accounting system
- Settlement ledger or payout reports
- Organizer-level Reports or Analytics
- Organizer-level default requirements
- Organizer-level communication templates
- Organizer-level policy templates
- Inherited Organizer templates or override rules
- First-class Vendors module or vendor management
- Direct Owner-created User accounts
- Waitlists
- Coupon system
- SMS-first workflows
- Separate Trip-level Requirements navigation

Future design work can revisit:

- Departures for repeated Trip runs
- Autopay or richer installment schedules
- EMI, insurance, forex, or lending
- Custom domains and broader brand controls
- Organizer-level templates only after repeated need is proven
- Marketplace only after the operations product is working

## Implementation Context

The MVP stack is Django DRF, PostgreSQL, background workers, S3-compatible storage, and Next.js. The UI should be designed around server-rendered public pages, authenticated operations routes, traveler portals, and API-backed workflow actions.

The current visual implementation already lives in `apps/web/src/app/styles.css`, `apps/web/src/app/AppShell.tsx`, and the shared UI components under `apps/web/src/components/ui/`. Future implementation work should preserve the current soft premium glass system unless a user explicitly asks for a new redesign.

Redesign implementation starts with the shared app shell and core tokens, then continues through the full app. First update the global canvas/background, color tokens, typography rhythm, Organizer Shell, Trip Workspace Shell, buttons, inputs, chips, panels, hover states, focus states, and transition behavior. In the same redesign program, update authenticated operations pages, auth and onboarding, public Trip pages, booking flow, and traveler portals so every surface inherits the new system instead of feeling like a partial reskin.

Anti-regression rules for future agents:

- Preserve the later `:root` token block as the active source of truth. Do not revive older top-of-file warm-neutral tokens as the design direction.
- Preserve the soft glass surface hierarchy: canvas, shell/header, panel/summary, row/queue, chip/marker.
- Preserve muted blue/lavender attention. Do not reintroduce beige, gold, yellow, or amber warning as the default attention language.
- Preserve status-in-marker behavior. Do not use full-card state washes except for very restrained blocked/attention accents already represented in the current CSS.
- Preserve the two-shell model. Organizer Shell and Trip Workspace Shell share aesthetic vocabulary but stay separate navigation contexts.
- Preserve dense, scan-first operational rows. Do not turn Bookings, Payments, Travelers, Communications, or Exports into repeated marketing cards.

Design decisions should keep modules aligned with the domain:

- Session and onboarding routing treat an Organizer with zero Trips as fully onboarded and route to Organizer Home.
- Operations Dashboard navigation owns the two-layer Organizer and Trip workspace hierarchy.
- Organizer Home readiness owns the Setup guide, zero-Trip empty state, role-aware actions, and cross-trip needs-attention summaries.
- Organizer Identity owns public identity name, optional Organizer Logo, and fallback display metadata.
- Organizer Invitations and Team Access own membership invitation, resend, revoke, and accept flows.
- Public Booking Gate decides public booking readiness.
- Financial Ledger owns collected balance and payment state derivation.
- Booking Operations Workflow owns booking and traveler state transitions.
- Traveler Readiness owns Confirmation Requirements.
- Trip Overview read model owns the selected Trip summary payload.
- Trip Setup owns wizard parsing, validation, and submission.

When in doubt, preserve product language and workflow clarity over visual novelty.

When in doubt, reduce words before adding visual weight.
