# Use Django DRF and Next.js for the MVP

TripOS will start with a Django + Django REST Framework backend, PostgreSQL, background workers for reminders and payment processing, S3-compatible file storage, and a Next.js frontend for the public trip page, traveler portal, and operations dashboard.

We are choosing this stack because the MVP is an operations-heavy, relational workflow product: bookings, traveler slots, payments, ledger entries, manual approvals, documents, reminders, exports, and activity logs all need strong data modeling and boring correctness more than realtime or marketplace-style scale. Django gives us fast back-office development, mature auth and permissions, a strong admin surface for pilots, reliable ORM transactions, and a straightforward home for payment/provider workflows. PostgreSQL is the source of truth for financial and operational state. Background workers handle reminder delivery, provider reconciliation, acknowledgements, exports, and file processing outside request/response paths. S3-compatible storage keeps traveler documents and payment proof out of the database while preserving controlled access.

Next.js remains the frontend choice because TripOS has distinct traveler-facing and organizer-facing surfaces: the public trip page, traveler portal, and operations dashboard. It gives us a polished web UX, shareable public pages, and a clean path to server-rendered/public trip pages without building a native app in the MVP.

The main rejected alternative is a full TypeScript NestJS backend. It would keep frontend and backend in one language, but it offers less immediate leverage for admin/support tooling and relational back-office workflows. We can revisit this after pilots if the product shifts toward complex realtime collaboration, event streaming, or a larger TypeScript-only engineering team.

## Considered Options

**Django DRF + Next.js** is the default recommendation because it gives the strongest MVP leverage for operations, admin tooling, permissions, relational data, background jobs, payments, files, and exports.

**NestJS + Next.js** is the strongest alternative if the team strongly prefers TypeScript end-to-end. It gives clean modular architecture and shared language across frontend and backend, but requires more custom work for admin/support surfaces and back-office workflows.

**Ruby on Rails + Hotwire or React** is a serious alternative for a small team that wants maximum CRUD and operational speed. It is excellent for relational workflows, admin-like screens, background jobs, and payment-heavy apps, but is a bigger ecosystem bet if the team is not already comfortable with Ruby/Rails.

**Next.js full-stack with Postgres and Prisma** is attractive for a very small prototype because it reduces moving parts and keeps everything TypeScript. It becomes less attractive once the product needs robust background processing, operational admin, complex permissions, and payment/document workflows.

**Supabase + Next.js** is useful for a fast prototype or internal pilot, especially for auth, storage, and Postgres. It is weaker as the long-term core if TripOS needs custom ledgers, approval workflows, provider payment orchestration, and carefully controlled back-office behavior.

**Laravel + Inertia or React** is a pragmatic alternative similar to Rails: productive, mature, and good for operational software. It is viable if the team has PHP/Laravel strength, but otherwise does not beat Django for this MVP.
