# Bookings Can Contain Multiple Travelers

TripOS will model a **Booking** as a reservation container that can include one or more **Travelers** under one **Booking Contact**. This matches real group-trip purchase behavior, where one person may coordinate and pay for multiple attendees, and avoids splitting shared deposits, balances, cancellations, and reminders across artificial per-traveler bookings.
