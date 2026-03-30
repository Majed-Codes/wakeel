"""
PDF Report Generator — ReportLab-based Arabic financial reports.

Generates professional PDF reports with:
- Executive summary
- Income/Expense breakdown
- Category analysis
- Top vendors
- Monthly trend (text-based, no matplotlib dependency)
- Forecast preview
"""

import io
import logging
from collections import defaultdict
from datetime import datetime, date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models.transaction import Transaction, TransactionType

logger = logging.getLogger(__name__)

# Try to import ReportLab; gracefully degrade if unavailable
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("ReportLab not installed — PDF generation unavailable")


class ReportGenerator:
    """Generates financial PDF reports for Saudi SMEs."""

    def generate_report(
        self,
        business_id: int,
        db: Session,
        business_name: str = "مقهى الوكيل",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        language: str = "ar",
    ) -> bytes:
        """
        Generate a PDF financial report.

        Returns:
            bytes: PDF file content
        """
        if not REPORTLAB_AVAILABLE:
            return self._fallback_text_report(business_id, db, business_name, start_date, end_date)

        # Default date range: last 30 days
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        # Fetch transactions
        transactions = self._fetch_transactions(business_id, db, start_date, end_date)
        summary = self._compute_summary(transactions)

        # Build PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        elements = []
        styles = getSampleStyleSheet()

        # ── Custom styles ──
        title_style = ParagraphStyle(
            "ArabicTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            alignment=TA_CENTER,
            spaceAfter=6,
            textColor=colors.HexColor("#1a1a2e"),
        )
        heading_style = ParagraphStyle(
            "ArabicHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            alignment=TA_LEFT,
            spaceBefore=12,
            spaceAfter=6,
            textColor=colors.HexColor("#2F80ED"),
        )
        body_style = ParagraphStyle(
            "ArabicBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            alignment=TA_LEFT,
            spaceAfter=4,
        )
        caption_style = ParagraphStyle(
            "Caption",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            alignment=TA_CENTER,
            textColor=colors.grey,
        )

        # ── Header ──
        elements.append(Paragraph(f"التقرير المالي — {business_name}", title_style))
        elements.append(Paragraph(
            f"الفترة: {start_date.strftime('%Y-%m-%d')} إلى {end_date.strftime('%Y-%m-%d')}",
            ParagraphStyle("Sub", parent=styles["Normal"], alignment=TA_CENTER, fontSize=10, textColor=colors.grey)
        ))
        elements.append(Paragraph(
            f"تاريخ الإصدار: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            caption_style
        ))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#2F80ED")))
        elements.append(Spacer(1, 0.3 * cm))

        # ── Executive Summary ──
        elements.append(Paragraph("الملخص التنفيذي", heading_style))
        summary_data = [
            ["البند", "المبلغ (ر.س)"],
            ["إجمالي الإيرادات", f"{summary['total_revenue']:,.0f}"],
            ["إجمالي المصاريف", f"{summary['total_expenses']:,.0f}"],
            ["صافي الربح", f"{summary['net_profit']:,.0f}"],
            ["عدد المعاملات", str(summary['transaction_count'])],
            ["متوسط المعاملة", f"{summary['avg_transaction']:,.0f}"],
        ]
        elements.append(self._build_table(summary_data, col_widths=[9 * cm, 6 * cm]))
        elements.append(Spacer(1, 0.5 * cm))

        # ── Category Breakdown ──
        if summary["by_category"]:
            elements.append(Paragraph("التوزيع حسب الفئة", heading_style))
            cat_data = [["الفئة", "الإجمالي (ر.س)", "النسبة"]]
            total_exp = summary["total_expenses"] or 1
            for cat, amt in sorted(summary["by_category"].items(), key=lambda x: -x[1]):
                pct = (amt / total_exp) * 100
                cat_data.append([cat, f"{amt:,.0f}", f"{pct:.1f}%"])
            elements.append(self._build_table(cat_data, col_widths=[7 * cm, 5 * cm, 3 * cm]))
            elements.append(Spacer(1, 0.5 * cm))

        # ── Top Vendors ──
        if summary["top_vendors"]:
            elements.append(Paragraph("أكبر الجهات إنفاقاً", heading_style))
            vendor_data = [["الجهة", "الإجمالي (ر.س)", "عدد المعاملات"]]
            for vendor, (amt, count) in list(summary["top_vendors"].items())[:10]:
                vendor_data.append([vendor or "غير محدد", f"{amt:,.0f}", str(count)])
            elements.append(self._build_table(vendor_data, col_widths=[8 * cm, 5 * cm, 3 * cm]))
            elements.append(Spacer(1, 0.5 * cm))

        # ── Monthly Trend ──
        if summary["monthly_trend"]:
            elements.append(Paragraph("الأداء الشهري", heading_style))
            trend_data = [["الشهر", "الإيرادات (ر.س)", "المصاريف (ر.س)", "الصافي (ر.س)"]]
            for month_key in sorted(summary["monthly_trend"].keys()):
                m = summary["monthly_trend"][month_key]
                net = m["revenue"] - m["expenses"]
                trend_data.append([
                    month_key,
                    f"{m['revenue']:,.0f}",
                    f"{m['expenses']:,.0f}",
                    f"{net:,.0f}",
                ])
            elements.append(self._build_table(trend_data, col_widths=[4 * cm, 4 * cm, 4 * cm, 4 * cm]))
            elements.append(Spacer(1, 0.5 * cm))

        # ── Transaction Detail ──
        elements.append(Paragraph("تفاصيل المعاملات", heading_style))
        txn_data = [["التاريخ", "الجهة", "الوصف", "الفئة", "المبلغ"]]
        for t in transactions[:50]:  # Limit to 50 rows
            txn_data.append([
                t.date.strftime("%Y-%m-%d") if t.date else "",
                (t.vendor or "")[:20],
                (t.description or "")[:25],
                t.category or "",
                f"{float(t.amount):,.0f}",
            ])
        elements.append(self._build_table(
            txn_data,
            col_widths=[3 * cm, 4 * cm, 4.5 * cm, 2.5 * cm, 2.5 * cm],
            header_color=colors.HexColor("#1a1a2e"),
        ))

        # ── Footer note ──
        elements.append(Spacer(1, 0.8 * cm))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
        elements.append(Paragraph(
            "تم إنشاء هذا التقرير بواسطة نظام وكيل AI — مساعدك المالي الذكي",
            caption_style
        ))

        doc.build(elements)
        return buffer.getvalue()

    def get_summary_data(
        self,
        business_id: int,
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        """Return report summary data without generating PDF."""
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        transactions = self._fetch_transactions(business_id, db, start_date, end_date)
        summary = self._compute_summary(transactions)

        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_revenue": summary["total_revenue"],
            "total_expenses": summary["total_expenses"],
            "net_profit": summary["net_profit"],
            "transaction_count": summary["transaction_count"],
            "by_category": summary["by_category"],
            "top_vendors": {v: {"amount": a, "count": c} for v, (a, c) in list(summary["top_vendors"].items())[:5]},
            "monthly_trend": summary["monthly_trend"],
        }

    # ── Private helpers ──────────────────────────────────────────────────────

    def _fetch_transactions(
        self, business_id: int, db: Session, start_date: date, end_date: date
    ) -> list:
        from datetime import datetime
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())
        return (
            db.query(Transaction)
            .filter(
                Transaction.business_id == business_id,
                Transaction.date >= start_dt,
                Transaction.date <= end_dt,
            )
            .order_by(Transaction.date.desc())
            .all()
        )

    def _compute_summary(self, transactions: list) -> dict:
        total_revenue = 0.0
        total_expenses = 0.0
        by_category: dict[str, float] = defaultdict(float)
        vendors: dict[str, list] = defaultdict(lambda: [0.0, 0])
        monthly: dict[str, dict] = defaultdict(lambda: {"revenue": 0.0, "expenses": 0.0})

        for t in transactions:
            amount = float(t.amount)
            month_key = t.date.strftime("%Y-%m") if t.date else "Unknown"

            if t.transaction_type == TransactionType.REVENUE:
                total_revenue += amount
                monthly[month_key]["revenue"] += amount
            else:
                total_expenses += amount
                monthly[month_key]["expenses"] += amount
                cat = t.category or "غير محدد"
                by_category[cat] += amount

            vendor = t.vendor or "غير محدد"
            vendors[vendor][0] += amount
            vendors[vendor][1] += 1

        # Sort vendors by amount
        sorted_vendors = dict(
            sorted(vendors.items(), key=lambda x: -x[1][0])[:10]
        )

        return {
            "total_revenue": total_revenue,
            "total_expenses": total_expenses,
            "net_profit": total_revenue - total_expenses,
            "transaction_count": len(transactions),
            "avg_transaction": (
                (total_revenue + total_expenses) / len(transactions)
                if transactions else 0
            ),
            "by_category": dict(by_category),
            "top_vendors": sorted_vendors,
            "monthly_trend": dict(monthly),
        }

    def _build_table(
        self,
        data: list[list],
        col_widths: Optional[list] = None,
        header_color=None,
    ) -> "Table":
        from reportlab.lib import colors as rc
        if header_color is None:
            header_color = rc.HexColor("#2F80ED")

        table = Table(data, colWidths=col_widths)
        style = TableStyle([
            # Header row
            ("BACKGROUND", (0, 0), (-1, 0), header_color),
            ("TEXTCOLOR", (0, 0), (-1, 0), rc.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [rc.white, rc.HexColor("#f8f9fa")]),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, rc.HexColor("#dee2e6")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])
        table.setStyle(style)
        return table

    def _fallback_text_report(
        self,
        business_id: int,
        db: Session,
        business_name: str,
        start_date: Optional[date],
        end_date: Optional[date],
    ) -> bytes:
        """Return a plain text report when ReportLab is unavailable."""
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        transactions = self._fetch_transactions(business_id, db, start_date, end_date)
        summary = self._compute_summary(transactions)

        lines = [
            f"FINANCIAL REPORT — {business_name}",
            f"Period: {start_date} to {end_date}",
            "=" * 50,
            f"Total Revenue: {summary['total_revenue']:,.0f} SAR",
            f"Total Expenses: {summary['total_expenses']:,.0f} SAR",
            f"Net Profit: {summary['net_profit']:,.0f} SAR",
            f"Transactions: {summary['transaction_count']}",
            "",
            "TOP CATEGORIES:",
        ]
        for cat, amt in sorted(summary["by_category"].items(), key=lambda x: -x[1])[:5]:
            lines.append(f"  {cat}: {amt:,.0f} SAR")
        lines.append("")
        lines.append("Generated by Wakeel AI")

        return "\n".join(lines).encode("utf-8")


report_generator = ReportGenerator()
