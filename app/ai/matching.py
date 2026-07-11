from sqlalchemy.orm import Session

from app.database.database import SessionLocal
from app.database.models import Donor
from openai import OpenAI
import os


class MatchingAgent:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
        )

    def extract_blood_group(self, user_message: str) -> str:
        system_prompt = """You are a blood group extraction AI.

Extract the blood group mentioned in the user's message.

Valid outputs are only:

A+
A-
B+
B-
AB+
AB-
O+
O-

If no blood group is mentioned, return:

UNKNOWN

Return ONLY the blood group.
"""

        response = self.client.chat.completions.create(
            model="openai/gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0,
        )

        return response.choices[0].message.content.strip().upper()

    def find_matching_donors(self, blood_group: str):
        db: Session = SessionLocal()

        try:
            donors = (
                db.query(Donor)
                .filter(
                    Donor.blood_group == blood_group,
                    Donor.currently_available == True
                )
                .all()
            )

            return donors

        finally:
            db.close()
