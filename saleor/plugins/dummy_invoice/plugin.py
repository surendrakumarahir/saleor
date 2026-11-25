from django.core.files.base import ContentFile
from django.utils.timezone import now

from ...core import JobStatus
from ...invoice.models import Invoice
from ..base_plugin import BasePlugin
from .pdf_generator import generate_invoice_pdf


class DummyInvoicePlugin(BasePlugin):
    PLUGIN_ID = "custom.invoice.dummy"
    PLUGIN_NAME = "Dummy Invoice"
    PLUGIN_DESCRIPTION = "A local development dummy invoice generator plugin."
    DEFAULT_ACTIVE = True
    CONFIGURATION_PER_CHANNEL = False

    def invoice_request(
        self,
        order,
        invoice,
        number,
        previous_value,
    ):
        invoice_number = number or f"INV-{order.id}-{int(now().timestamp())}"
        invoice.number = invoice_number
        invoice.status = JobStatus.SUCCESS

        # Generate the PDF file bytes using reportlab
        pdf_bytes = generate_invoice_pdf(order, invoice_number)

        # Save to Django's FileField
        filename = f"invoice_{invoice_number}.pdf"
        invoice.invoice_file.save(filename, ContentFile(pdf_bytes), save=False)

        invoice.save()
        return invoice
