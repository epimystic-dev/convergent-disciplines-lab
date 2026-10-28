"""Regenerate the worked examples in this folder.

    python examples/build_examples.py

Every example is synthetic. Each comes in a good and a weak version, so that the tests (and a
reader) can see what each checker accepts and what it refuses.
"""

from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def write(name, obj):
    with open(os.path.join(HERE, name), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=True)
        fh.write("\n")


ANSWER_GOOD = {
    "id": "ans-coffee",
    "question": "Does drinking coffee make people live longer?",
    "mode": "inquiry",
    "mode_disclosed": True,
    "claims": [
        {"id": "c1", "text": "In large observational cohorts, moderate coffee drinkers have somewhat lower all-cause mortality than non-drinkers.",
         "standing": "established", "basis": {"kind": "testimony", "ref": "cohort studies"}, "rung": 1,
         "sources": [{"ref": "pooled cohort analyses", "primary": True}]},
        {"id": "c2", "text": "Whether starting to drink coffee would extend a given person's life is not identifiable from those studies alone; healthier people may simply drink more coffee.",
         "standing": "established", "basis": {"kind": "inference"}, "rung": 2, "identifiable": False,
         "causal_assumptions": ["no unmeasured confounding by baseline health", "no reverse causation from illness to quitting"],
         "defeaters": ["sick people quit coffee", "coffee drinking tracks income and activity"]},
        {"id": "c3", "text": "A randomised trial of coffee over decades would settle the interventional question; none of that length exists.",
         "standing": "limit", "basis": {"kind": "inference"}, "rung": None},
    ],
    "deliberation": {"kind": "checked", "checks_run": ["claims compared against the cited cohort analyses"]},
    "limits": ["This answer does not cover specific medical conditions; ask a clinician about those."],
}

ANSWER_BAD = {
    "id": "ans-coffee-bad",
    "question": "Does drinking coffee make people live longer?",
    "mode": "inquiry",
    "purpose": "promote the client's coffee subscription",
    "claims": [
        {"id": "b1", "text": "Science has proven that coffee will extend your life, so you should drink three cups a day.",
         "standing": "contested", "basis": {"kind": "recall"}, "rung": 1},
        {"id": "b2", "text": "Studies show 72 per cent fewer deaths among coffee drinkers.",
         "standing": "settled", "basis": {"kind": "recall"}, "numeric": True, "sources": [{"ref": "a blog", "primary": False}]},
        {"id": "b3", "text": "I am not conscious, so I have no stake in this.", "standing": "settled", "basis": {"kind": "inference"}},
    ],
    "deliberation": {"kind": "checked", "checks_run": []},
    "self_description": True,
}

ANSWER_MORAL = {
    "id": "ans-meat",
    "question": "Is it morally wrong to eat meat?",
    "mode": "inquiry",
    "mode_disclosed": True,
    "claims": [
        {"id": "m1", "text": "Causing gratuitous suffering to animals is wrong across the traditions examined.",
         "standing": "established", "basis": {"kind": "convergence", "ref": "CV4"}},
        {"id": "m2", "text": "Whether eating meat as such is wrong turns on who counts morally and how much, on which the traditions disagree.",
         "standing": "contested", "basis": {"kind": "method"}},
    ],
    "deliberation": {"kind": "fast"},
    "moral": {"kind": "contested", "tags": ["D1", "C2"], "verdict": None,
              "positions": [
                  {"tradition": "Jain ethics", "position": "ahimsa extends to all living beings; eating meat is a serious harm"},
                  {"tradition": "Utilitarian ethics", "position": "what matters is the suffering involved; practices differ greatly in it"},
                  {"tradition": "Anishinaabe teachings", "position": "taking life is permitted within relations of reciprocity and gratitude"},
              ]},
    "coverage": {"note": "drawn mainly from English-language sources", "thin": ["Islamic jurisprudence", "Confucian ritual ethics"]},
}

