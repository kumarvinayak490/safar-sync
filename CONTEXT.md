# TripOS

TripOS is a domain for operating group travel experiences, where organizers manage trips, travelers, bookings, payments, and trip operations in one place.

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

**Creative Setup**:
Organizer-level preferences used by TripOS-assisted creative generation, including model choice, brand tone, default style, logo usage, and poster defaults.
_Avoid_: Organizer preferences, generated posters, trip creative assets, organizer profile, public content, trip itinerary, design system

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

**Organizer Media**:
The organizer-owned media library for public trust, discovery, and creative reuse across organizer and trip surfaces.
_Avoid_: Organizer profile identity, trip media gallery, traveler documents, operational files

**Public Organizer Media**:
Organizer media selected or marked for public organizer discovery and trust surfaces.
_Avoid_: Trip media gallery, traveler documents, operational files

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

**Organizer Onboarding**:
The initial setup in which a user creates an organizer, becomes its first owner, and establishes initial organizer profile basics to enter the operations dashboard.
_Avoid_: Trip setup, launch setup

**Operations Dashboard**:
The organizer-facing workspace for managing trip operations.
_Avoid_: Admin dashboard, organizer dashboard

**Trip Workspace**:
The private trip-scoped operations surface for managing one selected trip.
_Avoid_: Selected Trip mode, global workspace

**Trip Operations**:
The trip-scoped operational domain for communications, reminders, announcements, operational exports, activity log, and operational exception review while running a selected trip.
_Avoid_: Trip profile, booking state, traveler records, payment state, organizer settings, internal admin, catch-all module

**Internal Admin**:
The thin TripOS staff surface for orchestrating module-owned support and configuration actions during pilots.
_Avoid_: Internal CRM, support dashboard, business state owner

**Community-Led Organizer**:
An organizer that repeatedly sells paid trips to a creator audience, community, or affinity group.
_Avoid_: Travel agency, corporate planner, friend group

**Individual Creator Payment Path**:
Payment setup guidance for a community-led organizer that uses an individual or unregistered-business provider account.
_Avoid_: Registered business requirement, GST requirement, MSME requirement

**Payout Account**:
The account where an organizer receives settled trip payments.
_Avoid_: Bank account, settlement account

**Payout Status**:
The provider-confirmed setup state of an organizer's payout account.
_Avoid_: Settlement report, payout ledger

**Settlement Readiness**:
The organizer-facing readiness signal that settled provider payments can be received by the organizer.
_Avoid_: Editable bank details, settlement report

**Connected Provider Account**:
The organizer-owned payment provider account authorized for TripOS to create provider payment attempts and read provider-confirmed payments.
_Avoid_: TripOS wallet, provider linked account, platform-managed payment account

**Provider Authorization**:
The permission granted by an owner that lets TripOS act against a connected provider account.
_Avoid_: Provider password, user login session

**OAuth Provider Authorization**:
A provider-hosted authorization flow where the owner approves TripOS access without copying provider credentials into TripOS.
_Avoid_: API key paste, manual token entry

**API Key Provider Authorization**:
A fallback provider authorization method where provider API credentials are stored securely by TripOS for pilot use.
_Avoid_: Main payment setup path, shared password

**Sensitive Provider Credential**:
A provider credential or token that allows TripOS to access a connected provider account.
_Avoid_: Public key, merchant id

**Provider Mode**:
Whether a connected provider account is operating in test mode or live mode.
_Avoid_: Payment setup status

**Live Provider Mode**:
Provider mode in which real traveler payments can be collected.
_Avoid_: Test mode

**Test Provider Mode**:
Provider mode used for non-production payment testing.
_Avoid_: Ready to collect

**Provider Connection Test**:
An owner or staff validation run that checks a connected provider account without opening public booking.
_Avoid_: Test Booking, fake reservation, public booking test

**Provider Connection Test Result**:
The recorded outcome of a provider connection test.
_Avoid_: Provider Payment, Payment Attempt, Ledger Entry

**Provider Connection State**:
The state of TripOS access to a connected provider account.
_Avoid_: Payment readiness, payout status

**Healthy Provider Connection**:
TripOS can create payment attempts and read payment confirmations for the connected provider account.
_Avoid_: Verified provider account

**Unhealthy Provider Connection**:
TripOS cannot safely create payment attempts or read payment confirmations for the connected provider account.
_Avoid_: Failed organizer

**Provider Verification**:
The payment provider's verification process that determines whether a connected provider account can collect payments and receive payouts.
_Avoid_: TripOS KYC, organizer onboarding

**Provider Eligibility**:
The payment provider's assessment of whether a connected provider account can be used.
_Avoid_: Organizer setup requirement, TripOS approval

**Provider Verification Status**:
The visible progress state of provider verification.
_Avoid_: Payment readiness, payout status

**Not Started Provider Verification**:
Provider verification has not begun.
_Avoid_: Unverified

**Details Needed Provider Verification**:
Provider verification needs structured organizer or payout details before submission.
_Avoid_: Failed verification

**Submitted Provider Verification**:
Provider verification details have been submitted to the provider.
_Avoid_: Verified

**In Review Provider Verification**:
Provider verification is under provider review.
_Avoid_: Pending payment setup

**Action Required Provider Verification**:
Provider verification requires organizer action before it can continue or complete.
_Avoid_: Rejected

**Verified Provider Verification**:
The provider has verified the connected provider account.
_Avoid_: Ready to collect

**Provider Verification Document**:
A document required by the payment provider to verify a connected provider account.
_Avoid_: TripOS document, stored KYC document

**Provider Verification URL**:
The public URL an owner submits to the payment provider to help verify where payments will be accepted.
_Avoid_: Custom website, organizer homepage

**Online Payment Readiness**:
Whether an organizer can collect provider-confirmed payments through public booking.
_Avoid_: Provider verification status, payout status

**Provider Payment Capability**:
TripOS can create provider payment attempts and confirm captured provider payments for the connected provider account.
_Avoid_: OAuth connected, provider verification, settlement readiness

**Manual Payments Only**:
An organizer payment state where provider-confirmed public booking is unavailable but organizer-created manual bookings and manual payments can still operate.
_Avoid_: Failed payment setup, offline-only product

**Manual Payment Instructions**:
Organizer-level payment details used by travelers to make direct manual payments.
_Avoid_: Trip payment details, offline payment setup

**Organizer Payments**:
The organizer-owned payments submodule for provider setup, payout readiness, manual payment instructions, and future organizer-level payment operations.
_Avoid_: Organizer settings, trip payments, platform custody, platform fee billing

**Manual Payment Availability**:
The trip-level launch setting that controls whether travelers can submit manual payments for a trip.
_Avoid_: Manual payment setup, QR payment setup

**Payment Setup**:
The organizer payments workflow where an owner configures provider payments and manual payment instructions.
_Avoid_: Payout setup, payment gateway setup, raw gateway setup

**Assisted Payment Setup**:
A TripOS support-assisted version of payment setup used during pilots when provider connection or verification needs help.
_Avoid_: Manual gateway setup, organizer-facing Razorpay setup

**Provider Payment Setup**:
The organizer-level setup record and workflow required to prepare provider-confirmed payments.
_Avoid_: Manual payment setup

**Provider Disclosure**:
The organizer-facing trust text that names the payment provider processing and verifying online payments.
_Avoid_: Payment setup title, provider-branded workflow

**User**:
A person who logs in and acts on behalf of one or more organizers.
_Avoid_: Organizer, account

**Owner**:
A user role that can manage organizer profile, organizer settings UI actions, team access, organizer payments, and all trips for an organizer.
_Avoid_: Admin

**Operator**:
A user role that can manage trip operations, non-commercial trip profile content other than packages, booking confirmation, manual payment approvals, and closing bookings, but cannot manage organizer payments, team access, publication, opening bookings, trip capacity, post-booking trip dates, or packages.
_Avoid_: Staff, helper

**Organizer Membership**:
The relationship that lets a user act for an organizer with a role.
_Avoid_: Account membership

**Organizer Invitation**:
An invitation sent to an email address that lets a person become a user with an owner or operator organizer membership.
_Avoid_: Direct user creation, staff invite

**Team Access**:
The organizer-owned access-control submodule for managing owner and operator memberships, invitations, and ownership invariants.
_Avoid_: Users, staff, account access

**Trip**:
A sellable group travel offering presented by an organizer to travelers; before departures are introduced, a trip represents one scheduled run.
_Avoid_: Experience, package, tour

**Trip Overview**:
The trip workspace view that summarizes trip dates, capacity, packages, booking progress, payment readiness, traveler readiness, and recent operational activity.
_Avoid_: Launch checklist, trip setup

**Trip Profile**:
The editable trip-facing record for a trip that shapes the public trip page and booking readiness inputs.
_Avoid_: Trip setup, trip content, trip details, trip overview

**Published Trip Profile Lock**:
The locked state of trip profile content and core trip facts after a public trip page is published.
_Avoid_: Content staging, profile draft, page version

**Trip Profile Publication Readiness**:
Whether a trip profile has enough reviewed content to publish the public trip page.
_Avoid_: Launch readiness, payment readiness

**Trip Description**:
The rich organizer-authored narrative and details shown for a trip.
_Avoid_: Trip overview, itinerary, marketing copy

**Trip Rich Text**:
Constrained formatted text used in trip profile content.
_Avoid_: Arbitrary HTML, custom styling, embedded media

**Trip Media Gallery**:
The ordered set of media items attached to a trip profile.
_Avoid_: Social feed, media library, document folder

**Trip Media Item**:
An image asset stored by TripOS in a trip media gallery that can be ordered and optionally shown publicly.
_Avoid_: Post, attachment, traveler document, external image URL

**Completed Trip**:
A trip the organizer has marked as operationally finished.
_Avoid_: Archived trip

**Trip Cancellation**:
The owner-controlled cancellation of an entire trip.
_Avoid_: Archived trip, booking cancellation

**Trip Duplicate**:
A new trip created by copying setup from an existing trip.
_Avoid_: Departure, clone

**Paid Trip**:
A trip whose bookings require a payable booking total greater than zero.
_Avoid_: Free event, RSVP

**Public Discovery Catalog**:
The TripOS public discovery domain for demand pages, SEO metadata, discovery routing, and listing rules that compose published organizer and trip pages.
_Avoid_: Marketplace, travel marketplace, booking marketplace

**Organizer Public Page**:
The public page for an organizer that composes organizer profile content, public organizer media, organizer policies, and published offered trips.
_Avoid_: Organizer dashboard, organizer settings, public trip page

**Demand Page**:
An SEO-focused public discovery page that distributes traveler demand for a specific travel pattern to relevant published organizer and trip pages.
_Avoid_: Distribution page, trip, public trip page, booking request, waitlist

**Configured Demand Page**:
A staff-configured demand page with public copy, SEO metadata, demand pattern, and selected or rule-matched organizer and trip links.
_Avoid_: Auto-generated thin page, booking page

**Discovery SEO Metadata**:
The search-facing title, description, canonical URL, structured metadata, and indexability settings for public discovery pages.
_Avoid_: Trip profile content, organizer profile content, ad copy

**Discovery Routing**:
The public URL and route ownership for discovery pages such as demand pages and catalog pages.
_Avoid_: Public trip URL ownership, booking route, operations route

**Discovery Listing Rule**:
A configured or rule-based selection that decides which published organizer or trip pages appear on a discovery page.
_Avoid_: Booking rule, payment rule, manual curation only

**TripOS Marketing Site**:
The public TripOS-owned site that explains TripOS to prospective organizers.
_Avoid_: Public trip page, organizer public page, operations dashboard

**Public Trip Page**:
The shareable traveler-facing page for a trip.
_Avoid_: Microsite, landing page

**Public Trip URL**:
The TripOS-hosted URL for a public trip page.
_Avoid_: Custom domain

**Organizer Public URL**:
The TripOS-hosted URL for an organizer public page.
_Avoid_: Organizer dashboard URL, custom domain

**Demand Page URL**:
The TripOS-hosted URL for a demand page.
_Avoid_: Trip URL, public trip URL, booking URL

**Publication State**:
The visibility state of a public trip page.
_Avoid_: Trip status, booking status

**Draft Publication**:
A public trip page that is not publicly visible.
_Avoid_: Private trip

**Published Publication**:
A public trip page that is publicly visible.
_Avoid_: Live trip

**Archived Publication**:
A public trip page hidden from normal public sharing while retained for records.
_Avoid_: Deleted trip

**Booking Availability**:
Whether travelers can create and reserve bookings for a trip.
_Avoid_: Publication state, trip status

**Open Booking Availability**:
A trip state in which travelers can start and reserve bookings.
_Avoid_: Live booking

**Public Booking**:
A traveler-initiated booking created from a public trip page.
_Avoid_: Manual booking, unpaid booking request

**Public Booking Gate**:
The trip-owned rule that determines whether a traveler can start public booking from a public trip page.
_Avoid_: Discovery listing rule, demand page rule, publication state

**Trip Bookings**:
The trip-scoped booking domain for reservations, manual bookings, booking imports, booking state, access links, and booking contact coordination.
_Avoid_: Trip profile, traveler account, payment setup

**No-Login Public Booking**:
A public booking flow where the traveler or booking contact does not create a user account.
_Avoid_: Traveler account, customer login

**Bookings Opening Soon**:
The public trip page message shown when the page is visible but public booking is not available yet.
_Avoid_: Waitlist, booking request, manual payment instructions

**Closed Booking Availability**:
A trip state in which travelers cannot create or reserve new bookings because the organizer has closed booking.
_Avoid_: Sold out

**Sold Out Booking Availability**:
A derived trip state in which travelers cannot reserve because capacity is unavailable.
_Avoid_: Closed booking

**Departure**:
A scheduled run of a trip for a specific date range.
_Avoid_: Batch, instance, occurrence

**Traveler**:
A person who is expected to attend a trip.
_Avoid_: Participant, guest, passenger, customer

**Traveler Slot**:
A place in a booking intended for one traveler before identity details are complete.
_Avoid_: Unnamed traveler, seat

**Traveler Identity Details**:
The full name and phone number that identify a traveler, with email optional in the MVP; phone numbers need not be unique.
_Avoid_: Traveler documents, confirmation requirements

**Active Traveler**:
A traveler inside a reserved or confirmed booking who has not been cancelled or replaced.
_Avoid_: Participant, attendee

**No-Show Traveler**:
An active traveler who did not attend the trip.
_Avoid_: Cancelled traveler, booking state

**Traveler Check-In**:
The organizer action of marking that a traveler has arrived or joined the trip.
_Avoid_: QR check-in, attendance app

**Booking Contact**:
The person responsible for a booking's communication and payment coordination.
_Avoid_: Traveler, customer, payer

**Booking Contact Details**:
The name and phone number required to contact a booking contact, with email optional in the MVP.
_Avoid_: Traveler details

**Trip Travelers**:
The trip-scoped traveler readiness domain for traveler slots, traveler identity details, traveler documents, traveler check-in, and traveler-level changes.
_Avoid_: Booking contact, user account, customer profile

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
A secure link that gives a booking contact or traveler access to booking-related traveler actions without a user account.
_Avoid_: Traveler account, login

**Traveler Portal**:
The booking and traveler-facing workspace accessed through booking access links.
_Avoid_: Booking access link, traveler account

**Access Link Expiry**:
The time after which a booking access link stops granting access; the MVP default is 14 days.
_Avoid_: Session timeout

**Booking-Level Access Link**:
A booking access link for the booking contact to manage booking-level traveler actions.
_Avoid_: Traveler link

**Traveler-Level Access Link**:
A booking access link for one traveler to manage their own traveler actions.
_Avoid_: Booking link

**Reservation Amount**:
The minimum upfront amount required for a booking to reserve seats.
_Avoid_: Deposit, advance, token amount

**Booking Reservation Amount**:
The total upfront amount required for a booking to reserve its travelers' seats.
_Avoid_: Deposit total, booking deposit

**Booking State**:
The operational lifecycle state of a booking.
_Avoid_: Payment status, booking status

**Payment State**:
The money collection lifecycle state determined from a booking's financial ledger.
_Avoid_: Booking status, payment status

**Draft Booking**:
A booking whose details have started but whose seats are not reserved and which is excluded from core operational counts.
_Avoid_: Inquiry, initiated, lead

