import { drfApiUrl } from "./drf-request.ts";
import type {
  TripProfilePublicationReadinessDecision,
  WorkspaceTrip,
} from "./workspace.ts";
import {
  emptyTripRichText,
  getTripRichTextPlainText,
  isTripRichTextEmpty,
  normalizeTripRichText,
  type TripRichTextDocument,
} from "./trip-rich-text.ts";

export type TripProfileSectionId =
  | "description"
  | "itinerary"
  | "media"
  | "packages"
  | "payment-schedule"
  | "requirements";

export type TripProfileTone = "blocked" | "attention" | "clear" | "readonly";

export type TripProfileSectionDefinition = {
  id: TripProfileSectionId;
  label: string;
  shortLabel: string;
  detail: string;
  dense: boolean;
  ownerOnly: boolean;
};

export type TripProfileSectionState = TripProfileSectionDefinition & {
  editable: boolean;
  locked: boolean;
  readonlyReason: string;
  stateLabel: string;
  tone: TripProfileTone;
};

export type TripProfileReadinessItem = {
  id: string;
  label: string;
  detail: string;
  sectionId: TripProfileSectionId;
  tone: TripProfileTone;
};

export type TripProfileShellModel = {
  tripId: number;
  tripTitle: string;
  description: {
    richText: TripRichTextDocument;
    empty: boolean;
  };
  itinerary: {
    days: TripItineraryDay[];
    empty: boolean;
  };
  media: {
    items: TripMediaItem[];
    empty: boolean;
    publicCount: number;
  };
  packages: {
    rows: TripProfilePackage[];
    empty: boolean;
  };
  paymentSchedule: TripPaymentSchedule;
  confirmationRequirements: TripConfirmationRequirements;
  locked: boolean;
  lockLabel: string;
  lockDetail: string;
  publicUrlPath: string;
  roleLabel: "Owner" | "Operator";
  sections: TripProfileSectionState[];
  blockers: TripProfileReadinessItem[];
  encouraged: TripProfileReadinessItem[];
  publicationReady: boolean;
};

export type TripProfileSectionReadinessState = Pick<
  TripProfileSectionState,
  "locked" | "tone"
>;

export type TripProfileRole = "owner" | "operator";

export type TripItineraryDay = {
  id: number;
  sequence: number;
  title: string;
  dateLabel: string;
  descriptionRichText: TripRichTextDocument;
  descriptionPlainText: string;
};

export type TripProfilePackage = {
  id: number;
  name: string;
  description: string;
  priceInr: number;
  reservationAmountInr: number;
  position: number;
};

export type TripProfilePackageDraft = TripProfilePackage & {
  clientId: string;
};

export type TripMediaItem = {
  id: number;
  assetId: number;
  imageUrl: string;
  originalFilename: string;
  contentType: string;
  fileSize: number;
  position: number;
  caption: string;
  altText: string;
  isPublic: boolean;
  isCover: boolean;
};

export type TripMediaItemDraft = TripMediaItem & {
  clientId: string;
};

export type TripPaymentSchedule = {
  hasBalanceMilestone: boolean;
  balanceDueDaysBeforeStart: number | null;
  balanceDueDate: string | null;
  balanceReminderLeadDays: number;
  reviewed: boolean;
};

export type TripPaymentScheduleDraft = {
  hasBalanceMilestone: boolean;
  balanceDueDaysBeforeStart: number | null;
  balanceReminderLeadDays: number;
};

export type TripConfirmationRequirements = {
  travelerDocuments: boolean;
  travelerIdentityDetails: boolean;
  travelLogistics: boolean;
  emergencyContact: boolean;
  medicalDisclosure: boolean;
  fullPaymentBeforeConfirmation: boolean;
  reviewed: boolean;
};

export type TripConfirmationRequirementsDraft = Omit<
  TripConfirmationRequirements,
  "reviewed"
>;

export type TripPaymentScheduleValidationResult =
  | {
      ok: true;
      paymentSchedule: TripPaymentScheduleDraft;
      errors: {};
    }
  | {
      ok: false;
      errors: Partial<
        Record<
          "balanceDueDaysBeforeStart" | "balanceReminderLeadDays",
          string
        >
      >;
    };

export type TripPackageValidationField =
  | "name"
  | "priceInr"
  | "reservationAmountInr";