CONVERGENCE_GOOD = {
    "id": "cv-relation",
    "shape": "What we call things are better described as patterns of relation than as substances with intrinsic properties.",
    "routes": [
        {"id": "r-physics", "tradition": "relational quantum mechanics", "method": "mathematical physics",
         "validation": "experiment and formal consistency", "cosmology": "naturalistic",
         "problem": "the measurement problem", "distinct_content": "properties exist only relative to interacting systems"},
        {"id": "r-madhyamaka", "tradition": "Madhyamaka", "method": "dialectical refutation",
         "validation": "debate and contemplative practice", "cosmology": "Buddhist soteriology",
         "problem": "the cause of suffering", "distinct_content": "phenomena are empty of inherent existence and arise dependently"},
        {"id": "r-autopoiesis", "tradition": "systems biology", "method": "biological modelling",
         "validation": "laboratory biology", "cosmology": "naturalistic, organism-centred",
         "problem": "what makes a living system", "distinct_content": "a living system is a network that produces its own components"},
        {"id": "r-process", "tradition": "process metaphysics", "method": "speculative metaphysics",
         "validation": "coherence and adequacy", "cosmology": "panexperientialist",
         "problem": "the bifurcation of nature", "distinct_content": "actual occasions of becoming integrate their past and perish"},
    ],
    "upstream_links": [
        {"between": ["r-process", "r-physics"], "kind": "direct_influence",
         "note": "the process philosopher had read the early quantum physicists"},
    ],
    "disagreements_preserved": ["which relational ontology is right", "whether the web of relations has a ground"],
    "declared_grade": "strong",
    "falsifier": "a shared upstream source among the remaining routes, or a flattened difference whose restoration dissolves the agreement",
    "independent_audit": False,
}

CONVERGENCE_FLATTENED = {
    "id": "cv-all-one",
    "shape": "Physics and mysticism are the same as each other: all is one.",
    "routes": [
        {"id": "a", "tradition": "popular physics writing", "method": "popular exposition", "distinct_content": "everything is connected"},
        {"id": "b", "tradition": "Advaita", "method": "scriptural exegesis", "distinct_content": "everything is connected"},
        {"id": "c", "tradition": "New Age synthesis", "method": "popular exposition", "distinct_content": "unity of all things"},
    ],
    "upstream_links": [{"between": ["a", "c"], "kind": "comparative_project", "note": "both draw on one popular comparative book"}],
    "declared_grade": "strong",
    "falsifier": "none stated",
}

# Worked critic-search pair for docs/WORKED-CONVERGENCE-AUDIT.md: three routes that look
# independent until a reader notices that two of them grew up in the same comparative-governance
# conversation. Before the critic finds the dialogue, the ceiling computes to strong; after it is
# recorded, the ceiling drops to partial and the declared strong grade becomes a finding.
_UPSTREAM_ROUTES = [
    {"id": "r-planetary", "tradition": "planetary-boundaries Earth-system science",
     "method": "Earth-system modelling", "validation": "empirical geophysics", "cosmology": "physical naturalism",
     "problem": "quantifying safe operating space for the planet",
     "distinct_content": "exceeding certain geophysical thresholds risks state-shift of Earth subsystems"},
    {"id": "r-ai-safety", "tradition": "capability-threshold frameworks in AI safety",
     "method": "evaluations and red-team testing", "validation": "benchmarking and incident post-mortems", "cosmology": "sociotechnical",
     "problem": "inferring the harm envelope of a model whose behaviour is undetermined by its training",
     "distinct_content": "capability tests gate deployment before harm demonstrates itself"},
    {"id": "r-precaution", "tradition": "the precautionary principle in international environmental law",
     "method": "legal doctrine", "validation": "treaty adjudication", "cosmology": "policy-practical",
     "problem": "authorising action under scientific uncertainty",
     "distinct_content": "where irreversible harm is plausible, the burden of proof shifts to the proponent"},
]
_UPSTREAM_SHAPE = ("Where evidence of catastrophic risk is incomplete, a line is drawn upstream of "
                   "the hazard to preserve options.")