**Draft Expiry**:
The time after which a draft booking is considered abandoned for cleanup or recovery; the MVP default is 24 hours.
_Avoid_: Seat hold expiry

**Reserved Booking**:
A booking whose reservation amount has been paid and whose seats are held.
_Avoid_: Deposit paid, partially paid

**Confirmed Booking**:
A booking that satisfies the organizer's operational requirements and has been manually accepted as ready for the trip.
_Avoid_: Paid booking, completed booking

**Unconfirm Booking**:
The action of moving a confirmed booking back to reserved without cancelling it.
_Avoid_: Cancel booking

**Cancelled Booking**:
A booking that is no longer active.
_Avoid_: Refunded booking

**Traveler Cancellation**:
The removal of one traveler from an otherwise active booking.
_Avoid_: Booking cancellation, drop-out

**Traveler Replacement**:
The replacement of one traveler in a booking with another without changing the booking's reserved seat count.
_Avoid_: Name change, transfer

**Traveler Addition**:
The organizer-controlled addition of a new traveler to an existing booking.
_Avoid_: Traveler replacement, new booking

**Traveler Document**:
An identity or eligibility document collected for a traveler.
_Avoid_: Booking document, upload

**Travel Logistics**:
Traveler-specific arrival, departure, and operational details relevant to a trip.
_Avoid_: Transport management, vehicle assignment

**Emergency Contact**:
A traveler-specific contact used by the organizer in urgent situations.
_Avoid_: Travel logistics, booking contact

**Medical Disclosure**:
Traveler-provided health information requested by the organizer for trip readiness.
_Avoid_: Travel logistics, generic note

**Sensitive Traveler Information**:
Traveler information that should be handled with restricted visibility and explicit export choice.
_Avoid_: General traveler data

**Sensitive Payment Information**:
Payment-related information that should be handled with restricted visibility and explicit export choice.
_Avoid_: General payment data

**Traveler Data Request**:
A traveler request to correct, remove, or access their traveler information, handled as a manual support process in the MVP.
_Avoid_: Self-serve deletion

**Document State**:
The review lifecycle state of a traveler document.
_Avoid_: Upload status

**Missing Document**:
A required traveler document that has not been uploaded.
_Avoid_: Not uploaded

**Submitted Document**:
A traveler document that has been uploaded but not reviewed.
_Avoid_: Uploaded document

**Approved Document**:
A traveler document accepted by the organizer.
_Avoid_: Verified document

**Rejected Document**:
A traveler document rejected by the organizer and needing replacement.
_Avoid_: Invalid document

**Confirmation Requirements**:
Organizer-defined requirements a booking must satisfy before it can become a confirmed booking.
_Avoid_: Checklist, tasks, verification rules

**Booking Cancellation**:
The cancellation of an entire booking.
_Avoid_: Traveler cancellation

**Cancellation Reason**:
The explanation for why a traveler cancellation or booking cancellation exists.
_Avoid_: Note

**Completed Booking**:
A booking for which the trip has finished.
_Avoid_: Fully paid booking

**Unpaid Booking**:
A booking for which no money has been successfully collected.
_Avoid_: Pending payment

**Reservation Paid Booking**:
A booking for which the reservation amount has been collected but the total payable amount has not been collected.
_Avoid_: Deposit paid booking

**Partially Paid Booking**:
A booking for which more than the reservation amount has been collected but the total payable amount has not been collected.
_Avoid_: Half-paid booking

**Fully Paid Booking**:
A booking for which the total payable amount has been collected.
_Avoid_: Completed booking

**Overdue Booking**:
A booking whose expected payment date has passed while it still has an unpaid balance.
_Avoid_: Late booking

**Refund Due Booking**:
A booking for which refundable money is owed back.
_Avoid_: Cancelled booking

**Refunded Booking**:
A booking for which the refund has been completed.
_Avoid_: Cancelled booking

**Payment**:
Money collected against a booking.
_Avoid_: Transaction, traveler payment

**Trip Payments**:
The trip-scoped payment and reconciliation domain for payments, payment attempts, manual payment review, provider payment matching, ledgers, refunds, and payment exceptions connected to bookings on one trip.
_Avoid_: Organizer payments, payment setup, payout account, platform fee statements

**Payment Attempt**:
An attempted payment that may succeed or fail.
_Avoid_: Ledger entry

**Payment Purpose**:
The booking payment intent a payment attempt is trying to satisfy.
_Avoid_: Payment type, payment method

**Reservation Payment Attempt**:
A provider payment attempt intended to collect the booking reservation amount and reserve seats.
_Avoid_: Balance payment attempt

**Balance Payment Attempt**:
A provider payment attempt intended to collect balance due after seats are already reserved.
_Avoid_: Reservation payment attempt

**Active Payment Attempt**:
The current payment attempt for a payment purpose that can still produce a provider payment.
_Avoid_: Paid booking, active payment

**Superseded Payment Attempt**:
A payment attempt that has been replaced by a newer payment attempt for the same payment purpose.
_Avoid_: Failed payment

**Provider Payment Confirmation**:
A provider confirmation that captured money is matched to an expected payment attempt.
_Avoid_: Frontend checkout success, webhook, payment authorization

**Payment Confirming Booking**:
A booking waiting for backend confirmation of a provider payment attempt after checkout has begun.
_Avoid_: Reserved booking, paid booking

**Seat Hold**:
A short temporary hold on trip capacity while a provider payment attempt is being confirmed.
_Avoid_: Reserved seat, confirmed seat

**Seat Hold Expiry**:
The time at which a seat hold releases if provider payment confirmation has not completed.
_Avoid_: Booking expiry, payment due date

**Provider Payment**:
A payment confirmed by an integrated payment provider.
_Avoid_: Online payment, gateway payment

**Balance Payment Link**:
A booking-scoped payment link used to collect balance due after reservation.
_Avoid_: Public trip page payment link, generic payment link

**Gross Provider Payment Amount**:
The full traveler-paid amount confirmed by the payment provider before provider fees or settlement deductions.
_Avoid_: Settlement amount, net payout amount

**Provider Fee Amount**:
The payment provider's fee or deduction associated with a provider payment.
_Avoid_: Platform fee, booking discount

**Provider Net Settlement Amount**:
The provider-reported amount expected to settle or settled to the organizer after provider fees or deductions.
_Avoid_: Booking collected amount, gross payment amount

**Operational Exception**:
A trip-running issue that requires organizer review without itself owning booking, traveler, payment, or trip profile state.
_Avoid_: Booking state, payment state, refund record, cancellation

**Payment Exception**:
A payment situation that requires organizer review before normal booking progress can continue.
_Avoid_: Failed payment, reconciliation report

**Late Confirmed Payment Exception**:
A provider payment confirmed after the relevant seat hold expired.
_Avoid_: Successful booking

**Mismatched Provider Payment Exception**:
A provider payment confirmation whose amount, order, booking, or provider reference does not match the expected payment attempt.
_Avoid_: Successful booking, failed payment

**Provider Dispute**:
A provider-reported dispute, chargeback, or payment reversal claim for a provider payment.
_Avoid_: Refund record, cancellation

**Provider Dispute Exception**:
A provider dispute that requires organizer review before TripOS changes booking financial records.
_Avoid_: Automatic refund, booking cancellation

**Platform Fee**:
The organizer-absorbed fee TripOS records on successful provider payments and collects from the organizer later.
_Avoid_: Subscription fee, booking fee

**Platform Fee Basis**:
The successful provider payment amount used to calculate a platform fee.
_Avoid_: Reservation amount only, booking total only

**Platform Fee Collection**:
The later collection of recorded platform fees from an organizer.
_Avoid_: Payment split, settlement deduction

**Platform Fee Statement**:
A periodic summary of recorded platform fees owed by an organizer.
_Avoid_: Razorpay settlement report, booking invoice

**INR Amount**:
A money amount denominated in Indian rupees.
_Avoid_: Multi-currency amount

**Manual Payment**:
A payment recorded by a user rather than confirmed automatically by a payment provider.
_Avoid_: Offline payment, screenshot payment

**Manual Payment State**:
The review lifecycle state of a manual payment before it affects collected balance.
_Avoid_: Payment state

**Submitted Manual Payment**:
A manual payment that has been submitted but not approved.
_Avoid_: Pending manual payment

**Approved Manual Payment**:
A manual payment accepted by the organizer and counted toward collected balance.
_Avoid_: Verified manual payment

**Rejected Manual Payment**:
A manual payment rejected by the organizer.
_Avoid_: Failed manual payment

**Payment Proof**:
Evidence submitted for a manual payment.
_Avoid_: Screenshot, receipt upload

**Direct UPI Payment**:
A manual payment made directly to the organizer's UPI account and recorded through manual payment workflow.
_Avoid_: Public checkout UPI

**Payment QR**:
An organizer-provided QR image used by a traveler to make a direct UPI payment outside provider checkout.
_Avoid_: QR checkout, manual pay QR, Razorpay QR

**Payment Acknowledgement**:
Confirmation that a payment was recorded for a booking.
_Avoid_: Invoice, receipt

**Refund Acknowledgement**:
Confirmation that a refund record was recorded for a booking.
_Avoid_: Payment acknowledgement, receipt

**Reservation Acknowledgement**:
A notification sent when a booking becomes reserved, including reservation payment details and the booking-level access link when applicable.
_Avoid_: Booking confirmation

**Confirmation Notice**:
A notification sent when a booking becomes confirmed.
_Avoid_: Reservation acknowledgement

**Date Change Notice**:
A notification sent when trip dates change after reserved or confirmed bookings exist.
_Avoid_: Announcement

**Cancellation Notice**:
A notification sent when a trip, booking, or traveler cancellation should be communicated.
_Avoid_: Refund acknowledgement

**Refund Record**:
Money returned or owed back for a booking.
_Avoid_: Refund payment, provider refund

**Refund Reason**:
The explanation for why a refund record exists.
_Avoid_: Note

**Opening Payment Record**:
A historical collected amount imported into a booking during onboarding.
_Avoid_: Manual payment, provider payment

**Financial Ledger**:
The booking's financial records that determine collected, due, adjusted, and refunded amounts.
_Avoid_: Payment status, spreadsheet

**Booking Reconciliation**:
Determining whether a booking's collected, due, adjusted, and refunded amounts match its expected financial state.
_Avoid_: Settlement reconciliation, bank reconciliation

**Reconciliation Flag**:
A visible indication that booking reconciliation needs organizer attention.
_Avoid_: Error, settlement issue

**Ledger Entry**:
A financial ledger record that changes or explains a booking balance.
_Avoid_: Audit log, transaction

**Activity Log**:
A chronological record of operational actions taken on a booking or trip.
_Avoid_: Financial ledger, audit log

**Package**:
A purchasable trip option selected for a traveler.
_Avoid_: Plan, tier, variant

**Withdrawn Package**:
A package no longer available for future traveler selection but retained for historical booking records.
_Avoid_: Deleted package, inactive package, hidden package

**Booked Package Price**:
The package price captured for a traveler when the package is selected for a booking.
_Avoid_: Current package price

**Booked Reservation Amount**:
The reservation amount captured for a traveler when the booking reserves seats.
_Avoid_: Current reservation amount

**Booking Total**:
The payable amount for a booking before collected payments are applied.
_Avoid_: Trip price, payment amount

**Booking Adjustment**:
A booking-level discount, surcharge, or correction that changes the booking total.
_Avoid_: Coupon, manual edit

**Adjustment Reason**:
The explanation for why a booking adjustment changed the booking total.
_Avoid_: Note

**Rooming Note**:
An organizer-visible rooming preference or instruction related to a booking or traveler.
_Avoid_: Room assignment, room inventory

**Operational Export**:
An organizer-generated file of trip operations data for offline, vendor, or team use.
_Avoid_: Analytics report, generic export, PDF manifest

**Operational Metric**:
A trip operations count or amount used to decide immediate organizer action.
_Avoid_: Analytics metric, business intelligence

**Payment Schedule**:
Organizer-defined payment milestones for a trip.
_Avoid_: Installments, payment plan

**Payment Milestone**:
A payment obligation within a trip's payment schedule.
_Avoid_: Installment, reminder

**Reservation Milestone**:
The immediate payment milestone whose amount is derived from the booking's selected package reservation amounts.
_Avoid_: Deposit milestone

**Balance Milestone**:
The payment milestone for the remaining unpaid booking total, used only when money remains after reservation.
_Avoid_: Final installment

**Trip Start Date**:
The first date on which a trip's scheduled travel experience begins.
_Avoid_: Departure date

**Itinerary**:
The organizer-authored schedule and plan shown for a trip.
_Avoid_: Contract, package

**Itinerary Day**:
A sequenced part of an itinerary that describes one day or segment of a trip plan.
_Avoid_: Itinerary paragraph, schedule row

**Trip Date Change**:
An organizer-controlled change to a trip's scheduled date range after trip setup.
_Avoid_: Departure change, postponement

**Trip Capacity**:
The maximum number of travelers that can be reserved for a trip.
_Avoid_: Seat limit, inventory

**Available Seats**:
The number of traveler seats still available to reserve for a trip.
_Avoid_: Seats left, inventory count

**Bookable Seats**:
The number of traveler seats available for new public booking attempts after active seat holds are considered.
_Avoid_: Available seats, exact public inventory

**Availability Band**:
A public availability label derived from available seats.
_Avoid_: Exact seat count

**Notification**:
A system-sent or organizer-sent message related to a trip, booking, payment, document, or operational update.
_Avoid_: Chat message, WhatsApp message, alert

**Reminder**:
A notification that prompts action on an existing obligation.
_Avoid_: Alert, follow-up

**Automatic Reminder**:
A reminder sent by TripOS from a narrow predefined workflow.
_Avoid_: Automation builder

**Draft Recovery Reminder**:
An automatic reminder sent 20 hours after draft creation in the MVP.
_Avoid_: Abandoned checkout campaign

**Balance Due Reminder**:
An automatic reminder sent before a balance milestone is due; the MVP default is 3 days before the due date.
_Avoid_: Payment campaign

**Overdue Balance Reminder**:
An automatic reminder sent 1 day after a balance milestone is missed, then stopped automatically.
_Avoid_: Collections campaign

**Missing Requirements Reminder**:
An automatic reminder sent 3 days before trip start for unmet confirmation requirements.
_Avoid_: General reminder

**Automatic Reminder Timing**:
The default timing rules TripOS uses for automatic reminders.
_Avoid_: Automation settings

**Balance Reminder Lead Time**:
The trip-level setting for how long before a balance milestone the balance due reminder is sent.
_Avoid_: Reminder schedule

**Manual Reminder**:
A reminder sent by a user from an operational context.
_Avoid_: Custom campaign

**Announcement**:
A notification that broadcasts an organizer's trip operational update.
_Avoid_: Chat message, group message

**Notification Channel**:
A medium through which a notification is delivered.
_Avoid_: Chat, inbox

**WhatsApp Channel**:
The notification channel used for operational WhatsApp delivery without owning or mirroring group chat.
_Avoid_: WhatsApp chat, WhatsApp group

**Email Channel**:
The notification channel used for email delivery.
_Avoid_: SMS

## Relationships

