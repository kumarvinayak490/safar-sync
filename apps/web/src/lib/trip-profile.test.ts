import assert from "node:assert/strict";
import test from "node:test";

import {
  buildTripProfileShellModel,
  canSubmitTripProfileSection,
  countTripProfileReadySections,
  discardTripProfileSectionChanges,
  getTripProfileSectionEditability,
  markTripProfileSectionDirty,
  normalizeTripItineraryDays,
  normalizeTripConfirmationRequirements,
  normalizeTripMediaItems,
  normalizeTripPackages,
  normalizeTripPaymentSchedule,
  resolveTripProfileSectionSwitch,
  saveTripProfileSection,
  setTripProfileSectionDirtyState,
  shouldWarnBeforeLeavingTripProfile,
  tripProfileSectionNeedsReview,
  validateTripPaymentSchedule,
  validateTripProfilePackages,
  type TripProfileSectionId,
} from "./trip-profile.ts";
import {
  editableBlocksToTripRichText,
  getTripRichTextPlainText,
  normalizeTripRichText,
  tiptapJsonToTripRichText,
  tripRichTextToHtml,
  tripRichTextToRenderBlocks,
  tripRichTextValidationErrors,
} from "./trip-rich-text.ts";
import type { WorkspaceTrip } from "./workspace.ts";

test("Trip Profile shell exposes stable section navigation state", () => {
  const model = buildTripProfileShellModel({
    role: "owner",
    trip: workspaceTrip({ publicationState: "draft", publicationReady: false }),
  });

  assert.deepEqual(
    model.sections.map((section) => ({
      id: section.id,
      label: section.label,
      dense: section.dense,
      editable: section.editable,
      stateLabel: section.stateLabel,
    })),
    [
      {
        id: "description",
        label: "Description",
        dense: false,
        editable: true,
        stateLabel: "Needed",
      },
      {
        id: "itinerary",
        label: "Itinerary",
        dense: true,
        editable: true,
        stateLabel: "Needed",
      },
      {
        id: "media",
        label: "Media",
        dense: false,
        editable: true,
        stateLabel: "Encouraged",
      },
      {
        id: "packages",
        label: "Packages",
        dense: true,
        editable: true,
        stateLabel: "Ready",
      },
      {
        id: "payment-schedule",
        label: "Balance payment schedule",
        dense: true,
        editable: true,
        stateLabel: "Review needed",
      },
      {
        id: "requirements",
        label: "Requirements",
        dense: true,
        editable: true,
        stateLabel: "Review needed",
      },
    ],
  );
  assert.deepEqual(
    model.blockers.map((item) => item.sectionId),
    ["description", "itinerary", "payment-schedule", "requirements"],
  );
  assert.deepEqual(
    model.encouraged.map((item) => item.sectionId),
    ["media"],
  );
  assert.equal(model.publicationReady, false);
});

test("Trip Profile role editability keeps commercial sections Owner-managed", () => {
  assert.deepEqual(
    getTripProfileSectionEditability({
      locked: false,
      role: "operator",
      sectionId: "packages",
    }),
    { editable: false, reason: "Owner-managed section" },
  );
  assert.deepEqual(
    getTripProfileSectionEditability({
      locked: false,
      role: "operator",
      sectionId: "requirements",
    }),
    { editable: true, reason: "" },
  );
});

test("Trip Description readiness clears when structured rich text has content", () => {
  const model = buildTripProfileShellModel({
    role: "operator",
    trip: workspaceTrip({
      descriptionRichText: richTextDocument("Traveler-facing Spiti details."),
      publicationState: "draft",
      publicationReady: false,
    }),
  });

  const descriptionSection = model.sections.find(
    (section) => section.id === "description",
  );

  assert.equal(descriptionSection?.stateLabel, "Ready");
  assert.equal(descriptionSection?.tone, "clear");
  assert.deepEqual(
    model.blockers.map((item) => item.sectionId),
    ["itinerary", "payment-schedule", "requirements"],
  );
});

test("Itinerary Day readiness clears when structured days are present", () => {
  const model = buildTripProfileShellModel({
    role: "operator",
    trip: workspaceTrip({
      descriptionRichText: richTextDocument("Traveler-facing Spiti details."),
      itineraryDays: [
        {
          id: 9,
          sequence: 2,
          title: "Field day",
          date_label: "Day 2",
          description_rich_text: richTextDocument("High valley field work."),
          description_plain_text: "High valley field work.",
        },
        {
          id: 8,
          sequence: 1,
          title: "Arrival",
          date_label: "Day 1",
          description_rich_text: richTextDocument("Meet the group."),
        },
      ],
      publicationState: "draft",
      publicationReady: false,
    }),
  });

  const itinerarySection = model.sections.find(
    (section) => section.id === "itinerary",
  );

  assert.equal(model.itinerary.empty, false);
  assert.equal(model.itinerary.days[0]?.title, "Arrival");
  assert.equal(itinerarySection?.stateLabel, "Ready");
  assert.equal(itinerarySection?.tone, "clear");
  assert.deepEqual(
    model.blockers.map((item) => item.sectionId),
    ["payment-schedule", "requirements"],
  );
});