export type TripPackageValidationResult =
  | {
      ok: true;
      packages: TripProfilePackage[];
      formErrors: [];
      rowErrors: Record<string, Partial<Record<TripPackageValidationField, string>>>;
    }
  | {
      ok: false;
      formErrors: string[];
      rowErrors: Record<string, Partial<Record<TripPackageValidationField, string>>>;
    };

export const TRIP_PROFILE_SECTIONS: TripProfileSectionDefinition[] = [
  {
    id: "description",
    label: "Description",
    shortLabel: "Description",
    detail: "Trip Description",
    dense: false,
    ownerOnly: false,
  },
  {
    id: "itinerary",
    label: "Itinerary",
    shortLabel: "Itinerary",
    detail: "Itinerary Days",
    dense: true,
    ownerOnly: false,
  },
  {
    id: "media",
    label: "Media",
    shortLabel: "Media",
    detail: "Trip Media Gallery",
    dense: false,
    ownerOnly: false,
  },
  {
    id: "packages",
    label: "Packages",
    shortLabel: "Packages",
    detail: "Package terms",
    dense: true,
    ownerOnly: true,
  },
  {
    id: "payment-schedule",
    label: "Balance payment schedule",
    shortLabel: "Schedule",
    detail: "Final balance timing",
    dense: true,
    ownerOnly: true,
  },
  {
    id: "requirements",
    label: "Requirements",
    shortLabel: "Requirements",
    detail: "Confirmation Requirements",
    dense: true,
    ownerOnly: false,
  },
];

export const TRIP_PROFILE_DEFAULT_SECTION_ID: TripProfileSectionId =
  "description";

export function isTripProfileMediaEditableWhenLocked(
  sectionId: TripProfileSectionId,
): boolean {
  return sectionId === "media";
}

export function isTripProfileSectionReady(
  section: TripProfileSectionReadinessState,
) {
  return section.tone === "clear" || (section.locked && section.tone === "readonly");
}

export function countTripProfileReadySections(
  sections: TripProfileSectionReadinessState[],
) {
  return sections.filter(isTripProfileSectionReady).length;
}

export const TRIP_PROFILE_UNSAVED_LEAVE_MESSAGE =
  "Trip Profile has unsaved section changes. Leave without saving?";

export function buildTripProfileShellModel({
  role,
  trip,
}: {
  role: TripProfileRole;
  trip: Pick<
    WorkspaceTrip,
    | "id"
    | "title"
    | "descriptionRichText"
    | "itineraryDays"
    | "mediaItems"
    | "packages"
    | "paymentSchedule"
    | "confirmationRequirements"
    | "publicationState"
    | "launchReadiness"
    | "publicUrlPath"
  > &
    Partial<Pick<WorkspaceTrip, "tripProfilePublicationReadiness">>;
}): TripProfileShellModel {
  const locked = isTripProfileLocked(trip);
  const descriptionRichText = normalizeTripRichText(
    trip.descriptionRichText ?? emptyTripRichText(),
  );
  const itineraryDays = normalizeTripItineraryDays(trip.itineraryDays);
  const mediaItems = normalizeTripMediaItems(trip.mediaItems);
  const packages = normalizeTripPackages(trip.packages);
  const paymentSchedule = normalizeTripPaymentSchedule(trip.paymentSchedule);
  const confirmationRequirements = normalizeTripConfirmationRequirements(
    trip.confirmationRequirements,
  );
  const descriptionEmpty = isTripRichTextEmpty(descriptionRichText);
  const itineraryEmpty = itineraryDays.length === 0;
  const mediaEmpty = mediaItems.length === 0;
  const publicMediaCount = mediaItems.filter((item) => item.isPublic).length;
  const packagesEmpty = packages.length === 0;
  const paymentScheduleReviewed = paymentSchedule.reviewed;
  const confirmationRequirementsReviewed = confirmationRequirements.reviewed;
  const roleLabel = role === "owner" ? "Owner" : "Operator";
  const sections = TRIP_PROFILE_SECTIONS.map((section) =>
    buildSectionState({
      confirmationRequirementsReviewed,
      descriptionEmpty,
      itineraryEmpty,
      publicMediaCount,
      packagesEmpty,
      locked,
      paymentScheduleReviewed,
      role,
      section,
    }),
  );
  const fallbackBlockers = buildTripProfileBlockers({
    descriptionEmpty,
    itineraryEmpty,
    packagesEmpty,
    confirmationRequirementsReviewed,
    paymentScheduleReviewed,
  });
  const fallbackEncouraged: TripProfileReadinessItem[] = publicMediaCount > 0
    ? []
    : [
        {
          id: "media-gallery",
          label: "Add public media",
          detail: "Media is encouraged for the Public Trip Page.",
          sectionId: "media",
          tone: "attention",
        },
      ];
  const readiness = mapTripProfilePublicationReadiness(
    trip.tripProfilePublicationReadiness,
    {
      blockers: fallbackBlockers,
      encouraged: fallbackEncouraged,
    },
  );
  const blockers = locked ? [] : readiness.blockers;
  const encouraged: TripProfileReadinessItem[] = locked
    ? []
    : readiness.encouraged;

  return {
    tripId: trip.id,
    tripTitle: trip.title,
    description: {
      richText: descriptionRichText,
      empty: descriptionEmpty,
    },
    itinerary: {
      days: itineraryDays,
      empty: itineraryEmpty,
    },
    media: {
      items: mediaItems,
      empty: mediaEmpty,
      publicCount: publicMediaCount,
    },
    packages: {
      rows: packages,
      empty: packagesEmpty,
    },
    paymentSchedule,
    confirmationRequirements,
    locked,
    lockLabel: locked ? "Published Trip Profile Lock" : "Draft Trip Profile",
    lockDetail: locked
      ? "Normal profile edits are disabled after publication."
      : "Section edits remain local until Save.",
    publicUrlPath: trip.publicUrlPath,
    roleLabel,
    sections,
    blockers,
    encouraged,
    publicationReady: locked || readiness.publishEligible,
  };
}

