# TripOS Worker Runtime

The worker runtime runs current TripOS background work outside request/response paths. Today that means processing due Automatic Reminders through the same Django settings, models, and transaction behavior as the API.

Run locally:

```sh
just worker
```
