import asyncio

from sqlalchemy import select

from app.tasks.celery_app import celery
from app.database import SessionLocal

from app.models import (
    TimetableVersion,
    ScheduledClass,
    SchedulingRun,
    FacultyAssignment,
    VersionStatus,
)

from app.services.scheduler import HybridScheduler
from app.services.timetable import validate_timetable


@celery.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3}
)
def generate_timetable(self, config):
    db = SessionLocal()

    try:
        run = SchedulingRun(
            mode=config["mode"],
            status="RUNNING"
        )

        db.add(run)
        db.commit()

        scheduler = HybridScheduler(
            db,
            mode=config["mode"],
            priority_weight=config["priority_weight"],
            sjf_weight=config["sjf_weight"],
            weekdays=config["weekdays"],
            day_start=config["day_start"],
            day_end=config["day_end"],
            time_limit=config["time_limit"],
            section_id=config.get("section_id"),
            semester_id=config.get("semester_id"),
            programme_id=config.get("programme_id"),
            academic_year_id=config.get("academic_year_id")
        )

        result = scheduler.solve()

        if result["status"] not in ("OPTIMAL", "FEASIBLE"):
            run.status = result["status"]
            run.unscheduled = result["unscheduled"]
            db.commit()

            return {
                "status": run.status,
                "unscheduled": run.unscheduled
            }

        version_number = (
            db.scalar(
                select(TimetableVersion.version_number)
                .order_by(
                    TimetableVersion.version_number.desc()
                )
                .limit(1)
            ) or 0
        ) + 1

        version = TimetableVersion(
            version_number=version_number,
            status=VersionStatus.DRAFT,
            algorithm=config["mode"],
            priority_weight=config["priority_weight"],
            sjf_weight=config["sjf_weight"],
            quality_score=result["quality_score"],
            statistics=result["statistics"],
            section_id=config.get("section_id"),
            semester_id=config.get("semester_id"),
            programme_id=config.get("programme_id"),
            academic_year_id=config.get("academic_year_id"),
            created_by=config.get("admin_id")
        )

        db.add(version)
        db.flush()

        for index, item in enumerate(result["classes"]):
            db.add(
                ScheduledClass(
                    version_id=version.id,
                    assignment_id=item["assignment_id"],
                    faculty_id=item["faculty_id"],
                    subject_id=item["subject_id"],
                    section_id=item["section_id"],
                    room_id=item["room_id"],
                    weekday=item["weekday"],
                    start_minute=item["start_minute"],
                    end_minute=item["end_minute"],
                    session_number=index + 1
                )
            )

        db.flush()

        validation = validate_timetable(db, version.id)

        run.version_id = version.id
        run.status = "COMPLETED"
        run.unscheduled = result["unscheduled"]

        version.statistics = {
            **result["statistics"],
            "validation": validation,
            "unscheduled": result["unscheduled"]
        }

        db.commit()

        return {
            "status": "COMPLETED",
            "version_id": version.id,
            "quality_score": version.quality_score,
            "validation": validation,
            "unscheduled": result["unscheduled"]
        }

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


@celery.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3}
)
def deliver_notification(self, notification_id):
    from app.models import (
        WhatsAppNotification,
        TimetableImage,
        Student,
        Faculty,
    )
    from app.services.whatsapp import WhatsAppService

    db = SessionLocal()

    try:
        notification = db.get(
            WhatsAppNotification,
            notification_id
        )

        if not notification:
            return {"status": "NOT_FOUND"}

        if notification.status in (
            "DELIVERED", "READ"
        ):
            return {"status": notification.status}

        service = WhatsAppService()

        if not service.enabled:
            notification.last_error = "WhatsApp API not configured"
            db.commit()

            return {"status": "NOT_CONFIGURED"}

        if notification.attempts >= 5:
            notification.last_error = "Maximum attempts exceeded"
            db.commit()

            return {"status": "RETRY_LIMIT_REACHED"}

        notification.attempts += 1

        image = db.get(
            TimetableImage,
            notification.image_id
        )

        if not image:
            raise ValueError("Timetable image missing")

        # This worker needs a valid Meta media upload.
        media_id = asyncio.run(
            service.upload_image(image.file_path)
        )

        response = asyncio.run(
            service.send_image(
                notification.phone_number,
                media_id,
                "Your university timetable is attached."
            )
        )

        message_id = response["messages"][0]["id"]

        notification.message_id = message_id
        notification.status = "SENT"
        notification.last_error = None

        db.commit()

        return {
            "status": "SENT",
            "message_id": message_id
        }

    except Exception as exc:
        db.rollback()

        notification = db.get(
            WhatsAppNotification,
            notification_id
        )

        if notification:
            notification.status = "FAILED"
            notification.last_error = str(exc)
            db.commit()

        raise

    finally:
        db.close()