export function normalizeTripItineraryDays(value: unknown): TripItineraryDay[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((day, index) => normalizeTripItineraryDay(day, index))
    .filter((day): day is TripItineraryDay => day !== null)
    .sort((first, second) => first.sequence - second.sequence || first.id - second.id);
}

export function normalizeTripPackages(value: unknown): TripProfilePackage[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((tripPackage, index) => normalizeTripPackage(tripPackage, index))
    .filter((tripPackage): tripPackage is TripProfilePackage => tripPackage !== null)
    .sort(
      (first, second) =>
        first.position - second.position ||
        first.id - second.id ||
        first.name.localeCompare(second.name),
    );
}

export function normalizeTripMediaItems(value: unknown): TripMediaItem[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item, index) => normalizeTripMediaItem(item, index))
    .filter((item): item is TripMediaItem => item !== null)
    .sort((first, second) => first.position - second.position || first.id - second.id);
}

export function normalizeTripPaymentSchedule(value: unknown): TripPaymentSchedule {
  if (!isRecord(value)) {
    return {
      hasBalanceMilestone: false,
      balanceDueDaysBeforeStart: null,
      balanceDueDate: null,
      balanceReminderLeadDays: 3,
      reviewed: false,
    };
  }

  const rawDueDays =
    value.balance_due_days_before_start ?? value.balanceDueDaysBeforeStart;
  const balanceDueDaysBeforeStart =
    typeof rawDueDays === "number" && Number.isInteger(rawDueDays) && rawDueDays > 0
      ? rawDueDays
      : null;
  const hasBalanceMilestone =
    typeof value.has_balance_milestone === "boolean"
      ? value.has_balance_milestone
      : typeof value.hasBalanceMilestone === "boolean"
        ? value.hasBalanceMilestone
        : balanceDueDaysBeforeStart !== null;
  const reminderLeadDays = nonNegativeInteger(
    value.balance_reminder_lead_days ?? value.balanceReminderLeadDays,
    3,
  );

  return {
    hasBalanceMilestone,
    balanceDueDaysBeforeStart: hasBalanceMilestone
      ? balanceDueDaysBeforeStart
      : null,
    balanceDueDate:
      typeof value.balance_due_date === "string"
        ? value.balance_due_date
        : typeof value.balanceDueDate === "string"
          ? value.balanceDueDate
          : null,
    balanceReminderLeadDays: reminderLeadDays,
    reviewed:
      typeof value.reviewed === "boolean"
        ? value.reviewed
        : typeof value.is_reviewed === "boolean"
          ? value.is_reviewed
          : false,
  };
}

