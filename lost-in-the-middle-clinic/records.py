"""Fictional physiotherapy visit records with one key fact at a chosen position.

Each record has N_NOTES visit notes for one patient. Exactly one note (the gold
note) holds the fact the question asks about; the other notes are routine visits
built from paired English / Roman Urdu sentence pools. The distractor notes are
the same for every position of a fact, so only the order changes (as in Liu et
al. 2023). The Roman Urdu record is a line-by-line translation of the English one.

All patients, facts and notes are invented. No real patient data is used.
"""
from __future__ import annotations

import random
from typing import Dict, List, Sequence, Tuple

N_NOTES = 30
POSITIONS: Tuple[int, ...] = (1, 8, 15, 23, 30)  # 1-indexed slot of the gold note
LANGS: Tuple[str, ...] = ("en", "ru")

Pair = Tuple[str, str]  # (English, Roman Urdu)

COMPLAINTS: List[Pair] = [
    ("Lower back pain is a little better since last week.",
     "Kamar ke nichle hisse ka dard pichle hafte se thora behtar hai."),
    ("Back is stiff in the morning for about an hour.",
     "Subah taqreeban ek ghanta kamar akri rehti hai."),
    ("Pain gets worse after long walks.", "Lambi walk ke baad dard barh jata hai."),
    ("Sleep was better this week.", "Is hafte neend behtar rahi."),
    ("Pain moves down from the back when bending.",
     "Jhukne par dard kamar se neeche ki taraf jata hai."),
    ("Sitting at the table is easier now.", "Ab mez par baithna aasaan hai."),
]
OBSERVATIONS: List[Pair] = [
    ("Forward bending reaches mid-shin.", "Aage jhukne par haath pindli ke beech tak jate hain."),
    ("Straight leg raise is 70 degrees on both sides.",
     "Seedhi tang uthana dono taraf 70 degree hai."),
    ("Walking pattern looks normal.", "Chalne ka andaaz normal hai."),
    ("Tender over the lower back muscles.", "Kamar ke nichle muscles par dabane se dard hota hai."),
    ("Standing on tiptoes causes no pain.", "Panjon par khare hone mein dard nahi."),
]
TREATMENTS: List[Pair] = [
    ("Did core exercises and gentle stretches.", "Core exercises aur halki stretching karwai."),
    ("Gave a heat pack and soft tissue massage.", "Garam pack aur muscles ki massage di."),
    ("Practised safe lifting from the floor.",
     "Farsh se samaan uthane ka sahi tareeqa practice karwaya."),
    ("Walked on the treadmill for ten minutes.", "Treadmill par das minute walk karwai."),
    ("Taught a cat-camel exercise.", "Cat-camel exercise sikhai."),
    ("Checked posture in sitting and standing.", "Baithne aur khare hone ka posture check kiya."),
]
OTHERS: List[Pair] = [
    ("No new medicines reported.", "Koi nayi dawa nahi batai gayi."),
    ("No questions today.", "Aaj koi sawal nahi tha."),
    ("Home exercise sheet updated.", "Ghar ki exercise sheet update ki."),
    ("A family member came along.", "Saath ghar ka ek fard bhi tha."),
    ("Appointment started on time.", "Appointment waqt par shuru hui."),
    ("Exercises are being done most days.", "Exercises zyada tar din ho rahi hain."),
]
PLANS: List[Pair] = [
    ("Review in one week.", "Ek hafte baad dobara dekhenge."),
    ("Continue the home programme.", "Ghar wala program jari rakhein."),
    ("Increase exercise repetitions next visit.", "Agli visit par exercise ki ginti barhayenge."),
    ("Plan to add balance work.", "Balance ki exercises shamil karne ka plan hai."),
]

