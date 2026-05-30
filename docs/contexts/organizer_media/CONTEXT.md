# Organizer Media Context

This context covers organizer-level public media and reuse across organizer, trip, and future creative surfaces.

## Language

**Organizer Media**:
The organizer-owned media library for public trust, discovery, and creative reuse across organizer and trip surfaces.
_Avoid_: Organizer profile identity, trip media gallery, traveler documents, operational files

**Public Organizer Media**:
Organizer media selected or marked for public organizer discovery and trust surfaces.
_Avoid_: Trip media gallery, traveler documents, operational files

**Trip Media Gallery**:
The ordered media gallery for a trip profile.
_Avoid_: Operational files, traveler documents, social feed

**Trip Media Item**:
An uploaded media asset in a trip media gallery.
_Avoid_: External URL, document

## Relationships

- An **Organizer** has **Organizer Media**.
- **Organizer Media** owns organizer-level uploads, captions, ordering, visibility, and reuse.
- **Public Organizer Media** belongs to **Organizer Media**, not to **Organizer Profile** or **Trip Profile**.
- **Organizer Profile** can display **Public Organizer Media**.
- **Public Organizer Media** can remain visible even if an older **Trip** is archived.
- **Trip Media Gallery** and **Public Organizer Media** are separate public media collections.
- **Organizer Media** can support **Organizer Public Pages**, **Public Trip Pages**, and future creative generation.

## Flagged Ambiguities

- "organizer media" could be buried inside profile content — resolved: **Organizer Media** is its own organizer submodule, while **Organizer Profile** only displays selected public media.
- "media URLs" could make public pages depend on external hotlinks — resolved: MVP uploaded media is stored by TripOS, not hotlinked from external image URLs.