test("Itinerary Day normalizer preserves rich text and strips invalid rows", () => {
  const days = normalizeTripItineraryDays([
    {
      id: 3,
      sequence: 2,
      title: "  Field day  ",
      date_label: " Day 2 ",
      description_rich_text: richTextDocument("Field work."),
    },
    {
      id: 2,
      sequence: 1,
      title: "Arrival",
      description_rich_text: {
        type: "doc",
        content: [
          { type: "image", attrs: { src: "https://example.test/photo.jpg" } },
        ],
      },
    },
    {
      id: 1,
      sequence: 3,
      title: " ",
      description_rich_text: richTextDocument("Ignored."),
    },
  ]);

  assert.deepEqual(
    days.map((day) => ({
      sequence: day.sequence,
      title: day.title,
      dateLabel: day.dateLabel,
      descriptionPlainText: day.descriptionPlainText,
    })),
    [
      {
        sequence: 1,
        title: "Arrival",
        dateLabel: "",
        descriptionPlainText: "",
      },
      {
        sequence: 2,
        title: "Field day",
        dateLabel: "Day 2",
        descriptionPlainText: "Field work.",
      },
    ],
  );
});

test("Trip Package normalizer sorts rows and strips invalid packages", () => {
  const packages = normalizeTripPackages([
    {
      id: 9,
      position: 2,
      name: "  Premium room  ",
      description: " Twin sharing ",
      price_inr: 42000,
      reservation_amount_inr: 12000,
    },
    {
      id: 8,
      position: 1,
      name: "Standard",
      priceInr: 32000,
      reservationAmountInr: 8000,
    },
    {
      id: 7,
      name: "Missing money",
      price_inr: 0,
      reservation_amount_inr: 0,
    },
  ]);

  assert.deepEqual(
    packages.map((tripPackage) => ({
      id: tripPackage.id,
      name: tripPackage.name,
      description: tripPackage.description,
      priceInr: tripPackage.priceInr,
      reservationAmountInr: tripPackage.reservationAmountInr,
      position: tripPackage.position,
    })),
    [
      {
        id: 8,
        name: "Standard",
        description: "",
        priceInr: 32000,
        reservationAmountInr: 8000,
        position: 1,
      },
      {
        id: 9,
        name: "Premium room",
        description: "Twin sharing",
        priceInr: 42000,
        reservationAmountInr: 12000,
        position: 2,
      },
    ],
  );
});

test("Trip Media normalizer sorts gallery rows and maps metadata", () => {
  const mediaItems = normalizeTripMediaItems([
    {
      id: 12,
      asset_id: 5,
      image_url: "/media/trip-media/two.webp",
      original_filename: " two.webp ",
      content_type: "image/webp",
      file_size: 2048,
      position: 2,
      caption: "  High valley trail  ",
      alt_text: " Travelers walking ",
      is_public: true,
      is_cover: false,
    },
    {
      id: 11,
      assetId: 4,
      imageUrl: "media/trip-media/cover.png",
      originalFilename: "cover.png",
      contentType: "image/png",
      fileSize: 1024,
      position: 1,
      caption: "Cover image",
      altText: "Snowline approach",
      isPublic: false,
      isCover: true,
    },
    {
      id: 10,
      image_url: "",
      position: 3,
    },
  ]);

  assert.deepEqual(
    mediaItems.map((item) => ({
      id: item.id,
      imageUrl: item.imageUrl,
      caption: item.caption,
      altText: item.altText,
      isPublic: item.isPublic,
      isCover: item.isCover,
      position: item.position,
    })),
    [
      {
        id: 11,
        imageUrl: "http://localhost:8000/media/trip-media/cover.png",
        caption: "Cover image",
        altText: "Snowline approach",
        isPublic: false,
        isCover: true,
        position: 1,
      },
      {
        id: 12,
        imageUrl: "http://localhost:8000/media/trip-media/two.webp",
        caption: "High valley trail",
        altText: "Travelers walking",
        isPublic: true,
        isCover: false,
        position: 2,
      },
    ],
  );
});