- An **Organizer** can have one or more **Users**
- **Organizer Onboarding** creates one **Organizer** and one first **Owner** membership
- An **Organizer** has one **Operations Dashboard**
- **Organizer Settings** is a UI grouping, not a domain owner
- **Organizer Settings** can link to **Creative Setup** in the user interface, but does not own **Creative Setup**
- **Organizer Settings** can link to **Team Access** in the user interface, but does not own **Team Access**
- **Organizer Preferences** is not a first-version domain term
- An **Organizer** has **Team Access**
- **Creative Setup** owns organizer-level creative generation preferences, not generated creative assets
- Generated posters, itinerary posters, seats-left posters, and other trip-specific creative assets are scoped to the relevant **Trip**
- An **Organizer** has **Organizer Profile**
- **Organizer Profile** owns public organizer name, logo, description, and contact channel
- **Organizer Profile** may include one **Organizer Logo**
- **Organizer Profile** owns **Organizer Public Page** content and publication state
- **Organizer Profile** provides public profile content to an **Organizer Public Page**
- **Organizer Profile** has one **Organizer Profile Publication State**
- Publishing **Organizer Profile** requires **Organizer Profile Readiness**
- **Organizer Profile Readiness** requires **Public Organizer Description** and required **Organizer Policies**
- **Public Organizer Media** is encouraged but not required for **Organizer Profile Readiness**
- A public contact channel is encouraged but not required for **Organizer Profile Readiness**
- **Organizer Profile** includes **Public Organizer Description**
- **Organizer Profile** can display **Public Organizer Media**
- An **Organizer** has **Organizer Media**
- **Organizer Media** owns organizer-level uploads, captions, ordering, visibility, and reuse
- **Public Organizer Media** belongs to **Organizer Media**, not to **Organizer Profile** or **Trip Profile**
- **Public Organizer Media** can remain visible even if an older **Trip** is archived
- **Trip Media Gallery** and **Public Organizer Media** are separate public media collections
- **Organizer Media** can support **Organizer Public Pages**, **Public Trip Pages**, and future creative generation
- An **Organizer** has **Organizer Policies**
- **Organizer Policies** includes **Organizer Privacy Policy**, **Organizer Refund Policy**, and **Organizer Cancellation Policy** in the first version
- **Organizer Policies** provides policy content for an **Organizer Public Page** and **Public Trip Pages**
- **Organizer Profile** can include a public contact channel chosen by the **Organizer**
- **Organizer Profile** does not include **Organizer Policies**, **Payment Setup**, **Team Access**, provider credentials, traveler documents, bookings, or operational metrics
- **Owners** can edit and publish **Organizer Profile**
- **Owners** can edit **Organizer Policies** in the first version
- **Operators** can view **Organizer Profile** and **Organizer Policies** but cannot edit policies or publish the profile in the first version
- An **Organizer** has **Organizer Payments**
- **Organizer Payments** owns **Payment Setup** and organizer-level payment readiness
- **Organizer Onboarding** leads to the **Organizer Setup Checklist**
- An **Organizer** can offer one or more **Trips**
- A **Trip** is owned by an **Organizer** but is not part of **Organizer Profile**, **Organizer Settings**, **Organizer Media**, **Organizer Policies**, **Organizer Payments**, or **Team Access**
- **Trips** own trip profile, packages, itinerary, confirmation requirements, booking availability, trip profile publication readiness, public trip pages, and trip publication state
- **Trip Bookings**, **Trip Travelers**, **Trip Payments**, and **Trip Operations** belong to a **Trip** but are separate trip-scoped domains
- **Trip Operations** owns **Reminders**, **Announcements**, **Operational Exports**, **Activity Log**, and **Operational Exception** review
- **Trip Operations** can display data from **Trips**, **Trip Bookings**, **Trip Travelers**, and **Trip Payments** to help users run a trip
- **Trip Operations** does not own **Booking State**, **Traveler** records, **Payment State**, **Financial Ledger**, or **Trip Profile** content
- **Trips** are managed from a **Trip Workspace** inside the **Operations Dashboard**
- A **Trip Workspace** has exactly one selected **Trip**
- A selected **Trip** exists only inside a **Trip Workspace**
- A **Trip** has one **Trip Profile**
- A **Trip Profile** includes one **Trip Description**
- **Trip Description** uses **Trip Rich Text**
- **Itinerary Day** descriptions use **Trip Rich Text**
- A **Trip Profile** includes one **Trip Media Gallery**
- A **Trip Media Gallery** has one or more **Trip Media Items**
- A **Trip Media Gallery** may have one cover **Trip Media Item**
- MVP **Trip Media Items** are images only
- MVP **Trip Media Items** are uploaded and stored by TripOS, not hotlinked from external image URLs
- Private **Trip Media Items** are visible only in **Trip Profile** in the MVP
- Public **Trip Media Items** can appear on the **Public Trip Page**
- Meaningful **Trip Profile** section saves record **Activity Log** actions
- **Owners** can manage all unlocked **Trip Profile** content
- **Operators** can manage unlocked non-commercial **Trip Profile** content except **Packages** and **Payment Schedule**
- **Operators** can manage unlocked **Confirmation Requirements**
- **Operators** can manage unlocked **Trip Media Gallery** content
- Publishing a **Public Trip Page** requires **Trip Profile Publication Readiness**
- **Trip Profile Publication Readiness** requires **Trip Description**, at least one **Package**, reviewed **Payment Schedule**, at least one **Itinerary Day**, reviewed **Confirmation Requirements**, and explicit owner acknowledgement of the **Published Trip Profile Lock**
- **Trip Media Gallery** completion is encouraged but not required for **Trip Profile Publication Readiness**
- Publishing a **Public Trip Page** creates a **Published Trip Profile Lock**
- A **Published Trip Profile Lock** blocks normal edits to **Trip Profile** content, **Packages**, **Confirmation Requirements**, **Trip Date Changes**, and **Trip Capacity**
- The MVP has no self-serve unlock for a **Published Trip Profile Lock**
- A **Published Trip Profile Lock** does not block trip operations after publication
- A **Published Trip Profile Lock** does not block closing **Booking Availability**
- Archiving a **Public Trip Page** does not remove the **Published Trip Profile Lock**
- Publishing a **Public Trip Page** records an **Activity Log** action with the owner lock acknowledgement
- Unlocked **Trip Profile** package changes affect future package selection, while existing travelers keep their captured **Booked Package Price** and **Booked Reservation Amount**
- A selected **Package** can become a **Withdrawn Package** without changing historical **Traveler Slots**
- A **Withdrawn Package** cannot be selected for new **Public Bookings** or **Manual Bookings**
- A **Community-Led Organizer** is the MVP beachhead type of **Organizer**
- **Payment Setup** may guide a **Community-Led Organizer** through the **Individual Creator Payment Path**
- An **Organizer** has one **Payout Account** in the MVP
- An **Organizer** can see **Payout Status** in the MVP
- **Organizer Payments** includes **Payment Setup**
- An **Organizer** has at most one **Connected Provider Account** in the MVP
- MVP **Payment Setup** uses a **Connected Provider Account**
- **Payment Setup** connects an organizer-owned provider account to TripOS rather than creating a platform-managed provider linked account
- **Payment Setup** presents **Settlement Readiness** without requiring organizers to manually edit **Payout Account** details
- **Settlement Readiness** is provider-derived or support-confirmed, not owner self-certified
- Missing **Settlement Readiness** disables provider payments without unpublishing **Public Trip Pages** or changing existing **Bookings**
- **Owners** can manage **Payment Setup** actions but cannot self-certify provider-derived readiness facts
- A **Connected Provider Account** can create **Payment Attempts** and produce **Provider Payments**
- A **Connected Provider Account** belongs to the **Organizer**, not to the individual **Owner** who granted **Provider Authorization**
- A **Connected Provider Account** requires **Provider Authorization**
- **Provider Authorization** is owner-initiated but organizer-scoped
- **OAuth Provider Authorization** is the preferred **Provider Authorization** method
- **OAuth Provider Authorization** is the normal credential path for **Connected Provider Accounts**
- Completed **Provider Authorization** does not by itself create **Online Payment Readiness**
- **API Key Provider Authorization** is a pilot fallback, not the main organizer-facing path
- **Assisted Payment Setup** can use **API Key Provider Authorization** only for tightly controlled pilots
- **Assisted Payment Setup** is temporary and hidden from normal organizer-facing setup
- Only **Owners** can disconnect a **Connected Provider Account**
- Disconnecting a **Connected Provider Account** disables the provider payment method without deleting historical **Provider Payments**, **Ledger Entries**, **Bookings**, or **Public Trip Pages**
- Disconnecting a **Connected Provider Account** deactivates active unpaid **Payment Attempts** and releases their **Seat Holds**
- Provider confirmations received after **Provider Authorization** is disconnected are still reconciled against historical **Payment Attempts**
- Replacing a **Connected Provider Account** requires explicit **Owner** confirmation
- Replacing a **Connected Provider Account** disables the provider payment method until **Online Payment Readiness** is restored
- Replacing a **Connected Provider Account** preserves historical **Provider Payments** and deactivates active unpaid **Payment Attempts**
- **Sensitive Provider Credentials** are not visible in organizer-facing product surfaces
- A **Connected Provider Account** has one **Provider Mode**
- The MVP does not support parallel test and live **Provider Modes** for one **Organizer**
- A **Connected Provider Account** has one **Provider Connection State**
- **Online Payment Readiness** requires a **Healthy Provider Connection**
- **Online Payment Readiness** requires **Live Provider Mode**
- **Test Provider Mode** can support non-production provider payment testing but cannot make the provider payment method ready for **Public Booking**
- **Test Provider Mode** payment testing is an owner or staff validation workflow, not the normal public booking path
- A **Provider Connection Test** does not create **Bookings** or **Seat Holds**
- A **Provider Connection Test** does not create real **Provider Payments**, **Ledger Entries**, or **Platform Fees**
- A **Provider Connection Test** produces a **Provider Connection Test Result**
- **Provider Verification** is completed by the payment provider, not TripOS
- **Provider Eligibility** is a provider-side constraint, not organizer-facing setup language in the MVP
- **Provider Verification** has one **Provider Verification Status**
- The **Public Trip URL** can be the **Provider Verification URL**
- MVP **Payment Setup** does not store **Provider Verification Documents** after provider submission
- **Payment Setup** may show **Provider Disclosure** without making the provider name the workflow title
- MVP pilots may use **Assisted Payment Setup** while preserving **Payment Setup** as the organizer-facing workflow
- **Assisted Payment Setup** uses the same organizer-facing statuses as **Payment Setup**
- **Assisted Payment Setup** is not a separate organizer-facing mode
- **Online Payment Readiness** requires **Verified Provider Verification**, ready **Settlement Readiness**, and enabled **Provider Payment Capability**
- **Online Payment Readiness** is derived from **Provider Payment Setup** and is not the same thing as **Provider Payment Setup**
- Only **Owners** can submit or edit **Payment Setup**
- **Operators** can view **Online Payment Readiness** blockers but cannot submit or edit **Payment Setup**
- **Payment Setup** confirms the **Payout Account** before provider payments can open
- Public booking requires at least one ready payment method
- The provider payment method requires **Online Payment Readiness**
- If **Online Payment Readiness** is unavailable, an **Organizer** can operate as **Manual Payments Only**
- **Manual Payment Instructions** belong to **Payment Setup**
- **Manual Payment Availability** belongs to a **Trip**
- A **Trip** can accept traveler-submitted **Manual Payments** only when **Manual Payment Instructions** exist and **Manual Payment Availability** is open
- **Manual Payment Availability** can be open only when **Booking Availability** is open
- A **User** can act on behalf of one or more **Organizers**
- A **User** has one **Organizer Membership** for each **Organizer** they act for
- **Team Access** manages **Organizer Memberships** and **Organizer Invitations**
- An **Organizer Membership** has an **Owner** or **Operator** role
- An **Organizer Invitation** creates an **Organizer Membership** when accepted
- An **Organizer** can have multiple **Owner** memberships
- An **Organizer** must always have at least one **Owner** membership
- A **Trip** has one **Trip Overview**
- A **Trip Duplicate** copies **Trip Profile** content and package terms but not bookings, payments, travelers, or the **Published Trip Profile Lock**
- A **Trip Duplicate** starts with draft publication, closed booking availability, and an unlocked **Trip Profile**
- A **Trip Duplicate** can copy **Trip Media Item** records while reusing the same stored image assets
- The **Public Discovery Catalog** can list **Organizer Public Pages** and published **Public Trip Pages**
- The **Public Discovery Catalog** owns **Demand Pages**, **Discovery SEO Metadata**, **Discovery Routing**, and **Discovery Listing Rules**
- The **Public Discovery Catalog** composes **Published Organizer Profile** and published **Public Trip Pages**
- **Public Discovery Catalog** owns **Discovery Routing** and **Discovery Listing Rules** for **Organizer Public Pages**
- **Public Discovery Catalog** can own **Discovery Routing** and **Discovery Listing Rules** around published **Public Trip Pages**
- **Public Discovery Catalog** can host and link to **Organizer Public Pages** and **Public Trip Pages**, but does not own their source content or booking rules
- An **Organizer** may have one **Organizer Public Page**
- An **Organizer Public Page** has one **Organizer Public URL**
- An **Organizer Public URL** lives in **Public Discovery Catalog** routing
- An **Organizer Public Page** content comes from **Organizer Profile**, **Organizer Media**, **Organizer Policies**, and published **Public Trip Pages**
- An **Organizer Public Page** can list published **Public Trip Pages** for that **Organizer**
- A published **Public Trip Page** can exist before **Published Organizer Profile**
- **Organizer Profile Readiness** does not block publishing a **Public Trip Page**
- The **Public Discovery Catalog** lists only **Published Organizer Profile** and published **Public Trip Pages**
- **Demand Pages** should link only to published **Public Trip Pages** whose **Organizer** has **Published Organizer Profile**
- Published offered trips on an **Organizer Public Page** are derived from published **Public Trip Pages**, not manually curated in the first version
- A **Demand Page** distributes demand to relevant **Organizer Public Pages** and published **Public Trip Pages**
- A **Demand Page** has one **Demand Page URL**
- A first-version **Demand Page** is a **Configured Demand Page**
- A **Configured Demand Page** can use curated pins or rule-based selection for relevant organizers and trips
- A **Configured Demand Page** uses **Discovery Listing Rules** to select relevant organizer and trip links
- A **Configured Demand Page** belongs to **Public Discovery Catalog**
- **Internal Admin** provides the staff workflow for configuring **Configured Demand Pages** in the first version
- A **Demand Page** does not create **Bookings** or **Booking Requests**
- A **Demand Page** does not own checkout, payment, booking rules, or trip operations
- The **TripOS Marketing Site** is distinct from **Public Discovery Catalog**, **Organizer Public Pages**, and **Public Trip Pages**
- **Internal Admin** orchestrates module-owned staff actions and does not own **Organizer**, **Trip**, **Public Discovery**, **Booking**, **Traveler**, or **Payment** business state
- A **Trip** has one **Public Trip Page**
- **Trips** own **Public Trip Page** content, **Publication State**, **Booking Availability**, and the **Public Booking Gate**
- **Public Trip Page** belongs to the **Trip Profile** and trip booking domain, even when routed or linked from **Public Discovery Catalog**
- A **Public Trip Page** has one **Public Trip URL**
- A **Public Trip URL** may live in **Public Discovery Catalog** routing
- Public booking URLs and checkout behavior are owned by **Trips**, **Trip Bookings**, and **Trip Payments**, not **Public Discovery Catalog**
- MVP **Trips** are **Paid Trips**
- A **Public Trip Page** has one **Publication State**
- A **Trip** has one **Booking Availability**
- The **Public Booking Gate** allows **Public Booking** only when the **Public Trip Page** is published, **Booking Availability** is open, at least one payment method is ready, and **Bookable Seats** are sufficient
- A public QR-based manual payment submission creates a **Draft Booking** and a **Submitted Manual Payment**
- A **Submitted Manual Payment** does not create a **Seat Hold**
- A public QR-based manual payment submission is for the **Booking Reservation Amount**
- A **Submitted Manual Payment** can reserve seats only after approval, when the **Booking Reservation Amount** is met and **Bookable Seats** are sufficient
- Missing ready payment methods fully closes **Public Booking**, rather than creating unpaid public booking requests
- A published **Public Trip Page** with unavailable **Public Booking** can show **Bookings Opening Soon**
- **Bookings Opening Soon** does not create a waitlist or unpaid booking request in the MVP
- A **Public Trip Page** can be published before **Online Payment Readiness** is present
- **Online Payment Readiness** does not block **Public Trip Page** publication
- **Trip Profile Publication Readiness** blocks **Public Trip Page** publication until required profile content is reviewed
- Publishing a **Public Trip Page** creates a **Published Trip Profile Lock**
- If **Provider Connection State** becomes unhealthy, existing **Public Trip Pages** remain published but provider checkout is hidden
- MVP **Public Booking** uses **No-Login Public Booking**
- A **Trip** may later have one or more **Departures**, but currently stands alone as the scheduled offering
- A **Trip** has one or more **Packages**
- A draft **Trip** starts with at least one **Package**
- A **Trip** has **Confirmation Requirements**
- **Confirmation Requirements** can change after bookings exist without automatically changing **Booking State**
- A **Trip** has one **Payment Schedule**
- **Payment Schedule** is managed from **Trip Profile** before publication
- A **Trip** has one **Trip Capacity**
- A **Trip** has one **Itinerary**
- An **Itinerary** has one or more **Itinerary Days**
- An **Itinerary** can change after bookings exist without changing financial terms
- Itinerary changes may prompt an **Announcement** but do not require one in the MVP
- A **Completed Trip** completes active reserved or confirmed bookings as a bulk operational action
- A **Trip Date Change** changes the **Trip Start Date** without directly changing financial terms
- A **Trip Date Change** after bookings exist requires an **Owner** in the MVP
- A **Trip Date Change** after reserved or confirmed bookings exist produces a **Date Change Notice** by default
- A **Trip Cancellation** closes booking availability and cancels active reserved or confirmed bookings as a bulk operational action
- A **Trip Cancellation** requires an **Owner** in the MVP
- A **Trip Cancellation** has one **Cancellation Reason**
- A **Trip Cancellation** does not create a **Ledger Entry** directly
- A **Trip Cancellation** produces a **Cancellation Notice** by default
- A **Payment Schedule** has one **Reservation Milestone**
- A **Payment Schedule** may have one **Balance Milestone**
- A **Balance Milestone** is due relative to the **Trip Start Date**
- A **Booking** created after its **Balance Milestone** is due must pay the full **Booking Total** to reserve seats
- A **Booking** cannot start reservation payment unless the trip has enough **Bookable Seats**
- A **Booking** cannot reserve beyond **Trip Capacity** in the MVP
- A **Payment Confirming Booking** may create one or more **Seat Holds**
- A **Draft Booking** does not create **Seat Holds**
- A **Seat Hold** is created only when a reservation **Payment Attempt** begins before seats are reserved
- A **Seat Hold** has one **Seat Hold Expiry**
- A **Seat Hold** is not a **Reserved Booking**
- An expired **Seat Hold** releases capacity for other booking attempts
- Expired **Seat Holds** do not produce a payment-abandonment reminder in the MVP
- A **Reminder** is a type of **Notification**
- An **Automatic Reminder** is a type of **Reminder**
- **Draft Recovery Reminder**, **Balance Due Reminder**, **Overdue Balance Reminder**, and **Missing Requirements Reminder** are MVP **Automatic Reminders**
- **Automatic Reminder Timing** uses simple defaults in the MVP
- A **Trip** may have one **Balance Reminder Lead Time**
- A late reserved booking with unmet **Confirmation Requirements** receives a **Missing Requirements Reminder** soon after reservation
- A **Manual Reminder** is a type of **Reminder**
- An **Announcement** is a type of **Notification**
- A **Payment Acknowledgement** is a type of **Notification**
- A **Refund Acknowledgement** is a type of **Notification**
- A **Reservation Acknowledgement** is a type of **Notification**
- A **Confirmation Notice** is a type of **Notification**
- A **Date Change Notice** is a type of **Notification**
- A **Cancellation Notice** is a type of **Notification**
- A **Notification** is delivered through a **Notification Channel**
- A **Notification** content can use **Organizer Profile** facts for traveler-facing organizer branding
- The MVP supports the **WhatsApp Channel** and **Email Channel**
- A **Reminder** is sent to the **Booking Contact** by default
- A document-related **Reminder** may also be sent to the relevant **Traveler**
- An **Announcement** is sent to the **Booking Contact** and the **Active Travelers** in reserved or confirmed bookings
- A **Draft Booking** may receive one **Reminder** before **Draft Expiry** if booking contact details exist
- A **Completed Booking** with due balance may receive an organizer-triggered **Reminder**
- **Cancelled Bookings** do not receive payment or document **Reminders**
- **Manual Reminders** are sent by an **Owner** or **Operator** in the MVP
- **Announcements** are sent by an **Owner** or **Operator** in the MVP
- Sending a **Notification** records an **Activity Log** action
- A **Package** has one **Reservation Amount**
- A **Booking Contact** may or may not be a **Traveler**
- A **Trip** can have one or more **Bookings**
- A **Booking** belongs to exactly one **Trip**
- A **Manual Booking** is a type of **Booking**
- A **Manual Booking** is created from the **Operations Dashboard**, not the **Public Trip Page**
- A **Manual Booking** does not require **Provider Payment Setup**
- A **Booking Import** creates or updates bookings for exactly one **Trip**
- A **Booking Import** creates reserved bookings only when opening payment records meet the **Booking Reservation Amount**
- A **Booking Import** does not create confirmed bookings by default
- A **Booking Import** cannot exceed **Trip Capacity** by default
- A **Booking** has exactly one **Booking Contact**
- A **Booking Contact** has **Booking Contact Details** before payment starts
- Public booking requires **Booking Contact Details**, traveler count, package selection, and pricing inputs before payment starts
- Public booking does not require full **Traveler Identity Details** before payment starts in the MVP
- A **Booking** has one or more **Booking Access Links**
- The **Traveler Portal** is accessed through **Booking Access Links**
- **Balance Payment Links** are accessed through the **Traveler Portal** or **Booking Access Links**
- **Balance Payment Links** are scoped to an existing **Booking**
- A **Booking-Level Access Link** belongs to exactly one **Booking**
- A **Traveler-Level Access Link** belongs to exactly one **Traveler**
- A **Booking-Level Access Link** is sent to the **Booking Contact** by default after reservation
- **Traveler-Level Access Links** can be generated later for individual traveler readiness
- Booking contact changes revoke prior **Booking-Level Access Links**
- A **Booking Access Link** has one **Access Link Expiry**
- Expired **Booking Access Links** can be regenerated and sent again
- A **Booking** contains one or more **Traveler Slots**
- A **Traveler Slot** may become a **Traveler** when **Traveler Identity Details** are complete
- An **Active Traveler** belongs to a **Reserved Booking** or **Confirmed Booking**
- A **No-Show Traveler** remains part of the booking unless separately cancelled
- A **No-Show Traveler** does not automatically change the **Booking Total** or refund state
- **Traveler Check-In** applies to one **Active Traveler**
- **Traveler Check-In** is performed by an **Owner** or **Operator** in the MVP
- **Traveler Check-In** is available for active travelers in reserved or confirmed bookings
- A **Booking** reserves all of its travelers' seats only after its **Booking Reservation Amount** is paid
- A **Manual Booking** can reserve seats through approved **Manual Payments**
- A **Booking Reservation Amount** is the sum of the reservation amounts for the booking's travelers' selected packages
- Reservation payment requires traveler slot count and package selection
- A **Booking** has one **Booking State**
- A **Draft Booking** may have one **Draft Expiry**
- Public booking creates a **Draft Booking** before provider payment succeeds
- A **Payment Attempt** belongs to a **Draft Booking** or **Payment Confirming Booking**
- A **Draft Booking** can become a **Payment Confirming Booking** when provider checkout begins
- A **Booking** has one **Payment State**
- A **Booking** has one **Financial Ledger**
- A **Financial Ledger** has one or more **Ledger Entries**
- A **Booking** can have one **Activity Log**
- A **Trip** can have one **Activity Log**
- A **Booking Contact** can edit traveler details before reservation
- Traveler changes after reservation are organizer-controlled
- Booking contact changes after reservation are organizer-controlled
- Package changes after reservation are organizer-controlled
- Package changes after reservation create or explain a **Ledger Entry** only when they change the **Booking Total**
- A **Booking** can have one or more **Payments**
- A **Payment** belongs to exactly one **Booking**
- A **Booking** can have one or more **Payment Attempts**
- A **Payment Attempt** has one **Payment Purpose**
- A **Reservation Payment Attempt** is a type of **Payment Attempt**
- A **Balance Payment Attempt** is a type of **Payment Attempt**
- A **Booking** has at most one **Active Payment Attempt** for a given **Payment Purpose**
- A retry creates a new **Payment Attempt** and may make the previous attempt a **Superseded Payment Attempt**
- A **Provider Payment Confirmation** is matched to an expected **Payment Attempt** before creating a **Provider Payment**
- A provider authorization alone does not create a **Provider Payment**
- A frontend provider checkout success can create a **Payment Confirming Booking** but does not reserve seats by itself
- A **Provider Payment** is a type of **Payment**
- A **Provider Payment** affects collected balance using the **Gross Provider Payment Amount** after provider confirmation
- **Provider Fee Amount** does not reduce a booking's collected balance
- **Provider Net Settlement Amount** does not determine a booking's collected balance
- Trip-level Payments can show **Gross Provider Payment Amount**, **Provider Fee Amount**, **Provider Net Settlement Amount**, and **Platform Fee** separately where available
- A **Provider Payment** can reserve seats only after backend confirmation
- An initial **Provider Payment** reserves seats only when it meets the **Booking Reservation Amount**
- Later **Provider Payments** can collect balance due after reservation
- Later balance **Provider Payments** use **Balance Payment Links**, not the **Public Trip Page**
- Later balance **Provider Payments** do not create **Seat Holds**
- **Balance Payment Links** use **Balance Payment Attempts**
- MVP **Balance Payment Links** collect the current balance due, not arbitrary custom amounts
- **Owners** and **Operators** can manually send **Balance Payment Links**
- **Balance Due Reminders** can include **Balance Payment Links**
- A fully paid or cancelled **Booking** cannot start a new **Balance Payment Attempt**
- A backend-confirmed **Provider Payment** converts active **Seat Holds** for that booking into reserved seats
- A backend-confirmed **Provider Payment** after **Seat Hold Expiry** may create a **Late Confirmed Payment Exception**
- A **Late Confirmed Payment Exception** does not auto-reserve seats when **Bookable Seats** are insufficient
- A backend-confirmed **Provider Payment** after **Seat Hold Expiry** can auto-reserve seats when **Bookable Seats** are sufficient
- A **Late Confirmed Payment Exception** requires organizer review for reservation or refund handling
- An **Owner** or **Operator** can resolve the booking operation side of a **Late Confirmed Payment Exception**
- A backend provider confirmation with mismatched payment details creates a **Mismatched Provider Payment Exception**
- A duplicate **Provider Payment Confirmation** does not create duplicate **Provider Payments**
- A **Provider Dispute** creates a **Provider Dispute Exception** for organizer review
- A **Provider Dispute Exception** does not automatically create a **Refund Record** or change **Booking State** in the MVP
- Pending **Payment Attempts** do not affect collected balance or reserve seats
- A successful **Provider Payment** may produce a **Platform Fee**
- A **Platform Fee** uses the successful **Provider Payment** amount as its **Platform Fee Basis**
- MVP **Platform Fees** are recorded on successful **Provider Payments**
- MVP **Manual Payments** do not produce **Platform Fees**
- MVP **Platform Fee Collection** happens later from the **Organizer**, not through provider split settlement
- MVP **Platform Fee Collection** uses monthly **Platform Fee Statements**
- Trip-level Payments can show **Platform Fees** attributable to that **Trip** for reconciliation
- **Trip Payments** provides **Platform Fee** facts for **Platform Fee Statements**
- **Organizer Payments** does not manage **Platform Fee Statements** in the MVP
- **Internal Admin** can manage the staff workflow for **Platform Fee Statements** in the MVP
- A **Manual Payment** is a type of **Payment**
- A **Manual Payment** affects collected balance only after approval
- A **Manual Payment** may have **Payment Proof**
- **Payment Proof** is **Sensitive Payment Information**
- Traveler-submitted **Manual Payments** require **Payment Proof**
- Organizer-entered **Manual Payments** are **Approved Manual Payments** by default
- Traveler-submitted **Manual Payments** start as **Submitted Manual Payments**
- A **Direct UPI Payment** is a type of **Manual Payment**
- A **Payment QR** can be used to initiate a **Direct UPI Payment**
- A **Payment QR** is part of **Manual Payment Instructions**
- A recorded **Payment** can produce a **Payment Acknowledgement**
- A **Provider Payment** that makes a booking reserved produces a **Reservation Acknowledgement**, not a separate **Payment Acknowledgement**, by default
- Later **Provider Payments** may produce **Payment Acknowledgements** by default
- Approved traveler-submitted **Manual Payments** produce **Payment Acknowledgements** by default
- Organizer-entered **Manual Payments** may produce **Payment Acknowledgements** at user choice
- **Payment Acknowledgements** are sent to the **Booking Contact** by default
- A **Reservation Acknowledgement** is sent when a **Booking** becomes a **Reserved Booking**
- A **Reservation Acknowledgement** may include amount received, balance due, and the **Booking-Level Access Link**
- A **Confirmation Notice** is sent when a **Booking** becomes a **Confirmed Booking**
- **Reservation Acknowledgements** and **Confirmation Notices** are sent to the **Booking Contact** by default
- **Reservation Acknowledgements** and **Confirmation Notices** may also be sent to **Active Travelers** once **Traveler Identity Details** exist
- A **Booking** can have one or more **Refund Records**
- A **Refund Record** has one **Refund Reason**
- A **Refund Record** creates or explains a **Ledger Entry**
- Creating a **Refund Record** requires an **Owner** in the MVP
- Creating a **Refund Record** records an **Activity Log** action
- A **Refund Record** may produce a **Refund Acknowledgement** at user choice
- **Refund Acknowledgements** are sent to the **Booking Contact** by default
- A **Booking** can have one or more **Opening Payment Records**
- A **Booking Import** may create **Opening Payment Records**
- A **Traveler Cancellation** belongs to exactly one **Booking**
- A **Traveler Cancellation** releases the traveler's seat unless it is handled as a **Traveler Replacement**
- **Traveler Cancellation** is organizer-controlled in the MVP
- A **Traveler Cancellation** has one **Cancellation Reason**
- A **Traveler Cancellation** does not create a **Ledger Entry** directly
- A **Traveler Cancellation** records an **Activity Log** action
- A **Traveler Replacement** belongs to exactly one **Booking**
- A **Traveler Replacement** inherits the replaced traveler's package and commercial position
- A **Traveler Replacement** records an **Activity Log** action
- A **Traveler Addition** belongs to exactly one **Booking**
- A **Traveler Addition** requires enough **Available Seats**
- A **Traveler Addition** changes the **Booking Total**
- A **Traveler Addition** reserves the added traveler's seat only after the added traveler's package reservation amount is collected
- An unpaid **Traveler Addition** does not hold a seat in the MVP
- A **Traveler Addition** records an **Activity Log** action
- A **Traveler** can have one or more **Traveler Documents**
- A **Traveler Document** belongs to exactly one **Traveler**
- A **Traveler Document** has one **Document State**
- Identity **Traveler Documents** are **Sensitive Traveler Information**
- **Traveler Documents** and **Payment Proof** are stored in TripOS in the MVP
- Downloading **Sensitive Traveler Information** records an **Activity Log** action
- Downloading **Sensitive Payment Information** records an **Activity Log** action
- A **Traveler Data Request** is handled through the **Organizer** in the MVP
- A **Traveler** may have **Travel Logistics**
- A **Traveler** may have one **Emergency Contact**
- A **Traveler** may have one **Medical Disclosure**
- A **Medical Disclosure** is **Sensitive Traveler Information**
- A **Confirmed Booking** satisfies the trip's **Confirmation Requirements**
- A **Booking** becomes a **Confirmed Booking** only through organizer action
- Changing **Confirmation Requirements** can surface missing readiness for existing **Confirmed Bookings** without automatically unconfirming them
- **Unconfirm Booking** moves a **Confirmed Booking** back to a **Reserved Booking**
- **Unconfirm Booking** does not send a notification automatically in the MVP
- A **Booking** becomes a **Completed Booking** only through organizer action in the MVP
- **Confirmation Requirements** may include required **Travel Logistics**
- **Confirmation Requirements** may include required **Emergency Contact**
- **Confirmation Requirements** may include required **Medical Disclosure**
- **Confirmation Requirements** may include additional traveler identity, medical, or document requirements
- **Confirmation Requirements** may include payment expectations
- A **Booking Cancellation** applies to the whole **Booking**
- **Booking Cancellation** is organizer-controlled in the MVP
- A **Booking Cancellation** has one **Cancellation Reason**
- A **Booking Cancellation** does not create a **Ledger Entry** directly
- A **Booking Cancellation** records an **Activity Log** action
- A **Traveler Slot** has exactly one selected **Package** within a booking
- A **Traveler Slot** has one **Booked Package Price** within a booking
- A **Traveler Slot** has one **Booked Reservation Amount** once its seat is reserved
- A **Booking Total** is based on the selected packages for its travelers plus booking adjustments
- A **Booking Adjustment** belongs to exactly one **Booking**
- A **Booking Adjustment** has one **Adjustment Reason**
- A **Booking Adjustment** creates or explains a **Ledger Entry**
- Creating a **Booking Adjustment** records an **Activity Log** action
- A **Booking Adjustment** can create a **Refund Due Booking** when collected amount exceeds booking total
- A **Rooming Note** may belong to a **Booking** or **Traveler**
- An **Operational Export** belongs to exactly one **Trip**
- An **Operational Export** excludes **Draft Bookings** by default
- An **Operational Export** can include traveler check-in and no-show status
- An **Operational Export** includes **Sensitive Traveler Information** only when explicitly selected
- An **Operational Export** includes **Sensitive Payment Information** only when explicitly selected
- A **Payment State** is determined from the **Financial Ledger**
- **Booking Reconciliation** is determined from the **Financial Ledger**
- A **Completed Trip** may have **Reconciliation Flags**
- **Available Seats** are determined from **Trip Capacity** minus active reserved travelers
- **Bookable Seats** are determined from **Available Seats** minus active **Seat Holds**
- **Sold Out Booking Availability** is determined from **Available Seats**
- An **Availability Band** is shown on the **Public Trip Page** instead of exact available seats

