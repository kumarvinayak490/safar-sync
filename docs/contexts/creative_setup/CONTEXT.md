# Creative Setup Context

This context covers organizer-level creative generation preferences.

## Language

**Creative Setup**:
Organizer-level preferences used by TripOS-assisted creative generation, including model choice, brand tone, default style, logo usage, and poster defaults.
_Avoid_: Organizer preferences, generated posters, trip creative assets, organizer profile, public content, trip itinerary, design system

## Relationships

- An **Organizer** has **Creative Setup**.
- **Organizer Settings** can link to **Creative Setup** in the user interface, but does not own **Creative Setup**.
- **Creative Setup** owns organizer-level creative generation preferences, not generated creative assets.
- Generated posters, itinerary posters, seats-left posters, and other trip-specific creative assets are scoped to the relevant **Trip**.
- **Organizer Preferences** is not a first-version domain term.

## Flagged Ambiguities

- "creative setup" could become a storage area for generated trip posters — resolved: **Creative Setup** owns organizer-level generation preferences only; generated creative assets are trip-scoped.
- "organizer preferences" could become a replacement junk drawer — resolved: do not introduce **Organizer Preferences** in the first version; use **Creative Setup** as the concrete preference domain.
