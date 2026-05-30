# Reuse Trip Media assets when duplicating Trips

Trip Duplicate should create independent Trip Media Item records for ordering, captions, public visibility, and cover selection, but reuse the same immutable stored image assets in the MVP. This avoids wasteful file copying while preserving the duplicate Trip Profile as independently editable before publication.

**Consequences**

Replacing a media file in a future release should create a new stored image asset rather than mutating a shared asset that another trip may reference.
