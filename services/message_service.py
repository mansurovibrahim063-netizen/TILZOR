from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import MessageLog, User, Report
from moderation.pipeline import ModerationResult


class MessageService:
    @staticmethod
    async def get_or_create_user(
        db: AsyncSession,
        telegram_id: int,
        username: Optional[str] = None,
        full_name: Optional[str] = None
    ) -> User:
        result = await db.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                full_name=full_name,
                is_banned=False,
                warning_count=0
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        else:
            # Ma'lumotlarni yangilash
            if username and user.username != username:
                user.username = username
            if full_name and user.full_name != full_name:
                user.full_name = full_name
            await db.commit()
        return user

    @staticmethod
    async def log_message(
        db: AsyncSession,
        telegram_message_id: int,
        chat_id: int,
        chat_title: Optional[str],
        user_telegram_id: int,
        sender_name: Optional[str],
        sender_username: Optional[str],
        original_text: str,
        result: ModerationResult
    ) -> MessageLog:
        user = await MessageService.get_or_create_user(
            db,
            telegram_id=user_telegram_id,
            username=sender_username,
            full_name=sender_name
        )

        # Agar qoidabuzarlik bo'lsa, ogohlantirishni oshirish
        action = result.action_taken
        if result.is_violation:
            user.warning_count += 1
            if user.warning_count >= 3:
                user.is_banned = True
                action = "BANNED"
            else:
                action = "WARNED"
            await db.commit()

        log = MessageLog(
            telegram_message_id=telegram_message_id,
            chat_id=chat_id,
            chat_title=chat_title,
            user_id=user.id,
            user_telegram_id=user_telegram_id,
            sender_name=sender_name,
            sender_username=sender_username,
            original_text=original_text,
            translated_uz=result.translated_uz,
            translated_ru=result.translated_ru,
            status=result.status,
            detection_stage=result.detection_stage,
            violation_type=result.violation_type,
            toxicity_score=result.toxicity_score,
            reason=result.reason,
            action_taken=action
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)
        return log

    @staticmethod
    async def get_messages(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
        status: Optional[str] = None,
        stage: Optional[str] = None,
        violation_type: Optional[str] = None,
        search: Optional[str] = None
    ) -> Tuple[List[MessageLog], int]:
        stmt = select(MessageLog)

        filters = []
        if status and status != "ALL":
            filters.append(MessageLog.status == status)
        if stage and stage != "ALL":
            filters.append(MessageLog.detection_stage == stage)
        if violation_type and violation_type != "ALL":
            filters.append(MessageLog.violation_type == violation_type)
        if search:
            search_fmt = f"%{search}%"
            filters.append(
                or_(
                    MessageLog.original_text.ilike(search_fmt),
                    MessageLog.sender_name.ilike(search_fmt),
                    MessageLog.sender_username.ilike(search_fmt),
                    MessageLog.reason.ilike(search_fmt)
                )
            )

        if filters:
            stmt = stmt.where(and_(*filters))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_count = (await db.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(desc(MessageLog.created_at)).offset(skip).limit(limit)
        results = await db.execute(stmt)
        return results.scalars().all(), total_count

    @staticmethod
    async def get_message_by_id(db: AsyncSession, message_id: int) -> Optional[MessageLog]:
        stmt = select(MessageLog).where(MessageLog.id == message_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def update_message_status(db: AsyncSession, message_id: int, status: str, admin_reason: str = ""):
        msg = await MessageService.get_message_by_id(db, message_id)
        if msg:
            msg.status = status
            if admin_reason:
                msg.reason = f"{msg.reason or ''} [Admin: {admin_reason}]"
            await db.commit()
            return msg
        return None

    @staticmethod
    async def get_statistics(db: AsyncSession) -> Dict[str, Any]:
        """Hisobotlar va grafiklar uchun to'liq statistika ma'lumotlari"""
        now = datetime.utcnow()
        today_start = datetime(now.year, now.month, now.day)
        seven_days_ago = today_start - timedelta(days=6)
        thirty_days_ago = today_start - timedelta(days=29)

        # 1. Umumiy hisoblar
        total_messages = (await db.execute(select(func.count(MessageLog.id)))).scalar_one()
        total_blocked = (await db.execute(
            select(func.count(MessageLog.id)).where(MessageLog.status == "BLOCKED")
        )).scalar_one()
        total_allowed = (await db.execute(
            select(func.count(MessageLog.id)).where(MessageLog.status == "ALLOWED")
        )).scalar_one()

        # Bugungi hisoblar
        today_messages = (await db.execute(
            select(func.count(MessageLog.id)).where(MessageLog.created_at >= today_start)
        )).scalar_one()
        today_blocked = (await db.execute(
            select(func.count(MessageLog.id)).where(
                and_(MessageLog.created_at >= today_start, MessageLog.status == "BLOCKED")
            )
        )).scalar_one()

        # Shikoyatlar
        pending_reports = (await db.execute(
            select(func.count(Report.id)).where(Report.status == "PENDING")
        )).scalar_one()
        total_reports = (await db.execute(select(func.count(Report.id)))).scalar_one()

        # 2. Qoidabuzarlik turlari bo'yicha taqsimot
        violation_counts_raw = (await db.execute(
            select(MessageLog.violation_type, func.count(MessageLog.id))
            .where(MessageLog.violation_type != "NONE")
            .group_by(MessageLog.violation_type)
        )).all()
        violations_breakdown = {row[0]: row[1] for row in violation_counts_raw}

        # 3. Aniqlash bosqichi bo'yicha taqsimot (Regex vs Gemini)
        stages_raw = (await db.execute(
            select(MessageLog.detection_stage, func.count(MessageLog.id))
            .group_by(MessageLog.detection_stage)
        )).all()
        stage_breakdown = {row[0]: row[1] for row in stages_raw}

        # 4. Oxirgi 7 kunlik statistika (kunlar kesimida)
        daily_trend = []
        for i in range(7):
            day_dt = seven_days_ago + timedelta(days=i)
            next_day_dt = day_dt + timedelta(days=1)
            day_label = day_dt.strftime("%d-%b")

            day_total = (await db.execute(
                select(func.count(MessageLog.id)).where(
                    and_(MessageLog.created_at >= day_dt, MessageLog.created_at < next_day_dt)
                )
            )).scalar_one()

            day_blocked = (await db.execute(
                select(func.count(MessageLog.id)).where(
                    and_(
                        MessageLog.created_at >= day_dt,
                        MessageLog.created_at < next_day_dt,
                        MessageLog.status == "BLOCKED"
                    )
                )
            )).scalar_one()

            daily_trend.append({
                "date": day_label,
                "total": day_total,
                "blocked": day_blocked,
                "allowed": day_total - day_blocked
            })

        return {
            "total_messages": total_messages,
            "total_blocked": total_blocked,
            "total_allowed": total_allowed,
            "block_rate": round((total_blocked / total_messages * 100), 1) if total_messages > 0 else 0.0,
            "today_messages": today_messages,
            "today_blocked": today_blocked,
            "pending_reports": pending_reports,
            "total_reports": total_reports,
            "violations_breakdown": violations_breakdown,
            "stage_breakdown": stage_breakdown,
            "daily_trend": daily_trend
        }