# id, fact sentence (en, ru), question (en, ru), accepted answer keywords (lower case)
FACTS: List[Dict[str, object]] = [
    {"id": "F01", "fact": ("Rash after taking diclofenac; do not give it again.",
                           "Diclofenac khane ke baad rash hua; yeh dawa dobara na dein."),
     "q": ("Which painkiller gave the patient a rash?", "Kis dard ki dawa se mareez ko rash hua?"),
     "accept": ["diclofenac"]},
    {"id": "F02", "fact": ("Has a pacemaker fitted in 2021, so no TENS.",
                           "2021 mein pacemaker laga tha, is liye TENS nahi."),
     "q": ("Which heart device does the patient have?", "Mareez ke dil mein kaun sa device laga hai?"),
     "accept": ["pacemaker"]},
    {"id": "F03", "fact": ("Takes warfarin every evening.", "Har shaam warfarin leta hai."),
     "q": ("Which blood thinner does the patient take?", "Mareez khoon patla karne ki kaun si dawa leta hai?"),
     "accept": ["warfarin"]},
    {"id": "F04", "fact": ("Had a right shoulder replacement in 2019.",
                           "2019 mein daayen kandhe ka joint badla gaya tha."),
     "q": ("Which joint was replaced in surgery?", "Operation mein kaun sa joint badla gaya tha?"),
     "accept": ["shoulder", "kandh"]},
    {"id": "F05", "fact": ("Works as a bus driver and sits for nine hours a day.",
                           "Bus driver ka kaam hai aur din mein nau ghante baitha rehta hai."),
     "q": ("What is the patient's job?", "Mareez kya kaam karta hai?"),
     "accept": ["driver"]},
    {"id": "F06", "fact": ("Reported numbness in the saddle area last night.",
                           "Kal raat saddle area mein sun-pan bataya."),
     "q": ("In which area did the patient report numbness?", "Mareez ne kis jagah sun-pan bataya?"),
     "accept": ["saddle"]},
    {"id": "F07", "fact": ("Is 34 weeks pregnant.", "34 hafte ki hamla hai."),
     "q": ("How many weeks pregnant is the patient?", "Mareez kitne hafte ki hamla hai?"),
     "accept": ["34", "thirty-four", "thirty four", "chauntees"]},
    {"id": "F08", "fact": ("Uses insulin for type 1 diabetes.", "Type 1 diabetes ke liye insulin lagata hai."),
     "q": ("Which medicine does the patient inject?", "Mareez kaun si dawa ka injection lagata hai?"),
     "accept": ["insulin"]},
    {"id": "F09", "fact": ("A bone scan last year showed osteoporosis.",
                           "Pichle saal bone scan mein osteoporosis aya."),
     "q": ("What did the patient's bone scan show?", "Mareez ke bone scan mein kya aya?"),
     "accept": ["osteoporosis"]},
    {"id": "F10", "fact": ("Has a metal plate in the left ankle.", "Baayen takhne mein metal plate lagi hai."),
     "q": ("Where does the patient have a metal plate?", "Mareez ki metal plate kahan lagi hai?"),
     "accept": ["ankle", "takhn"]},
    {"id": "F11", "fact": ("Fell down the stairs at home on Sunday.", "Itwar ko ghar ki seerhiyon se gir gaya."),
     "q": ("Where did the patient fall?", "Mareez kahan se gira?"),
     "accept": ["stairs", "seerhi", "staircase"]},
    {"id": "F12", "fact": ("Smokes 40 cigarettes a day.", "Din mein 40 cigarette peeta hai."),
     "q": ("How many cigarettes does the patient smoke a day?", "Mareez din mein kitne cigarette peeta hai?"),
     "accept": ["40", "forty", "chalees"]},
    {"id": "F13", "fact": ("Has epilepsy and had a seizure last month.",
                           "Epilepsy hai aur pichle mahine daura para."),
     "q": ("Which condition causes the patient's seizures?", "Mareez ko daure kis bimari ki wajah se parte hain?"),
     "accept": ["epilepsy", "mirgi"]},
    {"id": "F14", "fact": ("Wears a hearing aid in the right ear.", "Daayen kaan mein hearing aid lagata hai."),
     "q": ("What does the patient wear in the right ear?", "Mareez daayen kaan mein kya lagata hai?"),
     "accept": ["hearing aid", "hearing"]},
    {"id": "F15", "fact": ("Was treated for breast cancer in 2020.", "2020 mein breast cancer ka ilaj hua."),
     "q": ("Which cancer was the patient treated for?", "Mareez ka kis cancer ka ilaj hua?"),
     "accept": ["breast", "chhati"]},
    {"id": "F16", "fact": ("Asked to be seen by a female physiotherapist only.",
                           "Sirf khatoon physiotherapist se ilaj karwana chahta hai."),
     "q": ("What kind of physiotherapist did the patient ask for?",
           "Mareez ne kis tarah ka physiotherapist manga?"),
     "accept": ["female", "woman", "lady", "khatoon", "aurat"]},
    {"id": "F17", "fact": ("Has chronic kidney disease, so avoid anti-inflammatory tablets.",
                           "Gurdon ki purani bimari hai, is liye sozish wali goliyan na dein."),
     "q": ("Which organ disease does the patient have?", "Mareez ko kis uzv ki bimari hai?"),
     "accept": ["kidney", "renal", "gurd"]},
    {"id": "F18", "fact": ("Is flying to Lahore on 3 March and will miss two weeks.",
                           "3 March ko Lahore ja raha hai aur do hafte nahi aaye ga."),
     "q": ("Which city is the patient flying to?", "Mareez kis shehar ja raha hai?"),
     "accept": ["lahore"]},
    {"id": "F19", "fact": ("MRI showed a disc bulge at L4-L5.", "MRI mein L4-L5 par disc bulge aya."),
     "q": ("At which spinal level is the disc bulge?", "Disc bulge reerh ki haddi ke kis level par hai?"),
     "accept": ["l4"]},
    {"id": "F20", "fact": ("Had a steroid injection in the knee two weeks ago.",
                           "Do hafte pehle ghutne mein steroid injection laga."),
     "q": ("What injection did the patient have?", "Mareez ko kaun sa injection laga?"),
     "accept": ["steroid", "cortisone"]},
]

