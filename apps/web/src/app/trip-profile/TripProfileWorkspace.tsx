"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  useTransition,
} from "react";
import {
  AlertCircle,
  ArrowDown,
  ArrowUp,
  CheckCircle2,
  ChevronDown,
  CircleDot,
  Image as ImageIcon,
  LockKeyhole,
  Plus,
  Save,
  Trash2,
  Upload,
} from "lucide-react";

import { RichTextEditor } from "@/components/RichTextEditor";
import { TripRichTextRenderer } from "@/components/TripRichTextRenderer";
import {
  TRIP_PROFILE_DEFAULT_SECTION_ID,
  TRIP_PROFILE_UNSAVED_LEAVE_MESSAGE,
  canSubmitTripProfileSection,
  countTripProfileReadySections,
  confirmationRequirementsToDraft,
  discardTripProfileSectionChanges,
  paymentScheduleToDraft,
  resolveTripProfileSectionSwitch,
  saveTripProfileSection,
  setTripProfileSectionDirtyState,
  shouldWarnBeforeLeavingTripProfile,
  tripProfileSectionNeedsReview,
  validateTripPaymentSchedule,
  validateTripProfilePackages,
  type TripProfileReadinessItem,
  type TripConfirmationRequirementsDraft,
  type TripItineraryDay,
  type TripMediaItem,
  type TripMediaItemDraft,
  type TripPaymentScheduleDraft,
  type TripPackageValidationField,
  type TripProfilePackage,
  type TripProfilePackageDraft,
  type TripProfileSectionId,
  type TripProfileSectionState,
  type TripProfileShellModel,
  type TripProfileTone,
} from "@/lib/trip-profile";
import {
  emptyTripRichText,
  getTripRichTextPlainText,
  normalizeTripRichText,
  tiptapJsonToTripRichText,
  tripRichTextToHtml,
  type TripRichTextDocument,
} from "@/lib/trip-rich-text";

import {
  saveTripDescriptionAction,
  saveTripConfirmationRequirementsAction,
  saveTripItineraryDaysAction,
  saveTripMediaGalleryAction,
  saveTripPackagesAction,
  saveTripPaymentScheduleAction,
  uploadTripMediaAction,
} from "./actions";

type ItineraryDayDraft = {
  clientId: string;
  id: number;
  sequence: number;
  title: string;
  dateLabel: string;
  descriptionRichText: TripRichTextDocument;
};

type PackageRowErrors = Record<
  string,
  Partial<Record<TripPackageValidationField, string>>
>;

type PaymentScheduleErrors = Partial<
  Record<"balanceDueDaysBeforeStart" | "balanceReminderLeadDays", string>
>;

type TripProfileSavedDrafts = {
  confirmationRequirements: TripConfirmationRequirementsDraft;
  description: TripRichTextDocument;
  itinerary: TripItineraryDay[];
  media: TripMediaItem[];
  packages: TripProfilePackage[];
  paymentSchedule: TripPaymentScheduleDraft;
};

