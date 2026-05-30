import Link from "next/link";
import { redirect } from "next/navigation";
import {
  ArrowRight,
  CheckCircle2,
  CircleAlert,
  Compass,
  CreditCard,
  LockKeyhole,
  Map,
  Plus,
  UsersRound,
  type LucideIcon,
} from "lucide-react";

import {
  OperationalEmptyState,
  OperationsWorkspaceShell,
} from "@/app/OperationsWorkspaceShell";
import { loadWorkspace } from "@/app/workspace";
import {
  buildOrganizerHomeReadModel,
  type OrganizerHomeAttentionItem,
  type OrganizerHomeSetupItem,
  type OrganizerHomeTone,
  type OrganizerHomeTripSummary,
} from "@/lib/organizer-home";
import { getOperationsDashboard } from "@/lib/operations-dashboard";

export const metadata = {
  title: "Organizer Home | TripOS",
  description: "Organizer-level TripOS operations home",
};

export default async function OrganizerHomePage() {
  const workspace = await loadWorkspace();
  const dashboard = await getOperationsDashboard();

  if (!dashboard.ok) {
    if (dashboard.status === "unauthenticated") {
      redirect("/login");
    }

    return (
      <OperationsWorkspaceShell
        activePath="/home"
        currentPath="/home"
        workspace={workspace}
      >
        <OperationalEmptyState
          eyebrow="Organizer Home"
          title="Organizer Home is not available"
          body="Your User does not have access to this Organizer workspace."
        />
      </OperationsWorkspaceShell>
    );
  }

  const home = buildOrganizerHomeReadModel(dashboard, workspace.trips);
  const setupProgress = buildSetupProgress(home.setupGuide);
  const readinessBlockers = buildReadinessBlockers(home);

  return (
    <OperationsWorkspaceShell
      activePath="/home"
      currentPath="/home"
      workspace={workspace}
    >
      <section
        className="organizer-home"
        aria-labelledby="organizer-home-title"
      >
        <div className="home-command-row">
          <div
            className="home-readiness-card"
            aria-labelledby="organizer-home-title"
          >
            <div className="home-readiness-orbit" aria-hidden="true" />
            <div className="home-readiness-heading">
              <div>
                <p className="eyebrow">{dashboard.activeOrganizer.name}</p>
                <h2 id="organizer-home-title">Launch readiness</h2>
              </div>
              <span
                className={`status-chip ${statusChipClass(
                  readinessBlockers.tone,
                )}`}
              >
                {readinessBlockers.statusLabel}
              </span>
            </div>
            <p>{readinessBlockers.summary}</p>
            <div
              className="home-readiness-progress"
              aria-label={`${setupProgress.completed} of ${setupProgress.total} setup items ready`}
            >
              <div className="home-progress-label">
                <span>Setup progress</span>
                <strong>
                  {setupProgress.completed}/{setupProgress.total}
                </strong>
              </div>
              <div className="home-progress-track" aria-hidden="true">
                <span style={{ width: `${setupProgress.percent}%` }} />
              </div>
            </div>
            <div className="home-blocker-grid" aria-label="Current blockers">
              {readinessBlockers.items.map((item) => (
                <Link
                  className={`home-blocker-item is-${item.tone}`}
                  href={item.href}
                  key={item.id}
                >
                  <span>{item.label}</span>
                  <strong>{item.title}</strong>
                  <em>{item.detail}</em>
                  <ArrowRight aria-hidden="true" />
                </Link>
              ))}
            </div>
          </div>

          <div
            className="home-action-panel"
            aria-label="Primary Organizer action"
          >
            <span>{home.primaryAction.label}</span>
            <strong>{home.primaryAction.title}</strong>
            <p>{home.primaryAction.body}</p>
            {home.primaryAction.action ? (
              <Link
                className="primary-link-button icon-link"
                href={home.primaryAction.action.href}
              >
                <Plus aria-hidden="true" />
                {home.primaryAction.action.label}
              </Link>
            ) : (
              <span className="home-readonly-note">
                <LockKeyhole aria-hidden="true" />
                Owner action required
              </span>
            )}
          </div>
        </div>

        <section
          className="home-status-grid"
          aria-label="Organizer setup status"
        >
          {home.summaryTiles.map((tile) => (
            <StatusTile
              detail={tile.detail}
              id={tile.id}
              key={tile.id}
              label={tile.label}
              tone={tile.tone}
              value={tile.value}
            />
          ))}
        </section>

        <section
          className="home-section"
          aria-labelledby="setup-guide-title"
        >
          <div className="workspace-heading">
            <div>
              <p className="eyebrow">Setup guide</p>
              <h2 id="setup-guide-title">Organizer setup</h2>
            </div>
            <span className="home-section-note">
              {home.isOwner ? "Owner actions available" : "Read-only setup view"}
            </span>
          </div>
          <ol className="setup-guide-list">
            {home.setupGuide.map((item) => (
              <SetupGuideRow item={item} key={item.id} />
            ))}
          </ol>
        </section>

        <section
          className="home-section"
          aria-labelledby="needs-attention-title"
        >
          <div className="workspace-heading">
            <div>
              <p className="eyebrow">Needs attention</p>
              <h2 id="needs-attention-title">Operational blockers</h2>
            </div>
          </div>
          <div className="attention-list">
            {home.attentionItems.map((item) => (
              <AttentionRow item={item} key={item.id} />
            ))}
          </div>
        </section>

        {home.hasTrips ? (
          <section
            className="workspace-section"
            aria-labelledby="active-trips-title"
          >
            <div className="workspace-heading">
              <div>
                <p className="eyebrow">Trips</p>
                <h2 id="active-trips-title">Open Trip work</h2>
              </div>
              <Link className="settings-link compact-link" href="/trips">
                View all Trips
              </Link>
            </div>
            <div className="trip-list">
              {home.tripSummaries.map((trip) => (
                <TripSummaryCard key={trip.id} trip={trip} />
              ))}
            </div>
          </section>
        ) : (
          <section
            className="home-zero-state"
            aria-labelledby="zero-trips-title"
          >
            <div>
              <p className="eyebrow">Trips</p>
              <h2 id="zero-trips-title">{home.zeroTripState.title}</h2>
              <p>{home.zeroTripState.body}</p>
            </div>
            {home.zeroTripState.action ? (
              <Link
                className="primary-link-button icon-link"
                href={home.zeroTripState.action.href}
              >
                <Plus aria-hidden="true" />
                {home.zeroTripState.action.label}
              </Link>
            ) : null}
          </section>
        )}
      </section>
    </OperationsWorkspaceShell>
  );
}

