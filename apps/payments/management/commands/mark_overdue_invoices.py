from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.payments.models import CreditInvoice


class Command(BaseCommand):
    help = "Tandai invoice kredit UNPAID yang sudah lewat jatuh tempo menjadi OVERDUE."

    def handle(self, *args, **options):
        today = timezone.now().date()
        qs = CreditInvoice.objects.filter(status='UNPAID', due_date__lt=today)
        count = qs.update(status='OVERDUE')
        self.stdout.write(
            self.style.SUCCESS(f"{count} invoice ditandai OVERDUE (per {today:%d %b %Y}).")
        )
