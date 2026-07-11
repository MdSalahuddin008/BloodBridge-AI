import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

from app.database.database import SessionLocal
from app.services.chat_service import ChatService
from app.ai.registration import RegistrationManager
from app.services.registration_service import RegistrationService

# Load environment variables from .env when present.
load_dotenv()

# Create OpenRouter client
client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)

registration = RegistrationManager()


class CoordinatorAgent:

    def generate_reply(
        self,
        user_type: str,
        user_id: int,
        user_message: str,
        matched_donors=None,
        total_matches=None,
        eligibility_response=None,
    ):

        db = SessionLocal()

        try:
            # ---------------- REGISTRATION FLOW ----------------
            if registration.is_registering:

                result = registration.process_message(user_message)

                if not result["completed"]:
                    return result["reply"]

                try:
                    if result["role"] == "donor":
                        RegistrationService.register_donor(
                            db=db,
                            **result["data"]
                        )
                    else:
                        RegistrationService.register_patient(
                            db=db,
                            **result["data"]
                        )
                except ValueError as error:
                    return (
                        "I couldn't save the registration yet.\n\n"
                        f"{error}\n\n"
                        "Please send the corrected detail."
                    )

                try:
                    if "app.rag.retriever" in sys.modules:
                        from app.rag.retriever import refresh_vector_store

                        refresh_vector_store()
                    else:
                        from app.rag.vector_store import create_vector_store

                        create_vector_store()
                except Exception as error:
                    print(f"[RAG] Vector-store refresh failed: {error}")

                registration.reset()

                return (
                    "✅ Registration completed successfully!\n\n"
                    "You can now start using BloodBridge AI."
                )

            # ---------------- CONVERSATION SETUP ----------------
            conversation = ChatService.get_or_create_conversation(
                db=db,
                user_type=user_type,
                user_id=user_id
            )

            ChatService.save_user_message(
                db=db,
                conversation_id=conversation.conversation_id,
                content=user_message
            )

            # Trigger registration start
            if user_message.lower() == "new user":
                reply = registration.start_registration()

                ChatService.save_ai_message(
                    db=db,
                    conversation_id=conversation.conversation_id,
                    content=reply,
                )

                return reply

            # Load history
            history = ChatService.load_messages(
                db=db,
                conversation_id=conversation.conversation_id
            )

            # ---------------- SPECIAL AGENT RESPONSES ----------------
            if eligibility_response:
                ChatService.save_ai_message(
                    db=db,
                    conversation_id=conversation.conversation_id,
                    content=eligibility_response,
                )
                return eligibility_response

            if matched_donors is not None:
                if len(matched_donors) == 0:
                    reply = "Sorry, I couldn't find any matching donors."
                else:
                    donor_list = "\n\n".join(
                        (
                            f"{index}.\n"
                            f"Name: {donor.full_name}\n"
                            f"Blood Group: {donor.blood_group}\n"
                            f"Phone: {donor.phone_number}\n"
                            f"City: {donor.city}"
                        )
                        for index, donor in enumerate(matched_donors, start=1)
                    )

                    reply = (
                        f"I found {total_matches} matching donor(s).\n\n"
                        "Showing the Top 5 ranked donors:\n\n"
                        f"{donor_list}"
                    )

                ChatService.save_ai_message(
                    db=db,
                    conversation_id=conversation.conversation_id,
                    content=reply,
                )
                return reply

            # ---------------- LLM RESPONSE ----------------
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are the Coordinator Agent for BloodBridge AI. "
                        "Your job is to help donors and patients, "
                        "understand their requests, and maintain a helpful conversation."
                    )
                }
            ]

            for message in history:
                role = "assistant" if message.sender == "assistant" else "user"
                messages.append(
                    {
                        "role": role,
                        "content": message.content
                    }
                )

            response = client.chat.completions.create(
                model="openai/gpt-4.1-mini",
                messages=messages
            )

            ai_reply = response.choices[0].message.content

            ChatService.save_ai_message(
                db=db,
                conversation_id=conversation.conversation_id,
                content=ai_reply
            )

            return ai_reply

        finally:
            db.close()


def start_registration():
    return registration.start_registration()