function StatusTile({
  detail,
  id,
  label,
  tone,
  value,
}: {
  detail: string;
  id: string;
  label: string;
  tone: OrganizerHomeTone;
  value: string;
}) {
  return (
    <div className={`is-${tone}`} data-status-id={id}>
      <span>{label}</span>
      <strong>{value}</strong>
      <em>{detail}</em>
    </div>
  );
}

function buildSetupProgress(setupGuide: OrganizerHomeSetupItem[]) {
  const total = setupGuide.length;
  const completed = setupGuide.filter((item) => item.tone === "clear").length;

  return {
    completed,
    total,
    percent: total ? Math.round((completed / total) * 100) : 0,
  };
}

function buildReadinessBlockers(
  home: ReturnType<typeof buildOrganizerHomeReadModel>,
) {
  const paymentSetup = home.setupGuide.find(
    (item) => item.id === "payment_setup",
  );
  const launchBlocker = home.attentionItems.find(
    (item) => item.id.includes("launch") || item.label === "Launch blocker",
  );
  const items: {
    id: string;
    label: string;
    title: string;
    detail: string;
    href: string;
    tone: OrganizerHomeTone;
  }[] = [];

  if (paymentSetup && paymentSetup.tone !== "clear") {
    items.push({
      id: "payment_setup_blocked",
      label: "Payment Setup",
      title: `${paymentSetup.label} blocked`,
      detail: paymentSetup.body,
      href: paymentSetup.action?.href ?? "/payment-setup",
      tone: "blocked",
    });
  }

  if (launchBlocker && launchBlocker.tone !== "clear") {
    items.push({
      id: "launch_blocked",
      label: launchBlocker.label,
      title: "Launch blocked",
      detail: `${launchBlocker.value}: ${launchBlocker.detail}`,
      href: launchBlocker.action?.href ?? "/trips",
      tone: "blocked",
    });
  }

  if (!items.length) {
    items.push({
      id: "launch_ready",
      label: "Launch readiness",
      title: "Ready",
      detail: "No launch or payment blockers are visible.",
      href: home.hasTrips
        ? home.tripSummaries[0]?.overviewHref ?? "/trips"
        : "/trips",
      tone: "clear",
    });
  }

  const hasBlockedItems = items.some((item) => item.tone === "blocked");
  const tone: OrganizerHomeTone = hasBlockedItems ? "blocked" : "clear";

  return {
    items,
    statusLabel: hasBlockedItems ? "Blocked" : "Clear",
    summary: hasBlockedItems
      ? "Resolve Payment Setup, then review Launch before public booking opens."
      : "Setup is ready for Trip work.",
    tone,
  };
}

