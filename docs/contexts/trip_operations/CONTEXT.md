# Trip Operations Context

This context covers reminders, announcements, operational exports, activity log, and operational exception review.

## Language

**Trip Operations**:
The trip-scoped operational domain for communications, reminders, announcements, operational exports, activity log, and operational exception review while running a selected trip.
_Avoid_: Trip profile, booking state, traveler records, payment state, organizer settings, internal admin, catch-all module

**Operational Exception**:
A trip-running issue that requires organizer review without itself owning booking, traveler, payment, or trip profile state.
_Avoid_: Booking state, payment state, refund record, cancellation

**Activity Log**:
The operational history log for meaningful actions.
_Avoid_: Financial ledger

**Operational Export**:
A trip execution export for field and operations use.
_Avoid_: Analytics report

**Operational Metric**:
A lightweight operations metric shown in the product.
_Avoid_: Analytics

**Notification**:
A structured message sent by TripOS.
_Avoid_: Chat

**Reminder**:
A notification that asks a booking contact or traveler to complete a pending action.
_Avoid_: Announcement

**Automatic Reminder**:
A reminder sent by TripOS according to a narrow product rule.
_Avoid_: Automation builder

**Draft Recovery Reminder**:
An automatic reminder for a recoverable draft booking.
_Avoid_: Abandoned checkout campaign

**Balance Due Reminder**:
A reminder for balance due.
_Avoid_: Invoice

**Overdue Balance Reminder**:
A reminder for overdue balance.
_Avoid_: Collections campaign

**Missing Requirements Reminder**:
A reminder for missing traveler readiness requirements.
_Avoid_: Document campaign

**Automatic Reminder Timing**:
The narrow timing rules for automatic reminders.
_Avoid_: Reminder schedule

**Balance Reminder Lead Time**:
The trip-level lead time before a balance due reminder.
_Avoid_: Reminder schedule

**Manual Reminder**:
A reminder manually sent by an owner or operator.
_Avoid_: Automated campaign

**Announcement**:
A notification sent by an owner or operator to active booking contacts and travelers for trip updates.
_Avoid_: Chat message, campaign

**Payment Acknowledgement**:
A notification acknowledging an approved payment.
_Avoid_: Receipt

**Refund Acknowledgement**:
A notification acknowledging a refund record.
_Avoid_: Refund receipt

**Reservation Acknowledgement**:
A notification acknowledging that reservation money has reserved seats.
_Avoid_: Payment acknowledgement

**Confirmation Notice**:
A notification that a booking has been confirmed.
_Avoid_: Booking state

**Date Change Notice**:
A notification sent when trip dates change after reserved or confirmed bookings exist.
_Avoid_: Itinerary announcement

**Cancellation Notice**:
A notification sent when a booking or trip is cancelled.
_Avoid_: Refund notice

## Relationships

- **Trip Operations** owns **Reminders**, **Announcements**, **Operational Exports**, **Activity Log**, and **Operational Exception** review.
- **Trip Operations** can display data from **Trips**, **Trip Bookings**, **Trip Travelers**, and **Trip Payments** to help users run a trip.
- **Trip Operations** does not own **Booking State**, **Traveler** records, **Payment State**, **Financial Ledger**, or **Trip Profile** content.
- Sending a **Notification** records an **Activity Log** action.
- A **Reminder** is sent to the **Booking Contact** by default.
- A document-related **Reminder** may also be sent to the relevant **Traveler**.
- An **Announcement** is sent to the **Booking Contact** and the **Active Travelers** in reserved or confirmed bookings.
- **Manual Reminders** and **Announcements** are sent by an **Owner** or **Operator** in the MVP.
- An **Operational Export** belongs to exactly one **Trip**.
- **Operational Exports** exclude **Draft Bookings** by default.
- **Operational Exports** include sensitive traveler or payment information only when explicitly selected.

## Flagged Ambiguities

- "trip operations" could become a broad owner of all trip state — resolved: **Trip Operations** owns communications, operational exports, activity log, and operational exception review, while source state stays in Trips, Trip Bookings, Trip Travelers, and Trip Payments.
- "notification" could include chat or organizer alerts — resolved: MVP notification types are **Reminder** and **Announcement** only, plus defined acknowledgements and notices.
- "reminders" could expand into an automation builder — resolved: MVP supports narrow **Automatic Reminders** and context-driven **Manual Reminders**.
- "export" could imply analytics reporting — resolved: use **Operational Export** for trip execution data.
