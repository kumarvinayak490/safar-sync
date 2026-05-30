# Store Trip Rich Text as structured JSON

Trip Profile introduces constrained rich text for Trip Description and Itinerary Day descriptions. Store this content as structured JSON rather than sanitized HTML so TripOS can validate allowed content nodes, keep storage separate from public rendering, and avoid turning profile content into arbitrary page markup.

**Considered Options**

- Structured JSON: preferred because it matches constrained editing, controlled rendering, and long-term validation.
- Sanitized HTML: faster to render but mixes persistence with presentation and makes future content constraints harder to enforce.

**Consequences**

TripOS needs a controlled renderer for Public Trip Page and workspace previews. Images remain in Trip Media Gallery rather than being embedded inside rich text.
