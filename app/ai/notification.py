from pathlib import Path
import sys

if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.database.database import SessionLocal
from app.database.models import Notification, Patient


class NotificationAgent:

    def notify_donors(self, patient_id: int, donors, blood_group: str | None = None):

        db = SessionLocal()

        try:
            patient = (
                db.query(Patient)
                .filter(Patient.patient_id == patient_id)
                .first()
            )

            if patient is None:
                return []

            requested_blood_group = blood_group or patient.blood_group
            notifications = []
            donor_ids = set()

            for donor in donors:
                if donor.donor_id in donor_ids:
                    continue

                donor_ids.add(donor.donor_id)

                existing = db.query(Notification).filter(
                    Notification.donor_id == donor.donor_id,
                    Notification.patient_id == patient.patient_id,
                    Notification.blood_group == requested_blood_group,
                    Notification.city == donor.city,
                    Notification.status.in_(["Pending", "Accepted"])
                ).first()

                if existing:
                    print(
                        "[Notification] "
                        f"{existing.status}: request #{existing.notification_id} "
                        f"already exists for donor {donor.full_name} "
                        f"({requested_blood_group}, {donor.city})"
                    )
                    continue

                notification = Notification(
                    donor_id=donor.donor_id,
                    patient_id=patient.patient_id,
                    blood_group=requested_blood_group,
                    city=donor.city,
                    status="Pending"
                )

                db.add(notification)
                db.flush()
                print(
                    "[Notification] "
                    f"Pending: request #{notification.notification_id} "
                    f"sent to donor {donor.full_name} "
                    f"({requested_blood_group}, {donor.city})"
                )
                notifications.append(notification)

            db.commit()

            return notifications

        finally:
            db.close()