export function normalizeTripConfirmationRequirements(
  value: unknown,
): TripConfirmationRequirements {
  if (!isRecord(value)) {
    return {
      travelerDocuments: false,
      travelerIdentityDetails: false,
      travelLogistics: false,
      emergencyContact: false,
      medicalDisclosure: false,
      fullPaymentBeforeConfirmation: false,
      reviewed: false,
    };
  }

  return {
    travelerDocuments: booleanValue(
      value.requires_traveler_documents ?? value.travelerDocuments,
    ),
    travelerIdentityDetails: booleanValue(
      value.requires_traveler_identity_details ?? value.travelerIdentityDetails,
    ),
    travelLogistics: booleanValue(
      value.requires_travel_logistics ?? value.travelLogistics,
    ),
    emergencyContact: booleanValue(
      value.requires_emergency_contact ?? value.emergencyContact,
    ),
    medicalDisclosure: booleanValue(
      value.requires_medical_disclosure ?? value.medicalDisclosure,
    ),
    fullPaymentBeforeConfirmation: booleanValue(
      value.requires_full_payment_before_confirmation ??
        value.fullPaymentBeforeConfirmation,
    ),
    reviewed: booleanValue(
      value.reviewed ?? value.confirmation_requirements_reviewed,
    ),
  };
}

export function confirmationRequirementsToDraft(
  requirements: TripConfirmationRequirements,
): TripConfirmationRequirementsDraft {
  return {
    travelerDocuments: requirements.travelerDocuments,
    travelerIdentityDetails: requirements.travelerIdentityDetails,
    travelLogistics: requirements.travelLogistics,
    emergencyContact: requirements.emergencyContact,
    medicalDisclosure: requirements.medicalDisclosure,
    fullPaymentBeforeConfirmation: requirements.fullPaymentBeforeConfirmation,
  };
}

function normalizeTripPackage(value: unknown, index: number): TripProfilePackage | null {
  if (!isRecord(value)) {
    return null;
  }

  const name = typeof value.name === "string" ? value.name.trim() : "";
  const priceInr = positiveInteger(value.price_inr ?? value.priceInr, 0);
  const reservationAmountInr = positiveInteger(
    value.reservation_amount_inr ?? value.reservationAmountInr,
    0,
  );
  if (!name || priceInr < 1 || reservationAmountInr < 1) {
    return null;
  }

  return {
    id: positiveInteger(value.id, 0),
    name,
    description:
      typeof value.description === "string" ? value.description.trim() : "",
    priceInr,
    reservationAmountInr,
    position: positiveInteger(value.position, index + 1),
  };
}

function normalizeTripMediaItem(value: unknown, index: number): TripMediaItem | null {
  if (!isRecord(value)) {
    return null;
  }

  const imageUrl =
    typeof value.image_url === "string"
      ? value.image_url
      : typeof value.imageUrl === "string"
        ? value.imageUrl
        : "";
  if (!imageUrl) {
    return null;
  }

  return {
    id: positiveInteger(value.id, 0),
    assetId: positiveInteger(value.asset_id ?? value.assetId, 0),
    imageUrl: normalizeTripMediaImageUrl(imageUrl),
    originalFilename:
      typeof value.original_filename === "string"
        ? value.original_filename
        : typeof value.originalFilename === "string"
          ? value.originalFilename
          : "",
    contentType:
      typeof value.content_type === "string"
        ? value.content_type
        : typeof value.contentType === "string"
          ? value.contentType
          : "",
    fileSize: nonNegativeInteger(value.file_size ?? value.fileSize, 0),
    position: positiveInteger(value.position, index + 1),
    caption: typeof value.caption === "string" ? value.caption.trim() : "",
    altText:
      typeof value.alt_text === "string"
        ? value.alt_text.trim()
        : typeof value.altText === "string"
          ? value.altText.trim()
          : "",
    isPublic: booleanValue(value.is_public ?? value.isPublic),
    isCover: booleanValue(value.is_cover ?? value.isCover),
  };
}

