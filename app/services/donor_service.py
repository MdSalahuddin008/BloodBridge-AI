from app.database.database import SessionLocal
from app.database.models import Notification, Donor


def get_donor_notifications(donor_id: int):
    db = SessionLocal()

    try:
        donor = db.query(Donor).filter(Donor.donor_id == donor_id).first()

        rows = (
            db.query(Notification)
            .filter(Notification.donor_id == donor_id)
            .order_by(Notification.created_at.desc(), Notification.notification_id.desc())
            .all()
        )

        notifications = []
        seen_requests = set()

        for notification in rows:
            request_key = (
                notification.patient_id,
                notification.blood_group,
                notification.city,
            )

            if request_key in seen_requests:
                continue

            seen_requests.add(request_key)
            notifications.append(notification)

        return donor, notifications

    finally:
        db.close()


def update_notification_status(notification_id: int, status: str):
    if status not in {"Accepted", "Declined"}:
        raise ValueError("Notification status must be Accepted or Declined")

    db = SessionLocal()

    try:
        notification = (
            db.query(Notification)
            .filter(Notification.notification_id == notification_id)
            .first()
        )

        if notification is None:
            return None

        notification.status = status
        db.commit()
        db.refresh(notification)

        donor = (
            db.query(Donor)
            .filter(Donor.donor_id == notification.donor_id)
            .first()
        )
        notification.donor_name = donor.full_name if donor else "Unknown donor"
        notification.donor_phone = donor.phone_number if donor else "Unknown phone"

        return notification

    finally:
        db.close()


def clear_notifications():
    db = SessionLocal()

    try:
        deleted_count = db.query(Notification).delete()
        db.commit()

        return deleted_count

    finally:
        db.close()
