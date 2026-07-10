# cert_generator.py
# Generates a professional disposal certificate PDF

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
import os


def generate_disposal_certificate(cert: dict, output_path: str = None) -> str:
    """
    Generates a PDF disposal certificate for a medicine batch.
    Returns the file path of the generated PDF.
    """
    if not output_path:
        cert_id = cert.get("certificate_id", "CERT-UNKNOWN")
        output_path = f"backend/certificates/{cert_id}.pdf"

    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )

    # ── Colors ────────────────────────────────────────────
    TEAL       = colors.HexColor("#006951")
    TEAL_LIGHT = colors.HexColor("#e0f5ee")
    DARK       = colors.HexColor("#0f1f1a")
    GRAY       = colors.HexColor("#6d7a74")
    RED        = colors.HexColor("#dc2626")
    RED_LIGHT  = colors.HexColor("#fef2f2")
    WHITE      = colors.white
    BORDER     = colors.HexColor("#e0e8e4")

    # ── Styles ────────────────────────────────────────────
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "title", fontSize=22, fontName="Helvetica-Bold",
        textColor=TEAL, alignment=TA_CENTER, spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        "subtitle", fontSize=11, fontName="Helvetica",
        textColor=GRAY, alignment=TA_CENTER, spaceAfter=2
    )
    cert_id_style = ParagraphStyle(
        "cert_id", fontSize=13, fontName="Helvetica-Bold",
        textColor=DARK, alignment=TA_CENTER, spaceAfter=2
    )
    section_style = ParagraphStyle(
        "section", fontSize=10, fontName="Helvetica-Bold",
        textColor=TEAL, spaceAfter=6, spaceBefore=10,
        borderPad=4
    )
    body_style = ParagraphStyle(
        "body", fontSize=10, fontName="Helvetica",
        textColor=DARK, spaceAfter=4
    )
    small_style = ParagraphStyle(
        "small", fontSize=8, fontName="Helvetica",
        textColor=GRAY, alignment=TA_CENTER
    )
    warning_style = ParagraphStyle(
        "warning", fontSize=9, fontName="Helvetica-Bold",
        textColor=RED, alignment=TA_CENTER
    )

    story = []

    # ── Header ────────────────────────────────────────────
    story.append(Paragraph("MedChain", title_style))
    story.append(Paragraph("Pharmaceutical Redistribution & Lifecycle Management Network", subtitle_style))
    story.append(Spacer(1, 4*mm))
    story.append(HRFlowable(width="100%", thickness=2, color=TEAL))
    story.append(Spacer(1, 4*mm))

    story.append(Paragraph("PHARMACEUTICAL DISPOSAL CERTIFICATE", cert_id_style))
    story.append(Paragraph(f"Certificate ID: {cert.get('certificate_id','—')}", cert_id_style))
    story.append(Spacer(1, 2*mm))

    # Status badge table
    status = cert.get("status","SCHEDULED")
    status_color = TEAL if status == "COMPLETED" else colors.HexColor("#d97706")
    status_data = [[Paragraph(f"STATUS: {status}", ParagraphStyle("s", fontSize=10, fontName="Helvetica-Bold", textColor=WHITE, alignment=TA_CENTER))]]
    status_table = Table(status_data, colWidths=[80*mm])
    status_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), status_color),
        ("ROUNDEDCORNERS", [4]),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
    ]))
    story.append(status_table)
    story.append(Spacer(1, 6*mm))

    # ── Issued info ───────────────────────────────────────
    issued_at = cert.get("issued_at","")
    try:
        dt = datetime.fromisoformat(issued_at)
        issued_str = dt.strftime("%d %B %Y at %H:%M UTC")
    except:
        issued_str = issued_at

    info_data = [
        ["Issued At", issued_str],
        ["Pickup Date", cert.get("pickup_date","—")],
        ["Compliance Framework", cert.get("compliance_note","—")],
        ["Authority", cert.get("cpcb_auth","—")],
    ]
    info_table = Table(info_data, colWidths=[55*mm, 115*mm])
    info_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (0,-1), TEAL_LIGHT),
        ("FONTNAME",      (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME",      (1,0), (1,-1), "Helvetica"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("TEXTCOLOR",     (0,0), (0,-1), TEAL),
        ("TEXTCOLOR",     (1,0), (1,-1), DARK),
        ("GRID",          (0,0), (-1,-1), 0.5, BORDER),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 5*mm))

    # ── Medicine details ──────────────────────────────────
    story.append(Paragraph("▸  MEDICINE DETAILS", section_style))
    med_data = [
        ["Field", "Value"],
        ["Drug Name",    cert.get("drug_name","—")],
        ["Quantity",     f"{cert.get('quantity','—')} units"],
        ["Expiry Date",  cert.get("expiry_date","—")],
        ["Surplus ID",   cert.get("surplus_id","—")],
        ["Sender / Hospital", cert.get("sender_id","—")],
        ["Disposal Method",   cert.get("disposal_method","INCINERATION")],
    ]
    med_table = Table(med_data, colWidths=[55*mm, 115*mm])
    med_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), TEAL),
        ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("BACKGROUND",    (0,1), (0,-1), TEAL_LIGHT),
        ("FONTNAME",      (0,1), (0,-1), "Helvetica-Bold"),
        ("FONTNAME",      (1,1), (1,-1), "Helvetica"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("TEXTCOLOR",     (0,1), (0,-1), TEAL),
        ("TEXTCOLOR",     (1,1), (1,-1), DARK),
        ("GRID",          (0,0), (-1,-1), 0.5, BORDER),
        ("TOPPADDING",    (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE, colors.HexColor("#f8fafb")]),
    ]))
    story.append(med_table)
    story.append(Spacer(1, 5*mm))

    # ── Facility details ──────────────────────────────────
    story.append(Paragraph("▸  AUTHORIZED DISPOSAL FACILITY", section_style))
    fac_data = [
        ["Field", "Value"],
        ["Facility Name",     cert.get("facility_name","—")],
        ["Facility ID",       cert.get("facility_id","—")],
        ["Location",          cert.get("facility_location","—")],
        ["Contact",           cert.get("facility_contact","—")],
        ["Authorization",     "CPCB Licensed — Bio-Medical Waste Management Rules 2016"],
    ]
    fac_table = Table(fac_data, colWidths=[55*mm, 115*mm])
    fac_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), DARK),
        ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("BACKGROUND",    (0,1), (0,-1), TEAL_LIGHT),
        ("FONTNAME",      (0,1), (0,-1), "Helvetica-Bold"),
        ("FONTNAME",      (1,1), (1,-1), "Helvetica"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("TEXTCOLOR",     (0,1), (0,-1), TEAL),
        ("TEXTCOLOR",     (1,1), (1,-1), DARK),
        ("GRID",          (0,0), (-1,-1), 0.5, BORDER),
        ("TOPPADDING",    (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[WHITE, colors.HexColor("#f8fafb")]),
    ]))
    story.append(fac_table)
    story.append(Spacer(1, 6*mm))

    # ── Compliance warning ────────────────────────────────
    warn_data = [[Paragraph(
        "⚠ This certificate confirms that the above pharmaceutical batch has been routed for safe disposal "
        "in compliance with the Bio-Medical Waste Management Rules 2016 (India). "
        "Unauthorized disposal of pharmaceutical waste is a criminal offence under the Environment Protection Act 1986.",
        ParagraphStyle("w", fontSize=8, fontName="Helvetica", textColor=RED, alignment=TA_CENTER)
    )]]
    warn_table = Table(warn_data, colWidths=[170*mm])
    warn_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), RED_LIGHT),
        ("BOX",           (0,0),(-1,-1), 1, RED),
        ("TOPPADDING",    (0,0),(-1,-1), 8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8),
        ("LEFTPADDING",   (0,0),(-1,-1), 10),
        ("RIGHTPADDING",  (0,0),(-1,-1), 10),
    ]))
    story.append(warn_table)
    story.append(Spacer(1, 6*mm))

    # ── Footer ────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        f"Generated by MedChain v2.0 — Pharmaceutical Lifecycle Management Network | "
        f"{datetime.utcnow().strftime('%d %B %Y')} | "
        f"Certificate: {cert.get('certificate_id','—')}",
        small_style
    ))

    # ── Build PDF ─────────────────────────────────────────
    doc.build(story)
    print(f"[CERT] PDF generated → {output_path}")
    return output_path
