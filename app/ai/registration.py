import json
import os
import re

from openai import OpenAI


class RegistrationManager:

    DONOR_FIELDS = [
        "full_name",
        "phone_number",
        "gender",
        "date_of_birth",
        "blood_group",
        "weight",
        "city",
        "state",
        "coordinates",
        "last_donation_date",
        "currently_available",
    ]

    PATIENT_FIELDS = [
        "full_name",
        "phone_number",
        "gender",
        "date_of_birth",
        "blood_group",
        "city",
        "state",
        "coordinates",
    ]

    QUESTIONS = {
        "role":
            "Hi! 👋 Welcome to BloodBridge AI.\n\n"
            "Are you registering as a donor or a patient?",

        "full_name":
            "Great! What's your full name?",

        "phone_number":
            "What's your phone number?",

        "gender":
            "What's your gender?",

        "date_of_birth":
            "What's your date of birth? (YYYY-MM-DD)",

        "blood_group":
            "What's your blood group?",

        "weight":
            "What's your weight (kg)?",

        "city":
            "Which city do you live in?",

        "state":
            "Which state do you live in?",

        "coordinates":
            "Please paste your Google Maps coordinates.\n\n"
            "Example:\n"
            "12.9716,77.5946",

        "last_donation_date":
            "When was your last blood donation?\n"
            "(YYYY-MM-DD or type 'None')",

        "currently_available":
            "Are you currently available to donate?\n"
            "(Yes / No)"
    }

    def __init__(self):
        api_key = os.getenv("OPENROUTER_API_KEY")
        self.client = None
        if api_key:
            self.client = OpenAI(
                api_key=api_key,
                base_url="https://openrouter.ai/api/v1",
            )
        self.reset()

    def reset(self):
        self.role = None
        self.data = {}
        self.pending_field = None
        self.is_registering = False


    def start_registration(self):

        self.reset()

        self.is_registering = True

        return self.QUESTIONS["role"]

    def _fields(self):
        if self.role == "donor":
            return self.DONOR_FIELDS

        if self.role == "patient":
            return self.PATIENT_FIELDS

        return []

    def _missing_fields(self):
        return [
            field
            for field in self._fields()
            if not str(self.data.get(field, "")).strip()
        ]

    @staticmethod
    def _extract_json(text: str):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if not match:
                return {}

            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return {}

    def _llm_extract(self, user_message: str):
        if self.client is None:
            raise RuntimeError("OPENROUTER_API_KEY is not configured")

        fields = self._fields()
        current_missing = self._missing_fields()
        role_instruction = (
            "If the user says they are registering as a donor or patient, "
            "set role to donor or patient. Otherwise use null."
            if self.role is None
            else f"The role is already {self.role}; keep role as {self.role}."
        )

        system_prompt = f"""
You extract structured registration data for BloodBridge AI.

{role_instruction}

Return ONLY valid JSON with these keys:
- role
- data

The data object may contain only these fields:
{fields or self.DONOR_FIELDS + self.PATIENT_FIELDS}

Rules:
- Extract multiple fields from natural language when possible.
- Use null for unknown values.
- coordinates must be a single "latitude,longitude" string.
- blood_group must be one of A+, A-, B+, B-, AB+, AB-, O+, O- when present.
- currently_available must be yes or no when present.
- date values should be YYYY-MM-DD when the user gives a clear date.
- The app is currently waiting for this field when present:
  {self.pending_field}
- Current missing fields:
  {current_missing}
"""

        response = self.client.chat.completions.create(
            model="openai/gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0,
        )

        parsed = self._extract_json(response.choices[0].message.content)
        if not isinstance(parsed, dict):
            return {}

        return parsed

    def _merge_extracted_data(self, extracted):
        extracted_role = str(extracted.get("role") or "").strip().lower()

        if self.role is None and extracted_role in {"donor", "patient"}:
            self.role = extracted_role

        if self.role is None:
            lowered = extracted_role.lower()
            if "donor" in lowered:
                self.role = "donor"
            elif "patient" in lowered:
                self.role = "patient"

        extracted_data = extracted.get("data") or {}
        if not isinstance(extracted_data, dict):
            return

        allowed_fields = set(self._fields())
        for field, value in extracted_data.items():
            if field not in allowed_fields or value is None:
                continue

            value = str(value).strip()
            if value:
                self.data[field] = value

    @staticmethod
    def _fallback_role(user_message: str):
        lowered = user_message.lower()
        if "donor" in lowered:
            return "donor"
        if "patient" in lowered:
            return "patient"
        return None

    @staticmethod
    def _fallback_coordinates(user_message: str):
        match = re.search(
            r"(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)",
            user_message,
        )
        if match:
            return f"{match.group(1)},{match.group(2)}"
        return None


    def process_message(self, user_message: str):

        user_message = user_message.strip()

        try:
            extracted = self._llm_extract(user_message)
            self._merge_extracted_data(extracted)
        except Exception as error:
            if "OPENROUTER_API_KEY" not in str(error):
                print(f"[Registration] LLM extraction failed: {error}")
            if self.role is None:
                self.role = self._fallback_role(user_message)

            if self.pending_field in self._fields():
                self.data[self.pending_field] = user_message

            if self.role is not None:
                missing = self._missing_fields()
                if "coordinates" in missing:
                    coordinates = self._fallback_coordinates(user_message)
                    if coordinates:
                        self.data["coordinates"] = coordinates

        if self.role is None:
            return {
                "completed": False,
                "reply": "Are you registering as a donor or a patient?",
            }

        missing_fields = self._missing_fields()

        if not missing_fields:
            self.pending_field = None

            return {
                "completed": True,
                "role": self.role,
                "data": self.data,
            }

        next_field = missing_fields[0]
        self.pending_field = next_field

        return {
            "completed": False,
            "reply": self.QUESTIONS[next_field],
        }