test("Trip Media readiness is encouraged without blocking publication", () => {
  const noMedia = buildTripProfileShellModel({
    role: "operator",
    trip: workspaceTrip({
      descriptionRichText: richTextDocument("Traveler-facing Spiti details."),
      itineraryDays: [
        {
          id: 8,
          sequence: 1,
          title: "Arrival",
          description_rich_text: richTextDocument("Meet the group."),
        },
      ],
      paymentSchedule: {
        has_balance_milestone: true,
        balance_due_days_before_start: 14,
        balance_reminder_lead_days: 3,
        reviewed: true,
      },
      confirmationRequirements: {
        reviewed: true,
      },
      mediaItems: [],
      publicationState: "draft",
      publicationReady: false,
    }),
  });
  const publicMedia = buildTripProfileShellModel({
    role: "operator",
    trip: workspaceTrip({
      descriptionRichText: richTextDocument("Traveler-facing Spiti details."),
      itineraryDays: [
        {
          id: 8,
          sequence: 1,
          title: "Arrival",
          description_rich_text: richTextDocument("Meet the group."),
        },
      ],
      paymentSchedule: {
        has_balance_milestone: true,
        balance_due_days_before_start: 14,
        balance_reminder_lead_days: 3,
        reviewed: true,
      },
      confirmationRequirements: {
        reviewed: true,
      },
      mediaItems: [
        {
          id: 3,
          image_url: "/media/trip-media/cover.png",
          position: 1,
          is_public: true,
          is_cover: true,
        },
      ],
      publicationState: "draft",
      publicationReady: false,
    }),
  });

  assert.equal(noMedia.publicationReady, true);
  assert.deepEqual(
    noMedia.encouraged.map((item) => item.sectionId),
    ["media"],
  );
  assert.equal(
    noMedia.sections.find((section) => section.id === "media")?.stateLabel,
    "Encouraged",
  );
  assert.equal(publicMedia.media.publicCount, 1);
  assert.deepEqual(publicMedia.encouraged, []);
  assert.equal(
    publicMedia.sections.find((section) => section.id === "media")?.stateLabel,
    "Ready",
  );
});

test("Trip Package validation blocks empty catalog and invalid money", () => {
  assert.deepEqual(validateTripProfilePackages([]), {
    ok: false,
    formErrors: ["At least one active Package is required."],
    rowErrors: {},
  });

  const result = validateTripProfilePackages([
    {
      clientId: "package-a",
      id: 1,
      name: " ",
      description: "",
      priceInr: 0,
      reservationAmountInr: 1000,
      position: 1,
    },
    {
      clientId: "package-b",
      id: 2,
      name: "Premium",
      description: "",
      priceInr: 12000,
      reservationAmountInr: 15000,
      position: 2,
    },
  ]);

  assert.equal(result.ok, false);
  assert.deepEqual(result.formErrors, []);
  assert.deepEqual(result.rowErrors, {
    "package-a": {
      name: "Package name is required.",
      priceInr: "Enter a Package price greater than 0.",
    },
    "package-b": {
      reservationAmountInr: "Reservation Amount cannot exceed Package price.",
    },
  });
});

test("Package readiness contributes to Trip Profile Publication Readiness", () => {
  const model = buildTripProfileShellModel({
    role: "owner",
    trip: workspaceTrip({
      packages: [],
      publicationState: "draft",
      publicationReady: false,
    }),
  });

  const packagesSection = model.sections.find(
    (section) => section.id === "packages",
  );

  assert.equal(model.packages.empty, true);
  assert.equal(packagesSection?.stateLabel, "Needed");
  assert.equal(packagesSection?.tone, "blocked");
  assert.equal(
    model.blockers.some((item) => item.sectionId === "packages"),
    true,
  );
});

