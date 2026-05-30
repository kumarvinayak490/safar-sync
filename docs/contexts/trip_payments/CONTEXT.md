# Trip Payments Context

This context covers booking-connected payments, attempts, provider payments, manual payments, ledgers, refunds, platform fee facts, and payment exceptions.

## Language

**Trip Payments**:
The trip-scoped payment and reconciliation domain for payments, payment attempts, manual payment review, provider payment matching, ledgers, refunds, and payment exceptions connected to bookings on one trip.
_Avoid_: Organizer payments, payment setup, payout account, platform fee statements

**Payment**:
Money collected against a booking.
_Avoid_: Transaction, traveler payment

**Payment State**:
The payment lifecycle state of a booking.
_Avoid_: Booking status, payment status

**Payment Attempt**:
An attempted payment that may succeed or fail.
_Avoid_: Ledger entry

**Payment Purpose**:
The booking payment intent a payment attempt is trying to satisfy.
_Avoid_: Payment type, payment method

**Reservation Payment Attempt**:
A payment attempt for the reservation amount.
_Avoid_: Deposit payment

**Balance Payment Attempt**:
A payment attempt for balance due after reservation.
_Avoid_: Installment payment

**Active Payment Attempt**:
The current payment attempt for a booking and payment purpose.
_Avoid_: Payment

**Superseded Payment Attempt**:
A payment attempt replaced by a newer retry.
_Avoid_: Failed payment

**Provider Payment Confirmation**:
A provider-originated confirmation that a payment was captured.
_Avoid_: Frontend checkout success, webhook, payment authorization

**Payment Confirming Booking**:
A booking waiting for backend confirmation of a provider payment attempt after checkout has begun.
_Avoid_: Reserved booking

**Seat Hold**:
A short-lived hold created when reservation payment begins before seats are reserved.
_Avoid_: Reserved seat

**Seat Hold Expiry**:
The time after which a seat hold releases.
_Avoid_: Draft expiry

**Provider Payment**:
A provider-confirmed payment recorded against a booking.
_Avoid_: Checkout success, payment attempt

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
_Avoid_: Payment provider fee, traveler fee

**Platform Fee Basis**:
The successful provider payment amount used to calculate a platform fee.
_Avoid_: Booking total

**Platform Fee Collection**:
The later process for collecting recorded platform fees from the organizer.
_Avoid_: Split settlement

**Platform Fee Statement**:
A periodic statement of platform fees owed by an organizer.
_Avoid_: Payment setup billing

**Manual Payment**:
A payment recorded from money collected outside provider checkout.
_Avoid_: Provider payment

**Manual Payment State**:
The review state of a manual payment.
_Avoid_: Payment state

**Submitted Manual Payment**:
A traveler-submitted manual payment awaiting organizer review.
_Avoid_: Approved payment

**Approved Manual Payment**:
A manual payment accepted by the organizer.
_Avoid_: Provider payment

**Rejected Manual Payment**:
A manual payment rejected by the organizer.
_Avoid_: Failed provider payment

**Payment Proof**:
Evidence submitted for a manual payment.
_Avoid_: Receipt

**Direct UPI Payment**:
A manual payment made directly to the organizer through UPI.
_Avoid_: Provider UPI checkout

**Payment QR**:
An organizer-provided QR image used by a traveler to make a direct UPI payment outside provider checkout.
_Avoid_: QR checkout, manual pay QR, Razorpay QR

**Refund Record**:
A manually recorded refund related to a booking.
_Avoid_: Provider refund automation

**Refund Reason**:
The reason for a refund record.
_Avoid_: Cancellation reason

**Opening Payment Record**:
A historical collected amount imported during onboarding.
_Avoid_: Manual payment

**Financial Ledger**:
The booking-level money ledger used to derive payment state.
_Avoid_: Payment status, spreadsheet

**Ledger Entry**:
A financial ledger line.
_Avoid_: Activity log

**Booking Reconciliation**:
The review of booking money, payment state, and ledger consistency.
_Avoid_: Settlement reconciliation

## Relationships

- A **Booking** can have one or more **Payments**.
- A **Payment** belongs to exactly one **Booking**.
- A **Booking** can have one or more **Payment Attempts**.
- A **Payment Attempt** has one **Payment Purpose**.
- A **Booking** has at most one **Active Payment Attempt** for a given **Payment Purpose**.
- A **Provider Payment Confirmation** is matched to an expected **Payment Attempt** before creating a **Provider Payment**.
- A frontend provider checkout success can create a **Payment Confirming Booking** but does not reserve seats by itself.
- A **Provider Payment** affects collected balance using the **Gross Provider Payment Amount** after backend confirmation.
- An initial **Provider Payment** reserves seats only when it meets the **Booking Reservation Amount**.
- Later **Provider Payments** can collect balance due after reservation and use **Balance Payment Links**.
- **Manual Payment** affects collected balance only after approval.
- Traveler-submitted **Manual Payments** require **Payment Proof**.
- Organizer-entered **Manual Payments** are **Approved Manual Payments** by default.
- **Payment State** is determined from the **Financial Ledger**.
- MVP **Platform Fees** are recorded on successful **Provider Payments**.
- MVP **Manual Payments** do not produce **Platform Fees**.
- **Trip Payments** provides **Platform Fee** facts for **Platform Fee Statements**.

## Flagged Ambiguities

- "payment" could have belonged to individual travelers or the booking — resolved: **Payment** belongs to **Booking**.
- "payment" overlapped with attempted payments — resolved: **Payment** is collected money; **Payment Attempt** covers failed or pending attempts.
- "payment state" could be treated as manually maintained truth — resolved: **Payment State** is determined from the **Financial Ledger**.
- "checkout success" could be mistaken for collected money — resolved: frontend success can create **Payment Confirming Booking**, but only backend-confirmed **Provider Payment** reserves seats.
- "manual payment" could imply trusted collected money immediately — resolved: **Manual Payment** affects collected balance only after approval.
- "platform fee deduction" would imply split settlement — resolved: record **Platform Fees** on successful **Provider Payments** and collect them later from the **Organizer**.
