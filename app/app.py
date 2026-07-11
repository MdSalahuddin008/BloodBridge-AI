from pathlib import Path
import sys

if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gradio as gr
from app.ai.coordinator import start_registration as coordinator_start_registration
from app.services.donor_service import (
    clear_notifications,
    get_donor_notifications,
    update_notification_status,
)

USER_TYPE = "patient"
USER_ID = 1


def hide_notification_actions():
    return (
        gr.update(visible=False),
        gr.update(visible=False),
    )


def show_notification_actions(notification_id):
    is_visible = notification_id is not None
    return (
        gr.update(visible=is_visible),
        gr.update(visible=is_visible),
    )


# ---------------- CHAT FUNCTION ----------------
def chat(user_message, history):
    if history is None:
        history = []

    user_message = user_message.strip()
    if not user_message:
        accept_update, decline_update = hide_notification_actions()
        return "", history, gr.update(), "", None, accept_update, decline_update

    from app.ai.graph import bloodbridge_graph

    result = bloodbridge_graph.invoke(
        {
            "user_type": USER_TYPE,
            "user_id": USER_ID,
            "message": user_message,
            "intent": "",
            "reply": "",
        }
    )

    ai_reply = result.get("reply", "")
    top_donors = result.get("matched_donors", [])

    donor_choices = [
        f"{d.donor_id} - {d.full_name} ({d.blood_group})"
        for d in top_donors[:5]
    ]

    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": ai_reply})

    accept_update, decline_update = hide_notification_actions()

    return (
        "",
        history,
        gr.update(choices=donor_choices, value=None),
        "",
        None,
        accept_update,
        decline_update,
    )


# ---------------- DONOR DETAILS ----------------
def show_donor_details(choice):
    if not choice:
        accept_update, decline_update = hide_notification_actions()
        return "Select a donor", None, accept_update, decline_update

    choice = str(choice).strip()

    if " - " not in choice:
        accept_update, decline_update = hide_notification_actions()
        return "Invalid selection", None, accept_update, decline_update

    donor_id = int(choice.split(" - ")[0])

    donor, notifications = get_donor_notifications(donor_id)

    if not donor:
        accept_update, decline_update = hide_notification_actions()
        return "❌ Donor not found", None, accept_update, decline_update

    text = f"## 🧑 {donor.full_name}\n"
    text += f"🩸 {donor.blood_group}\n"
    text += f"📍 {donor.city}\n\n"
    text += "## Notifications:\n"

    if not notifications:
        accept_update, decline_update = hide_notification_actions()
        return text + "\nNo notifications yet.", None, accept_update, decline_update

    pending_notification_id = None
    for n in notifications:
        text += f"- Request #{n.notification_id}: {n.status} | {n.blood_group} | {n.city}\n"

        if pending_notification_id is None and n.status == "Pending":
            pending_notification_id = n.notification_id

    if pending_notification_id is not None:
        text += "\nRespond to the pending notification below."

    accept_update, decline_update = show_notification_actions(
        pending_notification_id
    )

    return text, pending_notification_id, accept_update, decline_update


def respond_to_notification(notification_id, status, donor_choice, update_history):
    if update_history is None:
        update_history = []

    if notification_id is None:
        accept_update, decline_update = hide_notification_actions()
        return (
            "Select a donor with a pending notification.",
            None,
            accept_update,
            decline_update,
            update_history,
        )

    notification = update_notification_status(int(notification_id), status)

    donor_output, next_notification_id, accept_update, decline_update = (
        show_donor_details(donor_choice)
    )

    if notification is None:
        update_history.append(
            {
                "role": "assistant",
                "content": "The selected donor notification was not found.",
            }
        )
        print("[Notification] Error: selected notification was not found")
        return (
            donor_output,
            next_notification_id,
            accept_update,
            decline_update,
            update_history,
        )

    donor_name = notification.donor_name
    donor_phone = notification.donor_phone
    action = "accepted" if status == "Accepted" else "declined"

    if status == "Accepted":
        patient_message = (
            f"Good news: {donor_name} accepted your "
            f"{notification.blood_group} blood request in {notification.city}. "
            f"Contact: {donor_phone}"
        )
    else:
        patient_message = (
            f"{donor_name} declined your {notification.blood_group} "
            f"blood request in {notification.city}."
        )

    update_history.append({"role": "assistant", "content": patient_message})
    print(
        "[Notification] "
        f"{status}: donor {donor_name} {action} request "
        f"#{notification.notification_id} "
        f"({notification.blood_group}, {notification.city})"
    )
    print(
        "[Patient Chat] "
        f"Sent to patient: {patient_message}"
    )

    return (
        donor_output,
        next_notification_id,
        accept_update,
        decline_update,
        update_history,
    )

