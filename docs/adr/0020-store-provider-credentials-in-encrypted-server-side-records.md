# Store Provider Credentials in Encrypted Server-Side Records

TripOS will store **Sensitive Provider Credentials** in dedicated server-side records encrypted at rest with an application-managed encryption key, not in Organizer Profile or Provider Payment Setup records. This keeps organizer-facing payment setup facts separate from credential material while avoiding the deployment complexity of a managed secrets vault during the MVP; the storage boundary can later move behind a vault without changing the domain model.
