from openai import OpenAI
import os


class RouterAgent:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
        )

    def classify_intent(self, user_message: str) -> str:
        system_prompt = """
You are an intent classification AI.

Classify the user's message into exactly ONE of these intents:

- blood_request
- donor_registration
- eligibility_query
- general_chat

Examples:

"I need O+ blood urgently."
→ blood_request

"My father needs B- blood."
→ blood_request

"Can I donate blood after getting a tattoo?"
→ eligibility_query

"Can diabetics donate blood?"
→ eligibility_query

"What is the minimum age for blood donation?"
→ eligibility_query

"I want to become a blood donor."
→ donor_registration

"Register me as a donor."
→ donor_registration

"Hello"
→ general_chat

"How are you?"
→ general_chat

Return ONLY the intent name.
Do not explain your answer.
"""

        response = self.client.chat.completions.create(
            model="openai/gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=0,
        )

        return response.choices[0].message.content.strip()