def show_chat():
    return (
        gr.update(visible=False),   # Hide welcome page
        gr.update(visible=True),    # Show chat page
        gr.update(visible=True),    # Show existing-user donor panel
        gr.update(visible=True),    # Show patient updates for existing users
    )

def start_registration(history):

    if history is None:
        history = []

    history.append(
        {
            "role": "user",
            "content": "New User"
        }
    )

    reply = coordinator_start_registration()

    history.append(
        {
            "role": "assistant",
            "content": reply
        }
    )

    return (
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(visible=False),
        history,
    )
# ---------------- UI ----------------
# ---------------- UI ----------------
with gr.Blocks(title="BloodBridge AI") as demo:

    welcome_group = gr.Group(visible=True)

    with welcome_group:

        gr.Markdown("# 🩸 BloodBridge AI")

        gr.Markdown(
            "## Welcome!\n\n"
            "Please choose one of the following options."
        )

        new_user_btn = gr.Button("🆕 New User")

        existing_user_btn = gr.Button("👤 Existing User")

    chat_group = gr.Group(visible=False)

    with chat_group:
        with gr.Row():

        # LEFT SIDE - CHAT
            with gr.Column(scale=2):

                chatbot = gr.Chatbot(height=380)

                patient_updates = gr.Chatbot(
                    label="Patient Updates",
                    height=160,
                    visible=True,
                )

                message = gr.Textbox(
                    placeholder="Type your message...",
                    label="Message"
                )

                send = gr.Button("Send")

        # RIGHT SIDE - DONORS
            with gr.Column(scale=1, visible=True) as donor_panel:

                gr.Markdown("## 🏆 Top Matching Donors")

                donor_list = gr.Dropdown(
                    choices=[],
                    value=None,
                    label="Top 5 Donors"
                )

                donor_output = gr.Markdown()

                selected_notification = gr.State(value=None)

                with gr.Row():
                    accept = gr.Button("Accept", visible=False)
                    decline = gr.Button("Decline", visible=False)

        # ---------------- EVENTS ----------------
            send.click(
                fn=chat,
                inputs=[message, chatbot],
                outputs=[
                    message,
                    chatbot,
                    donor_list,
                    donor_output,
                    selected_notification,
                    accept,
                    decline,
                ]
            )

            message.submit(
                fn=chat,
                inputs=[message, chatbot],
                outputs=[
                    message,
                    chatbot,
                    donor_list,
                    donor_output,
                    selected_notification,
                    accept,
                    decline,
                ]
            )

            donor_list.change(
                fn=show_donor_details,
                inputs=[donor_list],
                outputs=[donor_output, selected_notification, accept, decline]
            )

            accept.click(
                fn=lambda notification_id, donor_choice, update_history: respond_to_notification(
                    notification_id,
                    "Accepted",
                    donor_choice,
                    update_history,
                ),
                inputs=[selected_notification, donor_list, patient_updates],
                outputs=[
                    donor_output,
                    selected_notification,
                    accept,
                    decline,
                    patient_updates,
                ]
            )

            decline.click(
                fn=lambda notification_id, donor_choice, update_history: respond_to_notification(
                    notification_id,
                    "Declined",
                    donor_choice,
                    update_history,
                ),
                inputs=[selected_notification, donor_list, patient_updates],
                outputs=[
                    donor_output,
                    selected_notification,
                    accept,
                    decline,
                    patient_updates,
                ]
            )

            new_user_btn.click(
                fn=start_registration,
                inputs=[chatbot],
                outputs=[
                    welcome_group,
                    chat_group,
                    donor_panel,
                    patient_updates,
                    chatbot,
                ]
            )

            existing_user_btn.click(
                fn=show_chat,
                outputs=[
                    welcome_group,
                    chat_group,
                    donor_panel,
                    patient_updates,
                ]
            )

def launch_app(*args, **kwargs):
    clear_notifications()

    try:
        from app.rag.vector_store import create_vector_store

        create_vector_store()
        return demo.launch(*args, **kwargs)
    finally:
        clear_notifications()


if __name__ == "__main__":
    launch_app()
