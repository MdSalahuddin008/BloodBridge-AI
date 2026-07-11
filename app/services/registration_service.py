from sqlalchemy.orm import Session
from app.database.models import Donor, Patient
from datetime import datetime
import re


class RegistrationService:

    # ---------------- DATE PARSER ----------------
    @staticmethod
    def _parse_date(value):
        if value is None:
            return None

        if isinstance(value, str):
            value = value.strip().lower()

            # Try common formats
            formats = [
                "%Y-%m-%d",
                "%B %d %Y",   # January 8 2026
                "%b %d %Y",   # Jan 8 2026
                "%d-%m-%Y",
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue

            return None  # fallback if parsing fails

        return value

    # ---------------- BOOL PARSER ----------------
    @staticmethod
    def _parse_bool(value):
        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            return value.strip().lower() in ["yes", "true", "1", "y"]

        return False

    @staticmethod
    def _parse_float(value):
        if value is None:
            return None

        if isinstance(value, (int, float)):
            return float(value)

        match = re.search(r"-?\d+(?:\.\d+)?", str(value))
        if match:
            return float(match.group(0))

        return None

    @staticmethod
    def _normalize_blood_group(value):
        return str(value).strip().upper().replace(" ", "")

    # ---------------- COORDINATES ----------------
    @staticmethod
    def _parse_coordinates(coordinates: str):
        try:
            if isinstance(coordinates, (tuple, list)) and len(coordinates) == 2:
                return float(coordinates[0]), float(coordinates[1])

            latitude, longitude = coordinates.split(",")
            return float(latitude.strip()), float(longitude.strip())

        except (ValueError, AttributeError):
            raise ValueError(
                "Coordinates must be in the format: latitude,longitude"
            )

    # ---------------- DONOR REGISTRATION ----------------
    @staticmethod
    def register_donor(
        db: Session,
        full_name: str,
        phone_number: str,
        gender: str,
        date_of_birth,
        blood_group: str,
        weight: float,
        city: str,
        state: str,
        coordinates: str,
        last_donation_date,
        currently_available: bool,
    ):

        latitude, longitude = RegistrationService._parse_coordinates(coordinates)
        existing = db.query(Donor).filter(
            Donor.phone_number == phone_number
        ).first()

        if existing:
            return existing

        donor = Donor(
            full_name=full_name,
            phone_number=phone_number,
            gender=gender,
            date_of_birth=RegistrationService._parse_date(date_of_birth),
            blood_group=RegistrationService._normalize_blood_group(blood_group),
            weight=RegistrationService._parse_float(weight),
            city=city,
            state=state,
            latitude=latitude,
            longitude=longitude,
            last_donation_date=RegistrationService._parse_date(last_donation_date),
            currently_available=RegistrationService._parse_bool(currently_available),
        )

        db.add(donor)
        db.commit()
        db.refresh(donor)

        return donor

    # ---------------- PATIENT REGISTRATION ----------------
    @staticmethod
    def register_patient(
        db: Session,
        full_name: str,
        phone_number: str,
        gender: str,
        date_of_birth,
        blood_group: str,
        city: str,
        state: str,
        coordinates: str,
    ):

        latitude, longitude = RegistrationService._parse_coordinates(coordinates)
        existing = db.query(Patient).filter(
            Patient.phone_number == phone_number
        ).first()

        if existing:
            return existing

        patient = Patient(
            full_name=full_name,
            phone_number=phone_number,
            gender=gender,
            date_of_birth=RegistrationService._parse_date(date_of_birth),
            blood_group=RegistrationService._normalize_blood_group(blood_group),
            city=city,
            state=state,
            latitude=latitude,
            longitude=longitude,
        )

        db.add(patient)
        db.commit()
        db.refresh(patient)

        return patient
