import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";
import { MessageCircle } from "lucide-react";

import {
  createPublicDraftBooking,
  getPublicTrip,
  startReservationCheckout,
  type PublicTrip,
} from "@/lib/public-trip";
import { buildOrganizerWhatsappHref } from "@/lib/organizer-identity";
import { TripRichTextRenderer } from "@/components/TripRichTextRenderer";
import { PublicQrPaymentFlow } from "./PublicQrPaymentFlow";

type PublicTripPageProps = {
  params: {
    organizerSlug: string;
    tripSlug: string;
  };
  searchParams?: {
    draft?: string;
    booking?: string;
    attempt?: string;
    checkout?: string;
    expires?: string;
    order?: string;
    error?: string;
  };
};

export async function generateMetadata({
  params,
}: PublicTripPageProps): Promise<Metadata> {
  const trip = await getPublicTrip(params.organizerSlug, params.tripSlug);
  if (!trip.ok) {
    return {
      title: "Public Trip Page unavailable | TripOS",
    };
  }

  return {
    title: `${trip.title} | ${trip.organizerIdentity.name}`,
    description: `${trip.organizerIdentity.name} Public Trip Page on TripOS`,
  };
}

export default async function PublicTripPage({
  params,
  searchParams,
}: PublicTripPageProps) {
  const trip = await getPublicTrip(params.organizerSlug, params.tripSlug);

  if (!trip.ok) {
    notFound();
  }

  const publicUrlPath = trip.publicUrlPath;
  const providerCheckoutVisible =
    trip.publicBookingGate.providerCheckoutVisible;
  const manualPaymentInstructions = trip.manualPaymentInstructions;

  async function startDraftBooking(formData: FormData) {
    "use server";

    const result = await createPublicDraftBooking({
      organizerSlug: params.organizerSlug,
      tripSlug: params.tripSlug,
      bookingContactName: String(formData.get("booking_contact_name") ?? ""),
      bookingContactPhone: String(formData.get("booking_contact_phone") ?? ""),
      bookingContactEmail: String(formData.get("booking_contact_email") ?? ""),
      travelerCount: Number(formData.get("traveler_count")),
      packageId: Number(formData.get("package_id")),
    });

    if (!result.ok) {
      redirect(`${publicUrlPath}?error=draft-booking#booking-intake`);
    }

    if (!providerCheckoutVisible) {
      const query = new URLSearchParams({
        draft: "created",
        booking: String(result.bookingId),
        expires: result.draftExpiresAt,
      });
      redirect(`${publicUrlPath}?${query.toString()}#booking-intake`);
    }

    const checkout = await startReservationCheckout(result.bookingId);
    if (!checkout.ok) {
      const query = new URLSearchParams({
        draft: "created",
        booking: String(result.bookingId),
        expires: result.draftExpiresAt,
        error: "checkout-start",
      });
      redirect(`${publicUrlPath}?${query.toString()}#booking-intake`);
    }

    const query = new URLSearchParams({
      draft: "created",
      booking: String(result.bookingId),
      expires: result.draftExpiresAt,
      checkout: "ready",
      attempt: String(checkout.paymentAttemptId),
      order: checkout.providerAttemptReference,
    });
    redirect(`${publicUrlPath}?${query.toString()}#booking-intake`);
  }

  const legacyItineraryRows = splitItinerary(trip.itinerary);
  const hasStructuredItinerary = trip.itineraryDays.length > 0;
  const lowestPackagePrice = lowestMoney(
    trip.packages.map((tripPackage) => tripPackage.priceInr),
  );
  const lowestReservationAmount = lowestMoney(
    trip.packages.map((tripPackage) => tripPackage.reservationAmountInr),
  );
  const bookingGate = trip.publicBookingGate;
  const inclusionRows = packageInclusionRows(trip);
  const whatsappHref = organizerWhatsappHref(trip);
  const bookingIntakeAvailable =
    providerCheckoutVisible || manualPaymentInstructions?.ready;
  const bookingIntakeBlockedDetail = bookingIntakeBlockedMessage(
    bookingGate,
    manualPaymentInstructions?.ready ?? false,
  );
  const coverMediaItem =
    trip.mediaItems.find((item) => item.isCover) ?? trip.mediaItems[0] ?? null;
  const galleryMediaItems = coverMediaItem
    ? trip.mediaItems.filter((item) => item !== coverMediaItem)
    : trip.mediaItems;

  return (
    <main
      className={`public-trip-shell ${
        whatsappHref ? "has-floating-whatsapp" : ""
      }`}
    >
      <section
        className={`public-trip-hero ${coverMediaItem ? "has-cover" : ""}`}
        aria-label="Public Trip Page"
      >
        {coverMediaItem ? (
          <>
            <div
              aria-hidden="true"
              className="public-trip-hero-cover"
              style={{
                backgroundImage: `url(${coverMediaItem.imageUrl})`,
              }}
            />
            <div aria-hidden="true" className="public-trip-hero-overlay" />
          </>
        ) : null}

        <div className="public-trip-hero-content">
          <div className="public-trip-hero-main">
            <div className="organizer-lockup">
              <OrganizerMark trip={trip} />
              <div>
                <span>Organizer Identity</span>
                <strong>{trip.organizerIdentity.name}</strong>
              </div>
            </div>

            <div className="trip-title-stack">
              <p className="eyebrow">Public Trip Page</p>
              <h1>{trip.title}</h1>
              <p>{formatDateRange(trip.startDate, trip.endDate)}</p>
              {coverMediaItem?.caption ? (
                <p className="public-trip-hero-caption">{coverMediaItem.caption}</p>
              ) : null}
            </div>
          </div>

          <aside className="booking-gate-panel" aria-label="Public booking gate">
          <div
            className={`availability-badge is-${bookingGate.availabilityBand}`}
          >
            {bookingGate.availabilityBandLabel}
          </div>
          <div
            className="public-trip-fact-grid"
            aria-label="Trip booking facts"
          >
            <div>
              <span>Price from</span>
              <strong>{formatOptionalInr(lowestPackagePrice)}</strong>
            </div>
            <div>
              <span>Seats left</span>
              <strong>{seatsLeftLabel(bookingGate)}</strong>
            </div>
            <div>
              <span>Reservation Amount</span>
              <strong>{formatOptionalInr(lowestReservationAmount)}</strong>
            </div>
          </div>
          <p>{bookingGate.message}</p>
          <div
            className={`public-trip-cta-row ${
              whatsappHref ? "has-whatsapp" : ""
            }`}
          >
            <a
              className={`public-cta ${bookingGate.ctaEnabled ? "" : "is-disabled"}`}
              href={bookingGate.ctaEnabled ? "#booking-intake" : undefined}
              aria-disabled={!bookingGate.ctaEnabled}
            >
              {publicCtaLabel(trip)}
            </a>
            {whatsappHref ? (
              <a
                className="public-whatsapp-cta"
                href={whatsappHref}
                target="_blank"
                rel="noreferrer"
              >
                <MessageCircle aria-hidden="true" />
                <span>Ask on WhatsApp</span>
              </a>
            ) : null}
          </div>
          </aside>
        </div>
      </section>

      {whatsappHref ? (
        <a
          aria-label={`Contact ${trip.organizerIdentity.name} on WhatsApp`}
          className="public-floating-whatsapp"
          href={whatsappHref}
          target="_blank"
          rel="noreferrer"
        >
          <MessageCircle aria-hidden="true" />
          <span>WhatsApp</span>
          <strong>{trip.organizerIdentity.whatsappNumber}</strong>
        </a>
      ) : null}

      {galleryMediaItems.length > 0 ? (
        <section
          className="public-trip-section"
          aria-label="Trip Media Gallery"
        >
          <div className="public-section-heading">
            <h2>Gallery</h2>
          </div>
          <div className="public-trip-gallery is-strip-only">
            <div className="public-trip-gallery-strip">
              {galleryMediaItems.map((item) => (
                <figure key={item.id || item.imageUrl}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    alt={item.altText || item.caption || trip.title}
                    src={item.imageUrl}
                  />
                  {item.caption ? (
                    <figcaption>{item.caption}</figcaption>
                  ) : null}
                </figure>
              ))}
            </div>
          </div>
        </section>
      ) : null}

      <section
        className="public-trip-section public-trip-description-section"
        aria-label="Trip Description"
      >
        <div className="public-section-heading">
          <h2>Description</h2>
        </div>
        <div className="public-trip-description">
          <TripRichTextRenderer
            document={trip.descriptionRichText}
            emptyLabel="Trip Description pending."
          />
        </div>
      </section>

      <section className="public-trip-section" aria-label="Itinerary">
        <div className="public-section-heading">
          <h2>Itinerary</h2>
          <p>Organizer updates apply.</p>
        </div>
        {hasStructuredItinerary ? (
          <ol className="itinerary-list is-structured">
            {trip.itineraryDays.map((day, index) => (
              <li key={day.id || `${day.title}-${index}`}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <div>
                  {day.dateLabel ? <em>{day.dateLabel}</em> : null}
                  <h3>{day.title}</h3>
                  <TripRichTextRenderer
                    className="trip-rich-text itinerary-day-rich-text"
                    document={day.descriptionRichText}
                    emptyLabel="Itinerary Day description pending."
                  />
                </div>
              </li>
            ))}
          </ol>
        ) : (
          <ol className="itinerary-list">
            {legacyItineraryRows.map((row, index) => (
              <li key={`${row}-${index}`}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <p>{row}</p>
              </li>
            ))}
          </ol>
        )}
      </section>

      <section className="public-trip-section" aria-label="Packages">
        <div className="public-section-heading">
          <h2>Packages</h2>
          <p>Price and Reservation Amount per traveler.</p>
        </div>
        <div className="package-list">
          {trip.packages.map((tripPackage) => (
            <article
              className="package-row"
              key={tripPackage.id || tripPackage.name}
            >
              <div>
                <h3>{tripPackage.name}</h3>
                {tripPackage.description ? (
                  <p>{tripPackage.description}</p>
                ) : null}
              </div>
              <dl>
                <div>
                  <dt>Price</dt>
                  <dd>{formatInr(tripPackage.priceInr)}</dd>
                </div>
                <div>
                  <dt>Reservation Amount</dt>
                  <dd>{formatInr(tripPackage.reservationAmountInr)}</dd>
                </div>
              </dl>
            </article>
          ))}
        </div>
      </section>

      <section
        className="public-trip-section"
        aria-label="Inclusions and pickup points"
      >
        <div className="public-section-heading">
          <h2>Inclusions and pickup points</h2>
        </div>
        <div className="public-trip-info-grid">
          <article className="public-trip-info-card">
            <span>Inclusions</span>
            {inclusionRows.length ? (
              <ul>
                {inclusionRows.map((row) => (
                  <li key={row.label}>
                    <strong>{row.label}</strong>
                    <p>{row.detail}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p>Organizer update pending.</p>
            )}
          </article>
          <article className="public-trip-info-card">
            <span>Pickup points</span>
            <p>Organizer update pending.</p>
          </article>
        </div>
      </section>

      <section
        className="public-trip-section"
        aria-label="Payment expectations"
      >
        <div className="public-section-heading">
          <h2>Payment expectations</h2>
          <p>{paymentScheduleCopy(trip)}</p>
        </div>
        <div className="payment-expectations">
          <div>
            <span>Reservation Amount</span>
            <strong>Immediate</strong>
            <p>Package x Traveler count.</p>
          </div>
          <div>
            <span>Final balance due</span>
            <strong>
              {trip.paymentSchedule.balanceDueDate
                ? formatDisplayDate(trip.paymentSchedule.balanceDueDate)
                : "No scheduled balance date"}
            </strong>
            <p>
              {trip.paymentSchedule.hasBalanceMilestone
                ? `${trip.paymentSchedule.balanceDueDaysBeforeStart} days before Trip Start Date.`
                : "Organizer update pending."}
            </p>
          </div>
        </div>
      </section>

      {trip.confirmationRequirementsNote ? (
        <section
          className="public-trip-section"
          aria-label="Confirmation requirements"
        >
          <div className="public-section-heading">
            <h2>Confirmation requirements</h2>
            <p>{trip.confirmationRequirementsNote}</p>
          </div>
        </section>
      ) : null}

      <section
        className="booking-intake-panel"
        id="booking-intake"
        aria-label="Booking intake"
      >
        <div className="booking-intake-copy">
          <p className="eyebrow">Draft Booking</p>
          <h2>Reserve seats</h2>
          <p>Contact, Traveler count, Package.</p>
          {searchParams?.draft === "created" ? (
            <div
              className={`draft-booking-notice ${
                searchParams.checkout === "ready"
                  ? "is-confirming"
                  : "is-success"
              }`}
              role="status"
            >
              <strong>
                {searchParams.checkout === "ready"
                  ? "Reservation checkout ready"
                  : "Draft Booking created"}
              </strong>
              <span>
                Reference #{searchParams.booking}.{" "}
                {searchParams.checkout === "ready"
                  ? `Attempt #${searchParams.attempt}. `
                  : ""}
                Expires {formatDateTime(searchParams.expires ?? "")}.
              </span>
            </div>
          ) : null}
          {searchParams?.error === "checkout-start" ? (
            <div className="draft-booking-notice is-error" role="alert">
              <strong>Reservation checkout not started</strong>
              <span>Provider checkout could not start.</span>
            </div>
          ) : null}
          {searchParams?.error === "draft-booking" ? (
            <div className="draft-booking-notice is-error" role="alert">
              <strong>Draft Booking not created</strong>
              <span>
                Check required contact details and select at least one Package.
              </span>
            </div>
          ) : null}
          {!providerCheckoutVisible && manualPaymentInstructions?.ready ? (
            <div className="draft-booking-notice is-confirming" role="status">
              <strong>Manual Payments available</strong>
              <span>Payment Proof is reviewed before seats are reserved.</span>
            </div>
          ) : null}
          {!bookingIntakeAvailable && bookingIntakeBlockedDetail ? (
            <div className="draft-booking-notice is-neutral" role="status">
              <strong>{bookingGate.message}</strong>
              <span>{bookingIntakeBlockedDetail}</span>
            </div>
          ) : null}
        </div>

        {providerCheckoutVisible ? (
          <form action={startDraftBooking} className="booking-intake-form">
            <fieldset disabled={!bookingGate.ctaEnabled}>
              <legend>Booking Contact Details</legend>
              <label>
                <span>Name</span>
                <input
                  name="booking_contact_name"
                  autoComplete="name"
                  required
                  maxLength={160}
                />
              </label>
              <label>
                <span>Phone number</span>
                <input
                  name="booking_contact_phone"
                  autoComplete="tel"
                  required
                  maxLength={40}
                />
              </label>
              <label>
                <span>Email (optional)</span>
                <input
                  name="booking_contact_email"
                  autoComplete="email"
                  type="email"
                />
              </label>
            </fieldset>

            <fieldset disabled={!bookingGate.ctaEnabled}>
              <legend>Reservation Inputs</legend>
              <label>
                <span>Traveler count</span>
                <input
                  defaultValue={1}
                  inputMode="numeric"
                  min={1}
                  name="traveler_count"
                  required
                  type="number"
                />
              </label>
              <label>
                <span>Package</span>
                <select name="package_id" required>
                  <option value="">Select Package</option>
                  {trip.packages.map((tripPackage) => (
                    <option
                      value={tripPackage.id}
                      key={tripPackage.id || tripPackage.name}
                    >
                      {tripPackage.name} ·{" "}
                      {formatInr(tripPackage.reservationAmountInr)} Reservation
                      Amount
                    </option>
                  ))}
                </select>
              </label>
            </fieldset>

            <div className="booking-intake-action">
              <p>{bookingGate.message}</p>
              <button
                className="public-cta"
                type="submit"
                disabled={!bookingGate.ctaEnabled}
              >
                {bookingGate.ctaEnabled
                  ? bookingGate.primaryPaymentActionLabel
                  : publicCtaLabel(trip)}
              </button>
            </div>
          </form>
        ) : null}

        {manualPaymentInstructions?.ready ? (
          <PublicQrPaymentFlow
            organizerSlug={params.organizerSlug}
            tripSlug={params.tripSlug}
            instructions={manualPaymentInstructions}
            packages={trip.packages}
          />
        ) : null}
      </section>
    </main>
  );
}

function OrganizerMark({ trip }: { trip: PublicTrip }) {
  if (trip.organizerIdentity.logoUrl) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        className="organizer-mark"
        src={trip.organizerIdentity.logoUrl}
        alt=""
        aria-hidden="true"
      />
    );
  }

  return (
    <div
      className="organizer-mark"
      aria-hidden="true"
      style={{
        background: trip.organizerIdentity.fallback.background,
        color: trip.organizerIdentity.fallback.foreground,
      }}
    >
      {trip.organizerIdentity.fallback.initials}
    </div>
  );
}

function splitItinerary(itinerary: string) {
  const rows = itinerary
    .split(/\n|(?=Day\s+\d+:)/i)
    .map((row) => row.trim())
    .filter(Boolean);

  return rows.length > 0
    ? rows
    : ["Itinerary details will be shared by the Organizer."];
}

function publicCtaLabel(trip: PublicTrip) {
  if (trip.publicBookingGate.reasonCode === "sold_out") {
    return "Sold out";
  }

  return trip.publicBookingGate.ready
    ? trip.publicBookingGate.primaryPaymentActionLabel
    : "Bookings opening soon";
}

function bookingIntakeBlockedMessage(
  gate: PublicTrip["publicBookingGate"],
  manualPaymentFormReady: boolean,
): string | null {
  if (gate.providerCheckoutVisible || manualPaymentFormReady) {
    return null;
  }

  const manualMethod = gate.manualPaymentMethod;
  const manualInstructionsReady =
    manualMethod.manualPaymentInstructionsReady === true;
  const manualAvailabilityOpen =
    manualMethod.manualPaymentAvailabilityOpen === true;

  if (!gate.bookingAvailabilityOpen) {
    if (manualInstructionsReady) {
      return "Manual Payment Instructions are saved. Open Public Booking from Trip Launch to accept Manual Payments on this page.";
    }

    return "Public Booking is still closed for this Trip.";
  }

  if (manualInstructionsReady && !manualAvailabilityOpen) {
    return "Enable Manual Payments for this Trip from Trip Launch before travelers can scan the Payment QR.";
  }

  if (manualMethod.blockerLabel && manualMethod.message) {
    return `${manualMethod.blockerLabel}: ${manualMethod.message}`;
  }

  if (gate.onlinePaymentReadinessMessage) {
    return gate.onlinePaymentReadinessMessage;
  }

  return gate.message;
}

function lowestMoney(values: number[]): number | null {
  const positiveValues = values.filter((value) => value > 0);
  if (positiveValues.length === 0) {
    return null;
  }

  return Math.min(...positiveValues);
}

function formatOptionalInr(value: number | null): string {
  return value === null ? "Pending" : formatInr(value);
}

function seatsLeftLabel(gate: PublicTrip["publicBookingGate"]): string {
  if (!gate.capacityAvailable || gate.reasonCode === "sold_out") {
    return "Sold out";
  }

  return `${gate.availableSeats} seat${gate.availableSeats === 1 ? "" : "s"} left`;
}

function packageInclusionRows(trip: PublicTrip) {
  return trip.packages
    .filter((tripPackage) => tripPackage.description.trim())
    .map((tripPackage) => ({
      label: tripPackage.name,
      detail: tripPackage.description.trim(),
    }));
}

function organizerWhatsappHref(trip: PublicTrip): string {
  const publicUrl = absolutePublicUrl(trip.publicUrlPath);
  const message = `Hi ${trip.organizerIdentity.name}, I have a question about ${trip.title}: ${publicUrl}`;
  return buildOrganizerWhatsappHref(
    trip.organizerIdentity.whatsappNumber,
    message,
  );
}

function absolutePublicUrl(path: string): string {
  const baseUrl =
    process.env.NEXT_PUBLIC_APP_BASE_URL ?? "http://localhost:3000";
  return new URL(path || "/", baseUrl).toString();
}

function paymentScheduleCopy(trip: PublicTrip) {
  if (!trip.paymentSchedule.hasBalanceMilestone) {
    return "Reserve now with the Reservation Amount. Balance timing will be confirmed by the Organizer.";
  }

  return `Reserve now with the Reservation Amount. Balance is scheduled for ${formatDisplayDate(
    trip.paymentSchedule.balanceDueDate ?? trip.startDate,
  )}.`;
}

function formatDateRange(startDate: string, endDate: string) {
  return `${formatDisplayDate(startDate)} to ${formatDisplayDate(endDate)}`;
}

function formatDisplayDate(value: string) {
  if (!value) {
    return "Date pending";
  }

  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

function formatDateTime(value: string) {
  if (!value) {
    return "24 hours from creation";
  }

  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    month: "short",
    timeZone: "Asia/Kolkata",
    year: "numeric",
  }).format(new Date(value));
}

function formatInr(amount: number) {
  return new Intl.NumberFormat("en-IN", {
    currency: "INR",
    maximumFractionDigits: 0,
    style: "currency",
  }).format(amount);
}