export function TripProfileWorkspace({
  model,
  organizerId,
}: {
  model: TripProfileShellModel;
  organizerId: number;
}) {
  const [activeSectionId, setActiveSectionId] =
    useState<TripProfileSectionId>(TRIP_PROFILE_DEFAULT_SECTION_ID);
  const [dirtySectionIds, setDirtySectionIds] = useState<
    TripProfileSectionId[]
  >([]);
  const savedDraftsRef = useRef<TripProfileSavedDrafts>({
    confirmationRequirements: confirmationRequirementsToDraft(
      model.confirmationRequirements,
    ),
    description: model.description.richText,
    itinerary: model.itinerary.days,
    media: model.media.items,
    packages: model.packages.rows,
    paymentSchedule: paymentScheduleToDraft(model.paymentSchedule),
  });
  const [pendingSectionId, setPendingSectionId] =
    useState<TripProfileSectionId | null>(null);
  const [savedSectionId, setSavedSectionId] =
    useState<TripProfileSectionId | null>(null);
  const [descriptionDocument, setDescriptionDocument] =
    useState<TripRichTextDocument>(() => model.description.richText);
  const [descriptionSaveError, setDescriptionSaveError] = useState("");
  const [itineraryDays, setItineraryDays] = useState<ItineraryDayDraft[]>(() =>
    model.itinerary.days.map((day, index) => itineraryDayToDraft(day, index)),
  );
  const [itinerarySaveError, setItinerarySaveError] = useState("");
  const [mediaDrafts, setMediaDrafts] = useState<TripMediaItemDraft[]>(() =>
    model.media.items.map((item, index) => mediaItemToDraft(item, index)),
  );
  const [mediaSaveError, setMediaSaveError] = useState("");
  const [mediaUploadError, setMediaUploadError] = useState("");
  const [packageDrafts, setPackageDrafts] = useState<TripProfilePackageDraft[]>(() =>
    model.packages.rows.map((tripPackage, index) =>
      tripPackageToDraft(tripPackage, index),
    ),
  );
  const [packageSaveError, setPackageSaveError] = useState("");
  const [packageFormErrors, setPackageFormErrors] = useState<string[]>([]);
  const [packageRowErrors, setPackageRowErrors] = useState<PackageRowErrors>({});
  const [paymentScheduleDraft, setPaymentScheduleDraft] =
    useState<TripPaymentScheduleDraft>(() =>
      paymentScheduleToDraft(model.paymentSchedule),
    );
  const [paymentScheduleErrors, setPaymentScheduleErrors] =
    useState<PaymentScheduleErrors>({});
  const [paymentScheduleSaveError, setPaymentScheduleSaveError] = useState("");
  const [confirmationRequirementsDraft, setConfirmationRequirementsDraft] =
    useState<TripConfirmationRequirementsDraft>(() =>
      confirmationRequirementsToDraft(model.confirmationRequirements),
    );
  const [
    confirmationRequirementsSaveError,
    setConfirmationRequirementsSaveError,
  ] = useState("");
  const [paymentScheduleReviewed, setPaymentScheduleReviewed] = useState(
    model.paymentSchedule.reviewed,
  );
  const [
    confirmationRequirementsReviewed,
    setConfirmationRequirementsReviewed,
  ] = useState(model.confirmationRequirements.reviewed);
  const [isSavingDescription, startDescriptionSave] = useTransition();
  const [isSavingItinerary, startItinerarySave] = useTransition();
  const [isSavingMedia, startMediaSave] = useTransition();
  const [isUploadingMedia, startMediaUpload] = useTransition();
  const [isSavingPackages, startPackagesSave] = useTransition();
  const [isSavingPaymentSchedule, startPaymentScheduleSave] = useTransition();
  const [
    isSavingConfirmationRequirements,
    startConfirmationRequirementsSave,
  ] = useTransition();

  const sections = useMemo(
    () =>
      model.sections.map((section) => {
        if (
          section.editable &&
          section.id === "payment-schedule" &&
          paymentScheduleReviewed
        ) {
          return {
            ...section,
            stateLabel: "Reviewed",
            tone: "clear" as const,
          };
        }

        if (
          section.editable &&
          section.id === "requirements" &&
          confirmationRequirementsReviewed
        ) {
          return {
            ...section,
            stateLabel: "Reviewed",
            tone: "clear" as const,
          };
        }

        return section;
      }),
    [
      confirmationRequirementsReviewed,
      model.sections,
      paymentScheduleReviewed,
    ],
  );
  const blockers = useMemo(
    () =>
      model.blockers.filter((item) => {
        if (item.sectionId === "payment-schedule" && paymentScheduleReviewed) {
          return false;
        }

        if (
          item.sectionId === "requirements" &&
          confirmationRequirementsReviewed
        ) {
          return false;
        }

        return true;
      }),
    [
      confirmationRequirementsReviewed,
      model.blockers,
      paymentScheduleReviewed,
    ],
  );
  const activeSection = useMemo(
    () =>
      sections.find((section) => section.id === activeSectionId) ??
      sections[0],
    [activeSectionId, sections],
  );
  const hasDirtyChanges = shouldWarnBeforeLeavingTripProfile({
    dirtySectionIds,
    locked: model.locked,
  });
  useEffect(() => {
    if (!hasDirtyChanges) {
      return undefined;
    }

    function handleBeforeUnload(event: BeforeUnloadEvent) {
      event.preventDefault();
      event.returnValue = "";
    }

    function handleDocumentClick(event: MouseEvent) {
      const target = event.target;
      if (!(target instanceof Element)) {
        return;
      }

      const anchor = target.closest("a[href]");
      if (!(anchor instanceof HTMLAnchorElement)) {
        return;
      }

      if (anchor.target && anchor.target !== "_self") {
        return;
      }

      const nextUrl = new URL(anchor.href, window.location.href);
      if (nextUrl.href === window.location.href) {
        return;
      }

      if (!window.confirm(TRIP_PROFILE_UNSAVED_LEAVE_MESSAGE)) {
        event.preventDefault();
        event.stopPropagation();
      }
    }

    window.addEventListener("beforeunload", handleBeforeUnload);
    document.addEventListener("click", handleDocumentClick, true);

    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
      document.removeEventListener("click", handleDocumentClick, true);
    };
  }, [hasDirtyChanges]);

  const setSectionDirtyState = useCallback(
    (sectionId: TripProfileSectionId, dirty: boolean) => {
      const section = sections.find((item) => item.id === sectionId);

      if (dirty) {
        setSavedSectionId(null);
      }
      setDirtySectionIds((current) =>
        setTripProfileSectionDirtyState({
          canEdit: section?.editable ?? false,
          dirty,
          dirtySectionIds: current,
          locked: model.locked,
          sectionId,
        }),
      );
    },
    [model.locked, sections],
  );

  const handleDescriptionChange = useCallback(
    (nextDocument: TripRichTextDocument) => {
      setDescriptionDocument(nextDocument);
      setDescriptionSaveError("");
      setSectionDirtyState(
        "description",
        !sameTripRichText(nextDocument, savedDraftsRef.current.description),
      );
    },
    [setSectionDirtyState],
  );

  const handleItineraryChange = useCallback(
    (nextDays: ItineraryDayDraft[]) => {
      const resequencedDays = resequenceItineraryDrafts(nextDays);
      setItineraryDays(resequencedDays);
      setItinerarySaveError("");
      setSectionDirtyState(
        "itinerary",
        !sameTripItineraryDays(
          resequencedDays.map(itineraryDraftToDay),
          savedDraftsRef.current.itinerary,
        ),
      );
    },
    [setSectionDirtyState],
  );

  const handleMediaChange = useCallback(
    (nextItems: TripMediaItemDraft[]) => {
      const resequencedItems = resequenceMediaDrafts(nextItems);
      setMediaDrafts(resequencedItems);
      setMediaSaveError("");
      setMediaUploadError("");
      setSectionDirtyState(
        "media",
        !sameTripMediaItems(
          resequencedItems.map(mediaDraftToItem),
          savedDraftsRef.current.media,
        ),
      );
    },
    [setSectionDirtyState],
  );

  const handleMediaUpload = useCallback(
    (files: FileList | null) => {
      if (!files || files.length === 0) {
        return;
      }

      const formData = new FormData();
      Array.from(files).forEach((file) => {
        formData.append("images", file);
      });

      setMediaUploadError("");
      startMediaUpload(() => {
        void uploadTripMediaAction({
          formData,
          organizerId,
          tripId: model.tripId,
        }).then((result) => {
          if (!result.ok) {
            setMediaUploadError(result.message);
            return;
          }
          setMediaDrafts(
            result.mediaItems.map((item, index) => mediaItemToDraft(item, index)),
          );
          savedDraftsRef.current.media = result.mediaItems;
          setDirtySectionIds((current) =>
            discardTripProfileSectionChanges({
              dirtySectionIds: current,
              sectionId: "media",
            }),
          );
          setSavedSectionId("media");
        });
      });
    },
    [model.tripId, organizerId],
  );

  const handlePackagesChange = useCallback(
    (nextPackages: TripProfilePackageDraft[]) => {
      const resequencedPackages = resequencePackageDrafts(nextPackages);
      setPackageDrafts(resequencedPackages);
      setPackageSaveError("");
      setPackageFormErrors([]);
      setPackageRowErrors({});
      setSectionDirtyState(
        "packages",
        !sameTripPackages(
          resequencedPackages.map(packageDraftToPackage),
          savedDraftsRef.current.packages,
        ),
      );
    },
    [setSectionDirtyState],
  );

  const handlePaymentScheduleChange = useCallback(
    (nextPaymentSchedule: TripPaymentScheduleDraft) => {
      setPaymentScheduleDraft(nextPaymentSchedule);
      setPaymentScheduleErrors({});
      setPaymentScheduleSaveError("");
      setSectionDirtyState(
        "payment-schedule",
        !samePaymentSchedules(
          nextPaymentSchedule,
          savedDraftsRef.current.paymentSchedule,
        ),
      );
    },
    [setSectionDirtyState],
  );

  const handleConfirmationRequirementsChange = useCallback(
    (nextRequirements: TripConfirmationRequirementsDraft) => {
      setConfirmationRequirementsDraft(nextRequirements);
      setConfirmationRequirementsSaveError("");
      setSectionDirtyState(
        "requirements",
        !sameConfirmationRequirements(
          nextRequirements,
          savedDraftsRef.current.confirmationRequirements,
        ),
      );
    },
    [setSectionDirtyState],
  );

  const completeSectionSave = useCallback(
    (
      sectionId: TripProfileSectionId,
      nextSectionId: TripProfileSectionId | null = null,
    ) => {
      setDirtySectionIds((current) =>
        discardTripProfileSectionChanges({
          dirtySectionIds: current,
          sectionId,
        }),
      );

      if (nextSectionId) {
        setActiveSectionId(nextSectionId);
        setPendingSectionId(null);
        setSavedSectionId(null);
        return;
      }

      setPendingSectionId(null);
      setSavedSectionId(sectionId);
    },
    [],
  );

  const handleSave = useCallback(
    (nextSectionId: TripProfileSectionId | null = null) => {
      if (
        !activeSection.editable ||
        (model.locked && activeSection.id !== "media") ||
        isSavingDescription ||
        isSavingItinerary ||
        isSavingMedia ||
        isUploadingMedia ||
        isSavingPackages ||
        isSavingPaymentSchedule ||
        isSavingConfirmationRequirements
      ) {
        return;
      }

      const sectionToOpen =
        nextSectionId && nextSectionId !== activeSection.id
          ? nextSectionId
          : null;

      if (activeSection.id === "description") {
        startDescriptionSave(() => {
          void saveTripDescriptionAction({
            descriptionRichText: descriptionDocument,
            organizerId,
            tripId: model.tripId,
          }).then((result) => {
            if (!result.ok) {
              setPendingSectionId(null);
              setDescriptionSaveError(result.message);
              return;
            }

            setDescriptionDocument(result.descriptionRichText);
            savedDraftsRef.current.description = result.descriptionRichText;
            completeSectionSave("description", sectionToOpen);
            setDescriptionSaveError("");
          });
        });
        return;
      }

      if (activeSection.id === "itinerary") {
        const daysToSave = itineraryDays.map(itineraryDraftToDay);
        startItinerarySave(() => {
          void saveTripItineraryDaysAction({
            itineraryDays: daysToSave,
            organizerId,
            tripId: model.tripId,
          }).then((result) => {
            if (!result.ok) {
              setPendingSectionId(null);
              setItinerarySaveError(result.message);
              return;
            }

            setItineraryDays(
              result.itineraryDays.map((day, index) =>
                itineraryDayToDraft(day, index),
              ),
            );
            savedDraftsRef.current.itinerary = result.itineraryDays;
            completeSectionSave("itinerary", sectionToOpen);
            setItinerarySaveError("");
          });
        });
        return;
      }

      if (activeSection.id === "packages") {
        const validation = validateTripProfilePackages(packageDrafts);
        if (!validation.ok) {
          setPendingSectionId(null);
          setPackageFormErrors(validation.formErrors);
          setPackageRowErrors(validation.rowErrors);
          setPackageSaveError("");
          return;
        }

        startPackagesSave(() => {
          void saveTripPackagesAction({
            organizerId,
            packages: validation.packages,
            tripId: model.tripId,
          }).then((result) => {
            if (!result.ok) {
              setPendingSectionId(null);
              setPackageSaveError(result.message);
              return;
            }

            setPackageDrafts(
              result.packages.map((tripPackage, index) =>
                tripPackageToDraft(tripPackage, index),
              ),
            );
            savedDraftsRef.current.packages = result.packages;
            completeSectionSave("packages", sectionToOpen);
            setPackageSaveError("");
            setPackageFormErrors([]);
            setPackageRowErrors({});
          });
        });
        return;
      }

      if (activeSection.id === "media") {
        startMediaSave(() => {
          void saveTripMediaGalleryAction({
            mediaItems: mediaDrafts.map(mediaDraftToItem),
            organizerId,
            tripId: model.tripId,
          }).then((result) => {
            if (!result.ok) {
              setPendingSectionId(null);
              setMediaSaveError(result.message);
              return;
            }

            setMediaDrafts(
              result.mediaItems.map((item, index) =>
                mediaItemToDraft(item, index),
              ),
            );
            savedDraftsRef.current.media = result.mediaItems;
            completeSectionSave("media", sectionToOpen);
            setMediaSaveError("");
          });
        });
        return;
      }

      if (activeSection.id === "payment-schedule") {
        const validation = validateTripPaymentSchedule(paymentScheduleDraft);
        if (!validation.ok) {
          setPendingSectionId(null);
          setPaymentScheduleErrors(validation.errors);
          setPaymentScheduleSaveError("");
          return;
        }

        startPaymentScheduleSave(() => {
          void saveTripPaymentScheduleAction({
            organizerId,
            paymentSchedule: validation.paymentSchedule,
            tripId: model.tripId,
          })
            .then((result) => {
              if (!result.ok) {
                setPendingSectionId(null);
                setPaymentScheduleSaveError(result.message);
                return;
              }

              setPaymentScheduleDraft(
                paymentScheduleToDraft(result.paymentSchedule),
              );
              setPaymentScheduleReviewed(result.paymentSchedule.reviewed);
              savedDraftsRef.current.paymentSchedule = paymentScheduleToDraft(
                result.paymentSchedule,
              );
              completeSectionSave("payment-schedule", sectionToOpen);
              setPaymentScheduleErrors({});
              setPaymentScheduleSaveError("");
            })
            .catch(() => {
              setPendingSectionId(null);
              setPaymentScheduleSaveError(
                "Balance payment schedule was not saved. Check the API connection and try again.",
              );
            });
        });
        return;
      }

      if (activeSection.id === "requirements") {
        startConfirmationRequirementsSave(() => {
          void saveTripConfirmationRequirementsAction({
            confirmationRequirements: confirmationRequirementsDraft,
            organizerId,
            tripId: model.tripId,
          }).then((result) => {
            if (!result.ok) {
              setPendingSectionId(null);
              setConfirmationRequirementsSaveError(result.message);
              return;
            }

            setConfirmationRequirementsDraft(
              confirmationRequirementsToDraft(result.confirmationRequirements),
            );
            setConfirmationRequirementsReviewed(
              result.confirmationRequirements.reviewed,
            );
            savedDraftsRef.current.confirmationRequirements =
              confirmationRequirementsToDraft(result.confirmationRequirements);
            completeSectionSave("requirements", sectionToOpen);
            setConfirmationRequirementsSaveError("");
          }).catch(() => {
            setPendingSectionId(null);
            setConfirmationRequirementsSaveError(
              "Confirmation Requirements were not saved. Check the API connection and try again.",
            );
          });
        });
        return;
      }

      const result = saveTripProfileSection({
        dirtySectionIds,
        sectionId: activeSection.id,
      });

      setDirtySectionIds(result.dirtySectionIds);
      setPendingSectionId(null);
      if (sectionToOpen && result.saved) {
        setActiveSectionId(sectionToOpen);
        setSavedSectionId(null);
        return;
      }

      setSavedSectionId(result.saved ? activeSection.id : null);
    },
    [
      activeSection,
      completeSectionSave,
      confirmationRequirementsDraft,
      descriptionDocument,
      dirtySectionIds,
      itineraryDays,
      isSavingDescription,
      isSavingItinerary,
      isSavingMedia,
      isUploadingMedia,
      isSavingPackages,
      isSavingPaymentSchedule,
      isSavingConfirmationRequirements,
      model.locked,
      model.tripId,
      organizerId,
      mediaDrafts,
      packageDrafts,
      paymentScheduleDraft,
    ],
  );

  const activeIsDirty = dirtySectionIds.includes(activeSection.id);
  const activeWasSaved = savedSectionId === activeSection.id;
  const activeNeedsReview = tripProfileSectionNeedsReview({
    confirmationRequirementsReviewed,
    paymentScheduleReviewed,
    sectionId: activeSection.id,
  });
  const readySectionCount = countTripProfileReadySections(sections);
  const totalSectionCount = sections.length;
  const completionPercent = totalSectionCount
    ? Math.round((readySectionCount / totalSectionCount) * 100)
    : 0;
  const activeIsSaving =
    (isSavingDescription && activeSection.id === "description") ||
    (isSavingItinerary && activeSection.id === "itinerary") ||
    (isSavingMedia && activeSection.id === "media") ||
    (isUploadingMedia && activeSection.id === "media") ||
    (isSavingPackages && activeSection.id === "packages") ||
    (isSavingPaymentSchedule && activeSection.id === "payment-schedule") ||
    (isSavingConfirmationRequirements && activeSection.id === "requirements");
  const isAnySectionBusy =
    isSavingDescription ||
    isSavingItinerary ||
    isSavingMedia ||
    isUploadingMedia ||
    isSavingPackages ||
    isSavingPaymentSchedule ||
    isSavingConfirmationRequirements;
  const canSaveActiveSection = canSubmitTripProfileSection({
    busy: isAnySectionBusy,
    confirmationRequirementsReviewed,
    dirty: activeIsDirty,
    editable: activeSection.editable,
    locked: model.locked,
    paymentScheduleReviewed,
    sectionId: activeSection.id,
  });
  const pendingSectionLabel =
    sections.find((section) => section.id === pendingSectionId)?.label ?? "";
  const activeSaveStateLabel = saveStateLabel({
    dirty: activeIsDirty,
    locked: model.locked,
    needsReview: activeNeedsReview,
    pendingSectionLabel,
    readonlyReason: activeSection.readonlyReason,
    saved: activeWasSaved,
    saving: activeIsSaving,
    sectionId: activeSection.id,
  });

  const handleSectionSelect = useCallback(
    (nextSectionId: TripProfileSectionId) => {
      if (nextSectionId === activeSectionId || isAnySectionBusy) {
        return;
      }

      const decision = resolveTripProfileSectionSwitch({
        activeSectionId,
        dirtySectionIds,
        locked: model.locked,
        nextSectionId,
      });

      if (decision.canSwitch) {
        setActiveSectionId(decision.activeSectionId);
        setPendingSectionId(null);
        setSavedSectionId(null);
        return;
      }

      if (!canSaveActiveSection) {
        setPendingSectionId(null);
        return;
      }

      setPendingSectionId(decision.pendingSectionId);
      setSavedSectionId(null);
      handleSave(decision.pendingSectionId);
    },
    [
      activeSectionId,
      canSaveActiveSection,
      dirtySectionIds,
      handleSave,
      isAnySectionBusy,
      model.locked,
    ],
  );

  return (
    <section
      aria-label="Trip Profile"
      className={`trip-profile-shell ${model.locked ? "is-locked" : ""}`}
    >
      <TripProfileReadiness
        blockers={blockers}
        completionPercent={completionPercent}
        encouraged={model.encouraged}
        locked={model.locked}
        onSelectSection={handleSectionSelect}
        readyCount={readySectionCount}
        totalCount={totalSectionCount}
      />

      <div className="trip-profile-workbench">
        <nav
          aria-label="Trip Profile sections"
          className="trip-profile-tabs"
        >
          <div className="trip-profile-tabs-header">
            <div>
              <span>Profile sections</span>
              <strong>
                {readySectionCount} of {totalSectionCount} ready
              </strong>
            </div>
            <div
              aria-label={`${completionPercent}% of Trip Profile sections ready`}
              className="trip-profile-mini-progress"
              role="progressbar"
              aria-valuemax={100}
              aria-valuemin={0}
              aria-valuenow={completionPercent}
            >
              <span style={{ width: `${completionPercent}%` }} />
            </div>
          </div>

          <div className="trip-profile-tab-list" role="tablist">
            {sections.map((section) => {
              const isActive = section.id === activeSection.id;
              const isDirty = dirtySectionIds.includes(section.id);
              const tabStatus = sectionBadgeLabel(section);
              const tabTone = sectionBadgeTone(section);

              return (
                <button
                  aria-controls={`trip-profile-panel-${section.id}`}
                  aria-selected={isActive}
                  className={isActive ? "is-active" : ""}
                  data-tone={section.tone}
                  id={`trip-profile-tab-${section.id}`}
                  key={section.id}
                  onClick={() => handleSectionSelect(section.id)}
                  role="tab"
                  type="button"
                >
                  <span>
                    <strong>{section.shortLabel}</strong>
                    <em>{isDirty ? "Unsaved changes" : section.detail}</em>
                  </span>
                  <span className={`status-chip ${toneClass(tabTone)}`}>
                    {tabStatus}
                  </span>
                </button>
              );
            })}
          </div>
        </nav>

        <section
          aria-labelledby={`trip-profile-tab-${activeSection.id}`}
          className="trip-profile-editor-panel"
          id={`trip-profile-panel-${activeSection.id}`}
          role="tabpanel"
        >
          <div className="trip-profile-editor-heading">
            <div>
              <p className="eyebrow">{activeSection.detail}</p>
              <h3>{activeSection.label}</h3>
              {activeSection.readonlyReason ? (
                <span>{activeSection.readonlyReason}</span>
              ) : (
                <span>{activeSection.detail}</span>
              )}
            </div>
            <div className="trip-profile-editor-actions">
              <span
                className={`trip-profile-save-state ${
                  activeIsDirty ? "is-dirty" : activeWasSaved ? "is-saved" : ""
                }`}
              >
                {activeSaveStateLabel}
              </span>
              <button
                className="trip-profile-save-button"
                disabled={!canSaveActiveSection}
                onClick={() => handleSave()}
                type="button"
              >
                {activeNeedsReview ? (
                  <CheckCircle2 aria-hidden="true" />
                ) : (
                  <Save aria-hidden="true" />
                )}
                {headerSaveLabel({
                  dirty: activeIsDirty,
                  locked: model.locked,
                  needsReview: activeNeedsReview,
                  saving: activeIsSaving,
                  sectionId: activeSection.id,
                })}
              </button>
            </div>
          </div>

          <TripProfileSectionBody
            descriptionDocument={descriptionDocument}
            descriptionSaveError={descriptionSaveError}
            itineraryDays={itineraryDays}
            itinerarySaveError={itinerarySaveError}
            mediaItems={mediaDrafts}
            mediaSaveError={mediaSaveError}
            mediaUploadError={mediaUploadError}
            mediaUploading={isUploadingMedia}
            onDescriptionChange={handleDescriptionChange}
            onItineraryChange={handleItineraryChange}
            onMediaChange={handleMediaChange}
            onMediaUpload={handleMediaUpload}
            onPackagesChange={handlePackagesChange}
            onConfirmationRequirementsChange={
              handleConfirmationRequirementsChange
            }
            onPaymentScheduleChange={handlePaymentScheduleChange}
            confirmationRequirements={confirmationRequirementsDraft}
            confirmationRequirementsSaveError={confirmationRequirementsSaveError}
            packageDrafts={packageDrafts}
            packageFormErrors={packageFormErrors}
            packageRowErrors={packageRowErrors}
            packageSaveError={packageSaveError}
            paymentSchedule={paymentScheduleDraft}
            paymentScheduleErrors={paymentScheduleErrors}
            paymentScheduleSaveError={paymentScheduleSaveError}
            section={activeSection}
          />
        </section>
      </div>
    </section>
  );
}