function SetupGuideRow({ item }: { item: OrganizerHomeSetupItem }) {
  const Icon = SETUP_ITEM_ICONS[item.id];

  return (
    <li className={`setup-guide-item is-${item.tone}`}>
      <div className="setup-guide-icon" aria-hidden="true">
        <Icon />
      </div>
      <div className="setup-guide-copy">
        <div className="setup-guide-title-row">
          <strong>{item.label}</strong>
          <span className={`status-chip ${statusChipClass(item.tone)}`}>
            {item.statusLabel}
          </span>
        </div>
        <p>{item.body}</p>
      </div>
      {item.action ? (
        <Link
          className={`setup-guide-action ${
            item.action.primary ? "is-primary" : ""
          }`}
          href={item.action.href}
        >
          <span>{item.action.label}</span>
          <ArrowRight aria-hidden="true" />
        </Link>
      ) : (
        <span className="setup-guide-readonly">
          <LockKeyhole aria-hidden="true" />
          {item.readOnlyLabel}
        </span>
      )}
    </li>
  );
}

function AttentionRow({ item }: { item: OrganizerHomeAttentionItem }) {
  const Icon = item.tone === "clear" ? CheckCircle2 : CircleAlert;

  return (
    <article className={`attention-row is-${item.tone}`}>
      <div className="attention-icon" aria-hidden="true">
        <Icon />
      </div>
      <div>
        <span>{item.label}</span>
        <strong>{item.value}</strong>
        <p>{item.detail}</p>
      </div>
      {item.action ? (
        <Link
          className={`setup-guide-action ${
            item.action.primary ? "is-primary" : ""
          }`}
          href={item.action.href}
        >
          <span>{item.action.label}</span>
          <ArrowRight aria-hidden="true" />
        </Link>
      ) : null}
    </article>
  );
}

function TripSummaryCard({ trip }: { trip: OrganizerHomeTripSummary }) {
  const launchChip = trip.statusChips.find((chip) =>
    chip.label.toLowerCase().includes("launch"),
  );
  const bookingChip = trip.statusChips.find((chip) =>
    chip.label.toLowerCase().includes("booking"),
  );

  return (
    <article>
      <div className="trip-card-header">
        <div>
          <span>Trip</span>
          <strong>{trip.title}</strong>
        </div>
        <Link className="icon-link trip-card-action" href={trip.overviewHref}>
          Open Overview
          <ArrowRight aria-hidden="true" />
        </Link>
      </div>
      <div className="trip-card-meta" aria-label={`${trip.title} metadata`}>
        <div>
          <span>Dates</span>
          <strong>{trip.dateRange}</strong>
        </div>
        <div>
          <span>Seats</span>
          <strong>{trip.capacitySummary}</strong>
        </div>
        <div>
          <span>Booking</span>
          <strong>{bookingChip?.label ?? trip.availabilitySummary}</strong>
        </div>
        <div>
          <span>Launch</span>
          <strong>{launchChip?.label ?? "Launch ready"}</strong>
        </div>
      </div>
      <div className="trip-status-chips" aria-label={`${trip.title} status`}>
        {trip.statusChips.map((chip) => (
          <span
            className={`status-chip ${statusChipClass(chip.tone)}`}
            key={chip.label}
          >
            {chip.label}
          </span>
        ))}
      </div>
    </article>
  );
}

function statusChipClass(tone: OrganizerHomeTone) {
  switch (tone) {
    case "clear":
      return "is-clear";
    case "blocked":
      return "is-blocked";
    case "readonly":
      return "is-readonly";
    default:
      return "";
  }
}

const SETUP_ITEM_ICONS: Record<OrganizerHomeSetupItem["id"], LucideIcon> = {
  organizer_identity: Compass,
  team_access: UsersRound,
  payment_setup: CreditCard,
  create_trip: Map,
};
