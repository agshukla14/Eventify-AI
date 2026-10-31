import io
import csv
from datetime import datetime
from typing import Any, Optional, Dict, List
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)

from .schemas import FullEventPlan


class ExportService:
    @staticmethod
    def generate_csv(plan: FullEventPlan) -> str:
        output = io.StringIO()
        writer = csv.writer(output)

        # 1. Event Overview
        writer.writerow(["EVENT OVERVIEW"])
        writer.writerow(["Event ID", plan.event_id])
        writer.writerow(["Title", plan.intake.title])
        writer.writerow(["Event Type", plan.intake.event_type.title()])
        writer.writerow(["Date", plan.intake.date])
        writer.writerow(["City", plan.intake.city])
        writer.writerow(["Guest Count", plan.intake.guest_count])
        writer.writerow(["Total Budget", f"{plan.budget.total_budget} {plan.intake.currency}"])
        writer.writerow(["Theme", plan.intake.theme_style or "N/A"])
        writer.writerow(["Dietary Preferences", "; ".join(plan.intake.dietary_preferences) or "N/A"])
        writer.writerow([])

        # 2. Budget Allocation
        writer.writerow(["BUDGET ALLOCATION"])
        writer.writerow(["Category", "Percentage (%)", f"Allocated ({plan.intake.currency})", f"Actual Spent ({plan.intake.currency})", "Notes"])
        for item in plan.budget.items:
            writer.writerow([
                item.category,
                f"{item.percentage:.2f}%",
                f"{item.allocated_amount:.2f}",
                f"{item.actual_spent:.2f}",
                item.notes,
            ])
        writer.writerow(["TOTAL", "100.00%", f"{plan.budget.total_allocated:.2f}", f"{plan.budget.total_actual_spent:.2f}", ""])
        writer.writerow([])

        # 3. Timeline Milestones
        writer.writerow(["TIMELINE MILESTONES"])
        writer.writerow(["Milestone Phase", "Task Title", "Due Date", "Owner", "Priority", "Status", "High Risk"])
        for task in plan.timeline.milestones:
            writer.writerow([
                task.milestone_phase,
                task.title,
                task.due_date,
                task.owner.title(),
                task.priority.title(),
                task.status.title(),
                "YES" if task.is_high_risk else "No",
            ])
        writer.writerow([])

        # 4. Day-of Run-of-Show
        writer.writerow(["DAY-OF RUN-OF-SHOW SCHEDULE"])
        writer.writerow(["Time Slot", "Activity", "Lead Person", "Location", "Notes"])
        for ros in plan.timeline.run_of_show:
            writer.writerow([
                ros.time_slot,
                ros.activity,
                ros.lead_person,
                ros.location,
                ros.notes,
            ])
        writer.writerow([])

        # 5. Vendor Checklist
        writer.writerow(["VENDOR CHECKLIST"])
        writer.writerow(["Category", "Vendor Name", "Contact", f"Quote ({plan.intake.currency})", "Status", "Checklist Items", "Backup Option"])
        for v in plan.vendors:
            cl_summary = "; ".join(f"[{'X' if c.is_completed else ' '}] {c.task_text}" for c in v.checklist)
            writer.writerow([
                v.category,
                v.vendor_name,
                v.contact_info,
                f"{v.quote_amount:.2f}",
                v.status.title(),
                cl_summary,
                v.backup_vendor or "N/A",
            ])
        writer.writerow([])

        # 6. Personalized Ideas & Swaps
        writer.writerow(["PERSONALIZED IDEAS & BUDGET SWAPS"])
        writer.writerow(["Type", "Title", "Description", "Budget-Friendly Swap"])
        for t in plan.ideas.themes:
            writer.writerow(["Theme", t.title, t.description, t.budget_friendly_swap])
        for d in plan.ideas.decor:
            writer.writerow(["Decor", d.title, d.description, d.budget_friendly_swap])
        for f in plan.ideas.food_menu:
            writer.writerow(["Food & Menu", f.title, f.description, f.budget_friendly_swap])
        for a in plan.ideas.activities:
            writer.writerow(["Activity", a.title, a.description, a.budget_friendly_swap])
        for e in plan.ideas.entertainment:
            writer.writerow(["Entertainment", e.title, e.description, e.budget_friendly_swap])
        for g in plan.ideas.return_gifts:
            writer.writerow(["Return Gifts", g.title, g.description, g.budget_friendly_swap])

        return output.getvalue()

    @staticmethod
    def generate_pdf(plan: FullEventPlan) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#1e293b"),
            fontName="Helvetica-Bold",
        )
        h2_style = ParagraphStyle(
            "SectionH2",
            parent=styles["Heading2"],
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#0f766e"),
            fontName="Helvetica-Bold",
            spaceBefore=10,
            spaceAfter=4,
        )
        body_style = ParagraphStyle(
            "DocBody",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#334155"),
        )
        small_bold = ParagraphStyle(
            "SmallBold",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#1e293b"),
        )
        table_cell = ParagraphStyle(
            "TableCell",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1e293b"),
        )

        story = []

        # Header Title
        story.append(Paragraph(f"{plan.intake.title}", title_style))
        subtitle = (
            f"<b>{plan.intake.event_type.upper()}</b> | Date: {plan.intake.date} | "
            f"Location: {plan.intake.city} | Guests: {plan.intake.guest_count} | "
            f"Budget: {plan.budget.total_budget:,.2f} {plan.intake.currency}"
        )
        story.append(Paragraph(subtitle, body_style))
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f766e"), spaceAfter=10))

        # 1. Budget Summary Table
        story.append(Paragraph("1. Budget Allocation Breakdown", h2_style))
        b_data = [["Category", "Allocated %", f"Amount ({plan.intake.currency})", f"Spent ({plan.intake.currency})", "Notes"]]
        for item in plan.budget.items:
            b_data.append([
                Paragraph(item.category, table_cell),
                Paragraph(f"{item.percentage:.2f}%", table_cell),
                Paragraph(f"{item.allocated_amount:,.2f}", table_cell),
                Paragraph(f"{item.actual_spent:,.2f}", table_cell),
                Paragraph(item.notes[:35] if item.notes else "-", table_cell),
            ])
        b_data.append([
            Paragraph("<b>TOTAL</b>", small_bold),
            Paragraph("<b>100.00%</b>", small_bold),
            Paragraph(f"<b>{plan.budget.total_allocated:,.2f}</b>", small_bold),
            Paragraph(f"<b>{plan.budget.total_actual_spent:,.2f}</b>", small_bold),
            Paragraph(f"Contingency: {plan.budget.contingency_percentage:.1f}%", small_bold),
        ])

        b_table = Table(b_data, colWidths=[140, 65, 85, 80, 170])
        b_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(b_table)
        story.append(Spacer(1, 12))

        # 2. Timeline Milestones Table
        story.append(Paragraph("2. Timeline Milestones", h2_style))
        t_data = [["Milestone Phase", "Task", "Due Date", "Owner", "Priority", "Status"]]
        for t in plan.timeline.milestones:
            prio_color = "#dc2626" if t.is_high_risk else "#1e293b"
            t_data.append([
                Paragraph(t.milestone_phase, table_cell),
                Paragraph(f"{'[RISK] ' if t.is_high_risk else ''}{t.title}", table_cell),
                Paragraph(t.due_date, table_cell),
                Paragraph(t.owner.title(), table_cell),
                Paragraph(f"<font color='{prio_color}'>{t.priority.upper()}</font>", table_cell),
                Paragraph(t.status.title(), table_cell),
            ])
        t_table = Table(t_data, colWidths=[100, 180, 70, 55, 65, 70])
        t_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t_table)
        story.append(Spacer(1, 12))

        # 3. Day-Of Hourly Run of Show
        story.append(Paragraph("3. Day-of Run-of-Show (Hourly Schedule)", h2_style))
        ros_data = [["Time Slot", "Activity", "Lead Person", "Location"]]
        for ros in plan.timeline.run_of_show:
            ros_data.append([
                Paragraph(ros.time_slot, table_cell),
                Paragraph(ros.activity, table_cell),
                Paragraph(ros.lead_person, table_cell),
                Paragraph(ros.location, table_cell),
            ])
        ros_table = Table(ros_data, colWidths=[80, 240, 100, 120])
        ros_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(ros_table)
        story.append(Spacer(1, 12))

        # 4. Vendor Checklist
        story.append(Paragraph("4. Vendor Checklist & Status", h2_style))
        v_data = [["Category", "Vendor Name", "Quote", "Status", "Backup Vendor"]]
        for v in plan.vendors:
            v_data.append([
                Paragraph(v.category, table_cell),
                Paragraph(v.vendor_name or "Pending Assignment", table_cell),
                Paragraph(f"{v.quote_amount:,.2f} {plan.intake.currency}", table_cell),
                Paragraph(v.status.upper(), table_cell),
                Paragraph(v.backup_vendor or "-", table_cell),
            ])
        v_table = Table(v_data, colWidths=[120, 150, 90, 70, 110])
        v_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(v_table)
        story.append(Spacer(1, 12))

        # 5. Personalized Ideas & Swaps
        story.append(Paragraph("5. Personalized Ideas & Budget-Friendly Swaps", h2_style))
        idea_data = [["Type", "Concept Title", "Budget-Friendly Alternative Swap"]]
        for t in plan.ideas.themes:
            idea_data.append([Paragraph("Theme", table_cell), Paragraph(t.title, table_cell), Paragraph(t.budget_friendly_swap, table_cell)])
        for f in plan.ideas.food_menu:
            idea_data.append([Paragraph("Food", table_cell), Paragraph(f.title, table_cell), Paragraph(f.budget_friendly_swap, table_cell)])
        for d in plan.ideas.decor:
            idea_data.append([Paragraph("Decor", table_cell), Paragraph(d.title, table_cell), Paragraph(d.budget_friendly_swap, table_cell)])
        for a in plan.ideas.activities:
            idea_data.append([Paragraph("Activity", table_cell), Paragraph(a.title, table_cell), Paragraph(a.budget_friendly_swap, table_cell)])

        idea_table = Table(idea_data, colWidths=[65, 205, 270])
        idea_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(idea_table)

        doc.build(story)
        return buffer.getvalue()

    @staticmethod
    def generate_expenses_csv(
        event_title: str,
        summary,
        expenses: list,
    ) -> str:
        """
        Generates CSV format export containing:
        - Event expense summary header
        - Category-wise Planned vs Actual breakdown
        - Complete expense transaction history
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # 1. Event Overview & Key Totals
        writer.writerow(["EVENT EXPENSE TRACKING REPORT"])
        writer.writerow(["Event Title", event_title])
        writer.writerow(["Currency", summary.currency])
        writer.writerow(["Total Event Budget", f"{summary.total_event_budget:,.2f}"])
        writer.writerow(["Total Actual Expenses", f"{summary.total_actual_spent:,.2f}"])
        writer.writerow(["Remaining Budget", f"{summary.remaining_budget:,.2f}"])
        writer.writerow(["Budget Utilization", f"{summary.budget_utilization_percentage:.1f}%"])
        writer.writerow(["Budget Status", "OVER BUDGET" if summary.is_over_budget else "WITHIN BUDGET"])
        if summary.is_over_budget:
            writer.writerow(["Over Budget Amount", f"{summary.over_budget_amount:,.2f}"])
        writer.writerow([])

        # 2. Category-wise Planned vs Actual Comparison
        writer.writerow(["CATEGORY-WISE PLANNED VS ACTUAL BUDGET"])
        writer.writerow([
            "Category",
            f"Planned ({summary.currency})",
            f"Actual ({summary.currency})",
            f"Remaining ({summary.currency})",
            f"Diff / Savings ({summary.currency})",
            "Utilization (%)",
            "Status",
        ])
        for cat in summary.categories:
            status = f"Overspent by {cat.overspent_amount:,.2f}" if cat.is_overspent else "On Track"
            writer.writerow([
                cat.category,
                f"{cat.planned_budget:,.2f}",
                f"{cat.actual_spent:,.2f}",
                f"{cat.remaining:,.2f}",
                f"{cat.difference:,.2f}",
                f"{cat.utilization_percentage:.1f}%",
                status,
            ])
        writer.writerow([])

        # 3. Expense Transaction History
        writer.writerow(["EXPENSE TRANSACTION HISTORY"])
        writer.writerow([
            "Expense ID",
            "Date",
            "Expense Name",
            "Category",
            f"Amount ({summary.currency})",
            "Payment Status",
            "Payment Method",
            "Vendor",
            "Notes",
        ])
        for exp in expenses:
            writer.writerow([
                exp.id,
                exp.expense_date,
                exp.expense_name,
                exp.category,
                f"{exp.amount:,.2f}",
                exp.payment_status,
                exp.payment_method or "-",
                exp.vendor_name or "-",
                exp.notes or "-",
            ])

        return output.getvalue()

    @staticmethod
    def generate_expenses_pdf(
        event_title: str,
        event_date: str,
        event_city: str,
        summary,
        expenses: list,
    ) -> bytes:
        """
        Generates PDF report containing:
        - Event Name & details
        - Total Budget, Total Actual Expenses, Remaining Budget, Utilization
        - Category-wise Planned vs Actual Comparison
        - Expense Transaction History
        - Savings and Overspending Summary
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ExpDocTitle",
            parent=styles["Heading1"],
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#0f766e"),
            fontName="Helvetica-Bold",
        )
        h2_style = ParagraphStyle(
            "ExpSectionH2",
            parent=styles["Heading2"],
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#0f766e"),
            fontName="Helvetica-Bold",
            spaceBefore=10,
            spaceAfter=4,
        )
        body_style = ParagraphStyle(
            "ExpDocBody",
            parent=styles["Normal"],
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#334155"),
        )
        table_cell = ParagraphStyle(
            "ExpTableCell",
            parent=styles["Normal"],
            fontSize=7.5,
            leading=9.5,
            textColor=colors.HexColor("#1e293b"),
        )
        table_cell_bold = ParagraphStyle(
            "ExpTableCellBold",
            parent=styles["Normal"],
            fontSize=7.5,
            leading=9.5,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#1e293b"),
        )
        overspent_cell = ParagraphStyle(
            "ExpOverspentCell",
            parent=styles["Normal"],
            fontSize=7.5,
            leading=9.5,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#b91c1c"),
        )
        savings_cell = ParagraphStyle(
            "ExpSavingsCell",
            parent=styles["Normal"],
            fontSize=7.5,
            leading=9.5,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#047857"),
        )

        story = []

        # 1. Header Banner
        story.append(Paragraph(f"{event_title} — Expense Tracking Report", title_style))
        subtitle = (
            f"Event Date: <b>{event_date}</b> | Location: <b>{event_city}</b> | "
            f"Generated: <b>{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</b>"
        )
        story.append(Paragraph(subtitle, body_style))
        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f766e"), spaceAfter=10))

        # 2. Executive Financial Summary Cards (Table)
        summary_data = [
            [
                Paragraph("<b>Total Event Budget</b>", table_cell_bold),
                Paragraph("<b>Total Actual Expenses</b>", table_cell_bold),
                Paragraph("<b>Remaining Budget</b>", table_cell_bold),
                Paragraph("<b>Budget Utilization</b>", table_cell_bold),
            ],
            [
                Paragraph(f"<font size=11 color='#0f172a'><b>{summary.total_event_budget:,.2f} {summary.currency}</b></font>", body_style),
                Paragraph(f"<font size=11 color='#0f766e'><b>{summary.total_actual_spent:,.2f} {summary.currency}</b></font>", body_style),
                Paragraph(
                    f"<font size=11 color='{'#b91c1c' if summary.is_over_budget else '#047857'}'><b>{summary.remaining_budget:,.2f} {summary.currency}</b></font>",
                    body_style,
                ),
                Paragraph(
                    f"<font size=11 color='{'#b91c1c' if summary.budget_utilization_percentage > 100 else '#0f766e'}'><b>{summary.budget_utilization_percentage:.1f}%</b></font>",
                    body_style,
                ),
            ],
        ]
        summary_table = Table(summary_data, colWidths=[135, 135, 135, 135])
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 10))

        # 3. Category-wise Planned vs Actual Comparison Table
        story.append(Paragraph("1. Category-wise Planned vs Actual Comparison", h2_style))
        cat_data = [
            [
                Paragraph("Category", table_cell_bold),
                Paragraph(f"Planned ({summary.currency})", table_cell_bold),
                Paragraph(f"Actual Spent ({summary.currency})", table_cell_bold),
                Paragraph(f"Remaining ({summary.currency})", table_cell_bold),
                Paragraph(f"Difference ({summary.currency})", table_cell_bold),
                Paragraph("Util %", table_cell_bold),
                Paragraph("Status", table_cell_bold),
            ]
        ]
        for c in summary.categories:
            cat_data.append([
                Paragraph(c.category, table_cell),
                Paragraph(f"{c.planned_budget:,.2f}", table_cell),
                Paragraph(f"{c.actual_spent:,.2f}", table_cell),
                Paragraph(f"{c.remaining:,.2f}", table_cell),
                Paragraph(f"{c.difference:+,.2f}", overspent_cell if c.is_overspent else savings_cell),
                Paragraph(f"{c.utilization_percentage:.1f}%", table_cell),
                Paragraph(
                    f"<font color='#b91c1c'>Over (+{c.overspent_amount:,.2f})</font>" if c.is_overspent else "<font color='#047857'>On Track</font>",
                    table_cell,
                ),
            ])
        cat_table = Table(cat_data, colWidths=[120, 75, 75, 75, 75, 50, 70])
        cat_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(cat_table)
        story.append(Spacer(1, 12))

        # 4. Expense Transaction History
        story.append(Paragraph("2. Expense Transaction History", h2_style))
        exp_data = [
            [
                Paragraph("Date", table_cell_bold),
                Paragraph("Expense Name", table_cell_bold),
                Paragraph("Category", table_cell_bold),
                Paragraph("Vendor", table_cell_bold),
                Paragraph("Status", table_cell_bold),
                Paragraph(f"Amount ({summary.currency})", table_cell_bold),
            ]
        ]
        if not expenses:
            exp_data.append([
                Paragraph("No expenses recorded yet.", table_cell),
                Paragraph("-", table_cell),
                Paragraph("-", table_cell),
                Paragraph("-", table_cell),
                Paragraph("-", table_cell),
                Paragraph("-", table_cell),
            ])
        else:
            for e in expenses:
                status_color = "#047857" if e.payment_status == "Paid" else "#b45309"
                exp_data.append([
                    Paragraph(e.expense_date, table_cell),
                    Paragraph(e.expense_name, table_cell),
                    Paragraph(e.category, table_cell),
                    Paragraph(e.vendor_name or "-", table_cell),
                    Paragraph(f"<font color='{status_color}'><b>{e.payment_status}</b></font>", table_cell),
                    Paragraph(f"<b>{e.amount:,.2f}</b>", table_cell),
                ])
        exp_table = Table(exp_data, colWidths=[65, 145, 105, 95, 60, 70])
        exp_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(exp_table)
        story.append(Spacer(1, 12))

        # 5. Savings and Overspending Summary
        story.append(Paragraph("3. Savings and Overspending Summary", h2_style))
        overspent_cats = [c for c in summary.categories if c.is_overspent]
        savings_cats = [c for c in summary.categories if not c.is_overspent and c.difference > 0]

        summary_paragraphs = []
        if overspent_cats:
            over_names = ", ".join(f"<b>{c.category}</b> (+{c.overspent_amount:,.2f} {summary.currency})" for c in overspent_cats)
            summary_paragraphs.append(
                Paragraph(f"<font color='#b91c1c'><b>Areas of Overspending:</b></font> {over_names}.", body_style)
            )
        else:
            summary_paragraphs.append(
                Paragraph("<font color='#047857'><b>No Overspending:</b></font> All expense categories are currently within their planned budget ceilings.", body_style)
            )

        if savings_cats:
            savings_names = ", ".join(f"<b>{c.category}</b> (saved {c.difference:,.2f} {summary.currency})" for c in savings_cats[:5])
            summary_paragraphs.append(
                Paragraph(f"<font color='#047857'><b>Categories with Remaining Surplus:</b></font> {savings_names}.", body_style)
            )

        if summary.is_over_budget:
            summary_paragraphs.append(
                Paragraph(
                    f"<b>Recommendation:</b> Overall event budget has been exceeded by {summary.over_budget_amount:,.2f} {summary.currency}. "
                    "Use the AI Budget Optimizer in the Budget Planner to rebalance category weights or request additional funds.",
                    body_style,
                )
            )
        else:
            summary_paragraphs.append(
                Paragraph(
                    f"<b>Fiscal Health:</b> You have {summary.remaining_budget:,.2f} {summary.currency} ({100.0 - summary.budget_utilization_percentage:.1f}%) "
                    "in reserve. Expenditures are currently sustainable.",
                    body_style,
                )
            )

        for p in summary_paragraphs:
            story.append(p)
            story.append(Spacer(1, 4))

        doc.build(story)
        return buffer.getvalue()

    @staticmethod
    def generate_guests_csv(
        event_title: str,
        guests: list,
        filter_status: str = "All",
    ) -> str:
        """
        Generates CSV format export of guests:
        Can be filtered by status (All, Accepted, Pending, Declined).
        """
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(["EVENT GUEST LIST & RSVP REPORT"])
        writer.writerow(["Event Title", event_title])
        writer.writerow(["Export Filter", f"{filter_status} Guests"])
        writer.writerow(["Total Records", len(guests)])
        writer.writerow([])

        writer.writerow([
            "Guest ID",
            "Full Name",
            "Category",
            "Email Address",
            "Phone Number",
            "Plus Ones",
            "Total Attendees",
            "Invitation Status",
            "RSVP Status",
            "Special Requirements",
            "Notes",
        ])

        for g in guests:
            total_attendees = 1 + (g.plus_ones or 0) if g.rsvp_status == "Accepted" else 0
            writer.writerow([
                g.id,
                g.full_name,
                g.category,
                g.email or "-",
                g.phone or "-",
                g.plus_ones,
                total_attendees,
                g.invitation_status,
                g.rsvp_status,
                g.special_requirements or "-",
                g.notes or "-",
            ])

        return output.getvalue()

    @staticmethod
    def generate_guests_pdf(
        event_title: str,
        event_date: str,
        event_city: str,
        summary,
        guests: list,
    ) -> bytes:
        """
        Generates complete PDF guest report with:
        - Event Name & details
        - Total Guests, Confirmed Guests, Pending Responses, Declined Guests
        - Guest Category Summary
        - Complete Guest List
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "GuestDocTitle",
            parent=styles["Heading1"],
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0f766e"),
            fontName="Helvetica-Bold",
        )
        h2_style = ParagraphStyle(
            "GuestSectionH2",
            parent=styles["Heading2"],
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#0f766e"),
            fontName="Helvetica-Bold",
            spaceBefore=9,
            spaceAfter=4,
        )
        body_style = ParagraphStyle(
            "GuestDocBody",
            parent=styles["Normal"],
            fontSize=8,
            leading=10.5,
            textColor=colors.HexColor("#334155"),
        )
        table_cell = ParagraphStyle(
            "GuestTableCell",
            parent=styles["Normal"],
            fontSize=7,
            leading=8.5,
            textColor=colors.HexColor("#1e293b"),
        )
        table_cell_bold = ParagraphStyle(
            "GuestTableCellBold",
            parent=styles["Normal"],
            fontSize=7,
            leading=8.5,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#1e293b"),
        )

        story = []

        # 1. Header Banner
        story.append(Paragraph(f"{event_title} — Guest Management & RSVP Report", title_style))
        subtitle = (
            f"Event Date: <b>{event_date}</b> | Location: <b>{event_city}</b> | "
            f"Report Generated: <b>{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</b>"
        )
        story.append(Paragraph(subtitle, body_style))
        story.append(Spacer(1, 6))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f766e"), spaceAfter=8))

        # 2. Executive RSVP KPI Metrics Table
        kpi_data = [
            [
                Paragraph("<b>Total Invited</b>", table_cell_bold),
                Paragraph("<b>Confirmed Guests</b>", table_cell_bold),
                Paragraph("<b>Pending Responses</b>", table_cell_bold),
                Paragraph("<b>Declined Invitations</b>", table_cell_bold),
            ],
            [
                Paragraph(f"<font size=10 color='#0f172a'><b>{summary.total_guests_invited}</b></font>", body_style),
                Paragraph(
                    f"<font size=10 color='#047857'><b>{summary.confirmed_guests}</b> (+{summary.confirmed_plus_ones} plus ones)</font>",
                    body_style,
                ),
                Paragraph(f"<font size=10 color='#b45309'><b>{summary.pending_responses}</b></font>", body_style),
                Paragraph(f"<font size=10 color='#b91c1c'><b>{summary.declined_guests}</b></font>", body_style),
            ],
            [
                Paragraph(f"Invitations Sent: {summary.total_invitations_sent} / {summary.total_guests_invited}", body_style),
                Paragraph(f"<b>Expected Attendance: {summary.total_expected_attendance}</b>", body_style),
                Paragraph(f"Response Rate: {summary.rsvp_response_rate:.1f}%", body_style),
                Paragraph(f"Acceptance Rate: {summary.acceptance_rate:.1f}%", body_style),
            ],
        ]
        kpi_table = Table(kpi_data, colWidths=[135, 135, 135, 135])
        kpi_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(kpi_table)
        story.append(Spacer(1, 8))

        # 3. Category Breakdown Table
        story.append(Paragraph("1. Guest Category Breakdown", h2_style))
        cat_data = [
            [
                Paragraph("Category", table_cell_bold),
                Paragraph("Invited Guests", table_cell_bold),
                Paragraph("Share of Guest List", table_cell_bold),
            ]
        ]
        for cat_name, count in summary.category_counts.items():
            if count > 0:
                share = (count / summary.total_guests_invited * 100) if summary.total_guests_invited > 0 else 0
                cat_data.append([
                    Paragraph(cat_name, table_cell),
                    Paragraph(str(count), table_cell),
                    Paragraph(f"{share:.1f}%", table_cell),
                ])
        cat_table = Table(cat_data, colWidths=[200, 170, 170])
        cat_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(cat_table)
        story.append(Spacer(1, 8))

        # 4. Complete Guest List
        story.append(Paragraph("2. Complete Guest Ledger & RSVP Status", h2_style))
        guest_rows = [
            [
                Paragraph("Guest Name", table_cell_bold),
                Paragraph("Category", table_cell_bold),
                Paragraph("Contact / Phone", table_cell_bold),
                Paragraph("+1s", table_cell_bold),
                Paragraph("Invitation", table_cell_bold),
                Paragraph("RSVP", table_cell_bold),
                Paragraph("Notes / Requirements", table_cell_bold),
            ]
        ]
        if not guests:
            guest_rows.append([
                Paragraph("No guests registered yet.", table_cell),
                Paragraph("-", table_cell),
                Paragraph("-", table_cell),
                Paragraph("-", table_cell),
                Paragraph("-", table_cell),
                Paragraph("-", table_cell),
                Paragraph("-", table_cell),
            ])
        else:
            for g in guests:
                rsvp_color = "#047857" if g.rsvp_status == "Accepted" else ("#b91c1c" if g.rsvp_status == "Declined" else "#b45309")
                inv_color = "#047857" if g.invitation_status == "Sent" else "#64748b"
                contact = g.phone or g.email or "-"
                notes_text = g.special_requirements or g.notes or "-"
                guest_rows.append([
                    Paragraph(g.full_name, table_cell_bold),
                    Paragraph(g.category, table_cell),
                    Paragraph(contact[:22], table_cell),
                    Paragraph(str(g.plus_ones), table_cell),
                    Paragraph(f"<font color='{inv_color}'>{g.invitation_status}</font>", table_cell),
                    Paragraph(f"<font color='{rsvp_color}'><b>{g.rsvp_status}</b></font>", table_cell),
                    Paragraph(notes_text[:30], table_cell),
                ])

        g_table = Table(guest_rows, colWidths=[110, 65, 95, 35, 65, 60, 110])
        g_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ]))
        story.append(g_table)

        doc.build(story)
        return buffer.getvalue()



    @staticmethod
    def generate_invitation_pdf(
        title: str,
        language: str,
        components: Any,
        design_config: Any,
    ) -> bytes:
        """Generates a luxury 5x7 inch printable PDF invitation card using ReportLab."""
        buffer = io.BytesIO()

        # 5 x 7 inches in points (72 points/inch)
        PAGE_WIDTH = 5 * 72   # 360 pt
        PAGE_HEIGHT = 7 * 72  # 504 pt

        doc = SimpleDocTemplate(
            buffer,
            pagesize=(PAGE_WIDTH, PAGE_HEIGHT),
            leftMargin=24,
            rightMargin=24,
            topMargin=24,
            bottomMargin=24,
        )

        def _safe_hex(hex_val: Optional[str], fallback: str) -> colors.HexColor:
            try:
                if hex_val and hex_val.startswith("#") and len(hex_val) in (4, 7):
                    return colors.HexColor(hex_val)
            except Exception:
                pass
            return colors.HexColor(fallback)

        bg_col = _safe_hex(getattr(design_config, "bg_color", "#FFFDF9"), "#FFFDF9")
        primary_col = _safe_hex(getattr(design_config, "primary_color", "#831843"), "#831843")
        text_col = _safe_hex(getattr(design_config, "text_color", "#1E293B"), "#1E293B")
        accent_col = _safe_hex(getattr(design_config, "accent_color", "#D97706"), "#D97706")

        def _escape(text: Optional[str]) -> str:
            if not text:
                return ""
            s = str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            return s.replace("\n", "<br/>")

        # Custom Page Background Canvas callback
        def draw_background(canvas, doc):
            canvas.saveState()
            canvas.setFillColor(bg_col)
            canvas.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, stroke=0, fill=1)

            # Outer border
            canvas.setStrokeColor(accent_col)
            canvas.setLineWidth(1.5)
            canvas.rect(12, 12, PAGE_WIDTH - 24, PAGE_HEIGHT - 24, stroke=1, fill=0)

            # Inner thin border
            canvas.setStrokeColor(primary_col)
            canvas.setLineWidth(0.75)
            canvas.rect(16, 16, PAGE_WIDTH - 32, PAGE_HEIGHT - 32, stroke=1, fill=0)

            # Corner decorative accents
            for x, y in [(16, 16), (PAGE_WIDTH - 16, 16), (16, PAGE_HEIGHT - 16), (PAGE_WIDTH - 16, PAGE_HEIGHT - 16)]:
                canvas.setFillColor(accent_col)
                canvas.circle(x, y, 2.5, stroke=0, fill=1)

            canvas.restoreState()

        styles = getSampleStyleSheet()

        motif_style = ParagraphStyle(
            "InvMotif",
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12,
            textColor=accent_col,
            alignment=1,  # Center
        )
        title_style = ParagraphStyle(
            "InvTitle",
            fontName="Times-Bold",
            fontSize=14,
            leading=17,
            textColor=primary_col,
            alignment=1,
        )
        greeting_style = ParagraphStyle(
            "InvGreeting",
            fontName="Times-BoldItalic",
            fontSize=10.5,
            leading=14,
            textColor=primary_col,
            alignment=1,
        )
        message_style = ParagraphStyle(
            "InvMessage",
            fontName="Times-Roman",
            fontSize=9.5,
            leading=13.5,
            textColor=text_col,
            alignment=1,
        )
        details_label_style = ParagraphStyle(
            "InvDetailsLabel",
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=primary_col,
            alignment=1,
        )
        details_style = ParagraphStyle(
            "InvDetails",
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=text_col,
            alignment=1,
        )
        closing_style = ParagraphStyle(
            "InvClosing",
            fontName="Times-BoldItalic",
            fontSize=9.5,
            leading=13.5,
            textColor=primary_col,
            alignment=1,
        )

        story = []
        story.append(Spacer(1, 6))

        # Top motif
        dec_elem = getattr(design_config, "decorative_element", "mandala_diya")
        motif_char = "❖ ❖ ❖"
        if dec_elem == "royal_crest":
            motif_char = "👑 ❖ ROYAL INVITATION ❖ 👑"
        elif dec_elem == "floral_wreath":
            motif_char = "❀ ❀ CELEBRATION ❀ ❀"
        elif dec_elem == "mandala_diya":
            motif_char = "॥ ॐ શ્રી ગણેશાય નમઃ ॥" if language == "Gujarati" else ("॥ ॐ श्री गणेशाय नमः ॥" if language == "Hindi" else "✦ CORDIAL INVITATION ✦")
        elif dec_elem == "confetti_stars":
            motif_char = "★ ★ ★ LET'S CELEBRATE ★ ★ ★"

        story.append(Paragraph(motif_char, motif_style))
        story.append(Spacer(1, 6))

        # Title
        story.append(Paragraph(_escape(title), title_style))
        story.append(Spacer(1, 6))

        # Greeting
        greeting_text = getattr(components, "personalized_greeting", "")
        if greeting_text:
            story.append(Paragraph(_escape(greeting_text), greeting_style))
            story.append(Spacer(1, 6))

        # Invitation Body Message
        inv_msg = getattr(components, "invitation_message", "")
        if inv_msg:
            story.append(Paragraph(_escape(inv_msg), message_style))
            story.append(Spacer(1, 8))

        # Highlight Box for Event Details
        evt_details = getattr(components, "event_details", "")
        if evt_details:
            details_content = [
                [Paragraph("EVENT DETAILS", details_label_style)],
                [Paragraph(_escape(evt_details), details_style)],
            ]
            details_table = Table(details_content, colWidths=[PAGE_WIDTH - 64])
            details_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFFFF") if bg_col != colors.HexColor("#FFFFFF") else colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.75, accent_col),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]))
            story.append(details_table)
            story.append(Spacer(1, 8))

        # Closing Message
        closing_msg = getattr(components, "closing_message", "")
        if closing_msg:
            story.append(Paragraph(_escape(closing_msg), closing_style))

        doc.build(story, onFirstPage=draw_background)
        return buffer.getvalue()
