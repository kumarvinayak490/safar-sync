# Derive Available Seats from Reserved Travelers

TripOS will derive **Available Seats** from **Trip Capacity** minus active reserved travelers, rather than storing available seats as editable truth. This keeps capacity consistent when bookings reserve seats, traveler cancellations release seats, traveler replacements preserve seats, and draft bookings remain outside operational counts.
