"""
Professional PDF Agreement Generator
Generates visually appealing PDF agreements for email attachments
"""

import io
import logging
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    HRFlowable,
    Table,
    TableStyle,
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from config import Config

logger = logging.getLogger(__name__)


class PDFAgreementGenerator:
    """Generate professional PDF agreements for LockBay platform"""

    @staticmethod
    def generate_user_agreement(user_name: str, user_email: str) -> bytes:
        """
        Generate a professional PDF user agreement

        Args:
            user_name: User's name for personalization
            user_email: User's email for record keeping

        Returns:
            bytes: PDF content as bytes
        """
        try:
            # Create PDF buffer
            buffer = io.BytesIO()

            # Create document
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                rightMargin=0.75 * inch,
                leftMargin=0.75 * inch,
                topMargin=1 * inch,
                bottomMargin=1 * inch,
            )

            # Get styles
            styles = getSampleStyleSheet()

            # Custom styles
            title_style = ParagraphStyle(
                "CustomTitle",
                parent=styles["Heading1"],
                fontSize=18,
                spaceAfter=20,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#2E86AB"),
            )

            heading_style = ParagraphStyle(
                "CustomHeading",
                parent=styles["Heading2"],
                fontSize=14,
                spaceAfter=12,
                spaceBefore=16,
                textColor=colors.HexColor("#2E86AB"),
            )

            body_style = ParagraphStyle(
                "CustomBody",
                parent=styles["Normal"],
                fontSize=11,
                spaceAfter=8,
                alignment=TA_JUSTIFY,
                leftIndent=20,
            )

            highlight_style = ParagraphStyle(
                "Highlight",
                parent=styles["Normal"],
                fontSize=11,
                spaceAfter=8,
                leftIndent=20,
                textColor=colors.HexColor("#A23B72"),
                fontName="Helvetica-Bold",
            )

            # Build content
            content = []

            # Header
            content.append(
                Paragraph(f"{Config.PLATFORM_NAME} User Agreement", title_style)
            )
            content.append(Spacer(1, 12))

            # User info section
            user_info_data = [
                ["Agreement Date:", datetime.now().strftime("%B %d, %Y")],
                ["User Name:", user_name],
                ["Email Address:", user_email],
                ["Platform:", f"{Config.PLATFORM_NAME} - Safe Money Exchange"],
            ]

            user_table = Table(user_info_data, colWidths=[2 * inch, 4 * inch])
            user_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8F9FA")),
                        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#2E86AB")),
                        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 0), (-1, -1), 10),
                        ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#E9ECEF")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 12),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ]
                )
            )

            content.append(user_table)
            content.append(Spacer(1, 20))
            content.append(HRFlowable(width="100%", color=colors.HexColor("#2E86AB")))
            content.append(Spacer(1, 16))

            # Agreement sections

            # 1. Platform Overview
            content.append(Paragraph("1. Platform Overview", heading_style))
            content.append(
                Paragraph(
                    f"{Config.PLATFORM_NAME} - Secure crypto exchange and escrow platform.",
                    body_style,
                )
            )

            # 2. User Commitments
            content.append(Paragraph("2. Your Commitments", heading_style))
            commitments = [
                "Engage only in honest and legitimate transactions",
                "Provide truthful information about goods and services",
                "Comply with all applicable local and international laws",
                "Resolve disputes fairly and in good faith",
                "Maintain account security and protect login credentials",
            ]
            for commitment in commitments:
                content.append(Paragraph(f"• {commitment}", body_style))

            # 3. Platform Services
            content.append(Paragraph("3. Platform Services", heading_style))
            content.append(Paragraph("We provide two primary services:", body_style))
            content.append(
                Paragraph(
                    "• <b>Instant Exchange:</b> Convert cryptocurrency to cash within minutes",
                    body_style,
                )
            )
            content.append(
                Paragraph(
                    "• <b>Secure Escrow:</b> Protected transactions for higher-value trades with dispute resolution",
                    body_style,
                )
            )

            # 4. Fee Structure
            content.append(Paragraph("4. Fee Structure", heading_style))
            fee_percentage = (
                int(Config.ESCROW_FEE_PERCENTAGE)
                if Config.ESCROW_FEE_PERCENTAGE % 1 == 0
                else Config.ESCROW_FEE_PERCENTAGE
            )
            content.append(
                Paragraph(
                    f"<b>Platform Fee:</b> {fee_percentage}% charged only when transactions complete successfully",
                    highlight_style,
                )
            )
            content.append(Paragraph("• No upfront costs or hidden fees", body_style))
            content.append(
                Paragraph(
                    "• Fees are clearly displayed before transaction confirmation",
                    body_style,
                )
            )
            content.append(
                Paragraph(
                    "• 100% money-back guarantee if service issues occur", body_style
                )
            )

            # 5. Important Policies
            content.append(Paragraph("5. Important Policies", heading_style))
            content.append(
                Paragraph(
                    "<b>Dispute Resolution:</b> In case of disagreements, funds may be held in escrow until resolution. "
                    "Our support team investigates all disputes fairly and thoroughly.",
                    body_style,
                )
            )
            content.append(
                Paragraph(
                    "<b>Account Security:</b> Users found engaging in fraudulent activities will be permanently banned "
                    "and reported to relevant authorities.",
                    body_style,
                )
            )
            content.append(
                Paragraph(
                    "<b>Data Protection:</b> We protect your personal information according to international privacy standards.",
                    body_style,
                )
            )

            # 6. Support & Contact
            content.append(Paragraph("6. Support & Contact", heading_style))
            content.append(
                Paragraph(f"Email Support: {Config.SUPPORT_EMAIL}", body_style)
            )
            content.append(
                Paragraph(f"Platform: @{Config.BOT_USERNAME} on Telegram", body_style)
            )
            content.append(
                Paragraph(
                    "Support Hours: 24/7 automated assistance, human support within 24 hours",
                    body_style,
                )
            )

            # Footer
            content.append(Spacer(1, 20))
            content.append(HRFlowable(width="100%", color=colors.HexColor("#2E86AB")))
            content.append(Spacer(1, 12))
            content.append(
                Paragraph(
                    f"By using {Config.PLATFORM_NAME}, you acknowledge that you have read, understood, and agree to these terms. "
                    "This agreement becomes effective upon account creation and remains valid for all platform usage.",
                    ParagraphStyle(
                        "Footer",
                        parent=styles["Normal"],
                        fontSize=10,
                        alignment=TA_CENTER,
                        textColor=colors.HexColor("#6C757D"),
                    ),
                )
            )
            content.append(Spacer(1, 8))
            content.append(
                Paragraph(
                    f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p UTC')} | {Config.PLATFORM_NAME} v2.0",
                    ParagraphStyle(
                        "Version",
                        parent=styles["Normal"],
                        fontSize=9,
                        alignment=TA_CENTER,
                        textColor=colors.HexColor("#ADB5BD"),
                    ),
                )
            )

            # Build PDF
            doc.build(content)

            # Get PDF bytes
            pdf_bytes = buffer.getvalue()
            buffer.close()

            logger.info(
                f"Generated user agreement PDF for {user_email} ({len(pdf_bytes)} bytes)"
            )
            return pdf_bytes

        except Exception as e:
            logger.error(f"Error generating PDF agreement: {e}")
            raise e

    @staticmethod
    def get_agreement_filename(user_name: str) -> str:
        """Generate a professional filename for the agreement"""
        safe_name = "".join(
            c for c in user_name if c.isalnum() or c in (" ", "-", "_")
        ).strip()
        safe_name = safe_name.replace(" ", "_")
        date_str = datetime.now().strftime("%Y%m%d")
        return f"{Config.PLATFORM_NAME}_Agreement_{safe_name}_{date_str}.pdf"