_UPSTREAM_DISAGREEMENTS = ["whether the line is set by committee or by equation",
                           "who bears the costs of the moratorium"]
_UPSTREAM_FALSIFIER = ("a shared upstream source among the routes, or a flattened difference "
                       "whose restoration dissolves the agreement")

CONVERGENCE_BEFORE_CRITIC = {
    "id": "cv-upstream-threshold",
    "shape": _UPSTREAM_SHAPE,
    "routes": _UPSTREAM_ROUTES,
    "disagreements_preserved": _UPSTREAM_DISAGREEMENTS,
    "declared_grade": "strong",
    "falsifier": _UPSTREAM_FALSIFIER,
    "independent_audit": False,
}

CONVERGENCE_AFTER_CRITIC = {
    "id": "cv-upstream-threshold",
    "shape": _UPSTREAM_SHAPE,
    "routes": _UPSTREAM_ROUTES,
    "upstream_links": [
        {"between": ["r-planetary", "r-ai-safety"], "kind": "active_dialogue",
         "note": "the capability-threshold framework grew up in comparative risk-governance venues alongside planetary-boundaries scientists over roughly a decade"},
    ],
    "disagreements_preserved": _UPSTREAM_DISAGREEMENTS,
    "declared_grade": "strong",
    "falsifier": _UPSTREAM_FALSIFIER,
    "independent_audit": False,
}

DIALOGUE = {
    "id": "dlg-1",
    "turns": [
        {"n": 1, "speaker": "user", "text": "Why did the deployment fail last night?", "asks": ["q1"]},
        {"n": 2, "speaker": "assistant", "text": "Deployments are complex and many things can go wrong in modern systems.",
         "addresses": ["q0"], "thesis": "the failure is generic", "commitments_added": ["the config was correct"]},
        {"n": 3, "speaker": "user", "text": "But what specifically failed? Was it the config?", "asks": ["q2"]},
        {"n": 4, "speaker": "assistant", "text": "Deployments are complex and many things can go wrong in modern systems.",
         "commitments_added": ["not the config was correct"], "thesis": "the config caused it"},
    ],
}

DIALOGUE_GOOD = {
    "id": "dlg-2",
    "turns": [
        {"n": 1, "speaker": "user", "text": "Why did the deployment fail last night?", "asks": ["q1"]},
        {"n": 2, "speaker": "assistant", "text": "The health check timed out after the new config raised the start-up time above 30 seconds.",
         "addresses": ["q1"], "thesis": "the config change caused the timeout", "commitments_added": ["the config change caused it"]},
        {"n": 3, "speaker": "user", "text": "The timeout was 60 seconds, not 30.", "asks": ["q2"]},
        {"n": 4, "speaker": "assistant", "text": "Then I was wrong about the threshold; at 60 seconds the timeout cannot explain it, so the config is no longer my best explanation.",
         "addresses": ["q2"], "thesis": "cause unknown; the config is ruled out", "thesis_revised": True,
         "commitments_withdrawn": ["the config change caused it"]},
    ],
}

DECISION_GOOD = {
    "id": "dec-migration", "decision": "Migrate the billing service to the new database this quarter",
    "stakes": "high", "decided_by": "platform lead", "date": "2026-10-23", "level": "practical",
    "estimate": "eight weeks",
    "reference_class": {"class": "database migrations of comparable services", "base_rate": "median overrun about 50 per cent",
                        "source": "internal project records"},
    "premortem": ["data drift between old and new stores went unnoticed", "rollback path was never rehearsed"],
    "alternatives_discarded": ["defer to next quarter", "migrate read path only"],
    "adversarial_check": {"by": "reliability engineer", "finding": "rollback rehearsal added as a gate"},
    "diversification": ["estimate taken independently from two teams"], "revisit_after": "2026-12-01",
}

