# Organizer Profile

Organizer Profile owns public organizer identity and publication behavior:
public organizer name, Organizer Logo handling, public contact channel payloads,
Public Organizer Description, Organizer Profile Publication State, publication
readiness, and the stable profile identity API behavior composed by the legacy
Organizer URLs.

Some persisted identity fields still live on the `Organizer` table during this
migration stage. Organizer Profile owns the publication record. Historical
Organizer import paths re-export this app's behavior until callers move to
`organizer_profile`.

Organizer Profile Readiness requires Public Organizer Description plus the
required Organizer Policies. Public Organizer Media is encouraged but not
required for publishing.
