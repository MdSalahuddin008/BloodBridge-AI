import os

from openai import OpenAI


class EligibilityAgent:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
        )

    def answer_question(self, user_message: str) -> str:
        from app.rag.retriever import retrieve_documents

        documents = retrieve_documents(user_message)

        context = "\n\n".join(
            doc.page_content
            for doc in documents
        )

        system_prompt = f"""
You are the BloodBridge Eligibility Agent.

Answer ONLY using the provided blood donation guidelines.

If the answer is not present in the guidelines, say:

"I don't have enough information in the current blood donation guidelines."

Blood Donation Guidelines:

{context}
"""

        response = self.client.chat.completions.create(
            model="openai/gpt-4.1-mini",
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_message,
                },
            ],
        )

        return response.choices[0].message.content.strip()