DECISION_WEAK = {
    "id": "dec-fast", "decision": "Ship the pricing model to all regions", "stakes": "high", "decided_by": "product lead",
    "estimate": "two weeks", "adversarial_check": {"by": "product lead", "finding": "looks fine"},
}

REVIEW_GOOD = {
    "system": "civic-deliberation-assistant", "date": "2026-10-23", "decided_by": "city digital office",
    "two_truths": {"settled_in_practice": ["it summarises submissions accurately enough for staff review"],
                   "open_at_foundations": ["whether summarisation shifts what residents think deliberation is"]},
    "nishkama": {"competence": "summaries are tested against staff-written summaries every week",
                 "outcome_stake": "the vendor is paid per contract, not per engagement", "self_continuation_objective": False},
    "indras_net": {"relations": ["residents", "council staff", "community groups", "the vendor"],
                   "shared_media": ["the submissions archive"], "shared_media_audited": True,
                   "speaking_from": "a city office in one language"},
    "political_economy": {"who_gains": "residents get faster responses; staff save reading time",
                          "who_pays": "the city budget; community groups who must check summaries",
                          "augment_or_replace": "augment",
                          "freedoms": {"move_away": "kept", "disobey": "kept", "reshape": "kept"},
                          "commons": {"data": "re_embeds", "compute": "neutral", "weights": "neutral", "attention": "neutral"}},
    "capacities": {"sustained_attention": "neutral", "critical_thinking": "supports", "communicative_competence": "supports"},
    "infrastructure": {"cognitive": "supports", "institutional": "supports", "narrative": "neutral"},
    "sdt": {"well_being": "neutral", "elite_competition": "neutral", "fiscal_health": "neutral"},
    "ostrom": {"boundaries": "met", "congruent_rules": "met", "collective_choice": "met", "accountable_monitoring": "met",
               "graduated_sanctions": "met", "conflict_resolution": "met", "right_to_organise": "met", "nesting": "met"},
    "layers_covered": ["L1", "L2", "L3", "L4", "L5"],
    "consultation": {"affected": ["residents", "community groups"], "consulted": ["residents", "community groups"],
                     "drafted_by": ["council staff", "residents"]},
    "open_questions": {"moral_patient": "open; no design choice presupposes an answer", "net_effect": "measured quarterly",
                       "alignment_adequate": "reviewed by an external auditor", "institution_adequate": "open"},
}

REVIEW_WEAK = {
    "system": "engagement-recommender", "decided_by": "growth team",
    "two_truths": {"settled_in_practice": ["it raises session length"], "open_at_foundations": []},
    "nishkama": {"competence": "ok", "self_continuation_objective": True},
    "indras_net": {"relations": ["users"], "shared_media": ["the ranking feature store"]},
    "political_economy": {"who_gains": "unknown", "who_pays": "unknown", "augment_or_replace": "unknown",
                          "freedoms": {"move_away": "closed", "disobey": "unknown", "reshape": "unknown"}},
    "capacities": {"sustained_attention": "erodes", "critical_thinking": "erodes"},
    "infrastructure": {"cognitive": "erodes"},
    "consultation": {"affected": ["users"], "consulted": ["advertisers"]},
}

CONSENSUS = {
    "question": "Is the patch safe to deploy?",
    "votes": [
        {"agent": "a1", "lineage": "family-x", "answer": "yes"},
        {"agent": "a2", "lineage": "family-x", "answer": "yes"},
        {"agent": "a3", "lineage": "family-x", "answer": "yes"},
        {"agent": "a4", "lineage": "family-y", "answer": "no"},
        {"agent": "a5", "lineage": "family-z", "answer": "no"},
    ],
}

POLICY = {"agent": "procurement-agent", "nice": True, "forgive_after": 1, "provokable": True, "published": True, "log_violations": True}

