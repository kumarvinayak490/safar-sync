# Make Public Discovery a Top-Level Module

TripOS will treat Public Discovery as a top-level domain module in the modular monolith.

Public Discovery owns Demand Pages, Discovery SEO Metadata, Discovery Routing, and Discovery Listing Rules. It can compose public discovery experiences from Published Organizer Profile and published Public Trip Pages. Organizer Public URLs and discovery-facing Public Trip URLs may live in Public Discovery routing.

Public Discovery does not own Organizer Profile content, Organizer Media, Organizer Policies, Organizer Profile publication state, Public Trip Page content, Public Trip Page publication state, booking gates, booking URLs, checkout behavior, payments, or trip operations. Those remain in their source domains and are only linked or summarized by discovery surfaces.

This keeps SEO and demand distribution explicit without turning TripOS into a marketplace owner of booking, settlement, reviews, or trip fulfillment. The tradeoff is that discovery pages must depend on published projections from Organizer and Trip domains instead of editing those source records directly.
