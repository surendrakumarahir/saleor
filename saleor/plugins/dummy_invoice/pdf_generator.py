from io import BytesIO
from django.utils.timezone import now
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER


def generate_invoice_pdf(order, invoice_number: str) -> bytes:
    buffer = BytesIO()

    # 0.75 inch margins
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    style_normal = ParagraphStyle(
        "InvoiceNormal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#2B2D42"),
    )

    style_bold = ParagraphStyle(
        "InvoiceBold", parent=style_normal, fontName="Helvetica-Bold"
    )

    style_header_title = ParagraphStyle(
        "InvoiceHeaderTitle",
        parent=style_normal,
        fontName="Helvetica-Bold",
        fontSize=26,
        leading=30,
        textColor=colors.HexColor("#4F6D7A"),
        alignment=TA_RIGHT,
    )

    style_company_tagline = ParagraphStyle(
        "InvoiceCompanyTagline",
        parent=style_normal,
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#7F8C8D"),
    )

    story = []

    # --- HEADER SECTION ---
    # Logo image path (converted from logo.svg to logo.png)
    logo_path = "/app/saleor/static/logo.png"
    logo_img = None
    try:
        # Scale to height 30 and width 106 to preserve the 3.52 aspect ratio
        logo_img = Image(logo_path, width=106, height=30)
    except Exception:
        pass

    # Company Info (Left Column)
    company_info = []
    if logo_img:
        company_info.append(logo_img)
        company_info.append(Spacer(1, 4))
    company_info.extend([
        Paragraph("YOUR ONLINE BOOKSTORE", style_company_tagline),
        Spacer(1, 6),
        Paragraph(
            "Easytopick Bookstore<br/>Website: easytopick.in<br/>Email: easytopickin@gmail.com",
            style_normal,
        ),
    ])

    header_left_table = Table([[company_info]], colWidths=[260])
    header_left_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    # Invoice Metadata (Right Column)
    invoice_title = Paragraph("INVOICE", style_header_title)

    # Get last 4 digits of invoice number
    display_number = invoice_number[-4:] if len(invoice_number) >= 4 else invoice_number

    # Box for Invoice # and Date
    invoice_box_style_key = ParagraphStyle(
        "InvoiceBoxKey",
        parent=style_normal,
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=colors.white,
        alignment=TA_CENTER,
    )

    invoice_box_data = [
        [
            Paragraph(
                f"INVOICE # {display_number} &nbsp;|&nbsp; DATE: {now().strftime('%d / %m / %Y')}",
                invoice_box_style_key,
            )
        ]
    ]
    invoice_box_table = Table(invoice_box_data, colWidths=[240])
    invoice_box_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#4F6D7A")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    header_right = [invoice_title, Spacer(1, 10), invoice_box_table]

    header_table = Table([[header_left_table, header_right]], colWidths=[260, 244])
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    story.append(header_table)
    story.append(Spacer(1, 24))

    # --- BILL TO SECTION ---
    bill_to_title_style = ParagraphStyle(
        "BillToTitle",
        parent=style_bold,
        textColor=colors.white,
        fontSize=10,
        leading=12,
    )

    # Added hAlign='LEFT' to left-align the Bill to table
    bill_to_header = Table(
        [[Paragraph("Bill to:", bill_to_title_style)]], colWidths=[100], hAlign="LEFT"
    )
    bill_to_header.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#4F6D7A")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    story.append(bill_to_header)
    story.append(Spacer(1, 6))

    # Format Customer Address
    addr = order.billing_address
    if addr:
        addr_lines = [
            f"{addr.first_name} {addr.last_name}",
            addr.street_address_1,
            addr.street_address_2,
            f"{addr.city}, {addr.postal_code}",
            str(addr.country),
        ]
        addr_lines = [line for line in addr_lines if line and line.strip()]
        addr_text = "<br/>".join(addr_lines)
    else:
        addr_text = order.user_email or "Guest Customer"

    story.append(Paragraph(addr_text, style_normal))
    story.append(Spacer(1, 24))

    # --- PRODUCTS TABLE SECTION (INCLUDING TOTALS) ---
    table_header_style = ParagraphStyle(
        "TableHeader", parent=style_bold, textColor=colors.white, alignment=TA_CENTER
    )
    table_header_style_left = ParagraphStyle(
        "TableHeaderLeft", parent=style_bold, textColor=colors.white, alignment=TA_LEFT
    )

    table_data = [
        [
            Paragraph("QTY", table_header_style),
            Paragraph("PRODUCT DESCRIPTION", table_header_style_left),
            Paragraph("PRICE", table_header_style),
            Paragraph("TOTAL", table_header_style),
        ]
    ]

    # Order items
    currency = order.currency
    for line in order.lines.all():
        qty = line.quantity
        product_name = line.product_name
        variant_name = line.variant_name
        desc = f"{product_name} ({variant_name})" if variant_name else product_name

        price = f"{currency} {line.unit_price_gross_amount:.2f}"
        total_price = f"{currency} {line.total_price_gross_amount:.2f}"

        style_desc = ParagraphStyle("ProductDesc", parent=style_normal, alignment=TA_LEFT)
        style_center = ParagraphStyle(
            "ProductCenter", parent=style_normal, alignment=TA_CENTER
        )

        table_data.append(
            [
                Paragraph(str(qty), style_center),
                Paragraph(desc, style_desc),
                Paragraph(price, style_center),
                Paragraph(total_price, style_center),
            ]
        )

    # Summary rows (Subtotal, Shipping, Tax, Total) appended to the same table_data
    summary_label_style = ParagraphStyle(
        "SummaryLabel", parent=style_bold, alignment=TA_RIGHT
    )
    summary_value_style = ParagraphStyle(
        "SummaryValue", parent=style_normal, alignment=TA_CENTER
    )
    summary_label_white_style = ParagraphStyle(
        "SummaryLabelWhite",
        parent=style_bold,
        textColor=colors.white,
        alignment=TA_RIGHT,
    )
    summary_value_white_style = ParagraphStyle(
        "SummaryValueWhite",
        parent=style_bold,
        textColor=colors.white,
        alignment=TA_CENTER,
    )

    subtotal_str = f"{currency} {order.subtotal_gross_amount:.2f}"
    shipping_str = f"{currency} {order.shipping_price_gross_amount:.2f}"
    total_str = f"{currency} {order.total_gross_amount:.2f}"

    table_data.append([
        "",
        "",
        Paragraph("Subtotal", summary_label_style),
        Paragraph(subtotal_str, summary_value_style),
    ])
    table_data.append([
        "",
        "",
        Paragraph("Shipping", summary_label_style),
        Paragraph(shipping_str, summary_value_style),
    ])
    table_data.append([
        "",
        "",
        Paragraph("Tax Rate", summary_label_style),
        Paragraph("0.00%", summary_value_style),
    ])
    table_data.append([
        "",
        "",
        Paragraph("TOTAL", summary_label_white_style),
        Paragraph(total_str, summary_value_white_style),
    ])

    item_rows_count = len(order.lines.all())

    # QTY=50pt, DESC=280pt, PRICE=87pt, TOTAL=87pt (Total 504pt)
    items_table = Table(table_data, colWidths=[50, 280, 87, 87])

    t_style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4F6D7A")),
        # Grid for the header and product lines
        ("GRID", (0, 0), (-1, item_rows_count), 0.5, colors.HexColor("#D8E2DC")),
        # Grid/border ONLY for the summary columns (2 & 3) of summary rows
        ("GRID", (2, item_rows_count + 1), (3, -1), 0.5, colors.HexColor("#D8E2DC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]

    # Alternating row background for product lines only
    for i in range(1, item_rows_count + 1):
        if i % 2 == 0:
            t_style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F9FBFB")))

    # Slate gray background for the TOTAL summary row columns 2 and 3
    t_style.append(("BACKGROUND", (2, -1), (3, -1), colors.HexColor("#4F6D7A")))

    items_table.setStyle(TableStyle(t_style))
    story.append(items_table)
    story.append(Spacer(1, 30))

    # --- FOOTER SECTION ---
    thanks_style = ParagraphStyle(
        "ThanksMsg",
        parent=style_bold,
        fontSize=12,
        textColor=colors.HexColor("#4F6D7A"),
        alignment=TA_LEFT,
    )
    footer_note_style = ParagraphStyle(
        "FooterNote", parent=style_normal, fontSize=8, textColor=colors.HexColor("#7F8C8D")
    )

    story.append(Paragraph("THANK YOU FOR YOUR BUSINESS", thanks_style))
    story.append(Spacer(1, 8))

    payment_message = "Payment is due max 7 days after invoice without deduction."
    if order.charge_status == "full":
        payment_message = "Thank you! This invoice has been fully paid."
    elif order.payments.filter(gateway="mirumee.payments.cod").exists():
        payment_message = "Cash on Delivery Order: Payment to be collected in cash at the time of delivery."

    story.append(Paragraph(payment_message, footer_note_style))
    story.append(
        Paragraph(
            "If you have any questions about this invoice, please contact us at easytopickin@gmail.com",
            footer_note_style,
        )
    )

    doc.build(story)

    pdf_content = buffer.getvalue()
    buffer.close()
    return pdf_content
