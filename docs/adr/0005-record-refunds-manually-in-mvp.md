# Record Refunds Manually in the MVP

TripOS will record refunds manually through **Refund Records** in the MVP instead of initiating refunds through payment provider APIs. Creating a **Refund Record** requires an **Owner**, because refund amounts and eligibility are organizer-controlled financial decisions; provider refund orchestration would add partial-refund, settlement, fee, failure, and reconciliation complexity before the core operations workflow is proven.