export function validateTripProfilePackages(
  packages: TripProfilePackageDraft[],
): TripPackageValidationResult {
  const rowErrors: Record<
    string,
    Partial<Record<TripPackageValidationField, string>>
  > = {};
  const formErrors: string[] = [];

  if (packages.length === 0) {
    formErrors.push("At least one active Package is required.");
  }

  const normalizedPackages = packages.map((tripPackage, index) => {
    const rowKey = tripPackage.clientId || `package-${index + 1}`;
    const errors: Partial<Record<TripPackageValidationField, string>> = {};
    const name = tripPackage.name.trim();
    const description = tripPackage.description.trim();
    const priceInr = tripPackage.priceInr;
    const reservationAmountInr = tripPackage.reservationAmountInr;

    if (!name) {
      errors.name = "Package name is required.";
    }
    if (!Number.isInteger(priceInr) || priceInr < 1) {
      errors.priceInr = "Enter a Package price greater than 0.";
    }
    if (!Number.isInteger(reservationAmountInr) || reservationAmountInr < 1) {
      errors.reservationAmountInr = "Enter a Reservation Amount greater than 0.";
    }
    if (
      Number.isInteger(priceInr) &&
      Number.isInteger(reservationAmountInr) &&
      priceInr > 0 &&
      reservationAmountInr > priceInr
    ) {
      errors.reservationAmountInr =
        "Reservation Amount cannot exceed Package price.";
    }
    if (Object.keys(errors).length > 0) {
      rowErrors[rowKey] = errors;
    }

    return {
      id: tripPackage.id,
      name,
      description,
      priceInr,
      reservationAmountInr,
      position: index + 1,
    };
  });

  if (formErrors.length > 0 || Object.keys(rowErrors).length > 0) {
    return {
      ok: false,
      formErrors,
      rowErrors,
    };
  }

  return {
    ok: true,
    packages: normalizedPackages,
    formErrors: [],
    rowErrors,
  };
}

export function validateTripPaymentSchedule(
  paymentSchedule: TripPaymentScheduleDraft,
): TripPaymentScheduleValidationResult {
  const errors: Partial<
    Record<"balanceDueDaysBeforeStart" | "balanceReminderLeadDays", string>
  > = {};
  const balanceDueDaysBeforeStart = paymentSchedule.hasBalanceMilestone
    ? paymentSchedule.balanceDueDaysBeforeStart
    : null;
  const balanceReminderLeadDays = paymentSchedule.balanceReminderLeadDays;

  if (
    paymentSchedule.hasBalanceMilestone &&
    (!Number.isInteger(balanceDueDaysBeforeStart) ||
      balanceDueDaysBeforeStart === null ||
      balanceDueDaysBeforeStart < 1)
  ) {
    errors.balanceDueDaysBeforeStart =
      "Enter final balance due days greater than 0.";
  }
  if (!Number.isInteger(balanceReminderLeadDays) || balanceReminderLeadDays < 0) {
    errors.balanceReminderLeadDays =
      "Enter a reminder lead time of 0 days or more.";
  }
  if (
    paymentSchedule.hasBalanceMilestone &&
    typeof balanceDueDaysBeforeStart === "number" &&
    Number.isInteger(balanceReminderLeadDays) &&
    balanceReminderLeadDays > balanceDueDaysBeforeStart
  ) {
    errors.balanceReminderLeadDays =
      "Reminder lead time cannot exceed final balance due days.";
  }

  if (Object.keys(errors).length > 0) {
    return { ok: false, errors };
  }

  return {
    ok: true,
    paymentSchedule: {
      hasBalanceMilestone: paymentSchedule.hasBalanceMilestone,
      balanceDueDaysBeforeStart,
      balanceReminderLeadDays,
    },
    errors: {},
  };
}

export function paymentScheduleToDraft(
  paymentSchedule: TripPaymentSchedule,
): TripPaymentScheduleDraft {
  return {
    hasBalanceMilestone: paymentSchedule.hasBalanceMilestone,
    balanceDueDaysBeforeStart: paymentSchedule.balanceDueDaysBeforeStart,
    balanceReminderLeadDays: paymentSchedule.balanceReminderLeadDays,
  };
}

function normalizeTripItineraryDay(value: unknown, index: number): TripItineraryDay | null {
  if (!isRecord(value)) {
    return null;
  }

  const title = typeof value.title === "string" ? value.title.trim() : "";
  if (!title) {
    return null;
  }

  const descriptionRichText = normalizeTripRichText(value.description_rich_text);
  const descriptionPlainText =
    typeof value.description_plain_text === "string"
      ? value.description_plain_text
      : getTripRichTextPlainText(descriptionRichText);

  return {
    id: typeof value.id === "number" ? value.id : 0,
    sequence: positiveInteger(value.sequence, index + 1),
    title,
    dateLabel: typeof value.date_label === "string" ? value.date_label.trim() : "",
    descriptionRichText,
    descriptionPlainText,
  };
}