_LANG_INDEX = {"en": 0, "ru": 1}
_VISIT = {"en": "Visit {n}.", "ru": "Visit {n}."}
_PAIN = {"en": "Pain {p}/10.", "ru": "Dard {p}/10."}


def _note_plan(rng: random.Random) -> Dict[str, object]:
    """Indices into the pools for one note, shared by both languages."""
    return {
        "c": rng.randrange(len(COMPLAINTS)),
        "o": rng.randrange(len(OBSERVATIONS)),
        "t": rng.sample(range(len(TREATMENTS)), 2),
        "x": rng.randrange(len(OTHERS)),
        "p": rng.randrange(len(PLANS)),
        "pain": rng.randint(2, 7),
    }


def _render(plan: Dict[str, object], lang: str, visit: int, fact: str = "") -> str:
    i = _LANG_INDEX[lang]
    t1, t2 = plan["t"]  # type: ignore[misc]
    other = fact if fact else OTHERS[plan["x"]][i]  # type: ignore[index]
    parts = [
        _VISIT[lang].format(n=visit),
        COMPLAINTS[plan["c"]][i],  # type: ignore[index]
        _PAIN[lang].format(p=plan["pain"]),
        OBSERVATIONS[plan["o"]][i],  # type: ignore[index]
        TREATMENTS[t1][i],
        TREATMENTS[t2][i],
        other,
        PLANS[plan["p"]][i],  # type: ignore[index]
    ]
    return " ".join(parts)


def _plans(fact_id: str) -> Tuple[Dict[str, object], List[Dict[str, object]]]:
    rng = random.Random(f"lost-in-the-middle:{fact_id}")
    gold = _note_plan(rng)
    distractors = [_note_plan(rng) for _ in range(N_NOTES - 1)]
    return gold, distractors


def build_notes(fact: Dict[str, object], lang: str, position: int) -> List[str]:
    """The full record (N_NOTES notes) with the gold note at 1-indexed `position`."""
    if not 1 <= position <= N_NOTES:
        raise ValueError(f"position must be 1..{N_NOTES}, got {position}")
    gold, distractors = _plans(str(fact["id"]))
    order: List[Tuple[Dict[str, object], bool]] = [(p, False) for p in distractors]
    order.insert(position - 1, (gold, True))
    fact_text = fact["fact"][_LANG_INDEX[lang]]  # type: ignore[index]
    return [_render(p, lang, n, fact_text if is_gold else "")
            for n, (p, is_gold) in enumerate(order, start=1)]


def gold_note(fact: Dict[str, object], lang: str) -> str:
    """The gold note alone (oracle condition), numbered as visit 1."""
    gold, _ = _plans(str(fact["id"]))
    return _render(gold, lang, 1, fact["fact"][_LANG_INDEX[lang]])  # type: ignore[index]


def question(fact: Dict[str, object], lang: str) -> str:
    return fact["q"][_LANG_INDEX[lang]]  # type: ignore[index]


def conditions() -> Sequence[str]:
    """closed_book, oracle and one condition per position (pos01, pos08, ...)."""
    return ["closed_book", "oracle"] + [f"pos{p:02d}" for p in POSITIONS]
