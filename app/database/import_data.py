import json
from datetime import datetime
from pathlib import Path

from app.database.database import SessionLocal
from app.database.models import Donor, Patient


BASE_DIR = Path(__file__).resolve().parents[2]

DONORS_JSON = BASE_DIR / "donors.json"
PATIENTS_JSON = BASE_DIR / "patients.json"


def parse_date(date_str):
    if not date_str:
        return None
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def import_donors(session):
    if session.query(Donor).first():
        print("⚠️ Donors already exist. Skipping donor import.")
        return

    with open(DONORS_JSON, "r", encoding="utf-8") as file:
        donors = json.load(file)

    for donor in donors:
        session.add(
            Donor(
                donor_id=donor["donor_id"],
                full_name=donor["full_name"],
                phone_number=donor["phone_number"],
                gender=donor["gender"],
                date_of_birth=parse_date(donor["date_of_birth"]),
                blood_group=donor["blood_group"],
                weight=donor["weight"],
                city=donor["city"],
                state=donor["state"],
                latitude=donor["latitude"],
                longitude=donor["longitude"],
                last_donation_date=parse_date(donor["last_donation_date"]),
                tattoo_date=parse_date(donor["tattoo_date"]),
                currently_available=donor["currently_available"],
            )
        )

    session.commit()
    print(f"✅ Imported {len(donors)} donors.")


def import_patients(session):
    if session.query(Patient).first():
        print("⚠️ Patients already exist. Skipping patient import.")
        return

    with open(PATIENTS_JSON, "r", encoding="utf-8") as file:
        patients = json.load(file)

    for patient in patients:
        session.add(
            Patient(
                patient_id=patient["patient_id"],
                full_name=patient["full_name"],
                phone_number=patient["phone_number"],
                gender=patient["gender"],
                date_of_birth=parse_date(patient["date_of_birth"]),
                blood_group=patient["blood_group"],
                city=patient["city"],
                state=patient["state"],
                latitude=patient["latitude"],
                longitude=patient["longitude"],
            )
        )

    session.commit()
    print(f"✅ Imported {len(patients)} patients.")


def main():
    session = SessionLocal()

    try:
        import_donors(session)
        import_patients(session)
    finally:
        session.close()


if __name__ == "__main__":
    main()