test("Payment Schedule review contributes to Trip Profile Publication Readiness", () => {
  const unreviewed = buildTripProfileShellModel({
    role: "owner",
    trip: workspaceTrip({
      publicationState: "draft",
      publicationReady: false,
      paymentSchedule: {
        has_balance_milestone: true,
        balance_due_days_before_start: 14,
        balance_reminder_lead_days: 3,
        reviewed: false,
      },
    }),
  });
  const reviewed = buildTripProfileShellModel({
    role: "owner",
    trip: workspaceTrip({
      descriptionRichText: richTextDocument("Traveler-facing Spiti details."),
      itineraryDays: [
        {
          id: 8,
          sequence: 1,
          title: "Arrival",
          description_rich_text: richTextDocument("Meet the group."),
        },
      ],
      publicationState: "draft",
      publicationReady: false,
      paymentSchedule: {
        has_balance_milestone: true,
        balance_due_days_before_start: 14,
        balance_due_date: "2026-09-26",
        balance_reminder_lead_days: 3,
        reviewed: true,
      },
    }),
  });

  assert.equal(unreviewed.paymentSchedule.reviewed, false);
  assert.equal(
    unreviewed.blockers.some((item) => item.sectionId === "payment-schedule"),
    true,
  );
  assert.equal(
    unreviewed.sections.find((section) => section.id === "payment-schedule")
      ?.stateLabel,
    "Review needed",
  );
  assert.equal(reviewed.paymentSchedule.balanceDueDate, "2026-09-26");
  assert.equal(
    reviewed.blockers.some((item) => item.sectionId === "payment-schedule"),
    false,
  );
  assert.equal(
    reviewed.sections.find((section) => section.id === "payment-schedule")
      ?.stateLabel,
    "Reviewed",
  );
});

test("Confirmation Requirements review contributes to Trip Profile Publication Readiness", () => {
  const unreviewed = buildTripProfileShellModel({
    role: "operator",
    trip: workspaceTrip({
      publicationState: "draft",
      publicationReady: false,
      confirmationRequirements: {
        requires_traveler_documents: true,
        requires_traveler_identity_details: true,
        reviewed: false,
      },
    }),
  });
  const reviewed = buildTripProfileShellModel({
    role: "operator",
    trip: workspaceTrip({
      descriptionRichText: richTextDocument("Traveler-facing Spiti details."),
      itineraryDays: [
        {
          id: 8,
          sequence: 1,
          title: "Arrival",
          description_rich_text: richTextDocument("Meet the group."),
        },
      ],
      paymentSchedule: {
        has_balance_milestone: true,
        balance_due_days_before_start: 14,
        balance_reminder_lead_days: 3,
        reviewed: true,
      },
      publicationState: "draft",
      publicationReady: false,
      confirmationRequirements: {
        requires_traveler_documents: true,
        requires_emergency_contact: true,
        reviewed: true,
      },
    }),
  });

  assert.equal(unreviewed.confirmationRequirements.travelerDocuments, true);
  assert.equal(
    unreviewed.blockers.some((item) => item.sectionId === "requirements"),
    true,
  );
  assert.equal(
    unreviewed.sections.find((section) => section.id === "requirements")
      ?.stateLabel,
    "Review needed",
  );
  assert.equal(reviewed.confirmationRequirements.emergencyContact, true);
  assert.equal(
    reviewed.blockers.some((item) => item.sectionId === "requirements"),
    false,
  );
  assert.equal(
    reviewed.sections.find((section) => section.id === "requirements")
      ?.stateLabel,
    "Reviewed",
  );
  assert.equal(reviewed.publicationReady, true);
});

test("Confirmation Requirements normalizer maps API flags to UI state", () => {
  assert.deepEqual(
    normalizeTripConfirmationRequirements({
      requires_traveler_documents: true,
      requires_traveler_identity_details: true,
      requires_travel_logistics: false,
      requires_emergency_contact: true,
      requires_medical_disclosure: false,
      requires_full_payment_before_confirmation: true,
      confirmation_requirements_reviewed: true,
    }),
    {
      travelerDocuments: true,
      travelerIdentityDetails: true,
      travelLogistics: false,
      emergencyContact: true,
      medicalDisclosure: false,
      fullPaymentBeforeConfirmation: true,
      reviewed: true,
    },
  );
});

test("Trip Profile review-only blockers can be submitted without local edits", () => {
  assert.equal(
    tripProfileSectionNeedsReview({
      confirmationRequirementsReviewed: true,
      paymentScheduleReviewed: false,
      sectionId: "payment-schedule",
    }),
    true,
  );
  assert.equal(
    canSubmitTripProfileSection({
      busy: false,
      confirmationRequirementsReviewed: true,
      dirty: false,
      editable: true,
      locked: false,
      paymentScheduleReviewed: false,
      sectionId: "payment-schedule",
    }),
    true,
  );
  assert.equal(
    canSubmitTripProfileSection({
      busy: false,
      confirmationRequirementsReviewed: false,
      dirty: false,
      editable: true,
      locked: false,
      paymentScheduleReviewed: true,
      sectionId: "requirements",
    }),
    true,
  );
  assert.equal(
    canSubmitTripProfileSection({
      busy: false,
      confirmationRequirementsReviewed: true,
      dirty: false,
      editable: true,
      locked: false,
      paymentScheduleReviewed: true,
      sectionId: "payment-schedule",
    }),
    false,
  );
  assert.equal(
    canSubmitTripProfileSection({
      busy: false,
      confirmationRequirementsReviewed: true,
      dirty: false,
      editable: false,
      locked: false,
      paymentScheduleReviewed: false,
      sectionId: "payment-schedule",
    }),
    false,
  );
});