function TripProfileReadiness({
  blockers,
  completionPercent,
  encouraged,
  locked,
  onSelectSection,
  readyCount,
  totalCount,
}: {
  blockers: TripProfileReadinessItem[];
  completionPercent: number;
  encouraged: TripProfileReadinessItem[];
  locked: boolean;
  onSelectSection: (sectionId: TripProfileSectionId) => void;
  readyCount: number;
  totalCount: number;
}) {
  const nextRequiredAction = locked
    ? null
    : blockers[0] ?? encouraged[0] ?? null;
  const nextActionLabel = nextRequiredAction
    ? nextRequiredActionLabel(nextRequiredAction)
    : locked
      ? "Published profile is read-only"
      : "Ready for Owner publish review";

  return (
    <section
      className="trip-profile-readiness-panel"
      aria-label="Trip Profile section readiness"
    >
      <div className="trip-profile-readiness-heading">
        <div>
          <h3>Profile readiness</h3>
          <p>
            {blockers.length} blockers &middot; {encouraged.length} encouraged
            &middot; {readyCount} ready
          </p>
        </div>
        <span className="status-chip is-blocked">
          {blockers.length ? `${blockers.length} blockers` : "No blockers"}
        </span>
      </div>

      <div
        aria-label={`${completionPercent}% of Trip Profile sections ready`}
        className="trip-profile-progress"
        role="progressbar"
        aria-valuemax={100}
        aria-valuemin={0}
        aria-valuenow={completionPercent}
      >
        <span style={{ width: `${completionPercent}%` }} />
      </div>

      {nextRequiredAction ? (
        <ReadinessButton
          actionLabel={nextActionLabel}
          item={nextRequiredAction}
          onSelectSection={onSelectSection}
        />
      ) : (
        <div className="trip-profile-readiness-empty">
          <CheckCircle2 aria-hidden="true" />
          <span>
            <strong>{nextActionLabel}</strong>
            <em>
              {locked
                ? "Published content is visible here as read-only."
                : `${readyCount} of ${totalCount} sections are ready.`}
            </em>
          </span>
        </div>
      )}
    </section>
  );
}

