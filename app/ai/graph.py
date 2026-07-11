from typing import TypedDict

from langgraph.graph import START, END, StateGraph

from app.ai.coordinator import CoordinatorAgent, registration
from app.ai.router import RouterAgent
from app.ai.matching import MatchingAgent
from app.ai.ranking import RankingAgent
from app.ai.eligibility import EligibilityAgent
from app.ai.notification import NotificationAgent
from app.database.database import SessionLocal
from app.database.models import Patient


class BloodBridgeState(TypedDict):
    user_type: str
    user_id: int
    message: str
    intent: str
    blood_group: str
    matched_donors: list
    total_matches: int
    notifications: list
    eligibility_response: str
    reply: str


coordinator = CoordinatorAgent()
router = RouterAgent()
matching = MatchingAgent()
eligibility = EligibilityAgent()
ranking = RankingAgent()
notification = NotificationAgent()


def router_node(state: BloodBridgeState) -> BloodBridgeState:
    if registration.is_registering:
        state["intent"] = "registration"
        print("[Router] Detected intent: registration")
        return state

    if state["message"].strip().lower() == "new user":
        state["intent"] = "registration"
        print("[Router] Detected intent: registration")
        return state

    intent = router.classify_intent(state["message"])
    print(f"[Router] Detected intent: {intent}")
    state["intent"] = intent
    return state


def matching_node(state: BloodBridgeState) -> BloodBridgeState:
    blood_group = matching.extract_blood_group(state["message"])

    print(f"[Matching] Extracted blood group: {blood_group}")

    if blood_group == "UNKNOWN":
        state["blood_group"] = blood_group
        state["matched_donors"] = []
        return state

    donors = matching.find_matching_donors(blood_group)

    print(f"[Matching] Found {len(donors)} donor(s)")
    
    state["total_matches"] = len(donors)
    state["blood_group"] = blood_group
    state["matched_donors"] = donors

    return state


def ranking_node(state: BloodBridgeState) -> BloodBridgeState:

    donors = state.get("matched_donors", [])
    patient_location = None
    patient_city = None
    requested_city = ranking.extract_city_from_text(state.get("message", ""))

    db = SessionLocal()
    try:
        patient = (
            db.query(Patient)
            .filter(Patient.patient_id == state["user_id"])
            .first()
        )
        if patient:
            patient_location = (patient.latitude, patient.longitude)
            patient_city = patient.city
    finally:
        db.close()

    city_for_matching = requested_city or patient_city
    ranked_donors = ranking.rank_donors(
        donors,
        patient_location=patient_location,
        patient_city=city_for_matching,
    )
    city_matched_donors = ranking.filter_donors_by_city(
        donors,
        patient_city=city_for_matching,
    )

    if city_for_matching:
        print(f"[Ranking] City filter: {city_for_matching}")
    print(f"[Ranking] Returning Top {len(ranked_donors)} donor(s)")

    state["matched_donors"] = ranked_donors
    state["total_matches"] = len(city_matched_donors)

    return state


def notification_node(state: BloodBridgeState) -> BloodBridgeState:

    notifications = notification.notify_donors(
        patient_id=state["user_id"],
        donors=state.get("matched_donors", []),
        blood_group=state.get("blood_group"),
    )

    print(f"[Notification] Created {len(notifications)} notification(s)")

    state["notifications"] = notifications

    return state



def eligibility_node(state: BloodBridgeState) -> BloodBridgeState:

    response = eligibility.answer_question(
        state["message"]
    )

    print("[Eligibility] Retrieved grounded response.")

    state["eligibility_response"] = response

    return state



def coordinator_node(state: BloodBridgeState) -> BloodBridgeState:
    reply = coordinator.generate_reply(
        user_type=state["user_type"],
        user_id=state["user_id"],
        user_message=state["message"],
        matched_donors=state.get("matched_donors"),
        total_matches=state.get("total_matches"),
        eligibility_response=state.get("eligibility_response"),
    )

    state["reply"] = reply
    return state


graph_builder = StateGraph(BloodBridgeState)

graph_builder.add_node("router", router_node)
graph_builder.add_node("matching", matching_node)
graph_builder.add_node("ranking", ranking_node)
graph_builder.add_node("eligibility", eligibility_node)
graph_builder.add_node("coordinator", coordinator_node)
graph_builder.add_node("notification", notification_node)




def route_after_router(state: BloodBridgeState) -> str:
    if registration.is_registering:
        return "coordinator"

    if state["intent"] == "blood_request":
        return "matching"

    if state["intent"] == "eligibility_query":
        return "eligibility"

    return "coordinator"




graph_builder.add_edge(START, "router")

graph_builder.add_conditional_edges(
    "router",
    route_after_router,
    {
        "matching": "matching",
        "eligibility": "eligibility",
        "coordinator": "coordinator",
    },
)

graph_builder.add_edge("matching", "ranking")
graph_builder.add_edge("ranking", "notification")
graph_builder.add_edge("notification", "coordinator")
graph_builder.add_edge("eligibility", "coordinator")
graph_builder.add_edge("coordinator", END)


bloodbridge_graph = graph_builder.compile()