test("Payment Schedule normalizer and validation support no balance milestone", () => {
  assert.deepEqual(
    normalizeTripPaymentSchedule({
      has_balance_milestone: false,
      balance_due_days_before_start: 14,
      balance_reminder_lead_days: 0,
      reviewed: true,
    }),
    {
      hasBalanceMilestone: false,
      balanceDueDaysBeforeStart: null,
      balanceDueDate: null,
      balanceReminderLeadDays: 0,
      reviewed: true,
    },
  );
  assert.deepEqual(
    validateTripPaymentSchedule({
      hasBalanceMilestone: true,
      balanceDueDaysBeforeStart: 5,
      balanceReminderLeadDays: 8,
    }),
    {
      ok: false,
      errors: {
        balanceReminderLeadDays:
          "Reminder lead time cannot exceed final balance due days.",
      },
    },
  );
  assert.deepEqual(
    validateTripPaymentSchedule({
      hasBalanceMilestone: false,
      balanceDueDaysBeforeStart: null,
      balanceReminderLeadDays: 0,
    }),
    {
      ok: true,
      paymentSchedule: {
        hasBalanceMilestone: false,
        balanceDueDaysBeforeStart: null,
        balanceReminderLeadDays: 0,
      },
      errors: {},
    },
  );
});

test("Trip Rich Text normalizer strips unsupported content for rendering", () => {
  const normalized = normalizeTripRichText({
    type: "doc",
    content: [
      {
        type: "heading",
        attrs: { level: 1, class: "hero" },
        content: [{ type: "text", text: "Mountain week" }],
      },
      {
        type: "paragraph",
        attrs: { style: "color:red" },
        content: [
          {
            type: "text",
            text: "Bring layers.",
            marks: [
              { type: "bold" },
              { type: "link", attrs: { href: "javascript:alert(1)" } },
            ],
          },
          { type: "image", attrs: { src: "https://example.test/photo.jpg" } },
        ],
      },
      { type: "embed", attrs: { src: "https://example.test" } },
      {
        type: "callout",
        content: [
          {
            type: "paragraph",
            content: [
              {
                type: "text",
                text: "Valid link",
                marks: [
                  { type: "link", attrs: { href: "https://tripos.test/pack" } },
                ],
              },
            ],
          },
        ],
      },
    ],
  });

  assert.deepEqual(
    normalized.content.map((block) => block.type),
    ["heading", "paragraph", "callout"],
  );
  assert.equal(normalized.content[0]?.type, "heading");
  assert.equal(
    normalized.content[0]?.type === "heading"
      ? normalized.content[0].attrs.level
      : 0,
    2,
  );
  assert.deepEqual(
    tripRichTextToRenderBlocks(normalized).map((block) => block.type),
    ["heading", "paragraph", "callout"],
  );
  assert.equal(
    getTripRichTextPlainText(normalized),
    "Mountain week Bring layers. Valid link",
  );
  assert.deepEqual(tripRichTextValidationErrors("<h1>bad</h1>"), [
    "Trip Rich Text must be a structured JSON document.",
  ]);
});

test("Trip Description editable blocks serialize to constrained rich text", () => {
  const document = editableBlocksToTripRichText([
    {
      id: "block-1",
      type: "bullet_list",
      text: "Carry layers\nKeep payment acknowledgement",
      bold: true,
      italic: false,
      linkHref: "https://tripos.test/notes",
    },
    {
      id: "block-2",
      type: "paragraph",
      text: "javascript links are stripped",
      bold: false,
      italic: true,
      linkHref: "javascript:alert(1)",
    },
  ]);

  const blocks = tripRichTextToRenderBlocks(document);

  assert.equal(blocks[0]?.type, "bullet_list");
  assert.equal(blocks[1]?.type, "paragraph");
  assert.equal(
    blocks[0]?.type === "bullet_list" ? blocks[0].items.length : 0,
    2,
  );
  assert.deepEqual(
    blocks[1]?.type === "paragraph" ? blocks[1].inlines[0]?.marks : [],
    [{ type: "italic" }],
  );
});