export function isTripProfileLocked(
  trip: Pick<WorkspaceTrip, "publicationState" | "launchReadiness">,
): boolean {
  return (
    trip.publicationState === "published" ||
    trip.publicationState === "archived" ||
    (trip.launchReadiness.publicationReady &&
      trip.publicationState !== "draft")
  );
}

export function getTripProfileSection(
  sectionId: TripProfileSectionId,
): TripProfileSectionDefinition {
  return (
    TRIP_PROFILE_SECTIONS.find((section) => section.id === sectionId) ??
    TRIP_PROFILE_SECTIONS[0]
  );
}

export function getTripProfileSectionEditability({
  locked,
  role,
  sectionId,
}: {
  locked: boolean;
  role: TripProfileRole;
  sectionId: TripProfileSectionId;
}): { editable: boolean; reason: string } {
  const section = getTripProfileSection(sectionId);
  const profileLocked =
    locked && !isTripProfileMediaEditableWhenLocked(sectionId);

  if (profileLocked) {
    return {
      editable: false,
      reason: "Published Trip Profile Lock",
    };
  }

  if (section.ownerOnly && role !== "owner") {
    return {
      editable: false,
      reason: "Owner-managed section",
    };
  }

  return {
    editable: true,
    reason: "",
  };
}

export function shouldWarnBeforeLeavingTripProfile({
  dirtySectionIds,
  locked,
}: {
  dirtySectionIds: TripProfileSectionId[];
  locked: boolean;
}): boolean {
  if (!locked) {
    return dirtySectionIds.length > 0;
  }

  return dirtySectionIds.includes("media");
}

export function resolveTripProfileSectionSwitch({
  activeSectionId,
  dirtySectionIds,
  locked,
  nextSectionId,
}: {
  activeSectionId: TripProfileSectionId;
  dirtySectionIds: TripProfileSectionId[];
  locked: boolean;
  nextSectionId: TripProfileSectionId;
}):
  | {
      canSwitch: true;
      activeSectionId: TripProfileSectionId;
      pendingSectionId: null;
    }
  | {
      canSwitch: false;
      activeSectionId: TripProfileSectionId;
      pendingSectionId: TripProfileSectionId;
    } {
  if (
    (locked && !isTripProfileMediaEditableWhenLocked(activeSectionId)) ||
    activeSectionId === nextSectionId ||
    !dirtySectionIds.includes(activeSectionId)
  ) {
    return {
      canSwitch: true,
      activeSectionId: nextSectionId,
      pendingSectionId: null,
    };
  }

  return {
    canSwitch: false,
    activeSectionId,
    pendingSectionId: nextSectionId,
  };
}

export function markTripProfileSectionDirty({
  canEdit,
  dirtySectionIds,
  locked,
  sectionId,
}: {
  canEdit: boolean;
  dirtySectionIds: TripProfileSectionId[];
  locked: boolean;
  sectionId: TripProfileSectionId;
}): TripProfileSectionId[] {
  if (
    (locked && !isTripProfileMediaEditableWhenLocked(sectionId)) ||
    !canEdit ||
    dirtySectionIds.includes(sectionId)
  ) {
    return dirtySectionIds;
  }

  return [...dirtySectionIds, sectionId];
}

export function setTripProfileSectionDirtyState({
  canEdit,
  dirty,
  dirtySectionIds,
  locked,
  sectionId,
}: {
  canEdit: boolean;
  dirty: boolean;
  dirtySectionIds: TripProfileSectionId[];
  locked: boolean;
  sectionId: TripProfileSectionId;
}): TripProfileSectionId[] {
  if (!dirty) {
    return dirtySectionIds.filter((id) => id !== sectionId);
  }

  return markTripProfileSectionDirty({
    canEdit,
    dirtySectionIds,
    locked,
    sectionId,
  });
}

export function saveTripProfileSection({
  dirtySectionIds,
  sectionId,
}: {
  dirtySectionIds: TripProfileSectionId[];
  sectionId: TripProfileSectionId;
}): {
  dirtySectionIds: TripProfileSectionId[];
  saved: boolean;
} {
  return {
    dirtySectionIds: dirtySectionIds.filter((id) => id !== sectionId),
    saved: dirtySectionIds.includes(sectionId),
  };
}

