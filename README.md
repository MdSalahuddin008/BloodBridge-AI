## BloodBridge AI

BloodBridge AI is a multi-agent donor discovery system for matching patients with
suitable blood donors. It includes routing, blood-group matching, donor ranking,
eligibility support, notifications, and an offline evaluator for measuring donor
recommendation quality.

## Donor Recommendation Evaluation

Run the offline evaluator:

```bash
python evaluate_donor_recommendations.py
```

Machine-readable output:

```bash
python evaluate_donor_recommendations.py --json
```

The evaluator treats each patient in `patients.json` as a recommendation query and
each donor in `donors.json` as a candidate. It uses the production ranking agent
for recommendations, then grades the output with an independent relevance function
based on:

- exact blood-group match
- donor availability
- same-city/local match
- age eligibility
- minimum weight
- donation cooldown
- geographic distance

Reported metrics include:

- `Precision@K`: fraction of the Top-K recommendations that are relevant
- `Recall@K`: fraction of all relevant donors recovered in the Top-K
- `HitRate@K`: whether at least one relevant donor appears in the Top-K
- `NDCG@K`: ranking quality with graded relevance
- `MRR`: how early the first relevant donor appears
- `MAP@K`: average precision across the ranked list
- `Top-1 accuracy`: whether the first donor is among the best available choices
- blood group, availability, city, and clinical eligibility constraint checks

Resume phrasing:

> Built an offline recommendation evaluator for a multi-agent blood-donor matching
> system using Precision@K, Recall@K, NDCG@K, MRR, MAP@K, Top-1 accuracy, and
> clinical constraint validation.