test("TipTap editor JSON serializes to constrained Trip Rich Text", () => {
  const document = tiptapJsonToTripRichText({
    type: "doc",
    content: [
      {
        type: "heading",
        attrs: { level: 1 },
        content: [{ type: "text", text: "Kudremukh Trek" }],
      },
      {
        type: "paragraph",
        content: [
          {
            type: "text",
            text: "Cloud forest trail.",
            marks: [
              { type: "bold" },
              { type: "underline" },
              { type: "link", attrs: { href: "https://tripos.test/trips" } },
            ],
          },
          {
            type: "text",
            text: " Unsafe link.",
            marks: [{ type: "link", attrs: { href: "javascript:alert(1)" } }],
          },
        ],
      },
      {
        type: "bulletList",
        content: [
          {
            type: "listItem",
            content: [
              {
                type: "paragraph",
                content: [{ type: "text", text: "Carry rain gear" }],
              },
            ],
          },
        ],
      },
      {
        type: "table",
        content: [
          {
            type: "tableRow",
            content: [
              {
                type: "tableHeader",
                content: [
                  {
                    type: "paragraph",
                    content: [{ type: "text", text: "Day" }],
                  },
                ],
              },
              {
                type: "tableHeader",
                content: [
                  {
                    type: "paragraph",
                    content: [{ type: "text", text: "Plan" }],
                  },
                ],
              },
            ],
          },
        ],
      },
    ],
  });

  assert.deepEqual(
    tripRichTextToRenderBlocks(document).map((block) => block.type),
    ["heading", "paragraph", "bullet_list", "paragraph"],
  );
  assert.equal(
    getTripRichTextPlainText(document),
    "Kudremukh Trek Cloud forest trail. Unsafe link. Carry rain gear Day | Plan",
  );
  assert.match(tripRichTextToHtml(document), /<h2>Kudremukh Trek<\/h2>/);
  assert.match(
    tripRichTextToHtml(document),
    /href="https:\/\/tripos.test\/trips"/,
  );
  assert.doesNotMatch(tripRichTextToHtml(document), /javascript/);
});

test("Trip Profile warns before switching away from a dirty active section", () => {
  assert.deepEqual(
    resolveTripProfileSectionSwitch({
      activeSectionId: "description",
      dirtySectionIds: ["description"],
      locked: false,
      nextSectionId: "itinerary",
    }),
    {
      canSwitch: false,
      activeSectionId: "description",
      pendingSectionId: "itinerary",
    },
  );

  assert.deepEqual(
    resolveTripProfileSectionSwitch({
      activeSectionId: "description",
      dirtySectionIds: ["itinerary"],
      locked: false,
      nextSectionId: "media",
    }),
    {
      canSwitch: true,
      activeSectionId: "media",
      pendingSectionId: null,
    },
  );
});

test("Trip Profile dirty state is local to each section save affordance", () => {
  const dirty = markTripProfileSectionDirty({
    canEdit: true,
    dirtySectionIds: ["itinerary"],
    locked: false,
    sectionId: "description",
  });

  assert.deepEqual(dirty, ["itinerary", "description"]);
  assert.deepEqual(
    saveTripProfileSection({
      dirtySectionIds: dirty,
      sectionId: "description",
    }),
    {
      dirtySectionIds: ["itinerary"],
      saved: true,
    },
  );
  assert.deepEqual(
    discardTripProfileSectionChanges({
      dirtySectionIds: dirty,
      sectionId: "itinerary",
    }),
    ["description"],
  );
});

test("Trip Profile dirty state clears when a section returns to its saved value", () => {
  const dirty = setTripProfileSectionDirtyState({
    canEdit: true,
    dirty: true,
    dirtySectionIds: [],
    locked: false,
    sectionId: "description",
  });

  assert.deepEqual(dirty, ["description"]);
  assert.deepEqual(
    setTripProfileSectionDirtyState({
      canEdit: true,
      dirty: false,
      dirtySectionIds: dirty,
      locked: false,
      sectionId: "description",
    }),
    [],
  );
  assert.deepEqual(
    setTripProfileSectionDirtyState({
      canEdit: false,
      dirty: true,
      dirtySectionIds: [],
      locked: false,
      sectionId: "packages",
    }),
    [],
  );
});

test("Trip Profile leave warnings depend on unsaved editable changes", () => {
  const dirty: TripProfileSectionId[] = ["description"];

  assert.equal(
    shouldWarnBeforeLeavingTripProfile({
      dirtySectionIds: dirty,
      locked: false,
    }),
    true,
  );
  assert.equal(
    shouldWarnBeforeLeavingTripProfile({
      dirtySectionIds: dirty,
      locked: true,
    }),
    false,
  );
  assert.deepEqual(
    markTripProfileSectionDirty({
      canEdit: false,
      dirtySectionIds: [],
      locked: false,
      sectionId: "packages",
    }),
    [],
  );
});