function ReadinessButton({
  actionLabel,
  item,
  onSelectSection,
}: {
  actionLabel: string;
  item: TripProfileReadinessItem;
  onSelectSection: (sectionId: TripProfileSectionId) => void;
}) {
  return (
    <button
      className={`trip-profile-readiness-row is-${item.tone}`}
      onClick={() => onSelectSection(item.sectionId)}
      type="button"
    >
      {item.tone === "blocked" ? (
        <AlertCircle aria-hidden="true" />
      ) : (
        <CircleDot aria-hidden="true" />
      )}
      <span>
        <em>
          {item.tone === "blocked"
            ? "Next required action"
            : "Next encouraged action"}
        </em>
        <strong>{actionLabel}</strong>
        <em>{item.detail}</em>
      </span>
      <span className={`status-chip ${toneClass(item.tone)}`}>
        {item.tone === "blocked" ? "Needed" : "Encouraged"}
      </span>
    </button>
  );
}

function TripProfileSectionBody({
  confirmationRequirements,
  confirmationRequirementsSaveError,
  descriptionDocument,
  descriptionSaveError,
  itineraryDays,
  itinerarySaveError,
  mediaItems,
  mediaSaveError,
  mediaUploadError,
  mediaUploading,
  onDescriptionChange,
  onItineraryChange,
  onMediaChange,
  onMediaUpload,
  onPackagesChange,
  onConfirmationRequirementsChange,
  onPaymentScheduleChange,
  packageDrafts,
  packageFormErrors,
  packageRowErrors,
  packageSaveError,
  paymentSchedule,
  paymentScheduleErrors,
  paymentScheduleSaveError,
  section,
}: {
  confirmationRequirements: TripConfirmationRequirementsDraft;
  confirmationRequirementsSaveError: string;
  descriptionDocument: TripRichTextDocument;
  descriptionSaveError: string;
  itineraryDays: ItineraryDayDraft[];
  itinerarySaveError: string;
  mediaItems: TripMediaItemDraft[];
  mediaSaveError: string;
  mediaUploadError: string;
  mediaUploading: boolean;
  onDescriptionChange: (document: TripRichTextDocument) => void;
  onItineraryChange: (days: ItineraryDayDraft[]) => void;
  onMediaChange: (items: TripMediaItemDraft[]) => void;
  onMediaUpload: (files: FileList | null) => void;
  onPackagesChange: (packages: TripProfilePackageDraft[]) => void;
  onConfirmationRequirementsChange: (
    requirements: TripConfirmationRequirementsDraft,
  ) => void;
  onPaymentScheduleChange: (paymentSchedule: TripPaymentScheduleDraft) => void;
  packageDrafts: TripProfilePackageDraft[];
  packageFormErrors: string[];
  packageRowErrors: PackageRowErrors;
  packageSaveError: string;
  paymentSchedule: TripPaymentScheduleDraft;
  paymentScheduleErrors: PaymentScheduleErrors;
  paymentScheduleSaveError: string;
  section: TripProfileSectionState;
}) {
  const readOnly = !section.editable;

  switch (section.id) {
    case "description":
      return (
        <TripDescriptionSection
          document={descriptionDocument}
          onChange={onDescriptionChange}
          readOnly={readOnly}
          saveError={descriptionSaveError}
        />
      );
    case "itinerary":
      return (
        <TripItinerarySection
          days={itineraryDays}
          onChange={onItineraryChange}
          readOnly={readOnly}
          saveError={itinerarySaveError}
        />
      );
    case "media":
      return (
        <TripMediaGallerySection
          items={mediaItems}
          onChange={onMediaChange}
          onUpload={onMediaUpload}
          readOnly={readOnly}
          readonlyReason={section.readonlyReason}
          saveError={mediaSaveError}
          uploading={mediaUploading}
          uploadError={mediaUploadError}
        />
      );
    case "packages":
      return (
        <TripPackagesSection
          formErrors={packageFormErrors}
          onChange={onPackagesChange}
          packages={packageDrafts}
          readOnly={readOnly}
          readonlyReason={section.readonlyReason}
          rowErrors={packageRowErrors}
          saveError={packageSaveError}
        />
      );
    case "payment-schedule":
      return (
        <TripPaymentScheduleSection
          errors={paymentScheduleErrors}
          onChange={onPaymentScheduleChange}
          paymentSchedule={paymentSchedule}
          readOnly={readOnly}
          readonlyReason={section.readonlyReason}
          saveError={paymentScheduleSaveError}
        />
      );
    case "requirements":
      return (
        <TripConfirmationRequirementsSection
          onChange={onConfirmationRequirementsChange}
          readOnly={readOnly}
          readonlyReason={section.readonlyReason}
          requirements={confirmationRequirements}
          saveError={confirmationRequirementsSaveError}
        />
      );
  }
}

function TripDescriptionSection({
  document,
  onChange,
  readOnly,
  saveError,
}: {
  document: TripRichTextDocument;
  onChange: (document: TripRichTextDocument) => void;
  readOnly: boolean;
  saveError: string;
}) {
  return (
    <div className="trip-profile-section-body trip-description-editor">
      {saveError ? (
        <div className="trip-description-error" role="alert">
          <AlertCircle aria-hidden="true" />
          <span>{saveError}</span>
        </div>
      ) : null}
      <p className="trip-description-helper">
        Helpful details: terrain, pace, who this trip suits, inclusions, group
        tone, and any readiness notes travelers should know before booking.
      </p>
      <div className="trip-description-grid">
        <RichTextEditor
          height={340}
          onJsonChange={(value) => onChange(tiptapJsonToTripRichText(value))}
          placeholder="Describe what travelers will experience, who this trip is for, and what makes it special."
          readOnly={readOnly}
          value={tripRichTextToHtml(document)}
          variant="article"
        />
        <div className="trip-description-preview" aria-label="Public preview preview">
          <span>Public preview</span>
          <TripRichTextRenderer
            document={document}
            emptyLabel="Your public trip description will appear here after you add content."
          />
        </div>
      </div>
    </div>
  );
}

