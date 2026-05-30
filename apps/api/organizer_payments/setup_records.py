from __future__ import annotations

from organizer_payments.models import PayoutAccount, ProviderPaymentSetup
from organizers.models import Organizer


def ensure_payment_setup_records(organizer: Organizer) -> None:
    PayoutAccount.objects.get_or_create(organizer=organizer)
    ProviderPaymentSetup.objects.get_or_create(organizer=organizer)