export function tripProfileSectionNeedsReview({
  confirmationRequirementsReviewed,
  paymentScheduleReviewed,
  sectionId,
}: {
  confirmationRequirementsReviewed: boolean;
  paymentScheduleReviewed: boolean;
  sectionId: TripProfileSectionId;
}): boolean {
  return (
    (sectionId === "payment-schedule" && !paymentScheduleReviewed) ||
    (sectionId === "requirements" && !confirmationRequirementsReviewed)
  );
}

export function canSubmitTripProfileSection({
  busy,
  confirmationRequirementsReviewed,
  dirty,
  editable,
  locked,
  paymentScheduleReviewed,
  sectionId,
}: {
  busy: boolean;
  confirmationRequirementsReviewed: boolean;
  dirty: boolean;
  editable: boolean;
  locked: boolean;
  paymentScheduleReviewed: boolean;
  sectionId: TripProfileSectionId;
}): boolean {
  const profileLocked =
    locked && !isTripProfileMediaEditableWhenLocked(sectionId);

  if (busy || profileLocked || !editable) {
    return false;
  }

  return (
    dirty ||
    tripProfileSectionNeedsReview({
      confirmationRequirementsReviewed,
      paymentScheduleReviewed,
      sectionId,
    })
  );
}

export function discardTripProfileSectionChanges({
  dirtySectionIds,
  sectionId,
}: {
  dirtySectionIds: TripProfileSectionId[];
  sectionId: TripProfileSectionId;
}): TripProfileSectionId[] {
  return dirtySectionIds.filter((id) => id !== sectionId);
}

function buildSectionState({
  confirmationRequirementsReviewed,
  descriptionEmpty,
  itineraryEmpty,
  packagesEmpty,
  paymentScheduleReviewed,
  publicMediaCount,
  locked,
  role,
  section,
}: {
  confirmationRequirementsReviewed: boolean;
  descriptionEmpty: boolean;
  itineraryEmpty: boolean;
  packagesEmpty: boolean;
  paymentScheduleReviewed: boolean;
  publicMediaCount: number;
  locked: boolean;
  role: TripProfileRole;
  section: TripProfileSectionDefinition;
}): TripProfileSectionState {
  const editability = getTripProfileSectionEditability({
    locked,
    role,
    sectionId: section.id,
  });

  if (locked) {
    if (isTripProfileMediaEditableWhenLocked(section.id)) {
      const state = unlockedSectionState(section.id, {
        descriptionEmpty,
        itineraryEmpty,
        packagesEmpty,
        confirmationRequirementsReviewed,
        paymentScheduleReviewed,
        publicMediaCount,
      });

      return {
        ...section,
        editable: editability.editable,
        locked: true,
        readonlyReason: editability.reason,
        stateLabel: editability.editable ? state.label : "Owner-managed",
        tone: editability.editable ? state.tone : "readonly",
      };
    }

    return {
      ...section,
      editable: false,
      locked: true,
      readonlyReason: editability.reason,
      stateLabel: "Locked",
      tone: "readonly",
    };
  }

  const state = unlockedSectionState(section.id, {
    descriptionEmpty,
    itineraryEmpty,
    packagesEmpty,
    confirmationRequirementsReviewed,
    paymentScheduleReviewed,
    publicMediaCount,
  });

  return {
    ...section,
    editable: editability.editable,
    locked: false,
    readonlyReason: editability.reason,
    stateLabel: editability.editable ? state.label : "Owner-managed",
    tone: editability.editable ? state.tone : "readonly",
  };
}

function buildTripProfileBlockers({
  confirmationRequirementsReviewed,
  descriptionEmpty,
  itineraryEmpty,
  packagesEmpty,
  paymentScheduleReviewed,
}: {
  confirmationRequirementsReviewed: boolean;
  descriptionEmpty: boolean;
  itineraryEmpty: boolean;
  packagesEmpty: boolean;
  paymentScheduleReviewed: boolean;
}): TripProfileReadinessItem[] {
  return [
    ...(descriptionEmpty
      ? [
          {
            id: "description",
            label: "Trip Description",
            detail: "Add traveler-facing trip details.",
            sectionId: "description" as const,
            tone: "blocked" as const,
          },
        ]
      : []),
    ...(itineraryEmpty
      ? [
          {
            id: "itinerary",
            label: "Itinerary Days",
            detail: "Add at least one structured Itinerary Day.",
            sectionId: "itinerary" as const,
            tone: "blocked" as const,
          },
        ]
      : []),
    ...(packagesEmpty
      ? [
          {
            id: "packages",
            label: "Packages",
            detail: "Add at least one active Package.",
            sectionId: "packages" as const,
            tone: "blocked" as const,
          },
        ]
      : []),
    ...(!paymentScheduleReviewed
      ? [
          {
            id: "payment-schedule",
            label: "Balance payment schedule",
            detail: "Owner review required before publication.",
            sectionId: "payment-schedule" as const,
            tone: "blocked" as const,
          },
        ]
      : []),
    ...(!confirmationRequirementsReviewed
      ? [
          {
            id: "requirements",
            label: "Confirmation Requirements",
            detail: "Review traveler readiness requirements.",
            sectionId: "requirements" as const,
            tone: "blocked" as const,
          },
        ]
      : []),
  ];
}