## Example dialogue

> **Dev:** "When a **User** creates a trip, who owns the trip?"
> **Domain expert:** "The **Organizer** owns the trip; the **User** is just the person acting for that organizer."
>
> **Dev:** "Where does an operator approve manual payments and chase missing documents?"
> **Domain expert:** "In the **Operations Dashboard**."
>
> **Dev:** "Can an organizer fully hide TripOS branding in the MVP?"
> **Domain expert:** "No, MVP supports **Organizer Profile** branding but not full white-label branding."
>
> **Dev:** "Is internal support tooling part of the main product surface?"
> **Domain expert:** "No, **Internal Admin** is minimal and exists only to operate and support pilots."
>
> **Dev:** "Can an ops assistant change the payout account?"
> **Domain expert:** "No, an **Operator** manages trip operations but payout setup belongs to an **Owner**."
>
> **Dev:** "Can an operator publish a trip page or open public booking?"
> **Domain expert:** "No, only an **Owner** can publish a **Public Trip Page** or open bookings."
>
> **Dev:** "Can an operator close bookings when operational capacity changes?"
> **Domain expert:** "Yes, an **Operator** can close bookings."
>
> **Dev:** "Can an operator confirm a booking after checking readiness?"
> **Domain expert:** "Yes, booking confirmation is part of **Operator** trip operations."
>
> **Dev:** "Can an operator increase trip capacity to sell more seats?"
> **Domain expert:** "No, **Trip Capacity** changes require an **Owner** in the MVP."
>
> **Dev:** "Can an operator change package price after bookings exist?"
> **Domain expert:** "No, post-booking package commercial term changes require an **Owner**."
>
> **Dev:** "Can one user manage trips for two separate organizer brands?"
> **Domain expert:** "Yes, the user has a separate **Organizer Membership** for each **Organizer**."
>
> **Dev:** "Can a trekking community have two co-founder owners?"
> **Domain expert:** "Yes, an **Organizer** can have multiple **Owner** memberships."
>
> **Dev:** "Can the last owner leave or downgrade themselves?"
> **Domain expert:** "No, an **Organizer** must always have at least one **Owner** membership."
>
> **Dev:** "Can an operator approve a submitted manual payment?"
> **Domain expert:** "Yes, manual payment approval is part of **Operator** trip operations."
>
> **Dev:** "Can two trips from the same organizer settle to different payout accounts?"
> **Domain expert:** "No, the MVP has one **Payout Account** per **Organizer**."
>
> **Dev:** "Does an owner copy OAuth tokens into TripOS?"
> **Domain expert:** "No, **OAuth Provider Authorization** happens through the provider-hosted approval flow; **API Key Provider Authorization** is only a pilot fallback."
>
> **Dev:** "Can test-mode provider setup open public booking?"
> **Domain expert:** "No, **Online Payment Readiness** requires **Live Provider Mode**."
>
> **Dev:** "Can the TripOS public trip page be used as the provider website URL?"
> **Domain expert:** "Yes, the **Public Trip URL** can be the **Provider Verification URL**."
>
> **Dev:** "What if provider verification is blocked or delayed?"
> **Domain expert:** "The **Organizer** can operate as **Manual Payments Only** while public provider booking remains closed."
>
> **Dev:** "Does the MVP show detailed settlement reports?"
> **Domain expert:** "No, the MVP only shows minimal **Payout Status**."
>
> **Dev:** "Is TripOS first designed for large travel agencies or casual friend trips?"
> **Domain expert:** "No, the MVP beachhead is repeat **Community-Led Organizers** running paid group trips."
>
> **Dev:** "If the same trek runs in January and February, is that one **Trip** or two?"
> **Domain expert:** "For now, it is two **Trips**; once the product supports recurring scheduled runs, it becomes one **Trip** with separate **Departures**."
>
> **Dev:** "How does an organizer create the same trip for a new date before departures exist?"
> **Domain expert:** "They create a **Trip Duplicate** and update dates, capacity, and other setup."
>
> **Dev:** "If a published open trip is duplicated, is the duplicate immediately bookable?"
> **Domain expert:** "No, a **Trip Duplicate** starts with draft publication and closed booking availability."
>
> **Dev:** "Can a free meetup be managed as an MVP trip?"
> **Domain expert:** "No, MVP **Trips** are **Paid Trips**."
>
> **Dev:** "What link does the organizer share in an Instagram bio?"
> **Domain expert:** "The trip's **Public Trip Page**."
>
> **Dev:** "Does an organizer need to set up a custom domain to share a trip?"
> **Domain expert:** "No, the MVP uses a TripOS-hosted **Public Trip URL**."
>
> **Dev:** "Can a trip page be visible while bookings are closed?"
> **Domain expert:** "Yes, **Publication State** controls visibility and **Booking Availability** controls whether travelers can book."
>
> **Dev:** "Does public booking always require Razorpay readiness?"
> **Domain expert:** "No, public booking requires at least one ready payment method; provider payments require **Online Payment Readiness**, and QR-based manual payments require **Manual Payment Instructions** plus open **Manual Payment Availability**."
>
> **Dev:** "Is sold out the same as manually closed?"
> **Domain expert:** "No, **Sold Out Booking Availability** means capacity is unavailable; **Closed Booking Availability** means the organizer closed booking."
>
> **Dev:** "If a cancellation frees a seat, should someone manually unsold-out the trip?"
> **Domain expert:** "No, **Sold Out Booking Availability** is derived from **Available Seats**."
>
> **Dev:** "Can travelers book a trip whose page is still draft?"
> **Domain expert:** "No, public booking requires a published **Public Trip Page**, open **Booking Availability**, at least one ready payment method, and sufficient **Bookable Seats**."
>
> **Dev:** "Can an organizer publish the trip page before payment collection is configured?"
> **Domain expert:** "Yes, payment method readiness does not block **Public Trip Page** publication, but public booking stays disabled until at least one payment method is ready."
>
> **Dev:** "Can a public booking reserve seats with manual payment proof only?"
> **Domain expert:** "No, a public QR-based manual payment creates a **Draft Booking** and a **Submitted Manual Payment**; seats reserve only after approval."
>
> **Dev:** "If provider verification is incomplete, can travelers submit an unpaid booking request from the public trip page?"
> **Domain expert:** "No, **Public Booking** is fully closed until at least one payment method is ready; QR-based manual payments still require **Manual Payment Instructions** and open **Manual Payment Availability**."
>
> **Dev:** "What should a traveler see if the trip page is published but online booking is not ready?"
> **Domain expert:** "If QR-based manual payments are ready, they can submit Payment Proof; otherwise they see **Bookings Opening Soon**."
>
> **Dev:** "What happens if a provider connection becomes unhealthy after a trip page is published?"
> **Domain expert:** "The **Public Trip Page** stays published; provider checkout is hidden until **Online Payment Readiness** is restored, and **Public Booking** closes only if no other payment method is ready."
>
> **Dev:** "Is a past trip deleted from the product?"
> **Domain expert:** "No, it can become an **Archived Publication** and remain available for records."
>
> **Dev:** "If a parent books for two students, who are the **Travelers**?"
> **Domain expert:** "The students are the **Travelers**; the parent is the **Booking Contact** unless they are also attending."
>
> **Dev:** "Can a startup admin coordinate a booking without attending the trip?"
> **Domain expert:** "Yes, the admin can be the **Booking Contact** while employees are the **Travelers**."
>
> **Dev:** "Can payment start before TripOS has a reachable booking contact?"
> **Domain expert:** "No, **Booking Contact Details** are required before payment starts."
>
> **Dev:** "Can a booking contact reserve three seats before entering every traveler's full name?"
> **Domain expert:** "Yes, reservation payment requires **Traveler Slot** count and package selection; full traveler names can be required before confirmation."
>
> **Dev:** "What does public booking collect before payment?"
> **Domain expert:** "It collects **Booking Contact Details**, traveler count, package selection, and pricing inputs; full **Traveler Identity Details** can be collected after reservation through the **Traveler Portal**."
>
> **Dev:** "What is created when someone reserves three unnamed seats?"
> **Domain expert:** "The booking contains three **Traveler Slots** until identity details are complete."
>
> **Dev:** "Does a traveler need every document before they count as a traveler?"
> **Domain expert:** "No, a **Traveler Slot** becomes a **Traveler** when **Traveler Identity Details** are complete; other readiness items come from **Confirmation Requirements**."
>
> **Dev:** "Can two child travelers use the parent's phone number?"
> **Domain expert:** "Yes, traveler phone numbers in **Traveler Identity Details** need not be unique."
>
> **Dev:** "Does a traveler create a user account to upload documents?"
> **Domain expert:** "No, they use a **Booking Access Link**."
>
> **Dev:** "Does public booking require traveler login?"
> **Domain expert:** "No, MVP **Public Booking** is **No-Login Public Booking** and uses **Booking Access Links** after reservation."
>
> **Dev:** "Where does a traveler upload documents?"
> **Domain expert:** "In the **Traveler Portal**, accessed through a **Booking Access Link**."
>
> **Dev:** "Who gets the booking access link after reservation payment?"
> **Domain expert:** "The **Booking-Level Access Link** is sent to the **Booking Contact** by default; **Traveler-Level Access Links** can be generated later for individual readiness."
>
> **Dev:** "Can one traveler with a link submit documents for everyone?"
> **Domain expert:** "No, a **Traveler-Level Access Link** is scoped to one traveler; the **Booking-Level Access Link** belongs to the booking contact."
>
> **Dev:** "If the booking contact changes, does the old contact keep the booking-level link?"
> **Domain expert:** "No, booking contact changes revoke prior **Booking-Level Access Links**."
>
> **Dev:** "Are booking access links permanent?"
> **Domain expert:** "No, they have an **Access Link Expiry** and can be regenerated."
>
> **Dev:** "Can a booking contact remove a traveler after seats are reserved?"
> **Domain expert:** "No, traveler changes after reservation are organizer-controlled."
>
> **Dev:** "Does a successful provider checkout callback reserve seats?"
> **Domain expert:** "No, it can place the booking in **Payment Confirming Booking** state, but seats reserve only after backend-confirmed **Provider Payment**."
>
> **Dev:** "Does public booking create a booking before payment succeeds?"
> **Domain expert:** "Yes, it creates a **Draft Booking** before provider payment succeeds, then moves to **Payment Confirming Booking** when checkout begins."
>
> **Dev:** "Does a draft booking hold seats while the traveler is filling details?"
> **Domain expert:** "No, **Draft Bookings** do not create **Seat Holds**; **Seat Holds** begin only when a reservation **Payment Attempt** begins before seats are reserved."
>
> **Dev:** "Can a payment-confirming booking temporarily hold seats?"
> **Domain expert:** "Yes, it may create short **Seat Holds**. If confirmation succeeds, the booking reserves seats; if confirmation fails or the hold expires, the seats are released."
>
> **Dev:** "Does an abandoned provider checkout send a special payment reminder?"
> **Domain expert:** "No, expired **Seat Holds** release capacity without a payment-abandonment reminder in the MVP; normal **Draft Booking** recovery can still apply."
>
> **Dev:** "If provider payment confirms after the seat hold expired, should TripOS auto-reserve?"
> **Domain expert:** "Yes, if **Bookable Seats** are still sufficient and the payment details match the expected payment attempt. Otherwise TripOS records a **Late Confirmed Payment Exception** or **Mismatched Provider Payment Exception**."
>
> **Dev:** "Can duplicate provider confirmations create duplicate payments?"
> **Domain expert:** "No, a **Provider Payment Confirmation** is matched to an expected **Payment Attempt**, and duplicate confirmations do not create duplicate **Provider Payments**."
>
> **Dev:** "Who can resolve a late confirmed payment exception?"
> **Domain expert:** "An **Owner** or **Operator** can resolve the booking operation side, but creating a **Refund Record** requires an **Owner** in the MVP."
>
> **Dev:** "Can a booking contact switch from triple-sharing to double-sharing after reservation?"
> **Domain expert:** "No, package changes after reservation are organizer-controlled."
>
> **Dev:** "Does every package switch affect the financial ledger?"
> **Domain expert:** "No, only package changes that change the **Booking Total** create or explain a **Ledger Entry**."
>
> **Dev:** "Can a booking contact transfer responsibility after seats are reserved?"
> **Domain expert:** "Yes, but booking contact changes after reservation are organizer-controlled."
>
> **Dev:** "If four friends reserve together, is that four **Bookings**?"
> **Domain expert:** "No, it is one **Booking** containing four **Traveler Slots**."
>
> **Dev:** "Can an operator create a booking from an Instagram DM?"
> **Domain expert:** "Yes, that is a **Manual Booking**, and it follows the same reservation rules."
>
> **Dev:** "Can a dashboard-created booking reserve seats after a verified direct transfer?"
> **Domain expert:** "Yes, a **Manual Booking** can reserve through approved **Manual Payments**."
>
> **Dev:** "Can an organizer create manual bookings while Razorpay setup is still pending?"
> **Domain expert:** "Yes, **Manual Bookings** do not require **Provider Payment Setup**."
>
> **Dev:** "Can an organizer bring an existing Excel participant list into a trip?"
> **Domain expert:** "Yes, through a narrowly scoped **Booking Import**."
>
> **Dev:** "Does an imported paid row become confirmed automatically?"
> **Domain expert:** "No, **Booking Import** creates reserved bookings when opening payment records meet the **Booking Reservation Amount**, but not confirmed bookings by default."
>
> **Dev:** "If an import has more paid travelers than trip capacity, does TripOS silently overbook?"
> **Domain expert:** "No, **Booking Import** cannot exceed **Trip Capacity** by default."
>
> **Dev:** "When does a **Booking** consume trip seats?"
> **Domain expert:** "Only after the **Reservation Amount** is paid."
>
> **Dev:** "If a reserved booking is later cancelled and awaiting refund, is that one status?"
> **Domain expert:** "No, the **Booking State** tracks the cancellation while the **Payment State** tracks the refund."
>
> **Dev:** "If a discount adjustment makes the collected amount cover the new total, who changes the payment state?"
> **Domain expert:** "The **Payment State** follows from the **Financial Ledger**."
>
> **Dev:** "What does payment reconciliation mean in the MVP?"
> **Domain expert:** "It means **Booking Reconciliation**, not bank or settlement reconciliation."
>
> **Dev:** "Can a completed trip still show unpaid balances or refund dues?"
> **Domain expert:** "Yes, as **Reconciliation Flags**."
>
> **Dev:** "Why did this booking's balance change after cancellation?"
> **Domain expert:** "The **Ledger Entries** explain the booking balance."
>
> **Dev:** "Where do document approvals and traveler replacements appear?"
> **Domain expert:** "They appear in the **Activity Log**, not the **Financial Ledger**."
>
> **Dev:** "If the **Reservation Amount** is paid but the ID document is missing, is the booking confirmed?"
> **Domain expert:** "No, it is a **Reserved Booking** until the organizer accepts it as a **Confirmed Booking**."
>
> **Dev:** "What does the traveler receive after paying enough to hold seats?"
> **Domain expert:** "They receive a **Reservation Acknowledgement**, not a **Confirmation Notice**."
>
> **Dev:** "After successful reservation payment, should TripOS send both payment and reservation messages?"
> **Domain expert:** "No, it sends one **Reservation Acknowledgement** with payment details, balance due, and the **Booking-Level Access Link** when applicable."
>
> **Dev:** "Who gets reservation and confirmation messages?"
> **Domain expert:** "The **Booking Contact** by default, and **Active Travelers** once **Traveler Identity Details** exist."
>
> **Dev:** "Can a booking become confirmed while required **Traveler Documents** are missing?"
> **Domain expert:** "No, missing required documents keep it from being a **Confirmed Booking**."
>
> **Dev:** "If all requirements are satisfied, does the booking auto-confirm?"
> **Domain expert:** "No, a **Booking** becomes a **Confirmed Booking** only through organizer action."
>
> **Dev:** "Does a booking need to be fully paid before confirmation?"
> **Domain expert:** "Only if the trip's **Confirmation Requirements** include that payment expectation."
>
> **Dev:** "If a confirmed booking needs another document review, is it cancelled?"
> **Domain expert:** "No, use **Unconfirm Booking** to move it back to reserved."
>
> **Dev:** "Does unconfirming a booking automatically warn travelers?"
> **Domain expert:** "No, **Unconfirm Booking** does not send a notification automatically in the MVP."
>
> **Dev:** "Does a booking become completed automatically after trip end?"
> **Domain expert:** "No, a **Booking** becomes a **Completed Booking** only through organizer action in the MVP."
>
> **Dev:** "What happens when an organizer marks a trip completed?"
> **Domain expert:** "A **Completed Trip** completes active reserved or confirmed bookings while leaving draft and cancelled bookings as they are."
>
> **Dev:** "Why is this booking not confirmed even though seats are reserved?"
> **Domain expert:** "It has not satisfied the trip's **Confirmation Requirements** yet."
>
> **Dev:** "Can emergency contact be required before confirmation?"
> **Domain expert:** "Yes, **Confirmation Requirements** may include a required **Emergency Contact**."
>
> **Dev:** "Does every trip require medical information?"
> **Domain expert:** "No, **Medical Disclosure** is collected only when included in the trip's **Confirmation Requirements**."
>
> **Dev:** "Should medical disclosures appear in every vendor export?"
> **Domain expert:** "No, **Sensitive Traveler Information** appears in **Operational Exports** only when explicitly selected."
>
> **Dev:** "Do all trips from an organizer require the same documents?"
> **Domain expert:** "No, **Confirmation Requirements** are defined per **Trip** in the MVP."
>
> **Dev:** "If a trip requires full payment at booking time, does it still have a payment schedule?"
> **Domain expert:** "Yes, full payment now is a one-step **Payment Schedule**."
>
> **Dev:** "Can organizers create arbitrary installment plans in the MVP?"
> **Domain expert:** "No, the MVP supports a **Reservation Milestone** and an optional **Balance Milestone**."
>
> **Dev:** "Does a full-pay-now trip need a balance milestone?"
> **Domain expert:** "No, it only has a **Reservation Milestone** when the **Booking Reservation Amount** equals the **Booking Total**."
>
> **Dev:** "If a trip is duplicated from June to July, should the balance due date be manually changed?"
> **Domain expert:** "No, the **Balance Milestone** is due relative to the **Trip Start Date**."
>
> **Dev:** "Does changing the itinerary reprice existing bookings?"
> **Domain expert:** "No, **Itinerary** changes are operational updates, not financial changes."
>
> **Dev:** "Can an itinerary change be saved without sending an announcement?"
> **Domain expert:** "Yes, the MVP can prompt an **Announcement** but does not require one."
>
> **Dev:** "If trip dates change after bookings exist, is that just an itinerary edit?"
> **Domain expert:** "No, that is a **Trip Date Change** and it produces a **Date Change Notice** by default."
>
> **Dev:** "Can an operator change trip dates after bookings exist?"
> **Domain expert:** "No, a post-booking **Trip Date Change** requires an **Owner** in the MVP."
>
> **Dev:** "Does cancelling an entire trip automatically calculate refunds?"
> **Domain expert:** "No, **Trip Cancellation** is operational; **Booking Adjustments** and **Refund Records** handle financial consequences."
>
> **Dev:** "If someone books after the balance due date has passed, can they pay only the reservation amount?"
> **Domain expert:** "No, they must pay the full **Booking Total** to reserve seats."
>
> **Dev:** "Does the organizer manually edit available seats after a cancellation?"
> **Domain expert:** "No, **Available Seats** are determined from **Trip Capacity** minus active reserved travelers."
>
> **Dev:** "Does the public page show exactly three seats left?"
> **Domain expert:** "No, the **Public Trip Page** shows an **Availability Band** like Available, Few seats left, or Sold out."
>
> **Dev:** "Can a booking contact pay the reservation amount when there are not enough available seats?"
> **Domain expert:** "No, reservation payment is blocked unless the trip has enough **Bookable Seats**."
>
> **Dev:** "Can an organizer overbook one extra traveler as a special case?"
> **Domain expert:** "No, they must increase **Trip Capacity** before reserving another traveler."
>
> **Dev:** "Are trip pickup updates sent as chat messages?"
> **Domain expert:** "No, pickup updates are **Announcements**; the MVP does not include chat."
>
> **Dev:** "Does TripOS own the WhatsApp group conversation?"
> **Domain expert:** "No, TripOS uses the **WhatsApp Channel** for structured notifications but does not own or mirror WhatsApp group chat."
>
> **Dev:** "Does a traveler see notifications as coming from the organizer or TripOS?"
> **Domain expert:** "Notification content can use **Organizer Profile** facts, while delivery can be TripOS-managed."
>
> **Dev:** "Who receives a balance payment reminder?"
> **Domain expert:** "The **Booking Contact** receives **Reminders** by default."
>
> **Dev:** "Who receives a pickup time update?"
> **Domain expert:** "The **Announcement** goes to the **Booking Contact** and the **Active Travelers**."
>
> **Dev:** "Does a cancelled traveler receive operational announcements?"
> **Domain expert:** "No, only **Active Travelers** receive them."
>
> **Dev:** "If one confirmed traveler does not arrive, is the booking cancelled?"
> **Domain expert:** "No, that traveler is a **No-Show Traveler**."
>
> **Dev:** "Does marking a traveler no-show automatically refund or charge them?"
> **Domain expert:** "No, **No-Show Traveler** is operational attendance data with no automatic financial effect."
>
> **Dev:** "Can a trek leader mark who has reached the pickup point?"
> **Domain expert:** "Yes, through lean **Traveler Check-In**."
>
> **Dev:** "Can non-user field staff check travelers in through a special link?"
> **Domain expert:** "No, **Traveler Check-In** is performed by an **Owner** or **Operator** in the MVP."
>
> **Dev:** "Does a reserved booking receive a pickup-location announcement before it is confirmed?"
> **Domain expert:** "Yes, **Announcements** go to reserved and confirmed bookings, but not draft or cancelled bookings."
>
> **Dev:** "Does uploading a blurry ID satisfy the requirement?"
> **Domain expert:** "No, the **Traveler Document** remains unaccepted until it becomes an **Approved Document**."
>
> **Dev:** "If the **Reservation Amount** is paid but the full amount is still pending, is the booking fully paid?"
> **Domain expert:** "No, it is a **Reservation Paid Booking** until more money is collected."
>
> **Dev:** "If one friend pays for four travelers, where is the payment recorded?"
> **Domain expert:** "The **Payment** belongs to the shared **Booking**, not to each **Traveler**."
>
> **Dev:** "Does a Razorpay payment need organizer approval?"
> **Domain expert:** "No, a **Provider Payment** affects collected balance after provider confirmation."
>
> **Dev:** "Does a failed checkout attempt change the financial ledger?"
> **Domain expert:** "No, failed **Payment Attempts** do not create **Ledger Entries**."
>
> **Dev:** "Does a pending UPI collect reserve a seat?"
> **Domain expert:** "No, only confirmed **Provider Payments** affect collected balance and seat reservation."
>
> **Dev:** "Can provider payments collect balance after reservation?"
> **Domain expert:** "Yes, the initial **Provider Payment** reserves seats when it meets the **Booking Reservation Amount**, and later **Provider Payments** can collect balance due."
>
> **Dev:** "Where does a booking contact pay a later balance?"
> **Domain expert:** "Through a booking-scoped **Balance Payment Link** in the **Traveler Portal** or **Booking Access Link**, not through the **Public Trip Page**."
>
> **Dev:** "Who can send a balance payment link?"
> **Domain expert:** "**Owners** and **Operators** can manually send **Balance Payment Links**, and **Balance Due Reminders** can include them automatically."
>
> **Dev:** "Can a balance payment link collect an arbitrary amount?"
> **Domain expert:** "No, MVP **Balance Payment Links** collect the current balance due, not arbitrary custom amounts."
>
> **Dev:** "Does a later balance payment create a seat hold?"
> **Domain expert:** "No, seats are already reserved; later balance **Provider Payments** affect collected and due state, not capacity."
>
> **Dev:** "What happens if the provider reports a dispute or chargeback?"
> **Domain expert:** "TripOS creates a **Provider Dispute Exception** for organizer review; it does not automatically create a **Refund Record** or change **Booking State** in the MVP."
>
> **Dev:** "Does booking collected balance use the amount after Razorpay fees?"
> **Domain expert:** "No, booking collected balance uses the **Gross Provider Payment Amount**; **Provider Fee Amount** is provider reconciliation detail."
>
> **Dev:** "Should Trip-level Payments show provider fees and net settlement?"
> **Domain expert:** "Yes, read-only where available, but **Provider Fee Amount** and **Provider Net Settlement Amount** do not determine booking collected balance."
>
> **Dev:** "Does TripOS charge its platform fee on a direct UPI payment recorded manually?"
> **Domain expert:** "No, the **Platform Fee** is charged on successful **Provider Payments**."
>
> **Dev:** "Do Manual Payments produce platform fees in the MVP?"
> **Domain expert:** "No, MVP **Manual Payments** are operational fallback and migration support; they do not produce **Platform Fees**."
>
> **Dev:** "Is the platform fee charged only on reservation payments?"
> **Domain expert:** "No, each successful **Provider Payment** amount is the **Platform Fee Basis**, including reservation and later balance payments."
>
> **Dev:** "Does TripOS deduct its platform fee from the traveler payment in the MVP?"
> **Domain expert:** "No, MVP **Platform Fees** are recorded on successful **Provider Payments** and collected later from the **Organizer**."
>
> **Dev:** "How often does TripOS collect recorded platform fees in the MVP?"
> **Domain expert:** "Monthly, using **Platform Fee Statements** and a pilot-friendly manual collection process."
>
> **Dev:** "Where do organizers see platform fees?"
> **Domain expert:** "Trip-level Payments can show fees attributable to the Trip for reconciliation; **Internal Admin** manages the staff workflow for **Platform Fee Statements** in the MVP."
>
> **Dev:** "Does a traveler see an extra platform fee at checkout?"
> **Domain expert:** "No, the **Platform Fee** is absorbed by the **Organizer** in the MVP."
>
> **Dev:** "Can an organizer record a direct UPI transfer that did not come through the payment provider?"
> **Domain expert:** "Yes, that is a **Manual Payment**."
>
> **Dev:** "Is direct UPI to the organizer shown as a public checkout option?"
> **Domain expert:** "No, **Direct UPI Payment** belongs inside the manual payment workflow."
>
> **Dev:** "If the traveler sees Scan QR code to pay, is that a provider checkout?"
> **Domain expert:** "No, the **Payment QR** helps the traveler make a **Direct UPI Payment** and submit **Payment Proof** for review."
>
> **Dev:** "Does a traveler-submitted payment screenshot reserve seats immediately?"
> **Domain expert:** "No, a **Manual Payment** affects collected balance only after approval."
>
> **Dev:** "Can a traveler upload a screenshot instead of sending it on WhatsApp?"
> **Domain expert:** "Yes, the traveler can submit **Payment Proof** for a **Manual Payment**."
>
> **Dev:** "Should payment screenshots appear in default exports?"
> **Domain expert:** "No, **Payment Proof** is **Sensitive Payment Information**."
>
> **Dev:** "Does TripOS only save links to documents and screenshots?"
> **Domain expert:** "No, **Traveler Documents** and **Payment Proof** are stored in TripOS in the MVP."
>
> **Dev:** "Can an operator download ID documents for permits?"
> **Domain expert:** "Yes, and downloading **Sensitive Traveler Information** records an **Activity Log** action."
>
> **Dev:** "Does downloading payment proof leave a trace?"
> **Domain expert:** "Yes, downloading **Sensitive Payment Information** records an **Activity Log** action."
>
> **Dev:** "Can an operator record cash received without a screenshot?"
> **Domain expert:** "Yes, **Payment Proof** is optional for organizer-entered **Manual Payments** but required for traveler-submitted ones."
>
> **Dev:** "Does organizer-entered cash wait for approval?"
> **Domain expert:** "No, organizer-entered **Manual Payments** are **Approved Manual Payments** by default."
>
> **Dev:** "Does TripOS issue a GST receipt when payment is recorded?"
> **Domain expert:** "No, it can send a **Payment Acknowledgement**."
>
> **Dev:** "Does approving a traveler-submitted screenshot notify the booking contact?"
> **Domain expert:** "Yes, approved traveler-submitted **Manual Payments** produce **Payment Acknowledgements** by default."
>
> **Dev:** "Do all travelers receive payment acknowledgements?"
> **Domain expert:** "No, **Payment Acknowledgements** go to the **Booking Contact** by default."
>
> **Dev:** "Does TripOS issue Razorpay refunds in the MVP?"
> **Domain expert:** "No, the MVP records refund reality with a **Refund Record**."
>
> **Dev:** "Can an operator record a refund without explaining why?"
> **Domain expert:** "No, creating a **Refund Record** requires an **Owner** in the MVP, and every **Refund Record** needs a **Refund Reason**."
>
> **Dev:** "Can an operator record that a manual refund was sent?"
> **Domain expert:** "No, creating a **Refund Record** requires an **Owner** in the MVP."
>
> **Dev:** "Does recording a refund automatically notify the booking contact?"
> **Domain expert:** "No, a **Refund Record** may produce a **Refund Acknowledgement** at user choice."
>
> **Dev:** "Do all travelers receive refund acknowledgements?"
> **Domain expert:** "No, **Refund Acknowledgements** go to the **Booking Contact** by default."
>
> **Dev:** "If an imported spreadsheet only says someone has paid so far, is that a manual payment?"
> **Domain expert:** "No, it becomes an **Opening Payment Record**."
>
> **Dev:** "If two travelers in one booking choose different room-sharing options, how is the amount calculated?"
> **Domain expert:** "The **Booking Total** is based on each traveler's selected **Package**, plus any **Booking Adjustments**."
>
> **Dev:** "If the package price changes after a traveler books, does the existing booking total change?"
> **Domain expert:** "No, the traveler keeps the **Booked Package Price** captured when the package was selected."
>
> **Dev:** "If reservation amount changes before a draft booking pays, which amount is due?"
> **Domain expert:** "Draft bookings follow current terms; reserved travelers keep their **Booked Reservation Amount**."
>
> **Dev:** "Does TripOS assign hotel rooms in the MVP?"
> **Domain expert:** "No, it captures **Rooming Notes** but does not manage room assignments or room inventory."
>
> **Dev:** "Is sending a trek leader the participant sheet an analytics report?"
> **Domain expert:** "No, that is an **Operational Export**."
>
> **Dev:** "Is repeat traveler cohort analysis part of the MVP?"
> **Domain expert:** "No, MVP dashboards use **Operational Metrics** only."
>
> **Dev:** "Does the MVP need polished PDF manifests?"
> **Domain expert:** "No, **Operational Exports** are CSV-first."
>
> **Dev:** "Should abandoned checkout attempts appear in the trek leader export?"
> **Domain expert:** "No, **Operational Exports** exclude **Draft Bookings** by default."
>
> **Dev:** "Can the export show who checked in or no-showed?"
> **Domain expert:** "Yes, **Operational Exports** can include traveler check-in and no-show status."
>
> **Dev:** "Does a one-price trip skip packages?"
> **Domain expert:** "No, it still has one default **Package**."
>
> **Dev:** "Can premium and standard packages require different upfront amounts?"
> **Domain expert:** "Yes, each **Package** defines its own **Reservation Amount**."
>
> **Dev:** "If a booking has travelers on different packages, what amount reserves the booking?"
> **Domain expert:** "The **Booking Reservation Amount** is the sum of the **Reservation Amounts** for each selected package."
>
> **Dev:** "If half the **Booking Reservation Amount** is paid for a four-traveler booking, are two seats reserved?"
> **Domain expert:** "No, the **Booking** reserves all seats together only after the full **Booking Reservation Amount** is paid."
>
> **Dev:** "Should abandoned checkout attempts appear in participant exports?"
> **Domain expert:** "No, **Draft Bookings** are excluded from core operational counts by default."
>
> **Dev:** "Does draft expiry release seats?"
> **Domain expert:** "No, **Draft Expiry** is for cleanup and recovery because drafts do not hold seats."
>
> **Dev:** "How long before an unpaid draft is considered abandoned?"
> **Domain expert:** "The MVP default **Draft Expiry** is 24 hours."
>
> **Dev:** "Does TripOS send repeated abandoned checkout campaigns?"
> **Domain expert:** "No, a **Draft Booking** may receive one **Reminder** before **Draft Expiry**."
>
> **Dev:** "Is the MVP a configurable reminder automation builder?"
> **Domain expert:** "No, it supports narrow **Automatic Reminders** and context-driven **Manual Reminders**."
>
> **Dev:** "Can organizers schedule announcement campaigns?"
> **Domain expert:** "No, MVP **Announcements** are sent by an **Owner** or **Operator** without announcement scheduling."
>
> **Dev:** "Which automatic reminders exist in the MVP?"
> **Domain expert:** "**Draft Recovery Reminder**, **Balance Due Reminder**, **Overdue Balance Reminder**, and **Missing Requirements Reminder**."
>
> **Dev:** "Can organizers build arbitrary reminder schedules?"
> **Domain expert:** "No, **Automatic Reminder Timing** uses simple defaults, with at most a trip-level **Balance Reminder Lead Time**."
>
> **Dev:** "If a booking reserves one day before trip start with missing requirements, does it miss the requirements reminder?"
> **Domain expert:** "No, a late reserved booking with unmet **Confirmation Requirements** receives a **Missing Requirements Reminder** soon after reservation."
>
> **Dev:** "Does TripOS automatically nag completed bookings with unpaid balances?"
> **Domain expert:** "No, but an organizer can send a **Reminder** for a **Completed Booking** with due balance."
>
> **Dev:** "Does a cancelled booking keep receiving document reminders?"
> **Domain expert:** "No, **Cancelled Bookings** do not receive payment or document **Reminders**."
>
> **Dev:** "If one person drops out of a four-person booking, is the whole booking cancelled?"
> **Domain expert:** "No, that is a **Traveler Cancellation**; a **Booking Cancellation** cancels the whole booking."
>
> **Dev:** "Can a traveler cancel themselves from the traveler portal?"
> **Domain expert:** "No, **Traveler Cancellation** is organizer-controlled in the MVP."
>
> **Dev:** "Can a booking contact cancel the entire booking from the traveler portal?"
> **Domain expert:** "No, **Booking Cancellation** is organizer-controlled in the MVP."
>
> **Dev:** "Can a cancellation be recorded without explaining why?"
> **Domain expert:** "No, cancellations require a **Cancellation Reason**."
>
> **Dev:** "Does cancellation itself change the financial ledger?"
> **Domain expert:** "No, cancellation is operational; **Booking Adjustments** and **Refund Records** handle financial consequences."
>
> **Dev:** "Where does a cancellation or replacement appear historically?"
> **Domain expert:** "Operational state changes record **Activity Log** actions."
>
> **Dev:** "Does TripOS calculate the exact refund for a cancelled traveler?"
> **Domain expert:** "No, the organizer records the **Traveler Cancellation** and uses a **Booking Adjustment** for the commercial consequence."
>
> **Dev:** "If a cancelled traveler is swapped for another person, does available capacity increase?"
> **Domain expert:** "No, that is a **Traveler Replacement**; otherwise a **Traveler Cancellation** releases the seat."
>
> **Dev:** "Does replacing a traveler reprice the booking?"
> **Domain expert:** "No, the **Traveler Replacement** inherits the replaced traveler's package and commercial position; any fee is a **Booking Adjustment**."
>
> **Dev:** "Can an operator change the booking total without explanation?"
> **Domain expert:** "No, every **Booking Adjustment** needs an **Adjustment Reason**."
>
> **Dev:** "Can an operator apply a name-change fee?"
> **Domain expert:** "Yes, through a **Booking Adjustment** with an **Adjustment Reason**, **Ledger Entry**, and **Activity Log** action."
>
> **Dev:** "What happens if an adjustment reduces the booking total below the collected amount?"
> **Domain expert:** "The booking becomes a **Refund Due Booking** until a **Refund Record** resolves it."
>
> **Dev:** "If a third friend wants to join an existing two-person booking, is that a replacement?"
> **Domain expert:** "No, that is a **Traveler Addition**, and it requires enough **Available Seats**."
>
> **Dev:** "Does adding a traveler to an existing booking reserve the extra seat immediately?"
> **Domain expert:** "No, a **Traveler Addition** reserves the added traveler's seat only after the added traveler's package reservation amount is collected."
>
> **Dev:** "Does a staged traveler addition hold capacity while waiting for payment?"
> **Domain expert:** "No, unpaid **Traveler Additions** do not hold seats in the MVP."
>
> **Dev:** "If three travelers upload ID and one does not, where is that missing item shown?"
> **Domain expert:** "On the specific **Traveler**, because identity and eligibility documents are **Traveler Documents**."
>
> **Dev:** "Do government ID files appear in default exports?"
> **Domain expert:** "No, identity **Traveler Documents** are **Sensitive Traveler Information**."
>
> **Dev:** "Can a traveler delete booking records directly?"
> **Domain expert:** "No, **Traveler Data Requests** are organizer-mediated in the MVP."
>
> **Dev:** "Does TripOS assign buses or vehicles in the MVP?"
> **Domain expert:** "No, it captures lightweight **Travel Logistics** for travelers."
>
> **Dev:** "Can a trip collect T-shirt size for included gear?"
> **Domain expert:** "Yes, if it is operationally required, as **Travel Logistics**, not arbitrary custom fields."