test("Published and archived Trip Profiles render as locked read-only shell state", () => {
  for (const publicationState of ["published", "archived"] as const) {
    for (const role of ["owner", "operator"] as const) {
      const model = buildTripProfileShellModel({
        role,
        trip: workspaceTrip({
          publicationState,
          publicationReady: true,
        }),
      });

      assert.equal(model.locked, true);
      assert.equal(model.lockLabel, "Published Trip Profile Lock");
      assert.equal(model.publicationReady, true);
      assert.deepEqual(model.blockers, []);
      assert.deepEqual(model.encouraged, []);
      assert.equal(
        countTripProfileReadySections(model.sections),
        model.sections.length - 1,
      );
      assert.equal(model.roleLabel, role === "owner" ? "Owner" : "Operator");
      assert.equal(
        model.sections.every(
          (section) =>
            section.id === "media"
              ? section.editable &&
                section.locked &&
                section.readonlyReason === ""
              : !section.editable &&
                section.locked &&
                section.readonlyReason === "Published Trip Profile Lock",
        ),
        true,
      );
    }
  }
});

function workspaceTrip({
  descriptionRichText = emptyRichTextDocument(),
  itineraryDays = [],
  packages = [
    {
      id: 3,
      name: "Standard shared room",
      description: "",
      priceInr: 32000,
      reservationAmountInr: 8000,
      position: 1,
    },
  ],
  mediaItems = [],
  paymentSchedule = {
    hasBalanceMilestone: true,
    balanceDueDaysBeforeStart: 14,
    balanceDueDate: "2026-09-26",
    balanceReminderLeadDays: 3,
    reviewed: false,
  },
  confirmationRequirements = {
    travelerDocuments: false,
    travelerIdentityDetails: false,
    travelLogistics: false,
    emergencyContact: false,
    medicalDisclosure: false,
    fullPaymentBeforeConfirmation: false,
    reviewed: false,
  },
  publicationReady,
  publicationState,
}: {
  descriptionRichText?: WorkspaceTrip["descriptionRichText"];
  itineraryDays?: unknown[];
  packages?: WorkspaceTrip["packages"];
  mediaItems?: unknown[];
  paymentSchedule?: unknown;
  confirmationRequirements?: unknown;
  publicationReady: boolean;
  publicationState: string;
}): WorkspaceTrip {
  return {
    id: 7,
    title: "Spiti Winter Field Week",
    startDate: "2026-10-10",
    endDate: "2026-10-15",
    capacity: 24,
    availableSeats: 24,
    descriptionRichText,
    itinerary: "Day 1: Chandigarh arrival.",
    itineraryDays: normalizeTripItineraryDays(itineraryDays),
    mediaItems: normalizeTripMediaItems(mediaItems),
    packages,
    paymentSchedule: normalizeTripPaymentSchedule(paymentSchedule),
    confirmationRequirements: normalizeTripConfirmationRequirements(
      confirmationRequirements,
    ),
    publicationState,
    bookingAvailability: "closed",
    manualPaymentAvailability: "closed",
    effectiveBookingAvailability: "closed",
    publicUrlPath: "/trips/himalayan-monsoon-cohort/spiti-winter-field-week",
    launchReadiness: {
      ctaEnabled: false,
      ready: false,
      reasonCode: "booking_closed",
      requestedSeats: 1,
      publicationReady,
      bookingAvailabilityOpen: false,
      paymentMethodReadinessReady: false,
      paymentMethodReadinessStatusLabel: "Blocked",
      readyPaymentMethodCount: 0,
      readyPaymentMethodIds: [],
      paymentMethods: paymentMethodsFixture(false),
      providerPaymentMethod: paymentMethodsFixture(false)[0],
      manualPaymentMethod: paymentMethodsFixture(false)[1],
      onlinePaymentReadinessReady: false,
      onlinePaymentReadinessStatusLabel: "Blocked",
      onlinePaymentReadinessMessage:
        "Provider verification must be verified before public booking can open.",
      providerPaymentSetupComplete: false,
      capacityAvailable: true,
      availableSeats: 24,
      activeSeatHolds: 0,
      bookableSeats: 24,
      bookingAvailability: "closed",
      bookingAvailabilityLabel: "Closed",
      effectiveBookingAvailability: "closed",
      effectiveBookingAvailabilityLabel: "Closed",
      availabilityBand: "available",
      availabilityBandLabel: "Available",
      ctaState: "disabled",
      message: "Public booking is closed.",
    },
    tripProfilePublicationReadiness: tripProfilePublicationReadiness({
      confirmationRequirements: normalizeTripConfirmationRequirements(
        confirmationRequirements,
      ),
      descriptionRichText,
      itineraryDays: normalizeTripItineraryDays(itineraryDays),
      mediaItems: normalizeTripMediaItems(mediaItems),
      packages: packages ?? [],
      paymentSchedule: normalizeTripPaymentSchedule(paymentSchedule),
    }),
  };
}

