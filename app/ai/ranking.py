from datetime import date
from math import asin, cos, radians, sin, sqrt
import re


class RankingAgent:
    MIN_DAYS_BETWEEN_DONATIONS = 90
    CITY_ALIASES = {
        "bagalkot": "bagalkot",
        "ballari": "ballari",
        "basavakalyan": "basavakalyan",
        "belagavi": "belagavi",
        "bengaluru": "bengaluru",
        "bidar": "bidar",
        "dharwad": "dharwad",
        "gadag": "gadag",
        "gulbarga": "kalaburagi",
        "haveri": "haveri",
        "hubballi": "hubballi",
        "kalaburagi": "kalaburagi",
        "koppal": "koppal",
        "mangaluru": "mangaluru",
        "mysuru": "mysuru",
        "raichur": "raichur",
        "shahapur": "shahapur",
        "shivamogga": "shivamogga",
        "tumakuru": "tumakuru",
        "vijayapura": "vijayapura",
        "yadgir": "yadgir",
    }

    @classmethod
    def normalize_city(cls, city):
        if not city:
            return None

        normalized = re.sub(r"\s+", " ", str(city).strip().lower())
        return cls.CITY_ALIASES.get(normalized, normalized)

    @classmethod
    def extract_city_from_text(cls, text):
        if not text:
            return None

        normalized_text = str(text).lower()
        for city, canonical_city in cls.CITY_ALIASES.items():
            if re.search(rf"\b{re.escape(city)}\b", normalized_text):
                return canonical_city

        return None

    def filter_donors_by_city(self, donors, patient_city=None):
        normalized_patient_city = self.normalize_city(patient_city)

        if not normalized_patient_city:
            return list(donors)

        return [
            donor
            for donor in donors
            if self.normalize_city(donor.city) == normalized_patient_city
        ]

    @staticmethod
    def calculate_age(date_of_birth):
        if date_of_birth is None:
            return None

        today = date.today()
        age = today.year - date_of_birth.year

        if (today.month, today.day) < (date_of_birth.month, date_of_birth.day):
            age -= 1

        return age

    @staticmethod
    def calculate_distance_km(origin, donor):
        if not origin:
            return None

        patient_latitude, patient_longitude = origin

        if (
            patient_latitude is None
            or patient_longitude is None
            or donor.latitude is None
            or donor.longitude is None
        ):
            return None

        earth_radius_km = 6371
        lat1 = radians(patient_latitude)
        lon1 = radians(patient_longitude)
        lat2 = radians(donor.latitude)
        lon2 = radians(donor.longitude)

        delta_lat = lat2 - lat1
        delta_lon = lon2 - lon1

        haversine = (
            sin(delta_lat / 2) ** 2
            + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
        )

        return 2 * earth_radius_km * asin(sqrt(haversine))

    @staticmethod
    def days_since_last_donation(last_donation_date):
        if last_donation_date is None:
            return None

        return (date.today() - last_donation_date).days

    def rank_donors(self, donors, patient_location=None, patient_city=None):
        """
        Rank donors by practical suitability:
        first restrict to the requested/patient city, then sort those donors by
        availability, basic eligibility, GPS distance, donation cooldown, and age.
        Return only the Top 5.
        """

        if not donors:
            return []

        candidate_donors = self.filter_donors_by_city(donors, patient_city)

        if not candidate_donors:
            return []

        def sort_key(donor):
            distance_km = self.calculate_distance_km(patient_location, donor)
            age = self.calculate_age(donor.date_of_birth)
            days_since_donation = self.days_since_last_donation(
                donor.last_donation_date
            )

            unavailable_penalty = 0 if donor.currently_available else 1

            age_penalty = 0
            if age is not None and not 18 <= age <= 65:
                age_penalty = 1

            weight_penalty = 0
            if donor.weight is not None and donor.weight < 50:
                weight_penalty = 1

            recent_donation_penalty = 0
            if (
                days_since_donation is not None
                and days_since_donation < self.MIN_DAYS_BETWEEN_DONATIONS
            ):
                recent_donation_penalty = 1

            gps_missing_penalty = 1 if distance_km is None else 0

            if age is None:
                age_tie_breaker = 99
            elif 25 <= age <= 45:
                age_tie_breaker = 0
            elif 18 <= age <= 65:
                age_tie_breaker = 1
            else:
                age_tie_breaker = 2

            return (
                unavailable_penalty,
                age_penalty,
                weight_penalty,
                gps_missing_penalty,
                distance_km if distance_km is not None else float("inf"),
                recent_donation_penalty,
                age_tie_breaker,
            )

        ranked = sorted(candidate_donors, key=sort_key)

        return ranked[:5]
