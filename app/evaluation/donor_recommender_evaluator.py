import argparse
import json
from dataclasses import dataclass
from datetime import date, datetime
from math import log2
from pathlib import Path
from statistics import mean

from app.ai.ranking import RankingAgent


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DONORS_PATH = PROJECT_ROOT / "donors.json"
DEFAULT_PATIENTS_PATH = PROJECT_ROOT / "patients.json"


@dataclass
class DonorRecord:
    donor_id: int
    full_name: str
    phone_number: str
    gender: str
    date_of_birth: date | None
    blood_group: str
    weight: float | None
    city: str | None
    state: str | None
    latitude: float | None
    longitude: float | None
    last_donation_date: date | None
    tattoo_date: date | None
    currently_available: bool


@dataclass
class PatientRecord:
    patient_id: int
    full_name: str
    phone_number: str
    gender: str
    date_of_birth: date | None
    blood_group: str
    city: str | None
    state: str | None
    latitude: float | None
    longitude: float | None


def parse_date(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def load_records(donors_path=DEFAULT_DONORS_PATH, patients_path=DEFAULT_PATIENTS_PATH):
    with open(donors_path, "r", encoding="utf-8") as file:
        donors = [
            DonorRecord(
                donor_id=row["donor_id"],
                full_name=row["full_name"],
                phone_number=row["phone_number"],
                gender=row["gender"],
                date_of_birth=parse_date(row["date_of_birth"]),
                blood_group=row["blood_group"],
                weight=row["weight"],
                city=row["city"],
                state=row["state"],
                latitude=row["latitude"],
                longitude=row["longitude"],
                last_donation_date=parse_date(row["last_donation_date"]),
                tattoo_date=parse_date(row["tattoo_date"]),
                currently_available=row["currently_available"],
            )
            for row in json.load(file)
        ]

    with open(patients_path, "r", encoding="utf-8") as file:
        patients = [
            PatientRecord(
                patient_id=row["patient_id"],
                full_name=row["full_name"],
                phone_number=row["phone_number"],
                gender=row["gender"],
                date_of_birth=parse_date(row["date_of_birth"]),
                blood_group=row["blood_group"],
                city=row["city"],
                state=row["state"],
                latitude=row["latitude"],
                longitude=row["longitude"],
            )
            for row in json.load(file)
        ]

    return donors, patients


class DonorRecommendationEvaluator:
    """Evaluate donor matching and ranking quality with offline recommendation metrics."""

    RELEVANT_DONOR_THRESHOLD = 5

    def __init__(self, donors, patients, top_k=5):
        self.donors = donors
        self.patients = patients
        self.top_k = top_k
        self.ranking_agent = RankingAgent()

    def recommend_for_patient(self, patient):
        matching_donors = [
            donor
            for donor in self.donors
            if donor.blood_group == patient.blood_group and donor.currently_available
        ]

        return self.ranking_agent.rank_donors(
            matching_donors,
            patient_location=(patient.latitude, patient.longitude),
            patient_city=patient.city,
        )

    def relevance_score(self, patient, donor):
        if donor.blood_group != patient.blood_group:
            return 0
        if not donor.currently_available:
            return 0

        score = 1

        if self.ranking_agent.normalize_city(donor.city) == self.ranking_agent.normalize_city(
            patient.city
        ):
            score += 2

        age = self.ranking_agent.calculate_age(donor.date_of_birth)
        days_since_donation = self.ranking_agent.days_since_last_donation(
            donor.last_donation_date
        )
        distance_km = self.ranking_agent.calculate_distance_km(
            (patient.latitude, patient.longitude),
            donor,
        )

        if age is not None and 18 <= age <= 65:
            score += 1
        if donor.weight is not None and donor.weight >= 50:
            score += 1
        if (
            days_since_donation is None
            or days_since_donation >= self.ranking_agent.MIN_DAYS_BETWEEN_DONATIONS
        ):
            score += 1
        if distance_km is not None and distance_km <= 25:
            score += 1

        return score

    def evaluate_patient(self, patient):
        recommendations = self.recommend_for_patient(patient)
        recommended_ids = {donor.donor_id for donor in recommendations}

        all_relevances = {
            donor.donor_id: self.relevance_score(patient, donor)
            for donor in self.donors
        }
        relevant_ids = {
            donor_id
            for donor_id, relevance in all_relevances.items()
            if relevance >= self.RELEVANT_DONOR_THRESHOLD
        }

        ranked_relevances = [
            all_relevances[donor.donor_id]
            for donor in recommendations[: self.top_k]
        ]
        ideal_relevances = sorted(all_relevances.values(), reverse=True)[: self.top_k]

        hits = recommended_ids & relevant_ids
        top_relevance = max(all_relevances.values(), default=0)
        top_relevant_ids = {
            donor_id
            for donor_id, relevance in all_relevances.items()
            if relevance == top_relevance and relevance > 0
        }

        return {
            "patient_id": patient.patient_id,
            "patient_name": patient.full_name,
            "blood_group": patient.blood_group,
            "city": patient.city,
            "recommendation_count": len(recommendations),
            "relevant_candidate_count": len(relevant_ids),
            "precision_at_k": precision_at_k(recommendations, relevant_ids, self.top_k),
            "recall_at_k": recall_at_k(recommendations, relevant_ids, self.top_k),
            "hit_rate_at_k": 1.0 if hits else 0.0,
            "ndcg_at_k": ndcg_at_k(ranked_relevances, ideal_relevances),
            "mrr": reciprocal_rank(recommendations, relevant_ids),
            "average_precision": average_precision(recommendations, relevant_ids, self.top_k),
            "top1_accuracy": (
                1.0
                if recommendations
                and recommendations[0].donor_id in top_relevant_ids
                else 0.0
            ),
            "blood_group_accuracy": recommended_constraint_rate(
                recommendations,
                lambda donor: donor.blood_group == patient.blood_group,
            ),
            "availability_accuracy": recommended_constraint_rate(
                recommendations,
                lambda donor: donor.currently_available,
            ),
            "city_match_rate": recommended_constraint_rate(
                recommendations,
                lambda donor: self.ranking_agent.normalize_city(donor.city)
                == self.ranking_agent.normalize_city(patient.city),
            ),
            "clinical_eligibility_rate": recommended_constraint_rate(
                recommendations,
                lambda donor: self.is_clinically_eligible(donor),
            ),
            "recommended_donor_ids": [
                donor.donor_id for donor in recommendations[: self.top_k]
            ],
        }

    def is_clinically_eligible(self, donor):
        age = self.ranking_agent.calculate_age(donor.date_of_birth)
        days_since_donation = self.ranking_agent.days_since_last_donation(
            donor.last_donation_date
        )

        return (
            age is not None
            and 18 <= age <= 65
            and donor.weight is not None
            and donor.weight >= 50
            and (
                days_since_donation is None
                or days_since_donation >= self.ranking_agent.MIN_DAYS_BETWEEN_DONATIONS
            )
        )

    def evaluate(self):
        rows = [self.evaluate_patient(patient) for patient in self.patients]

        metric_names = [
            "precision_at_k",
            "recall_at_k",
            "hit_rate_at_k",
            "ndcg_at_k",
            "mrr",
            "average_precision",
            "top1_accuracy",
        ]
        constraint_metric_names = [
            "blood_group_accuracy",
            "availability_accuracy",
            "city_match_rate",
            "clinical_eligibility_rate",
        ]
        summary = {
            metric: round(mean(row[metric] for row in rows), 4)
            for metric in metric_names
        }
        rows_with_recommendations = [
            row for row in rows if row["recommendation_count"] > 0
        ]
        summary.update(
            {
                metric: round(
                    mean(row[metric] for row in rows_with_recommendations),
                    4,
                )
                if rows_with_recommendations
                else 0.0
                for metric in constraint_metric_names
            }
        )
        summary.update(
            {
                "patients_evaluated": len(rows),
                "donors_evaluated": len(self.donors),
                "top_k": self.top_k,
                "avg_recommendations_per_patient": round(
                    mean(row["recommendation_count"] for row in rows),
                    2,
                ),
                "avg_relevant_candidates_per_patient": round(
                    mean(row["relevant_candidate_count"] for row in rows),
                    2,
                ),
            }
        )

        return summary, rows


def precision_at_k(recommendations, relevant_ids, k):
    if k <= 0:
        return 0.0

    top_k = recommendations[:k]
    if not top_k:
        return 0.0

    hits = sum(1 for donor in top_k if donor.donor_id in relevant_ids)
    return hits / k


def recall_at_k(recommendations, relevant_ids, k):
    if not relevant_ids:
        return 0.0

    top_k = recommendations[:k]
    hits = sum(1 for donor in top_k if donor.donor_id in relevant_ids)
    return hits / len(relevant_ids)


def discounted_cumulative_gain(relevances):
    return sum(
        ((2**relevance - 1) / log2(index + 2))
        for index, relevance in enumerate(relevances)
    )


def ndcg_at_k(ranked_relevances, ideal_relevances):
    ideal_dcg = discounted_cumulative_gain(ideal_relevances)
    if ideal_dcg == 0:
        return 0.0

    return discounted_cumulative_gain(ranked_relevances) / ideal_dcg


def reciprocal_rank(recommendations, relevant_ids):
    for index, donor in enumerate(recommendations, start=1):
        if donor.donor_id in relevant_ids:
            return 1 / index
    return 0.0


def average_precision(recommendations, relevant_ids, k):
    if not relevant_ids:
        return 0.0

    hits = 0
    precision_sum = 0.0

    for index, donor in enumerate(recommendations[:k], start=1):
        if donor.donor_id in relevant_ids:
            hits += 1
            precision_sum += hits / index

    return precision_sum / min(len(relevant_ids), k)


def recommended_constraint_rate(recommendations, predicate):
    if not recommendations:
        return 0.0

    return sum(1 for donor in recommendations if predicate(donor)) / len(recommendations)


def print_report(summary, rows):
    print("\nBloodBridge Donor Recommendation Evaluation")
    print("=" * 48)
    print(f"Patients evaluated: {summary['patients_evaluated']}")
    print(f"Donors evaluated: {summary['donors_evaluated']}")
    print(f"Top-K: {summary['top_k']}")
    print(f"Avg recommendations per patient: {summary['avg_recommendations_per_patient']}")
    print(
        "Avg relevant candidates per patient: "
        f"{summary['avg_relevant_candidates_per_patient']}"
    )
    print()
    print("Ranking metrics")
    print("-" * 48)
    print(f"Precision@K: {summary['precision_at_k']:.4f}")
    print(f"Recall@K: {summary['recall_at_k']:.4f}")
    print(f"HitRate@K: {summary['hit_rate_at_k']:.4f}")
    print(f"NDCG@K: {summary['ndcg_at_k']:.4f}")
    print(f"MRR: {summary['mrr']:.4f}")
    print(f"MAP@K: {summary['average_precision']:.4f}")
    print(f"Top-1 accuracy: {summary['top1_accuracy']:.4f}")
    print()
    print("Recommendation constraint checks")
    print("-" * 48)
    print(f"Blood group accuracy: {summary['blood_group_accuracy']:.4f}")
    print(f"Availability accuracy: {summary['availability_accuracy']:.4f}")
    print(f"City match rate: {summary['city_match_rate']:.4f}")
    print(f"Clinical eligibility rate: {summary['clinical_eligibility_rate']:.4f}")
    print()
    print("Lowest NDCG cases")
    print("-" * 48)

    for row in sorted(rows, key=lambda item: item["ndcg_at_k"])[:5]:
        print(
            f"Patient {row['patient_id']} | {row['blood_group']} | {row['city']} | "
            f"NDCG={row['ndcg_at_k']:.4f} | "
            f"recommended={row['recommended_donor_ids']}"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate BloodBridge donor matching and ranking quality."
    )
    parser.add_argument("--donors", default=DEFAULT_DONORS_PATH, type=Path)
    parser.add_argument("--patients", default=DEFAULT_PATIENTS_PATH, type=Path)
    parser.add_argument("--top-k", default=5, type=int)
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    donors, patients = load_records(args.donors, args.patients)
    evaluator = DonorRecommendationEvaluator(donors, patients, top_k=args.top_k)
    summary, rows = evaluator.evaluate()

    if args.json:
        print(json.dumps({"summary": summary, "patients": rows}, indent=2))
    else:
        print_report(summary, rows)


if __name__ == "__main__":
    main()
