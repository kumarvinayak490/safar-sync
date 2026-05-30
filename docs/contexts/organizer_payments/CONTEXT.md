# Organizer Payments Context

This context covers organizer-level payment setup, connected provider accounts, provider authorization, payout and settlement readiness, and manual payment instructions.

## Language

**Organizer Payments**:
The organizer-owned payments submodule for provider setup, payout readiness, manual payment instructions, and future organizer-level payment operations.
_Avoid_: Organizer settings, trip payments, platform custody, platform fee billing

**Payment Setup**:
The organizer payments workflow where an owner configures provider payments and manual payment instructions.
_Avoid_: Payout setup, payment gateway setup, raw gateway setup

**Assisted Payment Setup**:
A TripOS support-assisted version of payment setup used during pilots when provider connection or verification needs help.
_Avoid_: Manual gateway setup, organizer-facing Razorpay setup

**Provider Payment Setup**:
The organizer-level setup record and workflow required to prepare provider-confirmed payments.
_Avoid_: Manual payment setup

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

**Provider Verification Status**:
The visible progress state of provider verification.
_Avoid_: Payment readiness, payout status

**Verified Provider Verification**:
The provider has verified the connected provider account.
_Avoid_: Ready to collect

**Payout Account**:
The account where an organizer receives settled trip payments.
_Avoid_: Bank account, settlement account

**Payout Status**:
The provider-confirmed setup state of an organizer's payout account.
_Avoid_: Settlement report, payout ledger

**Settlement Readiness**:
The organizer-facing readiness signal that settled provider payments can be received by the organizer.
_Avoid_: Editable bank details, settlement report

**Online Payment Readiness**:
Whether an organizer can collect provider-confirmed payments through public booking.
_Avoid_: Provider verification status, payout status

**Manual Payments Only**:
An organizer payment state where provider-confirmed public booking is unavailable but organizer-created manual bookings and manual payments can still operate.
_Avoid_: Failed payment setup, offline-only product

**Manual Payment Instructions**:
Organizer-level payment details used by travelers to make direct manual payments.
_Avoid_: Trip payment details, offline payment setup

## Relationships

- An **Organizer** has **Organizer Payments**.
- **Organizer Payments** owns **Payment Setup** and organizer-level payment readiness.
- **Organizer Payments** includes **Payment Setup**.
- **Payment Setup** may guide a **Community-Led Organizer** through the **Individual Creator Payment Path**.
- The MVP has one **Payout Account** per **Organizer**.
- MVP **Payment Setup** uses a **Connected Provider Account**.
- A **Connected Provider Account** belongs to the **Organizer**, not to the individual **Owner** who granted **Provider Authorization**.
- **Provider Authorization** is owner-initiated but organizer-scoped.
- **OAuth Provider Authorization** is the preferred **Provider Authorization** method.
- **API Key Provider Authorization** is a pilot fallback, not the main organizer-facing path.
- **Online Payment Readiness** requires healthy provider connection, live provider mode, verified provider verification, ready settlement readiness, and enabled provider payment capability.
- Missing **Settlement Readiness** disables provider payments without unpublishing public pages or changing existing bookings.
- **Manual Payment Instructions** belong to **Payment Setup**.
- **Trip** controls **Manual Payment Availability**.
- Only **Owners** can submit or edit **Payment Setup**.
- **Operators** can view readiness blockers but cannot submit or edit **Payment Setup**.

## Flagged Ambiguities

- "payment setup" could be hidden under generic settings — resolved: **Organizer Payments** is its own organizer submodule, with **Payment Setup** as a workflow inside it.
- "payment setup" could mean provider payments or manual collection — resolved: **Payment Setup** owns provider setup and **Manual Payment Instructions**, while each **Trip** controls **Manual Payment Availability**.
- "platform payment operations" could imply TripOS custody or a platform-managed payment account in the MVP — resolved: MVP uses a **Connected Provider Account**.
- "payment setup billing" would overload organizer payment configuration — resolved: **Organizer Payments** does not manage **Platform Fee Statements** in the MVP.