function paymentMethodsFixture(onlineReady: boolean) {
  return [
    {
      id: "provider_payments",
      label: "Online payments",
      methodType: "provider_payment",
      ready: onlineReady,
      statusLabel: onlineReady ? "Ready" : "Blocked",
      blockerCode: onlineReady ? "ready" : "online_payment_readiness_blocked",
      blockerLabel: onlineReady ? "Ready" : "Online Payment Readiness blocked",
      message: onlineReady
        ? "Online payments are ready for public booking."
        : "Provider verification must be verified before public booking can open.",
      actionLabel: "Pay online",
      provider: "razorpay",
      providerLabel: "Razorpay",
      onlinePaymentReadinessReady: onlineReady,
      manualPaymentInstructionsReady: null,
      manualPaymentAvailabilityOpen: null,
      requiresReview: false,
    },
    {
      id: "qr_manual_payments",
      label: "Manual Payments",
      methodType: "qr_manual_payment",
      ready: false,
      statusLabel: "Blocked",
      blockerCode: "manual_payment_instructions_missing",
      blockerLabel: "Manual Payment Instructions missing",
      message:
        "Manual Payments require Manual Payment Instructions before travelers can scan a Payment QR.",
      actionLabel: "Scan QR code to pay",
      provider: "",
      providerLabel: "",
      onlinePaymentReadinessReady: null,
      manualPaymentInstructionsReady: false,
      manualPaymentAvailabilityOpen: false,
      requiresReview: true,
    },
  ];
}

function tripProfilePublicationReadiness({
  confirmationRequirements,
  descriptionRichText,
  itineraryDays,
  mediaItems,
  packages,
  paymentSchedule,
}: Pick<
  WorkspaceTrip,
  | "confirmationRequirements"
  | "descriptionRichText"
  | "itineraryDays"
  | "mediaItems"
  | "packages"
  | "paymentSchedule"
>): WorkspaceTrip["tripProfilePublicationReadiness"] {
  const blockers = [
    ...(getTripRichTextPlainText(
      normalizeTripRichText(descriptionRichText),
    ).trim()
      ? []
      : [
          {
            id: "description",
            label: "Trip Description",
            detail: "Add traveler-facing trip details.",
            sectionId: "description",
            tone: "blocked" as const,
            blocking: true,
          },
        ]),
    ...(itineraryDays?.length
      ? []
      : [
          {
            id: "itinerary",
            label: "Itinerary Days",
            detail: "Add at least one structured Itinerary Day.",
            sectionId: "itinerary",
            tone: "blocked" as const,
            blocking: true,
          },
        ]),
    ...(packages?.length
      ? []
      : [
          {
            id: "packages",
            label: "Packages",
            detail: "Add at least one active Package.",
            sectionId: "packages",
            tone: "blocked" as const,
            blocking: true,
          },
        ]),
    ...(paymentSchedule.reviewed
      ? []
      : [
          {
            id: "payment-schedule",
            label: "Balance payment schedule",
            detail: "Owner review required before publication.",
            sectionId: "payment-schedule",
            tone: "blocked" as const,
            blocking: true,
          },
        ]),
    ...(confirmationRequirements.reviewed
      ? []
      : [
          {
            id: "requirements",
            label: "Confirmation Requirements",
            detail: "Review traveler readiness requirements.",
            sectionId: "requirements",
            tone: "blocked" as const,
            blocking: true,
          },
        ]),
  ];
  const encouraged = mediaItems?.some((item) => item.isPublic)
    ? []
    : [
        {
          id: "media-gallery",
          label: "Add public media",
          detail: "Media is encouraged for the Public Trip Page.",
          sectionId: "media",
          tone: "attention" as const,
          blocking: false,
        },
      ];

  return {
    blockers,
    encouraged,
    blockerCount: blockers.length,
    encouragedCount: encouraged.length,
    publishEligible: blockers.length === 0,
    lockAcknowledgementRequired: true,
  };
}

function emptyRichTextDocument(): WorkspaceTrip["descriptionRichText"] {
  return {
    type: "doc",
    content: [],
  };
}

function richTextDocument(text: string): WorkspaceTrip["descriptionRichText"] {
  return {
    type: "doc",
    content: [
      {
        type: "paragraph",
        content: [{ type: "text", text }],
      },
    ],
  };
}