function mapTripProfilePublicationReadiness(
  readiness: TripProfilePublicationReadinessDecision | undefined,
  fallback: {
    blockers: TripProfileReadinessItem[];
    encouraged: TripProfileReadinessItem[];
  },
): {
  blockers: TripProfileReadinessItem[];
  encouraged: TripProfileReadinessItem[];
  publishEligible: boolean;
} {
  if (!readiness) {
    return {
      blockers: fallback.blockers,
      encouraged: fallback.encouraged,
      publishEligible: fallback.blockers.length === 0,
    };
  }

  const blockers = readiness.blockers.map(mapTripProfilePublicationReadinessItem);
  const encouraged = readiness.encouraged.map(mapTripProfilePublicationReadinessItem);

  return {
    blockers,
    encouraged,
    publishEligible: readiness.publishEligible,
  };
}

function mapTripProfilePublicationReadinessItem(
  item: TripProfilePublicationReadinessDecision["blockers"][number],
): TripProfileReadinessItem {
  return {
    id: item.id,
    label: item.label,
    detail: item.detail,
    sectionId: normalizeReadinessSectionId(item.sectionId),
    tone: item.blocking ? "blocked" : item.tone,
  };
}

function normalizeReadinessSectionId(value: string): TripProfileSectionId {
  return TRIP_PROFILE_SECTIONS.some((section) => section.id === value)
    ? (value as TripProfileSectionId)
    : "description";
}

function unlockedSectionState(
  sectionId: TripProfileSectionId,
  {
    descriptionEmpty,
    itineraryEmpty,
    packagesEmpty,
    confirmationRequirementsReviewed,
    paymentScheduleReviewed,
    publicMediaCount,
  }: {
    descriptionEmpty: boolean;
    itineraryEmpty: boolean;
    packagesEmpty: boolean;
    confirmationRequirementsReviewed: boolean;
    paymentScheduleReviewed: boolean;
    publicMediaCount: number;
  },
): { label: string; tone: TripProfileTone } {
  switch (sectionId) {
    case "description":
      return descriptionEmpty
        ? { label: "Needed", tone: "blocked" }
        : { label: "Ready", tone: "clear" };
    case "itinerary":
      return itineraryEmpty
        ? { label: "Needed", tone: "blocked" }
        : { label: "Ready", tone: "clear" };
    case "packages":
      return packagesEmpty
        ? { label: "Needed", tone: "blocked" }
        : { label: "Ready", tone: "clear" };
    case "payment-schedule":
      return paymentScheduleReviewed
        ? { label: "Reviewed", tone: "clear" }
        : { label: "Review needed", tone: "blocked" };
    case "media":
      return publicMediaCount > 0
        ? { label: "Ready", tone: "clear" }
        : { label: "Encouraged", tone: "attention" };
    case "requirements":
      return confirmationRequirementsReviewed
        ? { label: "Reviewed", tone: "clear" }
        : { label: "Review needed", tone: "blocked" };
    default:
      return { label: "Needed", tone: "blocked" };
  }
}

function positiveInteger(value: unknown, fallback: number): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 1) {
    return fallback;
  }
  return value;
}

function nonNegativeInteger(value: unknown, fallback: number): number {
  if (typeof value !== "number" || !Number.isInteger(value) || value < 0) {
    return fallback;
  }
  return value;
}

function normalizeTripMediaImageUrl(imageUrl: string): string {
  if (!imageUrl || /^(https?:|data:|blob:)/i.test(imageUrl)) {
    return imageUrl;
  }
  return drfApiUrl(imageUrl.startsWith("/") ? imageUrl : `/${imageUrl}`);
}

function booleanValue(value: unknown): boolean {
  return typeof value === "boolean" ? value : false;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