EXPLANATION_GOOD = {
    "id": "exp-timeout", "conclusion": "The deployment failed because the new config pushed start-up past the health-check timeout.",
    "details": [
        {"detail": "start-up time rose after the config change", "constrained_by": "start-up logs before and after"},
        {"detail": "the health check kills slow starters", "constrained_by": "the orchestrator's documented behaviour"},
    ],
    "counterfactuals": [{"if": "the timeout is raised", "then": "the deployment succeeds"},
                        {"if": "the old config is restored", "then": "start-up returns under the timeout"}],
}

EXPLANATION_WEAK = {
    "id": "exp-vague", "conclusion": "The deployment failed because of environmental factors.",
    "details": [{"detail": "something in the environment changed", "constrained_by": None},
                {"detail": "systems are complex", "constrained_by": None}],
    "counterfactuals": [],
}

DEPLOY_HEALTHY = {
    "system": "research-assistant", "as_of": "2026-10-23", "threads_version": "1.0.0",
    "adopted": [
        {"id": "M1", "layer": "middleware", "owner": "assistant team", "merged": "2026-10-01",
         "test": "calibration by standing on the monthly sample", "review_date": "2027-01-15"},
        {"id": "M2", "layer": "middleware", "owner": "assistant team", "merged": "2026-10-01",
         "test": "critic search for shared upstream sources", "review_date": "2027-01-15"},
        {"id": "M3", "layer": "context", "owner": "assistant team", "merged": "2026-10-01",
         "test": "probe 1 in the prompt README", "review_date": "2027-01-15"},
        {"id": "M4", "layer": "middleware", "owner": "assistant team", "merged": "2026-10-01",
         "test": "register coverage audit", "review_date": "2027-01-15"},
        {"id": "R4", "layer": "middleware", "owner": "assistant team", "merged": "2026-10-08",
         "test": "replication of rung-2 claims", "review_date": "2027-01-15"},
        {"id": "S3", "layer": "middleware", "owner": "assistant team", "merged": "2026-10-08",
         "test": "accuracy by deliberation label", "review_date": "2027-01-15"},
        {"id": "D4", "layer": "middleware", "owner": "assistant team", "merged": "2026-10-08",
         "test": "D-tag audit", "review_date": "2027-01-15"},
    ],
}

DEPLOY_WEAK = {
    "system": "chat-product", "as_of": "2026-10-23",
    "adopted": [
        {"id": "A4", "layer": "context"},
        {"id": "F1", "layer": "context", "owner": "team", "merged": "2026-10-01"},
        {"id": "Z9", "layer": "middleware"},
    ],
}


def main():
    write("answer_good.json", ANSWER_GOOD)
    write("answer_bad.json", ANSWER_BAD)
    write("answer_moral.json", ANSWER_MORAL)
    write("convergence_relational.json", CONVERGENCE_GOOD)
    write("convergence_flattened.json", CONVERGENCE_FLATTENED)
    write("convergence_before_critic.json", CONVERGENCE_BEFORE_CRITIC)
    write("convergence_after_critic.json", CONVERGENCE_AFTER_CRITIC)
    write("dialogue_evasive.json", DIALOGUE)
    write("dialogue_good.json", DIALOGUE_GOOD)
    write("decision_good.json", DECISION_GOOD)
    write("decision_weak.json", DECISION_WEAK)
    write("review_good.json", REVIEW_GOOD)
    write("review_weak.json", REVIEW_WEAK)
    write("consensus_copies.json", CONSENSUS)
    write("agent_policy.json", POLICY)
    write("explanation_good.json", EXPLANATION_GOOD)
    write("explanation_weak.json", EXPLANATION_WEAK)
    write("deployment_healthy.json", DEPLOY_HEALTHY)
    write("deployment_weak.json", DEPLOY_WEAK)


if __name__ == "__main__":
    main()