function TripMediaGallerySection({
  items,
  onChange,
  onUpload,
  readOnly,
  readonlyReason,
  saveError,
  uploading,
  uploadError,
}: {
  items: TripMediaItemDraft[];
  onChange: (items: TripMediaItemDraft[]) => void;
  onUpload: (files: FileList | null) => void;
  readOnly: boolean;
  readonlyReason: string;
  saveError: string;
  uploading: boolean;
  uploadError: string;
}) {
  const moveItem = useCallback(
    (clientId: string, direction: -1 | 1) => {
      const currentIndex = items.findIndex((item) => item.clientId === clientId);
      const nextIndex = currentIndex + direction;
      if (currentIndex < 0 || nextIndex < 0 || nextIndex >= items.length) {
        return;
      }
      const nextItems = [...items];
      const [item] = nextItems.splice(currentIndex, 1);
      nextItems.splice(nextIndex, 0, item);
      onChange(nextItems);
    },
    [items, onChange],
  );

  const updateItem = useCallback(
    (clientId: string, updates: Partial<Omit<TripMediaItemDraft, "clientId">>) => {
      onChange(
        ensureMediaCover(
          items.map((item) =>
            item.clientId === clientId
              ? {
                  ...item,
                  ...updates,
                }
              : updates.isCover
                ? { ...item, isCover: false }
                : item,
          ),
        ),
      );
    },
    [items, onChange],
  );

  const removeItem = useCallback(
    (clientId: string) => {
      onChange(ensureMediaCover(items.filter((item) => item.clientId !== clientId)));
    },
    [items, onChange],
  );

  return (
    <div className="trip-profile-section-body trip-profile-media-editor">
      <div className="trip-profile-media-drop">
        <Upload aria-hidden="true" />
        <div>
          <strong>{uploading ? "Uploading images" : "Trip Media Gallery"}</strong>
          <span>
            PNG, JPG, or WebP images. Uploaded images appear on the Public Trip
            Page unless marked private.
          </span>
        </div>
        <label
          aria-disabled={readOnly || uploading}
          className="trip-profile-media-upload-button"
        >
          <ImageIcon aria-hidden="true" />
          <span>{uploading ? "Uploading" : "Upload Images"}</span>
          <input
            accept="image/png,image/jpeg,image/webp"
            disabled={readOnly || uploading}
            multiple
            onChange={(event) => {
              onUpload(event.currentTarget.files);
              event.currentTarget.value = "";
            }}
            type="file"
          />
        </label>
      </div>

      {readonlyReason ? (
        <div className="trip-profile-readonly-callout">
          <LockKeyhole aria-hidden="true" />
          <span>{readonlyReason}</span>
        </div>
      ) : null}

      {[uploadError, saveError].filter(Boolean).map((message) => (
        <div className="trip-description-error" key={message} role="alert">
          <AlertCircle aria-hidden="true" />
          <span>{message}</span>
        </div>
      ))}

      {items.length === 0 ? (
        <div className="trip-profile-media-empty">
          <ImageIcon aria-hidden="true" />
          <div>
            <strong>No Trip Media yet</strong>
            <span>Media is encouraged for the Public Trip Page, but not required.</span>
          </div>
        </div>
      ) : (
        <div className="trip-profile-media-grid">
          {items.map((item, index) => {
            const title = item.caption || item.originalFilename || `Image ${index + 1}`;
            const captionId = `${item.clientId}-caption`;
            const altTextId = `${item.clientId}-alt`;

            return (
              <article className="trip-profile-media-card" key={item.clientId}>
                <div className="trip-profile-media-preview">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    alt={item.altText || item.caption || ""}
                    src={item.imageUrl}
                  />
                  <div className="trip-profile-media-badges">
                    {item.isCover ? <span>Cover</span> : null}
                    <span>{item.isPublic ? "Public" : "Private"}</span>
                  </div>
                </div>

                <div className="trip-profile-media-card-body">
                  <div className="trip-profile-media-order">
                    <span>{String(index + 1).padStart(2, "0")}</span>
                    <div className="trip-profile-media-row-actions">
                      <button
                        aria-label={`Move ${title} up`}
                        disabled={readOnly || index === 0}
                        onClick={() => moveItem(item.clientId, -1)}
                        type="button"
                      >
                        <ArrowUp aria-hidden="true" />
                      </button>
                      <button
                        aria-label={`Move ${title} down`}
                        disabled={readOnly || index === items.length - 1}
                        onClick={() => moveItem(item.clientId, 1)}
                        type="button"
                      >
                        <ArrowDown aria-hidden="true" />
                      </button>
                      <button
                        aria-label={`Remove ${title}`}
                        disabled={readOnly}
                        onClick={() => removeItem(item.clientId)}
                        type="button"
                      >
                        <Trash2 aria-hidden="true" />
                      </button>
                    </div>
                  </div>

                  <label className="trip-profile-field" htmlFor={captionId}>
                    <span>Caption</span>
                    <input
                      id={captionId}
                      maxLength={220}
                      onChange={(event) =>
                        updateItem(item.clientId, { caption: event.target.value })
                      }
                      placeholder="Snowline approach from Kaza"
                      readOnly={readOnly}
                      value={item.caption}
                    />
                  </label>

                  <label className="trip-profile-field" htmlFor={altTextId}>
                    <span>Alt text</span>
                    <input
                      id={altTextId}
                      maxLength={220}
                      onChange={(event) =>
                        updateItem(item.clientId, { altText: event.target.value })
                      }
                      placeholder="Travelers walking on a high valley trail"
                      readOnly={readOnly}
                      value={item.altText}
                    />
                  </label>

                  <div className="trip-profile-media-controls">
                    <label className="trip-profile-switch">
                      <input
                        checked={item.isPublic}
                        disabled={readOnly}
                        onChange={(event) =>
                          updateItem(item.clientId, { isPublic: event.target.checked })
                        }
                        type="checkbox"
                      />
                      <span>{item.isPublic ? "Public Page" : "Private"}</span>
                    </label>
                    <label className="trip-profile-switch">
                      <input
                        checked={item.isCover}
                        disabled={readOnly}
                        name="trip-profile-cover-image"
                        onChange={() => updateItem(item.clientId, { isCover: true })}
                        type="radio"
                      />
                      <span>Cover</span>
                    </label>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}

function TripPaymentScheduleSection({
  errors,
  onChange,
  paymentSchedule,
  readOnly,
  readonlyReason,
  saveError,
}: {
  errors: PaymentScheduleErrors;
  onChange: (paymentSchedule: TripPaymentScheduleDraft) => void;
  paymentSchedule: TripPaymentScheduleDraft;
  readOnly: boolean;
  readonlyReason: string;
  saveError: string;
}) {
  const update = (updates: Partial<TripPaymentScheduleDraft>) => {
    onChange({
      ...paymentSchedule,
      ...updates,
    });
  };

  return (
    <div className="trip-profile-section-body">
      <div className="trip-profile-payment-schedule-panel">
        <div className="trip-profile-payment-schedule-row">
          <div>
            <strong>Reservation Amount</strong>
            <span>Due immediately when the Booking Contact reserves seats.</span>
          </div>
          <span className="status-chip is-clear">Fixed</span>
        </div>

        <div className="trip-profile-payment-schedule-row">
          <div>
            <strong>Final balance due</strong>
            <span>
              {paymentSchedule.hasBalanceMilestone
                ? "Collect the remaining balance before the trip starts."
                : "No separate final balance due date is shown."}
            </span>
          </div>
          <label className="trip-profile-switch">
            <input
              checked={paymentSchedule.hasBalanceMilestone}
              disabled={readOnly}
              onChange={(event) =>
                update({
                  hasBalanceMilestone: event.target.checked,
                  balanceDueDaysBeforeStart: event.target.checked
                    ? paymentSchedule.balanceDueDaysBeforeStart ?? 14
                    : null,
                })
              }
              type="checkbox"
            />
            <span>{paymentSchedule.hasBalanceMilestone ? "Enabled" : "Off"}</span>
          </label>
        </div>

        <div className="trip-profile-form-grid">
          <label className="trip-profile-field">
            <span>Balance due, days before start</span>
            <input
              disabled={!paymentSchedule.hasBalanceMilestone}
              min={1}
              onChange={(event) =>
                update({
                  balanceDueDaysBeforeStart: parseOptionalPositiveInteger(
                    event.target.value,
                  ),
                })
              }
              readOnly={readOnly}
              type="number"
              value={paymentSchedule.balanceDueDaysBeforeStart ?? ""}
            />
            {errors.balanceDueDaysBeforeStart ? (
              <em>{errors.balanceDueDaysBeforeStart}</em>
            ) : null}
          </label>
          <label className="trip-profile-field">
            <span>Reminder, days before due date</span>
            <input
              min={0}
              onChange={(event) =>
                update({
                  balanceReminderLeadDays: parsePaymentScheduleNumber(
                    event.target.value,
                  ),
                })
              }
              readOnly={readOnly}
              type="number"
              value={paymentSchedule.balanceReminderLeadDays}
            />
            {errors.balanceReminderLeadDays ? (
              <em>{errors.balanceReminderLeadDays}</em>
            ) : null}
          </label>
        </div>

        {saveError ? (
          <div className="trip-profile-save-error" role="alert">
            <AlertCircle aria-hidden="true" />
            <span>{saveError}</span>
          </div>
        ) : null}
        {readonlyReason ? (
          <p className="trip-profile-readonly-note">{readonlyReason}</p>
        ) : null}
      </div>
    </div>
  );
}

function TripItinerarySection({
  days,
  onChange,
  readOnly,
  saveError,
}: {
  days: ItineraryDayDraft[];
  onChange: (days: ItineraryDayDraft[]) => void;
  readOnly: boolean;
  saveError: string;
}) {
  const addDay = useCallback(() => {
    const nextSequence = days.length + 1;
    onChange([
      ...days,
      {
        clientId: `itinerary-day-${Date.now()}-${Math.random().toString(36).slice(2)}`,
        id: 0,
        sequence: nextSequence,
        title: "",
        dateLabel: `Day ${nextSequence}`,
        descriptionRichText: emptyTripRichText(),
      },
    ]);
  }, [days, onChange]);

  const updateDay = useCallback(
    (clientId: string, updates: Partial<Omit<ItineraryDayDraft, "clientId">>) => {
      onChange(
        days.map((day) =>
          day.clientId === clientId
            ? {
                ...day,
                ...updates,
              }
            : day,
        ),
      );
    },
    [days, onChange],
  );

  const moveDay = useCallback(
    (clientId: string, direction: -1 | 1) => {
      const currentIndex = days.findIndex((day) => day.clientId === clientId);
      const nextIndex = currentIndex + direction;
      if (currentIndex < 0 || nextIndex < 0 || nextIndex >= days.length) {
        return;
      }
      const nextDays = [...days];
      const [day] = nextDays.splice(currentIndex, 1);
      nextDays.splice(nextIndex, 0, day);
      onChange(nextDays);
    },
    [days, onChange],
  );

  const removeDay = useCallback(
    (clientId: string) => {
      onChange(days.filter((day) => day.clientId !== clientId));
    },
    [days, onChange],
  );

  return (
    <div className="trip-profile-section-body trip-itinerary-editor">
      <div className="trip-itinerary-command-row">
        <div>
          <span>Structured Days</span>
          <strong>{days.length ? `${days.length} day${days.length === 1 ? "" : "s"}` : "No days"}</strong>
        </div>
        <button disabled={readOnly} onClick={addDay} type="button">
          <Plus aria-hidden="true" />
          <span>Add Day</span>
        </button>
      </div>

      {saveError ? (
        <div className="trip-description-error" role="alert">
          <AlertCircle aria-hidden="true" />
          <span>{saveError}</span>
        </div>
      ) : null}

      {days.length === 0 ? (
        <div className="trip-itinerary-empty">
          <CircleDot aria-hidden="true" />
          <div>
            <strong>Itinerary Days needed</strong>
            <span>At least one day is required before publication.</span>
          </div>
          <button disabled={readOnly} onClick={addDay} type="button">
            <Plus aria-hidden="true" />
            <span>Add Day</span>
          </button>
        </div>
      ) : (
        <div className="trip-profile-accordion-list trip-itinerary-day-list">
          {days.map((day, index) => {
            const summary = getTripRichTextPlainText(day.descriptionRichText);
            const dayLabel = day.dateLabel || `Day ${index + 1}`;
            const title = day.title || "Untitled Itinerary Day";

            return (
              <details key={day.clientId} open={index === 0}>
                <summary>
                  <span className="trip-itinerary-summary">
                    <span className="trip-itinerary-sequence">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <span>
                      <strong>{title}</strong>
                      <em>
                        {dayLabel}
                        {summary ? `, ${summary}` : ""}
                      </em>
                    </span>
                  </span>
                  <span className="trip-itinerary-row-actions">
                    <button
                      aria-label={`Move ${title} up`}
                      disabled={readOnly || index === 0}
                      onClick={(event) => {
                        event.preventDefault();
                        event.stopPropagation();
                        moveDay(day.clientId, -1);
                      }}
                      type="button"
                    >
                      <ArrowUp aria-hidden="true" />
                    </button>
                    <button
                      aria-label={`Move ${title} down`}
                      disabled={readOnly || index === days.length - 1}
                      onClick={(event) => {
                        event.preventDefault();
                        event.stopPropagation();
                        moveDay(day.clientId, 1);
                      }}
                      type="button"
                    >
                      <ArrowDown aria-hidden="true" />
                    </button>
                    <button
                      aria-label={`Remove ${title}`}
                      disabled={readOnly}
                      onClick={(event) => {
                        event.preventDefault();
                        event.stopPropagation();
                        removeDay(day.clientId);
                      }}
                      type="button"
                    >
                      <Trash2 aria-hidden="true" />
                    </button>
                    <ChevronDown aria-hidden="true" className="trip-itinerary-toggle" />
                  </span>
                </summary>

                <div className="trip-itinerary-day-body">
                  <div className="trip-profile-form-grid">
                    <label className="trip-profile-field">
                      <span>Title</span>
                      <input
                        maxLength={140}
                        onChange={(event) =>
                          updateDay(day.clientId, { title: event.target.value })
                        }
                        placeholder="Arrival and readiness review"
                        readOnly={readOnly}
                        value={day.title}
                      />
                    </label>
                    <label className="trip-profile-field">
                      <span>Date label</span>
                      <input
                        maxLength={80}
                        onChange={(event) =>
                          updateDay(day.clientId, { dateLabel: event.target.value })
                        }
                        placeholder={`Day ${index + 1}`}
                        readOnly={readOnly}
                        value={day.dateLabel}
                      />
                    </label>
                  </div>

                  <RichTextEditor
                    height={260}
                    onJsonChange={(value) =>
                      updateDay(day.clientId, {
                        descriptionRichText: tiptapJsonToTripRichText(value),
                      })
                    }
                    placeholder="Describe the day's route, rhythm, meals, transfers, and readiness notes."
                    readOnly={readOnly}
                    value={tripRichTextToHtml(day.descriptionRichText)}
                  />
                </div>
              </details>
            );
          })}
        </div>
      )}
    </div>
  );
}

function TripPackagesSection({
  formErrors,
  onChange,
  packages,
  readOnly,
  readonlyReason,
  rowErrors,
  saveError,
}: {
  formErrors: string[];
  onChange: (packages: TripProfilePackageDraft[]) => void;
  packages: TripProfilePackageDraft[];
  readOnly: boolean;
  readonlyReason: string;
  rowErrors: PackageRowErrors;
  saveError: string;
}) {
  const addPackage = useCallback(() => {
    const nextPosition = packages.length + 1;
    onChange([
      ...packages,
      {
        clientId: `package-draft-${Date.now()}-${Math.random().toString(36).slice(2)}`,
        id: 0,
        name: "",
        description: "",
        priceInr: 0,
        reservationAmountInr: 0,
        position: nextPosition,
      },
    ]);
  }, [packages, onChange]);

  const updatePackage = useCallback(
    (
      clientId: string,
      updates: Partial<Omit<TripProfilePackageDraft, "clientId">>,
    ) => {
      onChange(
        packages.map((tripPackage) =>
          tripPackage.clientId === clientId
            ? {
                ...tripPackage,
                ...updates,
              }
            : tripPackage,
        ),
      );
    },
    [packages, onChange],
  );

  const movePackage = useCallback(
    (clientId: string, direction: -1 | 1) => {
      const currentIndex = packages.findIndex(
        (tripPackage) => tripPackage.clientId === clientId,
      );
      const nextIndex = currentIndex + direction;
      if (currentIndex < 0 || nextIndex < 0 || nextIndex >= packages.length) {
        return;
      }
      const nextPackages = [...packages];
      const [tripPackage] = nextPackages.splice(currentIndex, 1);
      nextPackages.splice(nextIndex, 0, tripPackage);
      onChange(nextPackages);
    },
    [packages, onChange],
  );

  const removePackage = useCallback(
    (clientId: string) => {
      onChange(packages.filter((tripPackage) => tripPackage.clientId !== clientId));
    },
    [packages, onChange],
  );

  return (
    <div className="trip-profile-section-body trip-package-editor">
      <div className="trip-package-command-row">
        <div>
          <span>Active Package catalog</span>
          <strong>
            {packages.length
              ? `${packages.length} Package${packages.length === 1 ? "" : "s"}`
              : "No Packages"}
          </strong>
        </div>
        <button disabled={readOnly} onClick={addPackage} type="button">
          <Plus aria-hidden="true" />
          <span>Add Package</span>
        </button>
      </div>

      {readonlyReason ? (
        <div className="trip-profile-readonly-callout">
          <LockKeyhole aria-hidden="true" />
          <span>{readonlyReason}</span>
        </div>
      ) : null}

      {[...formErrors, saveError].filter(Boolean).map((message) => (
        <div className="trip-description-error" key={message} role="alert">
          <AlertCircle aria-hidden="true" />
          <span>{message}</span>
        </div>
      ))}

      {packages.length === 0 ? (
        <div className="trip-package-empty">
          <CircleDot aria-hidden="true" />
          <div>
            <strong>Package needed</strong>
            <span>At least one active Package is required before publication.</span>
          </div>
          <button disabled={readOnly} onClick={addPackage} type="button">
            <Plus aria-hidden="true" />
            <span>Add Package</span>
          </button>
        </div>
      ) : (
        <div className="trip-package-table" role="table" aria-label="Packages">
          <div className="trip-package-table-head" role="row">
            <span>Order</span>
            <span>Package</span>
            <span>Package price</span>
            <span>Reservation Amount</span>
            <span>Description</span>
            <span>Actions</span>
          </div>

          {packages.map((tripPackage, index) => {
            const errors = rowErrors[tripPackage.clientId] ?? {};
            const packageLabel = tripPackage.name || `Package ${index + 1}`;
            const nameErrorId = `${tripPackage.clientId}-name-error`;
            const priceErrorId = `${tripPackage.clientId}-price-error`;
            const reservationErrorId = `${tripPackage.clientId}-reservation-error`;

            return (
              <div className="trip-package-row" key={tripPackage.clientId} role="row">
                <div className="trip-package-order" role="cell">
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  <em>Active</em>
                </div>

                <label className="trip-profile-field" role="cell">
                  <span>Package name</span>
                  <input
                    aria-describedby={errors.name ? nameErrorId : undefined}
                    aria-invalid={Boolean(errors.name)}
                    maxLength={140}
                    onChange={(event) =>
                      updatePackage(tripPackage.clientId, {
                        name: event.target.value,
                      })
                    }
                    placeholder="Standard shared room"
                    readOnly={readOnly}
                    value={tripPackage.name}
                  />
                  {errors.name ? (
                    <em className="trip-package-field-error" id={nameErrorId}>
                      {errors.name}
                    </em>
                  ) : null}
                </label>

                <label className="trip-profile-field trip-package-money-field" role="cell">
                  <span>Package price</span>
                  <input
                    aria-describedby={errors.priceInr ? priceErrorId : undefined}
                    aria-invalid={Boolean(errors.priceInr)}
                    inputMode="numeric"
                    min={1}
                    onChange={(event) =>
                      updatePackage(tripPackage.clientId, {
                        priceInr: parsePackageAmount(event.target.value),
                      })
                    }
                    placeholder="32000"
                    readOnly={readOnly}
                    type="number"
                    value={tripPackage.priceInr || ""}
                  />
                  {errors.priceInr ? (
                    <em className="trip-package-field-error" id={priceErrorId}>
                      {errors.priceInr}
                    </em>
                  ) : (
                    <em>{tripPackage.priceInr ? formatInr(tripPackage.priceInr) : ""}</em>
                  )}
                </label>

                <label className="trip-profile-field trip-package-money-field" role="cell">
                  <span>Reservation Amount</span>
                  <input
                    aria-describedby={
                      errors.reservationAmountInr ? reservationErrorId : undefined
                    }
                    aria-invalid={Boolean(errors.reservationAmountInr)}
                    inputMode="numeric"
                    min={1}
                    onChange={(event) =>
                      updatePackage(tripPackage.clientId, {
                        reservationAmountInr: parsePackageAmount(event.target.value),
                      })
                    }
                    placeholder="8000"
                    readOnly={readOnly}
                    type="number"
                    value={tripPackage.reservationAmountInr || ""}
                  />
                  {errors.reservationAmountInr ? (
                    <em className="trip-package-field-error" id={reservationErrorId}>
                      {errors.reservationAmountInr}
                    </em>
                  ) : (
                    <em>
                      {tripPackage.reservationAmountInr
                        ? formatInr(tripPackage.reservationAmountInr)
                        : ""}
                    </em>
                  )}
                </label>

                <label className="trip-profile-field" role="cell">
                  <span>Description</span>
                  <textarea
                    onChange={(event) =>
                      updatePackage(tripPackage.clientId, {
                        description: event.target.value,
                      })
                    }
                    placeholder="Rooming, inclusions, or operational terms"
                    readOnly={readOnly}
                    rows={2}
                    value={tripPackage.description}
                  />
                </label>

                <div className="trip-package-row-actions" role="cell">
                  <button
                    aria-label={`Move ${packageLabel} up`}
                    disabled={readOnly || index === 0}
                    onClick={() => movePackage(tripPackage.clientId, -1)}
                    type="button"
                  >
                    <ArrowUp aria-hidden="true" />
                  </button>
                  <button
                    aria-label={`Move ${packageLabel} down`}
                    disabled={readOnly || index === packages.length - 1}
                    onClick={() => movePackage(tripPackage.clientId, 1)}
                    type="button"
                  >
                    <ArrowDown aria-hidden="true" />
                  </button>
                  <button
                    aria-label={`Remove ${packageLabel}`}
                    disabled={readOnly}
                    onClick={() => removePackage(tripPackage.clientId)}
                    type="button"
                  >
                    <Trash2 aria-hidden="true" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function AccordionList({
  items,
}: {
  items: Array<{ body: JSX.Element; title: string }>;
}) {
  return (
    <div className="trip-profile-accordion-list">
      {items.map((item, index) => (
        <details key={item.title} open={index === 0}>
          <summary>
            <span>{item.title}</span>
            <ChevronDown aria-hidden="true" />
          </summary>
          {item.body}
        </details>
      ))}
    </div>
  );
}

function TripConfirmationRequirementsSection({
  onChange,
  readOnly,
  readonlyReason,
  requirements,
  saveError,
}: {
  onChange: (requirements: TripConfirmationRequirementsDraft) => void;
  readOnly: boolean;
  readonlyReason: string;
  requirements: TripConfirmationRequirementsDraft;
  saveError: string;
}) {
  const update = (
    key: keyof TripConfirmationRequirementsDraft,
    checked: boolean,
  ) => {
    onChange({
      ...requirements,
      [key]: checked,
    });
  };

  return (
    <div className="trip-profile-section-body">
      <AccordionList
        items={[
          {
            body: (
              <RequirementGrid
                onChange={update}
                readOnly={readOnly}
                requirements={requirements}
                rows={[
                  {
                    key: "travelerIdentityDetails",
                    label: "Traveler Identity Details",
                    detail: "Full name and phone on each Traveler Slot.",
                  },
                  {
                    key: "travelLogistics",
                    label: "Travel Logistics",
                    detail: "Arrival, departure, pickup, or logistics note.",
                  },
                  {
                    key: "emergencyContact",
                    label: "Emergency Contact",
                    detail: "Name, phone, and relationship.",
                  },
                ]}
              />
            ),
            title: "Traveler details",
          },
          {
            body: (
              <RequirementGrid
                onChange={update}
                readOnly={readOnly}
                requirements={requirements}
                rows={[
                  {
                    key: "travelerDocuments",
                    label: "Traveler Documents",
                    detail: "At least one approved document per traveler.",
                  },
                  {
                    key: "medicalDisclosure",
                    label: "Medical Disclosure",
                    detail: "Medical notes collected before confirmation.",
                  },
                  {
                    key: "fullPaymentBeforeConfirmation",
                    label: "Full Payment Before Confirmation",
                    detail: "No due balance before confirming the Booking.",
                  },
                ]}
              />
            ),
            title: "Readiness gates",
          },
        ]}
      />
      {saveError ? (
        <div className="trip-profile-save-error" role="alert">
          <AlertCircle aria-hidden="true" />
          <span>{saveError}</span>
        </div>
      ) : null}
      {readonlyReason ? (
        <p className="trip-profile-readonly-note">{readonlyReason}</p>
      ) : null}
    </div>
  );
}

function RequirementGrid({
  onChange,
  readOnly,
  requirements,
  rows,
}: {
  onChange: (
    key: keyof TripConfirmationRequirementsDraft,
    checked: boolean,
  ) => void;
  readOnly: boolean;
  requirements: TripConfirmationRequirementsDraft;
  rows: Array<{
    key: keyof TripConfirmationRequirementsDraft;
    label: string;
    detail: string;
  }>;
}) {
  return (
    <div className="trip-profile-requirement-grid">
      {rows.map((row) => (
        <label key={row.key}>
          <input
            checked={requirements[row.key]}
            disabled={readOnly}
            onChange={(event) => onChange(row.key, event.target.checked)}
            type="checkbox"
          />
          <span>
            <strong>{row.label}</strong>
            <em>{row.detail}</em>
          </span>
        </label>
      ))}
    </div>
  );
}

function headerSaveLabel({
  dirty,
  locked,
  needsReview,
  saving,
  sectionId,
}: {
  dirty: boolean;
  locked: boolean;
  needsReview: boolean;
  saving: boolean;
  sectionId: TripProfileSectionId;
}) {
  if (locked && sectionId !== "media") {
    return "Read-only";
  }

  if (saving) {
    return needsReview ? "Marking ready" : "Saving";
  }

  if (needsReview && dirty) {
    return "Save and mark ready";
  }

  if (needsReview) {
    return "Mark ready";
  }

  return "Save changes";
}

function saveStateLabel({
  dirty,
  locked,
  needsReview,
  pendingSectionLabel,
  readonlyReason,
  saved,
  saving,
  sectionId,
}: {
  dirty: boolean;
  locked: boolean;
  needsReview: boolean;
  pendingSectionLabel: string;
  readonlyReason: string;
  saved: boolean;
  saving: boolean;
  sectionId: TripProfileSectionId;
}) {
  if (locked && sectionId !== "media") {
    return "Published profile is read-only";
  }

  if (readonlyReason) {
    return readonlyReason;
  }

  if (saving) {
    if (pendingSectionLabel) {
      return `Saving before opening ${pendingSectionLabel}`;
    }

    return "Saving section";
  }

  if (dirty) {
    return "Unsaved changes";
  }

  if (needsReview) {
    return "Review required";
  }

  if (saved) {
    return "Section saved";
  }

  return "No local changes";
}

function sectionBadgeLabel(section: TripProfileSectionState) {
  if (section.tone === "readonly") {
    return section.locked ? "Ready" : "Review";
  }

  if (section.tone === "attention") {
    return "Encouraged";
  }

  if (section.tone === "clear") {
    return "Ready";
  }

  return section.stateLabel.toLowerCase().includes("review")
    ? "Review"
    : "Needed";
}

function sectionBadgeTone(section: TripProfileSectionState): TripProfileTone {
  if (section.tone === "readonly" && section.locked) {
    return "clear";
  }

  return section.tone;
}

function nextRequiredActionLabel(item: TripProfileReadinessItem) {
  switch (item.sectionId) {
    case "description":
      return "Add trip description";
    case "itinerary":
      return "Add itinerary day";
    case "media":
      return "Add public trip media";
    case "packages":
      return "Add package";
    case "payment-schedule":
      return "Review balance payment schedule";
    case "requirements":
      return "Review confirmation requirements";
  }
}

function toneClass(tone: TripProfileTone) {
  switch (tone) {
    case "blocked":
      return "is-blocked";
    case "attention":
      return "is-attention";
    case "clear":
      return "is-clear";
    case "readonly":
      return "is-readonly";
  }
}

function itineraryDayToDraft(day: TripItineraryDay, index: number): ItineraryDayDraft {
  return {
    clientId: day.id ? `itinerary-day-${day.id}` : `itinerary-day-draft-${index + 1}`,
    id: day.id,
    sequence: index + 1,
    title: day.title,
    dateLabel: day.dateLabel,
    descriptionRichText: day.descriptionRichText,
  };
}

function itineraryDraftToDay(day: ItineraryDayDraft, index: number): TripItineraryDay {
  return {
    id: day.id,
    sequence: index + 1,
    title: day.title.trim(),
    dateLabel: day.dateLabel.trim(),
    descriptionRichText: day.descriptionRichText,
    descriptionPlainText: getTripRichTextPlainText(day.descriptionRichText),
  };
}

function sameTripRichText(
  current: TripRichTextDocument,
  saved: TripRichTextDocument,
): boolean {
  return comparableJson(normalizeTripRichText(current)) ===
    comparableJson(normalizeTripRichText(saved));
}

function sameTripItineraryDays(
  current: TripItineraryDay[],
  saved: TripItineraryDay[],
): boolean {
  return comparableJson(current.map(comparableItineraryDay)) ===
    comparableJson(saved.map(comparableItineraryDay));
}

function comparableItineraryDay(day: TripItineraryDay, index: number) {
  return {
    id: day.id,
    sequence: index + 1,
    title: day.title.trim(),
    dateLabel: day.dateLabel.trim(),
    descriptionRichText: normalizeTripRichText(day.descriptionRichText),
  };
}

function resequenceItineraryDrafts(days: ItineraryDayDraft[]): ItineraryDayDraft[] {
  return days.map((day, index) => ({
    ...day,
    sequence: index + 1,
  }));
}

function tripPackageToDraft(
  tripPackage: TripProfilePackage,
  index: number,
): TripProfilePackageDraft {
  return {
    clientId: tripPackage.id
      ? `package-${tripPackage.id}`
      : `package-draft-${index + 1}`,
    id: tripPackage.id,
    name: tripPackage.name,
    description: tripPackage.description,
    priceInr: tripPackage.priceInr,
    reservationAmountInr: tripPackage.reservationAmountInr,
    position: index + 1,
  };
}

function packageDraftToPackage(
  tripPackage: TripProfilePackageDraft,
  index: number,
): TripProfilePackage {
  return {
    id: tripPackage.id,
    name: tripPackage.name.trim(),
    description: tripPackage.description.trim(),
    priceInr: tripPackage.priceInr,
    reservationAmountInr: tripPackage.reservationAmountInr,
    position: index + 1,
  };
}

function sameTripPackages(
  current: TripProfilePackage[],
  saved: TripProfilePackage[],
): boolean {
  return comparableJson(current.map(comparablePackage)) ===
    comparableJson(saved.map(comparablePackage));
}

function comparablePackage(tripPackage: TripProfilePackage, index: number) {
  return {
    id: tripPackage.id,
    name: tripPackage.name.trim(),
    description: tripPackage.description.trim(),
    priceInr: tripPackage.priceInr,
    reservationAmountInr: tripPackage.reservationAmountInr,
    position: index + 1,
  };
}

function resequencePackageDrafts(
  packages: TripProfilePackageDraft[],
): TripProfilePackageDraft[] {
  return packages.map((tripPackage, index) => ({
    ...tripPackage,
    position: index + 1,
  }));
}

function mediaItemToDraft(
  item: TripMediaItem,
  index: number,
): TripMediaItemDraft {
  return {
    ...item,
    clientId: item.id ? `media-${item.id}` : `media-draft-${index + 1}`,
    position: index + 1,
  };
}

function mediaDraftToItem(item: TripMediaItemDraft): TripMediaItem {
  return {
    id: item.id,
    assetId: item.assetId,
    imageUrl: item.imageUrl,
    originalFilename: item.originalFilename,
    contentType: item.contentType,
    fileSize: item.fileSize,
    position: item.position,
    caption: item.caption.trim(),
    altText: item.altText.trim(),
    isPublic: item.isPublic,
    isCover: item.isCover,
  };
}

function sameTripMediaItems(
  current: TripMediaItem[],
  saved: TripMediaItem[],
): boolean {
  return comparableJson(current.map(comparableMediaItem)) ===
    comparableJson(saved.map(comparableMediaItem));
}

function comparableMediaItem(item: TripMediaItem, index: number) {
  return {
    id: item.id,
    assetId: item.assetId,
    imageUrl: item.imageUrl,
    originalFilename: item.originalFilename,
    contentType: item.contentType,
    fileSize: item.fileSize,
    position: index + 1,
    caption: item.caption.trim(),
    altText: item.altText.trim(),
    isPublic: item.isPublic,
    isCover: item.isCover,
  };
}

function resequenceMediaDrafts(items: TripMediaItemDraft[]): TripMediaItemDraft[] {
  return ensureMediaCover(
    items.map((item, index) => ({
      ...item,
      position: index + 1,
    })),
  );
}

function ensureMediaCover(items: TripMediaItemDraft[]): TripMediaItemDraft[] {
  if (items.length === 0) {
    return [];
  }

  const coverIndex = items.findIndex((item) => item.isCover);
  if (coverIndex < 0) {
    return items.map((item, index) => ({
      ...item,
      isCover: index === 0,
    }));
  }

  return items.map((item, index) => ({
    ...item,
    isCover: index === coverIndex,
  }));
}

function samePaymentSchedules(
  current: TripPaymentScheduleDraft,
  saved: TripPaymentScheduleDraft,
): boolean {
  return comparableJson({
    hasBalanceMilestone: current.hasBalanceMilestone,
    balanceDueDaysBeforeStart: current.hasBalanceMilestone
      ? current.balanceDueDaysBeforeStart
      : null,
    balanceReminderLeadDays: current.balanceReminderLeadDays,
  }) ===
    comparableJson({
      hasBalanceMilestone: saved.hasBalanceMilestone,
      balanceDueDaysBeforeStart: saved.hasBalanceMilestone
        ? saved.balanceDueDaysBeforeStart
        : null,
      balanceReminderLeadDays: saved.balanceReminderLeadDays,
    });
}

function sameConfirmationRequirements(
  current: TripConfirmationRequirementsDraft,
  saved: TripConfirmationRequirementsDraft,
): boolean {
  return comparableJson(current) === comparableJson(saved);
}

function comparableJson(value: unknown): string {
  return JSON.stringify(value);
}

function parsePackageAmount(value: string): number {
  if (!value) {
    return 0;
  }
  return Number(value);
}

function parsePaymentScheduleNumber(value: string): number {
  if (!value) {
    return 0;
  }
  return Number(value);
}

function parseOptionalPositiveInteger(value: string): number | null {
  if (!value) {
    return null;
  }
  return Number(value);
}

function formatInr(amount: number): string {
  return new Intl.NumberFormat("en-IN", {
    currency: "INR",
    maximumFractionDigits: 0,
    style: "currency",
  }).format(amount);
}