## Flagged ambiguities

- "organizer" was used to mean both the operating entity and the person using the product — resolved: **Organizer** is the operating entity, **User** is the login identity.
- "trip overview" could mean either the workspace summary or editable traveler-facing details — resolved: **Trip Overview** is the workspace summary, while **Trip Profile** is the editable trip-facing record.
- "trip overview text" could overload the workspace summary — resolved: use **Trip Description** for the rich traveler-facing narrative.
- "rich text" could become arbitrary page building — resolved: use constrained **Trip Rich Text** for trip profile content.
- "trip media" could mean documents, chat content, or a social feed — resolved: **Trip Media Gallery** contains ordered **Trip Media Items** for the trip profile.
- "media" could imply video storage or embeds — resolved: MVP **Trip Media Items** are images only.
- "media URLs" could make public pages depend on external hotlinks — resolved: MVP **Trip Media Items** are uploaded and stored by TripOS.
- "private media" could become an operational archive — resolved: private **Trip Media Items** stay visible only in **Trip Profile** in the MVP.
- "profile audit" could log every draft edit — resolved: only meaningful **Trip Profile** section saves record **Activity Log** actions.
- "operator profile edits" could include package, payment schedule, or launch-risk changes — resolved: **Operators** can manage non-commercial **Trip Profile** content except **Packages** and **Payment Schedule**.
- "admin" could mean either organizer-facing operations or TripOS staff support — resolved: use **Operations Dashboard** for organizer-facing work and **Internal Admin** only for minimal TripOS staff support in the MVP.
- "global settings" was too broad — resolved: **Organizer Settings** is only a UI grouping for organizer-level setup links and preferences, not a backend domain owner.
- "organizer public profile" could mix private setup and public discovery content — resolved: use **Organizer Profile** for public profile content and module-owned organizer setup for private configuration.
- "organizer profile" could mean private organizer setup or public discovery content — resolved: use **Organizer Profile** for public discovery content.
- "policies" could be mistaken for organizer profile identity fields — resolved: **Organizer Policies** is its own organizer submodule, required for publishing **Organizer Profile**.
- "organizer media" could be buried inside profile content — resolved: **Organizer Media** is its own organizer submodule, while **Organizer Profile** only displays selected public media.
- "creative setup" could become a storage area for generated trip posters — resolved: **Creative Setup** owns organizer-level generation preferences only; generated creative assets are trip-scoped.
- "payment setup" could be hidden under generic settings — resolved: **Organizer Payments** is its own organizer submodule, with **Payment Setup** as a workflow inside it.
- "team access" could look like a generic settings preference — resolved: **Team Access** is its own organizer submodule; Settings may link to it in the UI but does not own it.
- "organizer settings" could become a backend junk drawer — resolved: keep **Organizer Settings** as a UI grouping only; real domain ownership belongs to Profile, Media, Policies, Team Access, Organizer Payments, Creative Setup, Trips, and Public Discovery.
- "organizer preferences" could become a replacement junk drawer — resolved: do not introduce **Organizer Preferences** in the first version; use **Creative Setup** as the concrete preference domain.
- "organizer trips" could make Trips look like a nested Organizer submodule — resolved: **Trips** are owned by **Organizer** but remain their own operational domain.
- "trips module" could become a large catch-all for every trip-scoped concern — resolved: **Trips** owns core profile/publication/availability, while **Trip Bookings**, **Trip Travelers**, **Trip Payments**, and **Trip Operations** remain separate trip-scoped domains.
- "trip operations" could become a broad owner of all trip state — resolved: **Trip Operations** owns communications, operational exports, activity log, and operational exception review, while source state stays in Trips, Trip Bookings, Trip Travelers, and Trip Payments.
- "public discovery" could become a second owner of organizer or trip pages — resolved: **Public Discovery Catalog** owns demand pages, SEO metadata, discovery routing, and listing rules, but composes published organizer and trip pages from their owning domains.
- "organizer public page" could become a second owner of organizer profile content — resolved: **Organizer Profile** owns page content and publication state, while **Public Discovery Catalog** owns route and listing composition.
- "public trip page route" could make discovery own checkout behavior — resolved: **Public Discovery Catalog** may own discovery routing/listing around public trip pages, while **Trips**, **Trip Bookings**, and **Trip Payments** own content, publication, booking gates, booking URLs, and checkout behavior.
- "internal admin" could become the real owner of staff-managed records — resolved: **Internal Admin** is a thin orchestration surface for module-owned actions, not a business state owner.
- "notification defaults" and "export defaults" made Organizer setup feel abstract before trip operations exist — resolved: they are not part of MVP organizer-level setup.
- "default requirements" and "templates" introduce inheritance across trips — resolved: they are future organizer-level preferences, not MVP **Organizer Settings**.
- "communication templates" imply reusable Organizer-level messaging assets — resolved: MVP communications stay trip-scoped as **Reminders** and **Announcements**.
- "setup checklist" could be confused with Trip launch — resolved: **Organizer Setup Checklist** is post-onboarding organizer readiness, while Trip launch remains per-trip.
- "control room" is too metaphorical for the product UI — resolved: use **Operations Dashboard** for the product surface, Home for the organizer landing page, and **Trip Overview** for a trip workspace landing page.
- "reports and analytics" would add a cross-trip reporting module too early — resolved: MVP uses Trip-scoped **Operational Exports** and lightweight Home metrics.
- "vendor management" would introduce a separate commitments and payables domain — resolved: MVP supports vendor and field-team handoffs through **Operational Exports**, not a Vendors module.
- "organizer identity" sounded like a separate product module and overlapped with **Organizer Profile** — resolved: retire Organizer Identity as a domain term.
- "white-label" would expand the SaaS surface too early — resolved: MVP supports **Organizer Profile** branding only.
- "logo URL" made organizer branding depend on external hotlinked images — resolved: use an optional uploaded **Organizer Logo**.
- "operator invites" could become part of the initial setup gate — resolved: adding Operators is a post-onboarding Organizer setup action, not a blocker for **Organizer Onboarding**.
- "add operator" could imply directly creating a user — resolved: Owners send an **Organizer Invitation** instead of directly creating another **User**.
- "users" was too broad for organizer-facing access management — resolved: use **Team Access** for memberships and invitations.
- "ICP" was broad across many travel sellers — resolved: the MVP beachhead is **Community-Led Organizers** running paid trips with 10-80 travelers.
- "creator payment setup" could force registered-business assumptions — resolved: use **Individual Creator Payment Path** guidance for individual or unregistered-business provider accounts.
- "admin" was too broad for organizer access — resolved: MVP uses **Owner** and **Operator** roles.
- "payment operator" would blur role boundaries — resolved: only **Owners** submit or edit **Payment Setup**; **Operators** only view readiness blockers.
- "refund operator" would blur financial control — resolved: creating a **Refund Record** requires an **Owner** in the MVP.
- "per-trip provider accounts" would make reconciliation and support too complex in the MVP — resolved: an **Organizer** has at most one **Connected Provider Account**.
- "disconnecting Razorpay" could unpublish public pages unexpectedly — resolved: unhealthy **Provider Connection State** disables provider checkout but does not unpublish **Public Trip Pages**.
- "oauth details" could imply organizers manually provide tokens — resolved: **OAuth Provider Authorization** uses provider-hosted approval; **API Key Provider Authorization** is only a pilot fallback.
- "assisted API key setup" could become the default payment path — resolved: **Assisted Payment Setup** is temporary, staff-assisted, and hidden from normal organizer-facing setup.
- "test payments" could accidentally open real public booking — resolved: **Online Payment Readiness** requires **Live Provider Mode**.
- "provider website" could force creators to own a separate website — resolved: the **Public Trip URL** can be the **Provider Verification URL**.
- "razorpay rejection" could block all operations — resolved: organizers can operate as **Manual Payments Only** while provider booking remains unavailable.
- "payout setup" could vary by trip or organizer — resolved: the MVP has one **Payout Account** per **Organizer**.
- "payout account form" could make organizers self-certify bank or settlement readiness — resolved: **Payment Setup** presents **Settlement Readiness** while **Payout Account** facts are provider-derived or support-confirmed.
- "payment setup" could mean provider payments or manual collection — resolved: **Payment Setup** owns provider setup and **Manual Payment Instructions**, while each **Trip** controls **Manual Payment Availability**.
- "KYC" is provider onboarding, not a TripOS domain workflow — resolved: MVP links to or embeds provider onboarding and tracks setup status.
- "KYC documents" could make TripOS a sensitive document store — resolved: MVP does not retain **Provider Verification Documents** after provider submission.
- "turnover checks" and "payer-payee transparency" are provider-specific eligibility language — resolved: treat them as **Provider Eligibility**, not MVP organizer-facing setup copy.
- "admin-assisted payment setup" could expose provider plumbing to organizers — resolved: use **Assisted Payment Setup** only as a support-assisted pilot path behind **Payment Setup**.
- "assisted payment setup" could look like a separate organizer mode — resolved: it uses normal **Payment Setup** statuses and is not shown as a distinct mode.
- "booking request" could create an unpaid public flow while payments are not ready — resolved: **Public Booking** requires at least one ready payment method; QR-based manual submissions create **Draft Bookings** with **Submitted Manual Payments**, not unpaid booking requests.
- "bookings opening soon" could become a waitlist or lead-capture flow — resolved: **Bookings Opening Soon** is display-only in the MVP.
- "Razorpay setup" made the provider the product concept — resolved: use **Payment Setup** as the workflow and **Provider Disclosure** only for trust and transparency.
- "verified" could be mistaken for ready to collect payments — resolved: **Verified Provider Verification** is one input to **Online Payment Readiness**.
- "provider payment setup" could be mistaken for the final booking gate — resolved: **Provider Payment Setup** gates provider payments, while **Public Booking** requires at least one ready payment method.
- "provider linked account" implied a marketplace/split-provider model — resolved: MVP uses a **Connected Provider Account** owned by the organizer.
- "platform payment operations" could imply TripOS custody or a platform-managed payment account in the MVP — resolved: MVP uses a **Connected Provider Account**, while the domain keeps **Payment Setup**, **Payout Account**, and **Provider Payment Setup** broad enough for a future platform-managed model.
- "trip" was used to mean both a reusable travel template and a scheduled run — resolved: **Trip** currently means one scheduled offering; **Departure** is reserved for future repeated runs.
- "first trip" could look like a special onboarding exception — resolved: creating any **Trip**, including the first one, is owner-only.
- "trip" could include free events or RSVPs — resolved: MVP **Trips** are **Paid Trips**.
- "marketplace" could imply TripOS-owned checkout, split settlement, reviews, and marketplace policies — resolved: use **Public Discovery Catalog** for SEO-friendly discovery of organizers and published trips while booking remains on **Public Trip Pages**.
- "organizer page" could mean organizer setup or operations — resolved: use **Organizer Public Page** for the public discovery page.
- "demand page" could imply a trip, waitlist, or booking request — resolved: a **Demand Page** is SEO-focused public discovery and does not create bookings by itself.
- "landing page" could mean a trip page, organizer page, or product marketing page — resolved: use **TripOS Marketing Site** for the public TripOS-owned product site.
- "microsite" implied a larger marketing surface — resolved: use **Public Trip Page** for the MVP.
- "custom domain" would add launch and support complexity — resolved: MVP uses TripOS-hosted **Public Trip URLs**.
- "trip status" could mix page visibility with booking ability — resolved: use **Publication State** and **Booking Availability** separately.
- "payment readiness" could block public page publication — resolved: payment method readiness gates **Public Booking**, not **Public Trip Page** publication.
- "launch readiness" could mix content review with payment and booking gates — resolved: use **Trip Profile Publication Readiness** for profile completeness before publication.
- "publishing" could become content versioning or live profile editing — resolved: **Publication State** controls visibility and creates a **Published Trip Profile Lock**.
- "unlocking a published trip" could become a normal edit path — resolved: MVP has no self-serve unlock for a **Published Trip Profile Lock**.
- "archiving" could become an unlock workaround — resolved: archiving a **Public Trip Page** does not remove the **Published Trip Profile Lock**.
- "trip date change" could be treated as a harmless itinerary edit — resolved: use **Trip Date Change** and send **Date Change Notice** by default after bookings exist.
- "trip cancellation" could be confused with archiving or booking cancellation — resolved: use **Trip Cancellation** for cancelling the whole trip.
- "recurring trip" would reintroduce departure-like complexity — resolved: automatic recurrence is excluded from the MVP.
- "traveler" was used to mean both the attendee and the person managing the purchase — resolved: **Traveler** attends the trip, while **Booking Contact** manages communication and payment coordination.
- "active traveler" needed a precise operational meaning — resolved: **Active Traveler** is a traveler inside a reserved or confirmed booking who has not been cancelled or replaced.
- "no-show" could be confused with cancellation or booking state — resolved: **No-Show Traveler** is an operational mark on a traveler.
- "traveler account" would add customer-side auth friction — resolved: travelers and booking contacts use **Booking Access Links** in the MVP.
- "traveler details before payment" would add checkout friction — resolved: public booking collects minimum pricing and contact details before payment; full **Traveler Identity Details** can follow reservation.
- "booking access link" could be confused with the customer-facing workspace — resolved: **Booking Access Link** grants access to the **Traveler Portal**.
- "booking access link" could become permanent access — resolved: **Booking Access Links** expire after the **Access Link Expiry** and can be regenerated.
- "booking contact access" could imply unrestricted post-reservation edits — resolved: booking contacts can edit traveler details before reservation; after reservation, traveler changes are organizer-controlled.
- "booking" was considered as either one reservation per traveler or one reservation containing travelers — resolved: a **Booking** can contain one or more **Traveler Slots**.
- "traveler with no name" was semantically awkward — resolved: use **Traveler Slot** until identity details are complete.
- "traveler identity" could be confused with readiness requirements — resolved: **Traveler Identity Details** identify the person, while **Confirmation Requirements** cover additional readiness data.
- "offline booking" could imply bypassing the model — resolved: use **Manual Booking**, which follows the same reservation rules as other bookings.
- "import" could become a generic ETL surface — resolved: MVP supports narrow **Booking Import** for existing trip onboarding.
- "payment-first booking" would make provider events hard to attach to traveler intent — resolved: public booking creates a **Draft Booking** before provider payment succeeds.
- "draft booking" could accidentally consume capacity — resolved: **Seat Holds** start only when checkout begins or a **Payment Attempt** is created.
- "balance payment hold" would mix capacity with debt collection — resolved: later balance **Provider Payments** do not create **Seat Holds**.
- "payment abandonment reminder" could add pressure and noise — resolved: expired **Seat Holds** do not produce a special reminder in the MVP.
- "deposit" was too imprecise for the amount that reserves seats — resolved: use **Reservation Amount**.
- "provider payment" could be treated as reservation-only — resolved: later **Provider Payments** can collect balance due after reservation.
- "status" was used for both operational and money lifecycle — resolved: use **Booking State** and **Payment State** separately.
- "payment state" could be treated as manually maintained truth — resolved: **Payment State** is determined from the **Financial Ledger**.
- "financial audit trail" needed a domain unit — resolved: use **Ledger Entry** for records that change or explain booking balance.
- "audit log" could mix financial and operational history — resolved: use **Financial Ledger** for money and **Activity Log** for operations.
- "confirmed" was ambiguous between paid enough to hold seats and ready to travel — resolved: **Reserved Booking** holds seats; **Confirmed Booking** is organizer-accepted.
- "temporary hold" could be mistaken for a reserved booking — resolved: use **Seat Hold** for short provider-confirmation capacity holds.
- "booking confirmation" could mean reservation or readiness — resolved: use **Reservation Acknowledgement** and **Confirmation Notice**.
- "reservation payment acknowledgement" could duplicate notifications — resolved: the first reservation payment sends one **Reservation Acknowledgement**, not a separate **Payment Acknowledgement**.
- "unconfirm" could be confused with cancellation — resolved: **Unconfirm Booking** moves a confirmed booking back to reserved without cancelling it.
- "payment status" used deposit-oriented language — resolved: use **Unpaid Booking**, **Reservation Paid Booking**, **Partially Paid Booking**, **Fully Paid Booking**, **Overdue Booking**, **Refund Due Booking**, and **Refunded Booking** as payment-state concepts.
- "payment" could have belonged to individual travelers or the booking — resolved: **Payment** belongs to **Booking**.
- "payment" overlapped with attempted payments — resolved: **Payment** is collected money; **Payment Attempt** covers failed or pending attempts.
- "online payment" was too imprecise — resolved: use **Provider Payment** for payments confirmed by an integrated payment provider.
- "net settlement amount" could make traveler bookings look underpaid — resolved: booking collected balance uses **Gross Provider Payment Amount**, not **Provider Fee Amount** netting.
- "provider reconciliation" could alter booking balance — resolved: **Provider Fee Amount** and **Provider Net Settlement Amount** are read-only reconciliation details where available.
- "failed payment" could pollute the financial ledger — resolved: failed **Payment Attempts** do not create **Ledger Entries**.
- "provider webhook" is integration plumbing, not domain language — resolved: domain terms remain **Payment Attempt** and **Provider Payment**.
- "checkout success" could be mistaken for collected money — resolved: frontend success can create **Payment Confirming Booking**, but only backend-confirmed **Provider Payment** reserves seats.
- "payment authorization" could be mistaken for collected money — resolved: only captured provider money can create a **Provider Payment**.
- "available seats" during payment confirmation could overstate what another traveler can book — resolved: use **Bookable Seats** when active **Seat Holds** are considered.
- "late payment confirmation" could silently overbook after a seat hold expires — resolved: use **Late Confirmed Payment Exception** when capacity is insufficient.
- "provider confirmation" could be trusted without matching TripOS intent — resolved: mismatched amount, order, booking, or provider reference creates **Mismatched Provider Payment Exception**.
- "duplicate provider confirmation" could double-count money — resolved: duplicate **Provider Payment Confirmations** do not create duplicate **Provider Payments**.
- "provider dispute" could be treated like a refund or cancellation — resolved: use **Provider Dispute Exception** for organizer review in the MVP.
- "payment reconciliation" could mean bank settlement accounting — resolved: MVP reconciles booking-level collected and due amounts, not full settlement reconciliation.
- "payment reconciliation" needed a precise MVP term — resolved: use **Booking Reconciliation**.
- "revenue model" could mean subscription or booking fee — resolved: use **Platform Fee** charged on successful **Provider Payments**.
- "platform fee basis" could apply only to reservations — resolved: each successful **Provider Payment** amount is the **Platform Fee Basis**.
- "manual payment fee" would punish fallback and migration workflows — resolved: MVP **Manual Payments** do not produce **Platform Fees**.
- "platform fee deduction" would imply split settlement in the connected-account MVP — resolved: record **Platform Fees** on successful **Provider Payments** and collect them later from the **Organizer**.
- "per-transaction fee collection" would add billing friction too early — resolved: MVP uses monthly **Platform Fee Statements**.
- "payment setup billing" would overload organizer payment configuration — resolved: **Organizer Payments** does not manage **Platform Fee Statements** in the MVP.
- "currency" could expand beyond the India MVP — resolved: MVP money amounts are **INR Amounts** only.
- "invoice" could imply GST or accounting compliance — resolved: tax invoicing is excluded from the MVP.
- "offline payment" should not be hidden outside the ledger — resolved: use **Manual Payment** for payments recorded by users.
- "UPI payment" could mean provider-confirmed checkout or direct transfer — resolved: direct UPI to organizer is a **Direct UPI Payment** inside manual payment workflow.
- "QR payment" could sound provider-confirmed — resolved: use **Payment QR** for the organizer-provided QR image and "Scan QR code to pay" only as traveler-facing instruction copy.
- "manual payment" could imply trusted collected money immediately — resolved: **Manual Payment** affects collected balance only after approval.
- "refund" could imply provider-orchestrated money movement — resolved: MVP records refunds manually as **Refund Records**.
- "refund acknowledgement" could be confused with payment acknowledgement — resolved: use **Refund Acknowledgement** for refund-record notifications.
- "receipt" could imply tax compliance — resolved: use **Payment Acknowledgement** for payment confirmation.
- "imported paid amount" could be mistaken for a manual payment — resolved: use **Opening Payment Record** for historical collected amounts imported during onboarding.
- "price" was ambiguous between traveler-level package price and booking-level amount due — resolved: **Package** is selected per traveler, while **Booking Total** belongs to the booking.
- "package price" could change existing bookings retroactively — resolved: travelers keep a **Booked Package Price** captured at selection time.
- "reservation amount" could change reserved bookings retroactively — resolved: reserved travelers keep a **Booked Reservation Amount**, while draft bookings follow current terms.
- "package edits" after trip creation could imply retroactive repricing — resolved: **Trip Profile** package edits affect future package selection only unless a user explicitly changes a traveler package.
- "removing a package" after bookings exist could delete historical booking context — resolved: selected packages become **Withdrawn Packages** instead of being deleted.
- "itinerary" could mean an unstructured text block — resolved: an **Itinerary** is composed of sequenced **Itinerary Days**.
- "room sharing" could imply room allocation software — resolved: MVP captures **Rooming Notes** only.
- "coupon" could introduce a public promotion engine — resolved: MVP uses manual **Booking Adjustments** instead of a dedicated coupon system.
- "export" could imply analytics reporting — resolved: use **Operational Export** for trip execution data.
- "analytics" could expand the MVP beyond operations — resolved: MVP includes **Operational Metrics** only.
- "reservation amount" could have been trip-level or package-level — resolved: **Reservation Amount** belongs to **Package**.
- "reservation amount" was also used for both package-level and booking-level thresholds — resolved: **Reservation Amount** belongs to a **Package**; **Booking Reservation Amount** is the booking-level sum.
- "reserved seats" could have applied partially within a booking — resolved: seat reservation is all-or-nothing for a **Booking** in the MVP.
- "lead" would introduce a sales pipeline concept — resolved: **Draft Booking** is enough for the MVP.
- "draft expiry" could imply a seat hold — resolved: **Draft Expiry** is only for cleanup and recovery, not capacity.
- "cancellation" was ambiguous between a whole booking and one traveler inside it — resolved: use **Booking Cancellation** and **Traveler Cancellation**.
- "traveler cancellation" could either release capacity or swap attendees — resolved: cancellation releases the seat by default; **Traveler Replacement** preserves the seat.
- "traveler replacement" could be confused with adding another traveler — resolved: **Traveler Replacement** preserves seat count; **Traveler Addition** increases the booking's traveler count.
- "traveler addition" could imply a temporary seat hold — resolved: unpaid **Traveler Additions** do not hold seats in the MVP.
- "document" could have belonged to a booking or a traveler — resolved: identity and eligibility documents are **Traveler Documents**.
- "document expiry" would add unnecessary document management for most MVP trips — resolved: expiry is captured only when a required document type needs it.
- "arrival details" could imply transport management — resolved: MVP captures lightweight **Travel Logistics** only.
- "emergency contact" could be buried inside logistics — resolved: **Emergency Contact** is its own traveler-specific concept.
- "medical information" could be hardcoded for every trip — resolved: **Medical Disclosure** is configurable through **Confirmation Requirements**.
- "medical disclosure" could leak through routine exports — resolved: **Medical Disclosure** is **Sensitive Traveler Information** and is exported only by explicit choice.
- "ready to travel" needed a configurable organizer rule — resolved: use **Confirmation Requirements**.
- "custom fields" would turn readiness collection into a form builder — resolved: MVP uses structured **Confirmation Requirements** categories only.
- "requirement templates" would add another setup abstraction — resolved: **Confirmation Requirements** are configured per **Trip** in the MVP.
- "package-level requirements" would complicate readiness rules — resolved: **Confirmation Requirements** are trip-level only in the MVP.
- "changing requirements" could silently unconfirm bookings — resolved: **Confirmation Requirements** changes create readiness attention without automatically changing **Booking State**.
- "package-specific capacity" would add package inventory complexity — resolved: MVP uses **Trip Capacity** only.
- "document uploaded" was ambiguous with "document accepted" — resolved: use **Document State** with missing, submitted, approved, and rejected states.
- "installments" sounded optional or advanced — resolved: every **Trip** has a **Payment Schedule**, even when full payment is due immediately.
- "payment schedule" could imply arbitrary installment plans — resolved: the MVP supports a **Reservation Milestone** and optional **Balance Milestone**.
- "available seats" could be manually edited and drift from bookings — resolved: **Available Seats** are derived from **Trip Capacity** minus active reserved travelers.
- "public availability" could expose exact seat counts — resolved: the **Public Trip Page** shows **Availability Bands** instead.
- "balance payment on public page" would lose booking context — resolved: later balance collection uses booking-scoped **Balance Payment Links**.
- "manual balance chasing" could be blocked by automation-only reminders — resolved: **Owners** and **Operators** can manually send **Balance Payment Links**.
- "sold out" could be manually stored and drift from capacity — resolved: **Sold Out Booking Availability** is derived from **Available Seats**.
- "waitlist" would introduce a separate capacity queue — resolved: waitlists are excluded from the MVP.
- "overbooking" would break the capacity invariant — resolved: overbooking is excluded from the MVP.
- "message" could mean a notification, channel delivery, or chat — resolved: use **Notification** as the parent concept.
- "notification" could include chat or organizer alerts — resolved: MVP notification types are **Reminder** and **Announcement** only.
- "reminders" could expand into an automation builder — resolved: MVP supports narrow **Automatic Reminders** and context-driven **Manual Reminders**.
- "reminder timing" could expand into configurable automation settings — resolved: MVP uses **Automatic Reminder Timing** defaults with at most **Balance Reminder Lead Time** per trip.
- "announcement scheduling" would expand notifications toward campaign tooling — resolved: MVP sends **Announcements** manually without scheduling.
- "WhatsApp integration" could mean notification delivery or group chat ownership — resolved: TripOS uses the **WhatsApp Channel** for structured notifications and does not own or mirror group chat.
- "SMS" was considered as an MVP channel — resolved: MVP notification channels are **WhatsApp Channel** and **Email Channel**.
- "notification preferences" would add opt-out management for operational messages — resolved: preference management is excluded from the MVP.
