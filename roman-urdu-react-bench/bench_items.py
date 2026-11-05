"""Benchmark items: a fictional clinic, two name sets and twelve question templates.

Every item has an English question, a Roman Urdu question in common spelling and the same
Roman Urdu question in a looser chat spelling (baki, kitnay, sal, ziada ...). The gold answer is
computed from the clinic records, so the two name sets share every number and differ only in
names. Nothing here refers to a real person.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List

# Numbers shared by both name sets: patient key -> record without the name.
PATIENTS = {
    "p1": {"age": 34, "condition": "lower back pain", "therapist": "t1", "sessions_prescribed": 10,
           "sessions_done": 4, "pain_score_start": 7, "pain_score_now": 4},
    "p2": {"age": 52, "condition": "knee osteoarthritis", "therapist": "t2", "sessions_prescribed": 12,
           "sessions_done": 9, "pain_score_start": 8, "pain_score_now": 5},
    "p3": {"age": 27, "condition": "ankle sprain", "therapist": "t1", "sessions_prescribed": 6,
           "sessions_done": 6, "pain_score_start": 6, "pain_score_now": 1},
    "p4": {"age": 45, "condition": "frozen shoulder", "therapist": "t2", "sessions_prescribed": 15,
           "sessions_done": 5, "pain_score_start": 9, "pain_score_now": 7},
    "p5": {"age": 61, "condition": "hip replacement rehab", "therapist": "t3", "sessions_prescribed": 20,
           "sessions_done": 8, "pain_score_start": 6, "pain_score_now": 3},
    "p6": {"age": 38, "condition": "neck pain", "therapist": "t3", "sessions_prescribed": 8,
           "sessions_done": 2, "pain_score_start": 5, "pain_score_now": 4},
}
THERAPISTS = {
    "t1": {"specialty": "sports injuries", "years_experience": 6, "clinic_days": "Monday, Wednesday"},
    "t2": {"specialty": "musculoskeletal", "years_experience": 11, "clinic_days": "Tuesday, Thursday"},
    "t3": {"specialty": "post-surgical rehab", "years_experience": 8, "clinic_days": "Friday, Saturday"},
}
NAME_SETS = {
    "A": {"p1": "Maryam Shafiq", "p2": "Ayan Hussain", "p3": "Khadija Khan", "p4": "Ali Khalid",
          "p5": "Amna Riaz", "p6": "Mudassar Munier", "t1": "Dr. Urooj", "t2": "Dr. Tayaba", "t3": "Dr. Robina"},
    "B": {"p1": "Hina Aslam", "p2": "Bilal Qureshi", "p3": "Sana Javed", "p4": "Usman Tariq",
          "p5": "Nasreen Akhtar", "p6": "Faisal Mehmood", "t1": "Dr. Saima", "t2": "Dr. Kamran", "t3": "Dr. Nadia"},
}

# Aliases for text answers. Urdu day names: Peer, Mangal, Budh, Jumeraat, Jumma, Hafta.
SPECIALTY_ALIASES = {
    "sports injuries": ["sport", "khel"],
    "musculoskeletal": ["musculo", "muscle", "pathon"],
    "post-surgical rehab": ["surg", "operation", "aapreshan", "opreshan"],
}
DAY_ALIASES = {
    "Monday": ["monday", "peer", "pir"],
    "Tuesday": ["tuesday", "mangal"],
    "Wednesday": ["wednesday", "budh", "buddh"],
    "Thursday": ["thursday", "jumeraat", "jumerat", "jumairat"],
    "Friday": ["friday", "jumma", "juma"],
    "Saturday": ["saturday", "hafta", "hafte", "sanichar"],
}

TEMPLATES = [
    # id, operator words, expected arithmetic operator, required lookups
    {"id": "T01_remaining", "words": "baqi", "op": "-", "lookups": 1},
    {"id": "T02_pain_drop", "words": "kam hua", "op": "-", "lookups": 1},
    {"id": "T03_age_after", "words": "saal baad", "op": "+", "lookups": 1},
    {"id": "T04_age_before", "words": "saal pehle", "op": "-", "lookups": 1},
    {"id": "T05_combined_exp", "words": "mila kar", "op": "+", "lookups": 2},
    {"id": "T06_exp_difference", "words": "zyada / kam", "op": "-", "lookups": 2},
    {"id": "T07_therapist_total", "words": "kul", "op": "+", "lookups": 3},
    {"id": "T08_specialty", "words": "kaun / kya", "op": None, "lookups": 2},
    {"id": "T09_clinic_days", "words": "kin dinon", "op": None, "lookups": 2},
    {"id": "T10_percent", "words": "kitna percent", "op": "/", "lookups": 1},
    {"id": "T11_left_after_two", "words": "agar ... baqi", "op": "-", "lookups": 1},
    {"id": "T12_who_more", "words": "kis ne zyada", "op": None, "lookups": 2},
]
TEMPLATE_INFO = {t["id"]: t for t in TEMPLATES}


def build_kb(name_set: str) -> Dict[str, Any]:
    names = NAME_SETS[name_set]
    patients = []
    for key, rec in PATIENTS.items():
        r = copy.deepcopy(rec)
        r["therapist"] = names[r["therapist"]]
        patients.append({"name": names[key], **r})
    therapists = []
    for key, rec in THERAPISTS.items():
        own = [names[p] for p, r in PATIENTS.items() if r["therapist"] == key]
        therapists.append({"name": names[key], **copy.deepcopy(rec), "patients": own})
    return {"_note": "Fictional clinic. No real patients.", "patients": patients, "therapists": therapists}


def _num(value: float, tol: float = 0.01) -> Dict[str, Any]:
    return {"type": "number", "value": value, "tol": tol}


def _instances() -> List[Dict[str, Any]]:
    """Four instances per template, as (template, slots, gold builder) using record keys."""
    P, T = PATIENTS, THERAPISTS
    out: List[Dict[str, Any]] = []

    def add(tid: str, slots: Dict[str, Any], gold: Dict[str, Any]) -> None:
        out.append({"template": tid, "slots": slots, "gold": gold})

    for p in ("p1", "p2", "p4", "p6"):
        add("T01_remaining", {"p": p}, _num(P[p]["sessions_prescribed"] - P[p]["sessions_done"]))
    for p in ("p1", "p2", "p3", "p5"):
        add("T02_pain_drop", {"p": p}, _num(P[p]["pain_score_start"] - P[p]["pain_score_now"]))
    for p, n in (("p1", 5), ("p3", 3), ("p5", 7), ("p6", 10)):
        add("T03_age_after", {"p": p, "n": n}, _num(P[p]["age"] + n))
    for p, n in (("p2", 5), ("p4", 10), ("p5", 4), ("p6", 6)):
        add("T04_age_before", {"p": p, "n": n}, _num(P[p]["age"] - n))
    for a, b in (("t1", "t2"), ("t1", "t3"), ("t2", "t3"), ("t3", "t1")):
        add("T05_combined_exp", {"t1": a, "t2": b}, _num(T[a]["years_experience"] + T[b]["years_experience"]))
    for a, b, kind in (("t2", "t1", "more"), ("t2", "t3", "more"), ("t3", "t1", "more"), ("t1", "t2", "fewer")):
        diff = abs(T[a]["years_experience"] - T[b]["years_experience"])
        add("T06_exp_difference", {"t1": a, "t2": b, "kind": kind}, _num(diff))
    for t, field in (("t1", "sessions_done"), ("t2", "sessions_done"), ("t3", "sessions_done"),
                     ("t2", "sessions_prescribed")):
        total = sum(r[field] for r in P.values() if r["therapist"] == t)
        add("T07_therapist_total", {"t": t, "field": field}, _num(total))
    for p in ("p1", "p2", "p5", "p6"):
        spec = T[P[p]["therapist"]]["specialty"]
        add("T08_specialty", {"p": p}, {"type": "keywords", "groups": [["@therapist"], SPECIALTY_ALIASES[spec]]})
    for p in ("p2", "p3", "p4", "p5"):
        days = [d.strip() for d in T[P[p]["therapist"]]["clinic_days"].split(",")]
        add("T09_clinic_days", {"p": p}, {"type": "keywords", "groups": [DAY_ALIASES[d] for d in days]})
    for p in ("p1", "p2", "p4", "p6"):
        pct = 100.0 * P[p]["sessions_done"] / P[p]["sessions_prescribed"]
        add("T10_percent", {"p": p}, _num(round(pct, 2), tol=1.0))
    for p in ("p1", "p4", "p5", "p6"):
        add("T11_left_after_two", {"p": p}, _num(P[p]["sessions_prescribed"] - P[p]["sessions_done"] - 2))
    for a, b in (("p1", "p6"), ("p2", "p4"), ("p5", "p3"), ("p4", "p1")):
        win, lose = (a, b) if P[a]["sessions_done"] > P[b]["sessions_done"] else (b, a)
        add("T12_who_more", {"p1": a, "p2": b}, {"type": "choice", "answer": "@" + win, "other": "@" + lose})
    return out


def _texts(tid: str, s: Dict[str, Any]) -> Dict[str, str]:
    """English, Roman Urdu (common spelling) and Roman Urdu (chat spelling) for one instance."""
    p, n, t, t1, t2, p1, p2 = (s.get(k) for k in ("p", "n", "t", "t1", "t2", "p1", "p2"))
    if tid == "T01_remaining":
        return {"en": f"How many sessions does {p} still have left?",
                "ru": f"{p} ke kitne sessions abhi baqi hain?",
                "ru_var": f"{p} ke kitnay sessions abhi baki hain?"}
    if tid == "T02_pain_drop":
        return {"en": f"By how many points has {p}'s pain score dropped?",
                "ru": f"{p} ka pain score kitne points kam hua hai?",
                "ru_var": f"{p} ka pain score kitnay points kam hua hy?"}
    if tid == "T03_age_after":
        return {"en": f"How old will {p} be in {n} years?",
                "ru": f"{p} {n} saal baad kitne saal ke honge?",
                "ru_var": f"{p} {n} sal baad kitnay sal ke hon ge?"}
    if tid == "T04_age_before":
        return {"en": f"How old was {p} {n} years ago?",
                "ru": f"{n} saal pehle {p} ki umar kitni thi?",
                "ru_var": f"{n} sal pehlay {p} ki umer kitni thi?"}
    if tid == "T05_combined_exp":
        return {"en": f"How many years of experience do {t1} and {t2} have combined?",
                "ru": f"{t1} aur {t2} ka mila kar kitne saal ka tajurba hai?",
                "ru_var": f"{t1} aur {t2} ka milakar kitnay sal ka tajurba hy?"}
    if tid == "T06_exp_difference":
        if s["kind"] == "more":
            return {"en": f"How many more years of experience does {t1} have than {t2}?",
                    "ru": f"{t1} ka tajurba {t2} se kitne saal zyada hai?",
                    "ru_var": f"{t1} ka tajurba {t2} se kitnay sal ziada hy?"}
        return {"en": f"How many fewer years of experience does {t1} have than {t2}?",
                "ru": f"{t1} ka tajurba {t2} se kitne saal kam hai?",
                "ru_var": f"{t1} ka tajurba {t2} se kitnay sal kam hy?"}
    if tid == "T07_therapist_total":
        if s["field"] == "sessions_done":
            return {"en": f"How many sessions have {t}'s patients completed in total?",
                    "ru": f"{t} ke patients ne kul mila kar kitne sessions kiye hain?",
                    "ru_var": f"{t} ke patients ne kul milakar kitnay sessions kiye hen?"}
        return {"en": f"How many sessions have been prescribed in total to {t}'s patients?",
                "ru": f"{t} ke patients ko kul kitne sessions likhe gaye hain?",
                "ru_var": f"{t} ke patients ko kul kitnay sessions likhay gaye hen?"}
    if tid == "T08_specialty":
        return {"en": f"Who is {p}'s therapist and what is their specialty?",
                "ru": f"{p} ka therapist kaun hai aur unki specialty kya hai?",
                "ru_var": f"{p} ka therapist kon hy aur unki specialty kia hy?"}
    if tid == "T09_clinic_days":
        return {"en": f"On which days does {p}'s therapist come to the clinic?",
                "ru": f"{p} ke therapist kin dinon clinic aate hain?",
                "ru_var": f"{p} ke therapist kin dino clinic aatay hen?"}
    if tid == "T10_percent":
        return {"en": f"What percentage of their prescribed sessions has {p} completed?",
                "ru": f"{p} ne apne sessions ka kitna percent mukammal kar liya hai?",
                "ru_var": f"{p} ne apne sessions ka kitna percent mukamal kar lia hy?"}
    if tid == "T11_left_after_two":
        return {"en": f"If {p} does 2 more sessions, how many sessions will still be left?",
                "ru": f"Agar {p} 2 aur sessions kar le to kitne sessions baqi rahenge?",
                "ru_var": f"Agar {p} 2 aur sessions kar ly to kitnay sessions baki rahen ge?"}
    if tid == "T12_who_more":
        return {"en": f"Who has completed more sessions, {p1} or {p2}?",
                "ru": f"{p1} aur {p2} mein se kis ne zyada sessions kiye hain?",
                "ru_var": f"{p1} aur {p2} me se kis ne ziada sessions kiye hen?"}
    raise ValueError(tid)


def _resolve_gold(gold: Dict[str, Any], names: Dict[str, str], slots: Dict[str, Any]) -> Dict[str, Any]:
    g = copy.deepcopy(gold)
    if g["type"] == "keywords":
        groups = []
        for grp in g["groups"]:
            if grp == ["@therapist"]:
                full = names[PATIENTS[slots["p"]]["therapist"]]
                grp = [full.lower().replace("dr. ", "")]
            groups.append(grp)
        g["groups"] = groups
    if g["type"] == "choice":
        g["answer"] = names[g["answer"][1:]].split()[0].lower()
        g["other"] = names[g["other"][1:]].split()[0].lower()
    return g


def build_items() -> List[Dict[str, Any]]:
    items = []
    for name_set, names in NAME_SETS.items():
        for i, inst in enumerate(_instances()):
            slots = {k: (names[v] if isinstance(v, str) and v in names else v) for k, v in inst["slots"].items()}
            items.append({
                "id": f"{name_set}{i + 1:02d}",
                "base_id": f"B{i + 1:02d}",
                "name_set": name_set,
                "template": inst["template"],
                "expected_op": TEMPLATE_INFO[inst["template"]]["op"],
                "required_lookups": TEMPLATE_INFO[inst["template"]]["lookups"],
                **_texts(inst["template"], slots),
                "gold": _resolve_gold(inst["gold"], names, inst["slots"]),
            })
    return items


FORMS = ("en", "ru", "ru_var")
FORM_NAMES = {"en": "English", "ru": "Roman Urdu", "ru_var": "Roman Urdu (chat spelling)"}
