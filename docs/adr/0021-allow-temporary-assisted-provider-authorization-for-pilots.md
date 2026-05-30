# Allow Temporary Assisted Provider Authorization for Pilots

TripOS will keep **OAuth Provider Authorization** as the normal connected-account path, but may use **Assisted Payment Setup** with encrypted API-key credentials for tightly controlled pilots if Razorpay Partner OAuth is not yet available. This fallback is hidden from normal organizer-facing setup and treated as temporary so pilot payment collection is not blocked while preserving the long-term connected-account model.
