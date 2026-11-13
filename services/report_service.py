from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Report, MessageLog, User


class ReportService:
    @staticmethod
    async def create_report(
        db: AsyncSession,
        message_id: int,
        reporter_telegram_id: int,
        reporter_name: Optional[str] = None,
        reason: Optional[str] = None
    ) -> Optional[Report]:
        # Xabar mavjudligini tekshirish
        msg = await db.get(MessageLog, message_id)
        if not msg:
            return None

        report = Report(
            message_id=message_id,
            reporter_telegram_id=reporter_telegram_id,
            reporter_name=reporter_name,
            reason=reason or "Qoidalarga zid mazmun",
            status="PENDING",
            created_at=datetime.utcnow()
        )
        db.add(report)
        # Xabar statusini ham REPORTED ga yangilash (agar u ALLOWED bo'lgan bo'lsa)
        if msg.status == "ALLOWED":
            msg.status = "REPORTED"

        await db.commit()
        await db.refresh(report)
        return report

    @staticmethod
    async def get_reports(
        db: AsyncSession,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[Report], int]:
        stmt = select(Report).options(selectinload(Report.message))

        if status and status != "ALL":
            stmt = stmt.where(Report.status == status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_count = (await db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(desc(Report.created_at)).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all(), total_count

    @staticmethod
    async def resolve_report(
        db: AsyncSession,
        report_id: int,
        action: str,  # "APPROVED" (qoidabuzarlik tasdiqlandi) yoki "REJECTED" (asossiz)
        admin_notes: Optional[str] = None
    ) -> Optional[Report]:
        stmt = select(Report).options(selectinload(Report.message)).where(Report.id == report_id)
        result = await db.execute(stmt)
        report = result.scalar_one_or_none()

        if not report:
            return None

        report.status = action
        report.admin_notes = admin_notes
        report.resolved_at = datetime.utcnow()

        # Agar shikoyat tasdiqlansa (APPROVED), xabarni bloklash va foydalanuvchini ogohlantirish
        if action == "APPROVED" and report.message:
            report.message.status = "BLOCKED"
            report.message.action_taken = "DELETED"
            # User warning
            if report.message.user_id:
                user = await db.get(User, report.message.user_id)
                if user:
                    user.warning_count += 1
                    if user.warning_count >= 3:
                        user.is_banned = True
        elif action == "REJECTED" and report.message:
            if report.message.status == "REPORTED":
                report.message.status = "ALLOWED"

        await db.commit()
        await db.refresh(report)
        return report
