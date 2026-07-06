from __future__ import annotations

import random
from collections import Counter, defaultdict
from pathlib import Path

from db import clamp, connect, decode_ids, encode_ids, fetch_all, fetch_one, get_state, set_state
from llm import ollama_generate

FIRST_NAMES = [
    "Alex", "Mia", "Leo", "Sophie", "Noah", "Emma", "Oliver", "Ava", "Ethan", "Chloe",
    "Lucas", "Grace", "Henry", "Ruby", "Jack", "Lily", "Charlie", "Zoe", "Oscar", "Ella",
    "Kai", "Ivy", "Max", "Nora", "Ryan", "Luna", "Felix", "Aria", "Jude", "Mila",
    "Theo", "Isla", "Hugo", "Eva", "Finn", "Alice", "Ben", "Poppy", "Sam", "Rose",
    "Tara", "Eli", "June", "Miles", "Nina", "Owen", "Yuki", "Rae", "Jonah", "Mei",
]
LAST_NAMES = [
    "Liang", "Chen", "Wang", "Lin", "Zhang", "Nguyen", "Patel", "Smith", "Brown", "Wilson",
    "Taylor", "Martin", "Kim", "Lee", "Garcia", "Singh", "Khan", "Miller", "Davis", "Clark",
]
JOBS = [
    "teacher", "nurse", "software developer", "barista", "mechanic", "accountant", "builder", "chef",
    "student", "shop owner", "designer", "bus driver", "doctor", "researcher", "gardener", "artist",
    "journalist", "police officer", "electrician", "project manager", "retired", "daycare worker",
]
HOMES = ["North Quarter", "River Street", "Old Town", "Market Lane", "Hill View", "Station Road", "Garden Court"]
PERSONALITIES = [
    "calm and reliable", "ambitious and restless", "warm and social", "quiet and observant",
    "stubborn but loyal", "creative and emotional", "practical and careful", "funny and chaotic",
]
STORY_ARCS = [
    "wants to start over", "is looking for a real friend", "wants a better life for family", "fears failure but refuses to quit",
    "secretly wants to change career", "is trying to repair a relationship", "wants to earn a first real win", "feels responsible for the town future",
    "wants to write a book but never starts", "wants to leave town but is tied down by relationships",
]
LIFE_GOALS = [
    "save enough money to leave town", "get a small shop running", "write a book that truly belongs to them", "repair family relationships",
    "become recognized in their field", "find someone they can trust", "protect someone more fragile than themselves", "prove they are not a failure",
    "learn how to be happy again", "repay what they owe from the past", "help children or students live better lives", "find a second chance in life",
]
DRAMATIC_NEEDS = [
    "learn to tell the truth", "learn to accept failure", "learn to ask for help", "learn to stop pleasing everyone",
    "learn to forgive themselves", "learn to accept the consequences of choices", "learn to leave places that are not theirs", "learn to value the people in front of them",
]
SECRETS = [
    "once betrayed a friend, but no one knows", "secretly owes money", "has long wanted to leave their partner or job",
    "keeps a letter they never sent", "has feelings for someone they should not love", "pretends to be more successful than they are",
    "carries guilt over an accident", "is secretly preparing to leave town", "has a long-hidden family conflict",
    "once gave up an important dream and regrets it", "knows someone else’s secret", "fears repeating their parents’ mistakes",
]

EVENT_TEMPLATES = {
    "work_win": ("Work breakthrough", "{a} solved a difficult problem at work as a {job}, gaining confidence."),
    "work_fail": ("Work setback", "{a} had a bad day at work and had to reconsider their plan."),
    "friendship": ("New connection", "{a} had a good conversation with {b} at {place}, and they became a little closer."),
    "conflict": ("Relationship conflict", "{a} argued with {b} over something small, leaving both of them unsettled."),
    "romance": ("Romantic tension", "{a} felt obvious romantic tension with {b}."),
    "health": ("Health fluctuation", "{a} felt unwell today and realized they needed rest."),
    "money": ("Money shift", "{a} made a decision that affected cash flow and changed their financial situation."),
    "family": ("Family event", "{a} changed today’s plans because of family responsibilities."),
    "community": ("Town event", "{place} had an incident that affected several people emotionally."),
    "breakthrough": ("Life turning point", "{a} decided to seriously face their main arc: {arc}."),
    "breakup": ("Relationship breakdown", "{a} could no longer hold the relationship with {b} together."),
    "goal_progress": ("Goal progress", "{a} took a step toward their goal: {goal}."),
    "goal_setback": ("Goal blocked", "{a} ran into resistance around their goal: {goal}."),
    "secret_pressure": ("Secret pressure", "{a} had their secret influence today’s choices: {secret_hint}."),
    "secret_reveal": ("Secret leak", "{a} had something hidden noticed by {b}, changing the trust in the relationship."),
    "secret_full_reveal": ("Secret revealed", "{a} finally had their secret exposed: {secret_hint}. {b} was pulled into the fallout, and the relationship could no longer pretend to be normal."),
    "health_crisis": ("Health crisis", "{a} had a sudden health crisis, and people around {place} realized it was not normal fatigue."),
    "runaway_attempt": ("Runaway signal", "{a} showed clear signs of leaving at {place}: packing, avoiding familiar faces, or dealing with final loose ends."),
    "public_argument": ("Public argument", "{a} had an old conflict with {b} exposed in public at {place}, and others started smelling drama."),
    "memory_trigger": ("Old memory echoes", "{a} was reminded of the past by a small event today and began to rethink {need}."),
    "choice": ("Critical choice", "{a} made a small decision at {place}, but it may change many things later."),
}

SCENE_TURNS = [
    "from hesitation to action", "from expectation to disappointment", "from conflict to silence", "from loneliness to being seen",
    "from confidence to doubt", "from avoidance to responsibility", "from calm to undertow", "from misunderstanding to closeness",
    "from concealment to exposure", "from goal to cost", "from old memory to new choice", "from companionship to debt",
]
CHAPTER_TITLES = [
    "After the Town Woke Up", "The Unsent Letter", "The Convenience Store Light", "A Choice in the Rain", "Someone Starts Telling the Truth",
    "Platform Delay", "The Past Is Not Over", "Cracks Between Friends", "A Second Chance", "Before Leaving",
]


def population_count() -> int:
    row = fetch_one("SELECT COUNT(*) AS c FROM people")
    return int(row["c"] if row else 0)


def current_day() -> int:
    return int(get_state("day", "0"))


def reset_world() -> None:
    with connect() as conn:
        conn.executescript(
            """
            DELETE FROM gossip_reports;
            DELETE FROM serial_stories;
            DELETE FROM conversations;
            DELETE FROM chapter_outlines;
            DELETE FROM director_notes;
            DELETE FROM memories;
            DELETE FROM scene_cards;
            DELETE FROM snapshots;
            DELETE FROM relationships;
            DELETE FROM events;
            DELETE FROM journal;
            DELETE FROM people;
            UPDATE sqlite_sequence SET seq=0 WHERE name IN ('people','relationships','events','journal','scene_cards','memories','director_notes','chapter_outlines','conversations','serial_stories','gossip_reports');
            INSERT INTO world_state(key, value) VALUES('day', '0')
                ON CONFLICT(key) DO UPDATE SET value='0';
            INSERT INTO world_state(key, value) VALUES('last_auto_timestamp', '0')
                ON CONFLICT(key) DO UPDATE SET value='0';
            """
        )
        conn.commit()


def init_world(count: int = 100, force: bool = False) -> None:
    if force:
        reset_world()
    if population_count() > 0:
        _backfill_v3_fields()
        return

    rng = random.Random(20260706)
    used_names: set[str] = set()
    people_payload = []
    for _ in range(count):
        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        while name in used_names:
            name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        used_names.add(name)
        age = rng.randint(18, 76)
        gender = rng.choice(["female", "male", "nonbinary"])
        job = rng.choice(JOBS if age < 65 else JOBS + ["retired", "retired", "retired"])
        home = rng.choice(HOMES)
        personality = rng.choice(PERSONALITIES)
        ambition = rng.randint(20, 95)
        sociability = rng.randint(10, 95)
        stability = rng.randint(15, 95)
        wealth = rng.randint(10, 85)
        happiness = rng.randint(35, 80)
        energy = rng.randint(35, 90)
        health = rng.randint(40, 95)
        relationship_status = rng.choice(["single", "single", "single", "married", "partnered"])
        story_arc = rng.choice(STORY_ARCS)
        life_goal = rng.choice(LIFE_GOALS)
        dramatic_need = rng.choice(DRAMATIC_NEEDS)
        secret = rng.choice(SECRETS)
        memory_summary = (
            f"{name} is a {job}, lives in {home}, personality: {personality}. "
            f"Arc: {story_arc}. Life goal: {life_goal}. Dramatic need: {dramatic_need}. "
        )
        people_payload.append(
            (name, age, gender, job, home, personality, ambition, sociability, stability, wealth,
             happiness, energy, health, relationship_status, None, story_arc, life_goal, dramatic_need,
             secret, "hidden", memory_summary, 0)
        )

    with connect() as conn:
        conn.executemany(
            """
            INSERT INTO people(
                name, age, gender, job, home, personality, ambition, sociability, stability, wealth,
                happiness, energy, health, relationship_status, partner_id, story_arc, life_goal,
                dramatic_need, secret, secret_status, memory_summary, created_day
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            people_payload,
        )
        people = list(conn.execute("SELECT id, name, home, relationship_status FROM people"))

        relation_rows = []
        for person in people:
            candidates = [p for p in people if p["id"] != person["id"]]
            rng.shuffle(candidates)
            for other in candidates[: rng.randint(3, 6)]:
                a, b = sorted([person["id"], other["id"]])
                relation_type = "neighbour" if person["home"] == other["home"] else rng.choice(["friend", "coworker", "acquaintance"])
                score = rng.randint(35, 80)
                trust = clamp(score + rng.randint(-10, 12))
                attraction = rng.randint(0, 35)
                jealousy = rng.randint(0, 20)
                dependency = rng.randint(5, 45)
                resentment = clamp(60 - score + rng.randint(-8, 12))
                relation_rows.append((a, b, relation_type, score, trust, attraction, jealousy, dependency, resentment, "initial relationship"))
        seen = set()
        clean = []
        for row in relation_rows:
            pair = (row[0], row[1])
            if pair not in seen:
                clean.append(row)
                seen.add(pair)
        conn.executemany(
            """
            INSERT OR IGNORE INTO relationships(
                person_a, person_b, relation_type, score, trust, attraction, jealousy, dependency, resentment, history
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            clean,
        )

        ids = [p["id"] for p in people]
        rng.shuffle(ids)
        paired = set()
        for a, b in zip(ids[0::2], ids[1::2]):
            if rng.random() < 0.18 and a not in paired and b not in paired:
                conn.execute("UPDATE people SET relationship_status='partnered', partner_id=? WHERE id=?", (b, a))
                conn.execute("UPDATE people SET relationship_status='partnered', partner_id=? WHERE id=?", (a, b))
                x, y = sorted([a, b])
                conn.execute(
                    """
                    INSERT OR IGNORE INTO relationships(person_a, person_b, relation_type, score, trust, attraction, jealousy, dependency, resentment, history)
                    VALUES (?, ?, 'partner', ?, ?, ?, ?, ?, ?, 'initial partner relationship')
                    """,
                    (x, y, rng.randint(60, 90), rng.randint(55, 90), rng.randint(45, 90), rng.randint(0, 25), rng.randint(35, 85), rng.randint(0, 20)),
                )
                paired.update([a, b])

        conn.execute(
            "INSERT INTO events(day, hour, title, description, importance, people_ids) VALUES(0, 8, 'World initialized', '100 residents enter M6 Town. Everyone has goals, secrets, long-term memory, and relationship dimensions.', 9, ?)",
            (encode_ids([]),),
        )
        conn.execute(
            "INSERT INTO scene_cards(day, title, viewpoint_person_id, scene_type, summary, emotional_turn, involved_ids, importance) VALUES(0, 'Prologue: M6 Town Wakes Up', NULL, 'world', 'This is a small world of 100 people. Everyone has a job, relationships, wishes, secrets, and an unfinished fate.', 'from blank slate to beginning', ?, 9)",
            (encode_ids([]),),
        )
        conn.execute(
            "INSERT INTO director_notes(day, focus_people_ids, diagnosis, tomorrow_hooks) VALUES(0, ?, 'The world has just started. There is no protagonist yet, only 100 life-lines that have not collided.', 'Advance a few days and watch whose goals, secrets, and relationships become tense first.')",
            (encode_ids([]),),
        )
        conn.commit()


def _backfill_v3_fields() -> None:
    rng = random.Random(8808)
    rows = fetch_all("SELECT id, name, job, home, personality, story_arc, life_goal, dramatic_need, secret, memory_summary FROM people")
    with connect() as conn:
        for p in rows:
            life_goal = p["life_goal"] or rng.choice(LIFE_GOALS)
            dramatic_need = p["dramatic_need"] or rng.choice(DRAMATIC_NEEDS)
            secret = p["secret"] or rng.choice(SECRETS)
            memory = p["memory_summary"] or f"{p['name']} is a {p['job']} and lives in {p['home']}."
            if "Life goal" not in memory:
                memory = (memory + f" Life goal: {life_goal}. Dramatic need: {dramatic_need}.")[-1100:]
            conn.execute(
                "UPDATE people SET life_goal=?, dramatic_need=?, secret=?, memory_summary=? WHERE id=?",
                (life_goal, dramatic_need, secret, memory, p["id"]),
            )
        conn.commit()


def _row_to_person(row) -> dict:
    return {k: row[k] for k in row.keys()}


def _pick_person(rng: random.Random) -> dict:
    rows = fetch_all("SELECT * FROM people ORDER BY RANDOM() LIMIT 1")
    return _row_to_person(rows[0])


def _pick_other(person_id: int, rng: random.Random) -> dict:
    rows = fetch_all("SELECT * FROM people WHERE id != ? ORDER BY RANDOM() LIMIT 1", (person_id,))
    return _row_to_person(rows[0])


def _secret_hint(secret: str) -> str:
    if not secret:
        return "something left unsaid"
    # Keep summaries readable while still showing the writer what drives the character.
    return secret.replace("secretly", "quietly").replace("no one knows", "not yet exposed")


def _append_memory(person_id: int, day: int, text: str, importance: int = 5, memory_type: str = "event") -> None:
    row = fetch_one("SELECT memory_summary FROM people WHERE id=?", (person_id,))
    if not row:
        return
    new_memory = (row["memory_summary"] + f" Day {day}: {text}")[-1200:]
    with connect() as conn:
        conn.execute("UPDATE people SET memory_summary=? WHERE id=?", (new_memory, person_id))
        conn.execute(
            "INSERT INTO memories(person_id, day, importance, memory_type, text) VALUES (?, ?, ?, ?, ?)",
            (person_id, day, importance, memory_type, text),
        )
        conn.commit()


def _update_person(person_id: int, **changes: int | str | None) -> None:
    if not changes:
        return
    allowed = {
        "wealth", "happiness", "energy", "health", "story_arc", "memory_summary", "relationship_status", "partner_id",
        "life_goal", "dramatic_need", "secret", "secret_status",
    }
    assignments = []
    values = []
    for key, value in changes.items():
        if key not in allowed:
            continue
        assignments.append(f"{key} = ?")
        values.append(value)
    if not assignments:
        return
    values.append(person_id)
    with connect() as conn:
        conn.execute(f"UPDATE people SET {', '.join(assignments)} WHERE id = ?", values)
        conn.commit()


def _add_event(day: int, hour: int, key: str, people: list[dict], importance: int, place: str | None = None) -> int:
    title, template = EVENT_TEMPLATES[key]
    a = people[0] if people else {"name": "town", "job": "", "story_arc": "", "life_goal": "", "dramatic_need": "", "secret": ""}
    b = people[1] if len(people) > 1 else {"name": "a resident", "job": "", "story_arc": ""}
    description = template.format(
        a=a["name"],
        b=b["name"],
        job=a.get("job", ""),
        place=place or a.get("home", "M6 Town"),
        arc=a.get("story_arc", "their own future"),
        goal=a.get("life_goal", "a goal they have not said out loud"),
        need=a.get("dramatic_need", "what they truly need to learn"),
        secret_hint=_secret_hint(a.get("secret", "")),
    )
    ids = [p["id"] for p in people]
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO events(day, hour, title, description, importance, people_ids) VALUES (?, ?, ?, ?, ?, ?)",
            (day, hour, title, description, importance, encode_ids(ids)),
        )
        conn.commit()
        event_id = int(cur.lastrowid)

    for p in people:
        if importance >= 6:
            _append_memory(p["id"], day, description, importance, key)
    if importance >= 7:
        _add_scene_from_event(day, title, description, key, people, importance)
    return event_id


def _add_scene_from_event(day: int, title: str, description: str, scene_type: str, people: list[dict], importance: int) -> None:
    viewpoint = people[0] if people else None
    involved_ids = [p["id"] for p in people]
    if viewpoint:
        summary = (
            f"From {viewpoint['name']}'s perspective, {description} "
            f"This event also touches the goal '{viewpoint.get('life_goal', 'unknown')}' and the dramatic need '{viewpoint.get('dramatic_need', 'unknown')}'."
        )
    else:
        summary = f"A town-level change occurred: {description}"
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO scene_cards(day, title, viewpoint_person_id, scene_type, summary, emotional_turn, involved_ids, importance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (day, title, viewpoint["id"] if viewpoint else None, scene_type, summary, random.choice(SCENE_TURNS), encode_ids(involved_ids), importance),
        )
        conn.commit()


def _change_relation(a_id: int, b_id: int, delta: int, relation_type: str, note: str, *,
                     trust_delta: int = 0, attraction_delta: int = 0, jealousy_delta: int = 0,
                     dependency_delta: int = 0, resentment_delta: int = 0) -> int:
    a, b = sorted([a_id, b_id])
    with connect() as conn:
        row = conn.execute("SELECT * FROM relationships WHERE person_a=? AND person_b=?", (a, b)).fetchone()
        if row:
            new_score = clamp(int(row["score"]) + delta)
            trust = clamp(int(row["trust"]) + trust_delta)
            attraction = clamp(int(row["attraction"]) + attraction_delta)
            jealousy = clamp(int(row["jealousy"]) + jealousy_delta)
            dependency = clamp(int(row["dependency"]) + dependency_delta)
            resentment = clamp(int(row["resentment"]) + resentment_delta)
            history = (row["history"] + " | " + note)[-1000:]
            conn.execute(
                "UPDATE relationships SET score=?, trust=?, attraction=?, jealousy=?, dependency=?, resentment=?, history=? WHERE person_a=? AND person_b=?",
                (new_score, trust, attraction, jealousy, dependency, resentment, history, a, b),
            )
        else:
            new_score = clamp(50 + delta)
            conn.execute(
                """
                INSERT INTO relationships(person_a, person_b, relation_type, score, trust, attraction, jealousy, dependency, resentment, history)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (a, b, relation_type, new_score, clamp(50 + trust_delta), clamp(10 + attraction_delta), clamp(jealousy_delta), clamp(10 + dependency_delta), clamp(resentment_delta), note),
            )
        conn.commit()
        return new_score


def _simulate_person_baseline(day: int, p: dict, rng: random.Random) -> None:
    energy = clamp(p["energy"] + rng.randint(-9, 5))
    happiness = clamp(p["happiness"] + rng.randint(-4, 4))
    health = clamp(p["health"] + rng.randint(-3, 2))
    wealth = clamp(p["wealth"] + rng.choice([-1, 0, 0, 1, 1, 2]))

    if p["ambition"] > 75 and rng.random() < 0.20:
        wealth = clamp(wealth + 1)
        energy = clamp(energy - 2)
    if p["sociability"] > 75 and rng.random() < 0.16:
        happiness = clamp(happiness + 2)
    if p["stability"] < 30 and rng.random() < 0.13:
        happiness = clamp(happiness - 3)
    if p["age"] > 65 and rng.random() < 0.14:
        health = clamp(health - 2)
    if "leave" in p.get("life_goal", "") and rng.random() < 0.08:
        happiness = clamp(happiness - 1)
        energy = clamp(energy + 1)
    if "learn how to be happy again" in p.get("life_goal", "") and rng.random() < 0.10:
        happiness = clamp(happiness + 1)

    _update_person(p["id"], energy=energy, happiness=happiness, health=health, wealth=wealth)


def simulate_day(use_ai: bool = False) -> int:
    init_world()
    day = current_day() + 1
    rng = random.Random(day * 9173 + 42)
    people = [_row_to_person(r) for r in fetch_all("SELECT * FROM people")]

    for p in people:
        _simulate_person_baseline(day, p, rng)

    event_count = rng.randint(11, 18)
    for _ in range(event_count):
        p = _pick_person(rng)
        roll = rng.random()
        hour = rng.randint(7, 22)
        if roll < 0.14:
            key = "work_win" if rng.random() < (p["ambition"] / 130) else "work_fail"
            delta_h = 4 if key == "work_win" else -5
            delta_w = 2 if key == "work_win" else -1
            _update_person(p["id"], happiness=clamp(p["happiness"] + delta_h), wealth=clamp(p["wealth"] + delta_w))
            _add_event(day, hour, key, [p], rng.randint(4, 7))
        elif roll < 0.30:
            other = _pick_other(p["id"], rng)
            score = _change_relation(
                p["id"], other["id"], rng.randint(4, 12), "friend", f"Day {day}: pleasant conversation",
                trust_delta=rng.randint(2, 8), dependency_delta=rng.randint(0, 4), resentment_delta=-rng.randint(0, 3),
            )
            imp = rng.randint(3, 6) + (1 if score > 80 else 0)
            _add_event(day, hour, "friendship", [p, other], min(9, imp), place=rng.choice(HOMES))
        elif roll < 0.46:
            other = _pick_other(p["id"], rng)
            score = _change_relation(
                p["id"], other["id"], -rng.randint(5, 15), "rival", f"Day {day}: conflict",
                trust_delta=-rng.randint(3, 12), jealousy_delta=rng.randint(0, 7), resentment_delta=rng.randint(5, 15),
            )
            imp = rng.randint(5, 8) + (1 if score < 25 else 0)
            _add_event(day, hour, "conflict", [p, other], min(10, imp), place=rng.choice(HOMES))
        elif roll < 0.55:
            other = _pick_other(p["id"], rng)
            if p["relationship_status"] == "single" and other["relationship_status"] == "single":
                score = _change_relation(
                    p["id"], other["id"], rng.randint(8, 18), "romance", f"Day {day}: romantic tension",
                    trust_delta=rng.randint(0, 5), attraction_delta=rng.randint(12, 25), jealousy_delta=rng.randint(0, 4), dependency_delta=rng.randint(0, 5),
                )
                _add_event(day, hour, "romance", [p, other], 8 if score > 80 else rng.randint(5, 7), place="Market Lane")
        elif roll < 0.64:
            _update_person(p["id"], health=clamp(p["health"] - rng.randint(4, 12)), energy=clamp(p["energy"] - rng.randint(4, 12)))
            _add_event(day, hour, "health", [p], rng.randint(4, 7))
        elif roll < 0.72:
            _update_person(p["id"], wealth=clamp(p["wealth"] + rng.randint(-7, 8)))
            _add_event(day, hour, "money", [p], rng.randint(3, 7))
        elif roll < 0.82:
            key = "goal_progress" if rng.random() < (0.45 + p["ambition"] / 260) else "goal_setback"
            _update_person(
                p["id"],
                happiness=clamp(p["happiness"] + (5 if key == "goal_progress" else -6)),
                energy=clamp(p["energy"] + (-3 if key == "goal_progress" else -5)),
            )
            _add_event(day, hour, key, [p], rng.randint(6, 9), place=p["home"])
        elif roll < 0.90:
            _update_person(p["id"], happiness=clamp(p["happiness"] - rng.randint(2, 8)), energy=clamp(p["energy"] - rng.randint(1, 6)))
            _add_event(day, hour, "secret_pressure", [p], rng.randint(6, 9), place=rng.choice(HOMES))
        elif roll < 0.96:
            _add_event(day, hour, "memory_trigger", [p], rng.randint(6, 8), place=p["home"])
        elif roll < 0.985:
            _add_event(day, hour, "choice", [p], rng.randint(7, 9), place=rng.choice(HOMES))
        else:
            _add_event(day, hour, "community", [], rng.randint(5, 9), place=rng.choice(HOMES))

    _life_changes(day, rng)
    _secret_reveals(day, rng)
    _gossip_escalations(day, rng)
    set_state("day", day)
    _save_snapshot(day)
    generate_daily_journal(day, use_ai=use_ai)
    generate_director_note(day, use_ai=use_ai)
    generate_chapter_outline(day)
    generate_key_scene_texts(day, use_ai=use_ai)
    if get_state("auto_story_enabled", "1") == "1":
        generate_daily_story(day, use_ai=use_ai if get_state("auto_story_use_ai", "0") == "1" else False)
    generate_gossip_report(day)
    return day


def _life_changes(day: int, rng: random.Random) -> None:
    top_romance = fetch_one(
        """
        SELECT r.*, pa.name AS a_name, pb.name AS b_name, pa.relationship_status AS a_status, pb.relationship_status AS b_status
        FROM relationships r
        JOIN people pa ON pa.id = r.person_a
        JOIN people pb ON pb.id = r.person_b
        WHERE (r.score >= 88 OR r.attraction >= 82) AND r.relation_type IN ('romance','friend')
        ORDER BY RANDOM() LIMIT 1
        """
    )
    if top_romance and rng.random() < 0.16:
        a_id, b_id = int(top_romance["person_a"]), int(top_romance["person_b"])
        pa_row = fetch_one("SELECT * FROM people WHERE id=?", (a_id,))
        pb_row = fetch_one("SELECT * FROM people WHERE id=?", (b_id,))
        if pa_row and pb_row:
            pa = _row_to_person(pa_row)
            pb = _row_to_person(pb_row)
            if pa["relationship_status"] == "single" and pb["relationship_status"] == "single":
                _update_person(a_id, relationship_status="partnered", partner_id=b_id, happiness=clamp(pa["happiness"] + 8))
                _update_person(b_id, relationship_status="partnered", partner_id=a_id, happiness=clamp(pb["happiness"] + 8))
                _change_relation(a_id, b_id, 8, "partner", f"Day {day}: became partners", trust_delta=8, attraction_delta=8, dependency_delta=8)
                _add_event(day, rng.randint(18, 22), "romance", [pa, pb], 9, place="River Street")

    weak_partner = fetch_one(
        """
        SELECT r.*, pa.name AS a_name, pb.name AS b_name
        FROM relationships r
        JOIN people pa ON pa.id = r.person_a
        JOIN people pb ON pb.id = r.person_b
        WHERE (r.score <= 15 OR r.resentment >= 85) AND r.relation_type IN ('partner','romance')
        ORDER BY RANDOM() LIMIT 1
        """
    )
    if weak_partner and rng.random() < 0.10:
        a_id, b_id = int(weak_partner["person_a"]), int(weak_partner["person_b"])
        pa = _row_to_person(fetch_one("SELECT * FROM people WHERE id=?", (a_id,)))
        pb = _row_to_person(fetch_one("SELECT * FROM people WHERE id=?", (b_id,)))
        _update_person(a_id, relationship_status="single", partner_id=None, happiness=clamp(pa["happiness"] - 10))
        _update_person(b_id, relationship_status="single", partner_id=None, happiness=clamp(pb["happiness"] - 10))
        _add_event(day, rng.randint(18, 23), "breakup", [pa, pb], 10, place="Old Town")


def _secret_reveals(day: int, rng: random.Random) -> None:
    candidate = fetch_one(
        """
        SELECT * FROM people
        WHERE secret_status='hidden' AND id IN (
          SELECT person_id FROM memories GROUP BY person_id HAVING COUNT(*) >= 2
        )
        ORDER BY RANDOM() LIMIT 1
        """
    )
    if not candidate or rng.random() > 0.13:
        return
    p = _row_to_person(candidate)
    other = _pick_other(p["id"], rng)
    _update_person(p["id"], secret_status="suspected", happiness=clamp(p["happiness"] - 8), energy=clamp(p["energy"] - 6))
    _change_relation(p["id"], other["id"], -rng.randint(4, 12), "secret", f"Day {day}: secret suspected", trust_delta=-rng.randint(8, 18), resentment_delta=rng.randint(4, 10))
    _add_event(day, rng.randint(19, 23), "secret_reveal", [p, other], rng.randint(8, 10), place=rng.choice(HOMES))



def _recent_memory_count(person_id: int, memory_type: str, since_day: int) -> int:
    row = fetch_one(
        "SELECT COUNT(*) AS c FROM memories WHERE person_id=? AND memory_type=? AND day>=?",
        (person_id, memory_type, since_day),
    )
    return int(row["c"] or 0) if row else 0


def _strongest_related_person(person_id: int) -> dict | None:
    row = fetch_one(
        """
        SELECT CASE WHEN r.person_a=? THEN r.person_b ELSE r.person_a END AS other_id
        FROM relationships r
        WHERE r.person_a=? OR r.person_b=?
        ORDER BY (100-r.trust) + r.resentment + ABS(r.score-50) DESC
        LIMIT 1
        """,
        (person_id, person_id, person_id),
    )
    if row and row["other_id"]:
        other = fetch_one("SELECT * FROM people WHERE id=?", (int(row["other_id"]),))
        return _row_to_person(other) if other else None
    return None


def _gossip_escalations(day: int, rng: random.Random) -> None:
    """V7: make the town less polite. Suspicions can explode, sick people can trigger crisis,
    escape plans can become visible, and bad relationships can turn into public arguments.
    """
    # 1) Secret suspected for high-score people can become revealed.
    suspected = protagonist_candidates(20)
    suspected = [p for p in suspected if p.get("secret_status") == "suspected"]
    for p in suspected[:5]:
        stress = max(0, 55 - int(p["happiness"])) + max(0, 45 - int(p["health"])) + max(0, 45 - int(p["energy"]))
        already = _recent_memory_count(int(p["id"]), "secret_full_reveal", max(0, day - 40))
        chance = 0.10 + min(0.35, stress / 220) + (0.12 if int(p.get("story_score", 0)) > 1600 else 0)
        if already == 0 and rng.random() < chance:
            other = _strongest_related_person(int(p["id"])) or _pick_other(int(p["id"]), rng)
            _update_person(int(p["id"]), secret_status="revealed", happiness=clamp(int(p["happiness"]) - 14), energy=clamp(int(p["energy"]) - 8))
            _change_relation(int(p["id"]), int(other["id"]), -rng.randint(10, 24), "secret",
                             f"Day {day}: secret fully revealed", trust_delta=-rng.randint(14, 30), resentment_delta=rng.randint(10, 26))
            _add_event(day, rng.randint(18, 23), "secret_full_reveal", [p, other], 10, place=rng.choice(HOMES))
            _append_memory(int(p["id"]), day, f"The secret was finally exposed: {p['secret']}. {other['name']} was pulled into the fallout.", 10, "secret_full_reveal")
            _append_memory(int(other["id"]), day, f"{p['name']}'s secret was exposed, and they were pulled into it too.", 9, "secret_full_reveal")
            break

    # 2) Health crisis for very low-health high-story characters, not every day.
    low_health = protagonist_candidates(25)
    low_health = [p for p in low_health if int(p["health"]) <= 5]
    for p in low_health[:4]:
        if _recent_memory_count(int(p["id"]), "health_crisis", max(0, day - 21)) == 0 and rng.random() < 0.20:
            _update_person(int(p["id"]), happiness=clamp(int(p["happiness"]) - 8), energy=clamp(int(p["energy"]) - 8))
            _add_event(day, rng.randint(6, 22), "health_crisis", [p], 9, place=p["home"])
            _append_memory(int(p["id"]), day, "Their health visibly entered crisis, and others could no longer treat it as ordinary fatigue.", 9, "health_crisis")
            break

    # 3) Runaway attempt for people whose goals/secrets point to leaving.
    runaway_rows = fetch_all(
        """
        SELECT * FROM people
        WHERE (life_goal LIKE '%leave%' OR secret LIKE '%leave%')
        ORDER BY (100-happiness) + (100-health) + (100-energy) DESC
        LIMIT 8
        """
    )
    for row in runaway_rows:
        p = _row_to_person(row)
        if _recent_memory_count(int(p["id"]), "runaway_attempt", max(0, day - 28)) == 0 and rng.random() < 0.16:
            _update_person(int(p["id"]), happiness=clamp(int(p["happiness"]) - 5), energy=clamp(int(p["energy"]) - 5), wealth=clamp(int(p["wealth"]) - rng.randint(1, 6)))
            _add_event(day, rng.randint(5, 23), "runaway_attempt", [p], 9, place=p["home"])
            _append_memory(int(p["id"]), day, "They showed clear signs of leaving town: packing, dealing with money, or avoiding familiar people.", 9, "runaway_attempt")
            break

    # 4) Relationship bomb: bad trust + resentment becomes public.
    bomb = fetch_one(
        """
        SELECT r.*, pa.name AS a_name, pb.name AS b_name
        FROM relationships r
        JOIN people pa ON pa.id=r.person_a
        JOIN people pb ON pb.id=r.person_b
        WHERE r.trust <= 18 OR r.resentment >= 88 OR r.score <= 12
        ORDER BY r.resentment DESC, (100-r.trust) DESC
        LIMIT 1
        """
    )
    if bomb and rng.random() < 0.18:
        a = _row_to_person(fetch_one("SELECT * FROM people WHERE id=?", (int(bomb["person_a"]),)))
        b = _row_to_person(fetch_one("SELECT * FROM people WHERE id=?", (int(bomb["person_b"]),)))
        if _recent_memory_count(int(a["id"]), "public_argument", max(0, day - 14)) == 0:
            _change_relation(int(a["id"]), int(b["id"]), -rng.randint(5, 14), "conflict",
                             f"Day {day}: public argument", trust_delta=-rng.randint(5, 14), resentment_delta=rng.randint(5, 16))
            _add_event(day, rng.randint(9, 22), "public_argument", [a, b], 9, place=rng.choice(HOMES))
            _append_memory(int(a["id"]), day, f"Their conflict with {b['name']} was exposed in public.", 8, "public_argument")
            _append_memory(int(b["id"]), day, f"Their conflict with {a['name']} was exposed in public.", 8, "public_argument")

def _save_snapshot(day: int) -> None:
    row = fetch_one(
        """
        SELECT AVG(happiness) AS happiness, AVG(energy) AS energy, AVG(health) AS health, AVG(wealth) AS wealth,
               SUM(CASE WHEN happiness < 30 THEN 1 ELSE 0 END) AS low_happiness,
               SUM(CASE WHEN health < 35 THEN 1 ELSE 0 END) AS low_health,
               SUM(CASE WHEN relationship_status IN ('partnered','married') THEN 1 ELSE 0 END) AS partnered
        FROM people
        """
    )
    events = fetch_one("SELECT COUNT(*) AS c FROM events WHERE day=?", (day,))
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO snapshots(day, avg_happiness, avg_energy, avg_health, avg_wealth, low_happiness_count, low_health_count, partnered_count, event_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(day) DO UPDATE SET
                avg_happiness=excluded.avg_happiness,
                avg_energy=excluded.avg_energy,
                avg_health=excluded.avg_health,
                avg_wealth=excluded.avg_wealth,
                low_happiness_count=excluded.low_happiness_count,
                low_health_count=excluded.low_health_count,
                partnered_count=excluded.partnered_count,
                event_count=excluded.event_count
            """,
            (
                day,
                float(row["happiness"] or 0),
                float(row["energy"] or 0),
                float(row["health"] or 0),
                float(row["wealth"] or 0),
                int(row["low_happiness"] or 0),
                int(row["low_health"] or 0),
                int(row["partnered"] or 0),
                int(events["c"] or 0),
            ),
        )
        conn.commit()


def generate_daily_journal(day: int, use_ai: bool = False) -> None:
    events = fetch_all("SELECT * FROM events WHERE day=? ORDER BY importance DESC, hour ASC", (day,))
    scenes = fetch_all("SELECT * FROM scene_cards WHERE day=? ORDER BY importance DESC LIMIT 5", (day,))
    if not events:
        summary = "The town was mostly quiet today, with no obvious turning point."
        notable = "No major event."
    else:
        important = events[:8]
        event_lines = [f"{e['hour']:02d}:00 | {e['title']} | {e['description']} | importance {e['importance']}" for e in important]
        scene_lines = [f"Scene: {s['title']} | {s['summary']} | Emotional turn: {s['emotional_turn']}" for s in scenes]
        ai_text = None
        if use_ai:
            prompt = (
                "You are the English narrator of a 100-person simulated town. Write today’s summary."
                "Requirements: realistic, no fantasy; include one overview, three people worth tracking, and possible hooks for tomorrow."
                "Do not imitate any living author. Do not write exaggerated web fiction.\n\n"
                + "\n".join(event_lines + scene_lines)
            )
            ai_text = ollama_generate(prompt)
        if ai_text:
            summary = ai_text[:4000]
            notable = "Generated by local AI from key events and scene cards."
        else:
            types = Counter(e["title"] for e in events)
            top_type = types.most_common(1)[0][0]
            top_event = important[0]
            summary = (
                f"Day {day} ; M6 Town recorded {len(events)}  trackable events."
                f"The strongest theme today is '{top_type}'. Most notable: {top_event['description']}"
            )
            scene_text = "\n".join([f"- {s['title']}: {s['emotional_turn']}. {s['summary']}" for s in scenes[:3]])
            event_text = "\n".join([f"- {e['description']} (importance {e['importance']})" for e in important[:5]])
            notable = (scene_text + "\n" + event_text).strip()

    with connect() as conn:
        conn.execute(
            "INSERT INTO journal(day, summary, notable) VALUES (?, ?, ?) ON CONFLICT(day) DO UPDATE SET summary=excluded.summary, notable=excluded.notable",
            (day, summary, notable),
        )
        conn.commit()


def protagonist_candidates(limit: int = 12) -> list[dict]:
    rows = fetch_all("SELECT * FROM people")
    candidates = []
    for p in rows:
        pid = int(p["id"])
        mem = fetch_one("SELECT COUNT(*) AS c, COALESCE(SUM(importance),0) AS imp FROM memories WHERE person_id=?", (pid,))
        rel = fetch_one(
            """
            SELECT COUNT(*) AS c,
                   COALESCE(MAX(CASE WHEN score >= 50 THEN score ELSE 100-score END),0) AS intensity,
                   COALESCE(MAX(resentment),0) AS max_resentment,
                   COALESCE(MAX(attraction),0) AS max_attraction,
                   COALESCE(MAX(jealousy),0) AS max_jealousy
            FROM relationships WHERE person_a=? OR person_b=?
            """,
            (pid, pid),
        )
        scenes = fetch_one("SELECT COUNT(*) AS c, COALESCE(SUM(importance),0) AS imp FROM scene_cards WHERE viewpoint_person_id=? OR involved_ids LIKE ?", (pid, f"%{pid}%"))
        stress = max(0, 55 - int(p["happiness"])) + max(0, 50 - int(p["energy"])) + max(0, 45 - int(p["health"]))
        goal_bonus = 10 if p["life_goal"] else 0
        secret_bonus = 18 if p["secret_status"] in {"suspected", "revealed"} else 10 if p["secret"] else 0
        score = int(mem["imp"] or 0) + int(scenes["imp"] or 0) + int(rel["intensity"] or 0) // 2 + int(rel["max_resentment"] or 0) // 3 + int(rel["max_attraction"] or 0) // 4 + stress + goal_bonus + secret_bonus
        candidate = dict(p)
        candidate.update({
            "story_score": score,
            "memory_count": int(mem["c"] or 0),
            "scene_count": int(scenes["c"] or 0),
            "relationship_intensity": int(rel["intensity"] or 0),
            "story_reason": _candidate_reason(p, stress, rel, mem),
        })
        candidates.append(candidate)
    return sorted(candidates, key=lambda x: x["story_score"], reverse=True)[:limit]


def _candidate_reason(p, stress: int, rel, mem) -> str:
    reasons = []
    if stress > 25:
        reasons.append("high stress")
    if p["secret_status"] in {"suspected", "revealed"}:
        reasons.append("secret is loosening")
    elif p["secret"]:
        reasons.append("hidden secret")
    if int(rel["max_resentment"] or 0) > 70:
        reasons.append("strong resentment")
    if int(rel["max_attraction"] or 0) > 70:
        reasons.append("strong emotional tension")
    if int(mem["c"] or 0) >= 4:
        reasons.append("rich long-term memory")
    if not reasons:
        reasons.append("clear goal, worth watching")
    return ", ".join(reasons[:3])


def generate_director_note(day: int, use_ai: bool = False) -> None:
    events = fetch_all("SELECT * FROM events WHERE day=? ORDER BY importance DESC LIMIT 10", (day,))
    candidates = protagonist_candidates(5)
    focus_ids = [int(p["id"]) for p in candidates[:4]]
    lines = [f"{p['name']} | score{p['story_score']} | {p['life_goal']} | {p['story_reason']}" for p in candidates[:5]]
    event_lines = [f"{e['title']}: {e['description']}" for e in events[:8]]
    ai_text = None
    if use_ai:
        prompt = (
            "You are the AI director of a text simulation. Write the director diagnosis in English."
            "Do not imitate any specific author. Output two sections: 1) today’s most valuable narrative clue; 2) what to watch tomorrow."
            "Tone: calm, realistic, suitable for long-form fiction.\n\nProtagonist candidates: \n"
            + "\n".join(lines)
            + "\n\nToday’s events: \n"
            + "\n".join(event_lines)
        )
        ai_text = ollama_generate(prompt, timeout=90)
    if ai_text:
        diagnosis = ai_text[:3500]
        hooks = "AI director generated observation directions from today’s events."
    else:
        if candidates:
            lead = candidates[0]
            diagnosis = (
                f"Today the most interesting person to watch is {lead['name']}. Their goal is '{lead['life_goal']}.' "
                f"Secret status is '{lead['secret_status']}', story score {lead['story_score']}. "
                f"Reason: {lead['story_reason']}."
            )
        else:
            diagnosis = "There is no obvious protagonist today; the world is still accumulating material."
        hooks = "\n".join([
            f"- Watch whether {p['name']} will pay a cost for '{p['life_goal']}'."
            for p in candidates[:3]
        ]) or "- Advance a few more days and let relationships and secrets ferment naturally."
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO director_notes(day, focus_people_ids, diagnosis, tomorrow_hooks)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(day) DO UPDATE SET focus_people_ids=excluded.focus_people_ids, diagnosis=excluded.diagnosis, tomorrow_hooks=excluded.tomorrow_hooks
            """,
            (day, encode_ids(focus_ids), diagnosis, hooks),
        )
        conn.commit()


def generate_chapter_outline(day: int) -> None:
    candidates = protagonist_candidates(4)
    focus_ids = [int(p["id"]) for p in candidates[:3]]
    scenes = fetch_all("SELECT * FROM scene_cards WHERE day=? ORDER BY importance DESC LIMIT 5", (day,))
    events = fetch_all("SELECT * FROM events WHERE day=? ORDER BY importance DESC LIMIT 5", (day,))
    title = CHAPTER_TITLES[day % len(CHAPTER_TITLES)]
    theme = _infer_theme(events)
    lines = [f"This chapter’s theme is: {theme}. "]
    if candidates:
        lines.append("Protagonist candidates: " + ", ".join([p["name"] for p in candidates[:3]]))
    if scenes:
        lines.append("Expandable scenes:")
        for s in scenes:
            lines.append(f"- {s['title']}: {s['emotional_turn']}. {s['summary']}")
    elif events:
        lines.append("Expandable events:")
        for e in events:
            lines.append(f"- {e['title']}: {e['description']}")
    lines.append("Chapter function: make goals, secrets, and relationship costs collide at least once.")
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO chapter_outlines(day, title, theme, protagonist_ids, outline)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(day) DO UPDATE SET title=excluded.title, theme=excluded.theme, protagonist_ids=excluded.protagonist_ids, outline=excluded.outline
            """,
            (day, title, theme, encode_ids(focus_ids), "\n".join(lines)),
        )
        conn.commit()


def _infer_theme(events) -> str:
    titles = [e["title"] for e in events]
    if any("Secret" in t for t in titles):
        return "the pressure of concealment"
    if any("Goal" in t for t in titles):
        return "goals and costs"
    if any("conflict" in t.lower() or "breakdown" in t.lower() for t in titles):
        return "cracks in relationships"
    if any("romantic" in t.lower() or "New connection" in t for t in titles):
        return "closeness and misunderstanding"
    return "small turns in daily life"


def dashboard_data() -> dict:
    init_world()
    day = current_day()
    people_count = population_count()
    avg = fetch_one("SELECT AVG(happiness) AS happiness, AVG(energy) AS energy, AVG(health) AS health, AVG(wealth) AS wealth FROM people")
    latest_journal = fetch_one("SELECT * FROM journal ORDER BY day DESC LIMIT 1")
    latest_director = fetch_one("SELECT * FROM director_notes ORDER BY day DESC LIMIT 1")
    latest_chapter = fetch_one("SELECT * FROM chapter_outlines ORDER BY day DESC LIMIT 1")
    latest_story = fetch_one("""
        SELECT ss.*, p.name AS protagonist_name
        FROM serial_stories ss
        LEFT JOIN people p ON p.id = ss.protagonist_id
        ORDER BY ss.day DESC LIMIT 1
    """)
    latest_gossip = fetch_one("SELECT * FROM gossip_reports ORDER BY day DESC LIMIT 1")
    latest_conversations = fetch_all(
        """
        SELECT c.*, s.title AS scene_title, vp.name AS viewpoint_name, pp.name AS partner_name
        FROM conversations c
        LEFT JOIN scene_cards s ON s.id = c.scene_id
        LEFT JOIN people vp ON vp.id = c.viewpoint_person_id
        LEFT JOIN people pp ON pp.id = c.partner_person_id
        ORDER BY c.day DESC, c.importance DESC, c.id DESC
        LIMIT 4
        """
    )
    top_events = fetch_all("SELECT * FROM events ORDER BY day DESC, importance DESC, hour DESC LIMIT 12")
    latest_scenes = fetch_all(
        """
        SELECT s.*, p.name AS viewpoint_name
        FROM scene_cards s
        LEFT JOIN people p ON p.id = s.viewpoint_person_id
        ORDER BY s.day DESC, s.importance DESC
        LIMIT 6
        """
    )
    snapshots = fetch_all("SELECT * FROM snapshots ORDER BY day DESC LIMIT 14")
    critical_people = protagonist_candidates(8)
    return {
        "day": day,
        "people_count": people_count,
        "avg": avg,
        "journal": latest_journal,
        "director": latest_director,
        "chapter": latest_chapter,
        "latest_story": latest_story,
        "latest_gossip": latest_gossip,
        "conversations": latest_conversations,
        "events": top_events,
        "critical_people": critical_people,
        "scenes": latest_scenes,
        "snapshots": list(reversed(snapshots)),
        "auto_enabled": get_state("auto_enabled", "0") == "1",
        "auto_interval_minutes": get_state("auto_interval_minutes", "1440"),
    }


def get_people(search: str = ""):
    if search:
        like = f"%{search}%"
        return fetch_all(
            """
            SELECT * FROM people
            WHERE name LIKE ? OR job LIKE ? OR home LIKE ? OR story_arc LIKE ? OR memory_summary LIKE ? OR life_goal LIKE ? OR secret LIKE ?
            ORDER BY happiness ASC, name ASC LIMIT 200
            """,
            (like, like, like, like, like, like, like),
        )
    return fetch_all("SELECT * FROM people ORDER BY happiness ASC, name ASC LIMIT 200")


def get_person(person_id: int) -> dict | None:
    p = fetch_one("SELECT * FROM people WHERE id=?", (person_id,))
    if not p:
        return None
    rels = fetch_all(
        """
        SELECT r.*, pa.name AS a_name, pb.name AS b_name
        FROM relationships r
        JOIN people pa ON pa.id = r.person_a
        JOIN people pb ON pb.id = r.person_b
        WHERE r.person_a=? OR r.person_b=?
        ORDER BY CASE WHEN r.score >= 50 THEN r.score ELSE 100-r.score END DESC LIMIT 30
        """,
        (person_id, person_id),
    )
    all_events = fetch_all("SELECT * FROM events ORDER BY day DESC, importance DESC LIMIT 900")
    events = [e for e in all_events if person_id in decode_ids(e["people_ids"])][:60]
    scenes = fetch_all(
        """
        SELECT * FROM scene_cards
        WHERE viewpoint_person_id=? OR involved_ids LIKE ?
        ORDER BY day DESC, importance DESC LIMIT 40
        """,
        (person_id, f"%{person_id}%"),
    )
    memories = fetch_all("SELECT * FROM memories WHERE person_id=? ORDER BY day DESC, importance DESC LIMIT 50", (person_id,))
    conversations = fetch_all(
        """
        SELECT c.*, pp.name AS partner_name, s.title AS scene_title
        FROM conversations c
        LEFT JOIN people pp ON pp.id = c.partner_person_id
        LEFT JOIN scene_cards s ON s.id = c.scene_id
        WHERE c.viewpoint_person_id=? OR c.partner_person_id=?
        ORDER BY c.day DESC, c.importance DESC LIMIT 40
        """,
        (person_id, person_id),
    )
    score = next((c["story_score"] for c in protagonist_candidates(100) if c["id"] == person_id), 0)
    return {"person": p, "relationships": rels, "events": events, "scenes": scenes, "memories": memories, "conversations": conversations, "story_score": score}


def get_storylines() -> dict:
    scenes = fetch_all(
        """
        SELECT s.*, p.name AS viewpoint_name, p.job AS viewpoint_job
        FROM scene_cards s
        LEFT JOIN people p ON p.id = s.viewpoint_person_id
        ORDER BY s.day DESC, s.importance DESC
        LIMIT 80
        """
    )
    journals = fetch_all("SELECT * FROM journal ORDER BY day DESC LIMIT 30")
    intense_relationships = fetch_all(
        """
        SELECT r.*, pa.name AS a_name, pb.name AS b_name
        FROM relationships r
        JOIN people pa ON pa.id = r.person_a
        JOIN people pb ON pb.id = r.person_b
        WHERE r.score >= 85 OR r.score <= 20 OR r.trust <= 20 OR r.resentment >= 80 OR r.attraction >= 80
        ORDER BY CASE WHEN r.score >= 50 THEN r.score ELSE 100-r.score END DESC, r.resentment DESC
        LIMIT 25
        """
    )
    chapters = fetch_all("SELECT * FROM chapter_outlines ORDER BY day DESC LIMIT 20")
    conversations = fetch_all(
        """
        SELECT c.*, vp.name AS viewpoint_name, pp.name AS partner_name, s.title AS scene_title
        FROM conversations c
        LEFT JOIN people vp ON vp.id = c.viewpoint_person_id
        LEFT JOIN people pp ON pp.id = c.partner_person_id
        LEFT JOIN scene_cards s ON s.id = c.scene_id
        ORDER BY c.day DESC, c.importance DESC LIMIT 30
        """
    )
    return {
        "scenes": scenes,
        "protagonists": protagonist_candidates(12),
        "journals": journals,
        "relationships": intense_relationships,
        "chapters": chapters,
        "conversations": conversations,
    }


def get_director_room() -> dict:
    return {
        "notes": fetch_all("SELECT * FROM director_notes ORDER BY day DESC LIMIT 60"),
        "protagonists": protagonist_candidates(15),
        "chapters": fetch_all("SELECT * FROM chapter_outlines ORDER BY day DESC LIMIT 30"),
        "secret_people": fetch_all("SELECT * FROM people WHERE secret_status != 'hidden' ORDER BY happiness ASC LIMIT 20"),
    }


def app_settings() -> dict:
    return {
        "auto_enabled": get_state("auto_enabled", "0"),
        "auto_interval_minutes": get_state("auto_interval_minutes", "1440"),
        "auto_use_ai": get_state("auto_use_ai", "0"),
        "last_auto_timestamp": get_state("last_auto_timestamp", "0"),
        "world_name": get_state("world_name", "M6 Town"),
        "director_style": get_state("director_style", "literary"),
        "auto_story_enabled": get_state("auto_story_enabled", "1"),
        "auto_story_export": get_state("auto_story_export", "1"),
        "auto_story_use_ai": get_state("auto_story_use_ai", "0"),
        "auto_story_catchup": get_state("auto_story_catchup", "1"),
    }


def update_settings(auto_enabled: bool, interval_minutes: int, auto_use_ai: bool,
                    auto_story_enabled: bool = True, auto_story_export: bool = True,
                    auto_story_use_ai: bool = False, auto_story_catchup: bool = True) -> None:
    interval_minutes = max(1, min(int(interval_minutes), 10080))
    set_state("auto_enabled", "1" if auto_enabled else "0")
    set_state("auto_interval_minutes", str(interval_minutes))
    set_state("auto_use_ai", "1" if auto_use_ai else "0")
    set_state("auto_story_enabled", "1" if auto_story_enabled else "0")
    set_state("auto_story_export", "1" if auto_story_export else "0")
    set_state("auto_story_use_ai", "1" if auto_story_use_ai else "0")
    set_state("auto_story_catchup", "1" if auto_story_catchup else "0")


def export_novel_markdown(output_path: str | Path | None = None) -> Path:
    init_world()
    output = Path(output_path) if output_path else Path(__file__).resolve().parent / "simworld_novel_seed_v7.md"
    day = current_day()
    journals = fetch_all("SELECT * FROM journal ORDER BY day ASC")
    scenes = fetch_all(
        """
        SELECT s.*, p.name AS viewpoint_name
        FROM scene_cards s
        LEFT JOIN people p ON p.id = s.viewpoint_person_id
        ORDER BY s.day ASC, s.importance DESC
        """
    )
    candidates = protagonist_candidates(15)
    rels = fetch_all(
        """
        SELECT r.*, pa.name AS a_name, pb.name AS b_name
        FROM relationships r
        JOIN people pa ON pa.id = r.person_a
        JOIN people pb ON pb.id = r.person_b
        ORDER BY CASE WHEN r.score >= 50 THEN r.score ELSE 100-r.score END DESC, r.resentment DESC, r.attraction DESC
        LIMIT 50
        """
    )
    notes = fetch_all("SELECT * FROM director_notes ORDER BY day ASC")
    chapters = fetch_all("SELECT * FROM chapter_outlines ORDER BY day ASC")
    lines = [
        "# M6 SimWorld v7: Auto-Serial Story Material Pack",
        "",
        f"Current simulation day: {day}.",
        "",
        "> Note: This is story material automatically organized from the simulated world. v7 adds town gossip, secret reveals, daily stories, chapter index, and Markdown exports. It does not imitate any specific living author.",
        "",
        "## 1. Protagonist Candidate Scores",
        "",
    ]
    for p in candidates:
        lines.append(f"- **{p['name']}** | score {p['story_score']} | {p['age']} years old | {p['job']} | {p['home']} | happiness {p['happiness']} | health {p['health']}")
        lines.append(f"  - Goal: {p['life_goal']}")
        lines.append(f"  - Arc: {p['story_arc']}")
        lines.append(f"  - Dramatic need: {p['dramatic_need']}")
        lines.append(f"  - Secret: {p['secret']}(status: {p['secret_status']})")
        lines.append(f"  - Reason: {p['story_reason']}")
        lines.append(f"  - Memory summary: {p['memory_summary']}")
    lines += ["", "## 2. Strong Relationships and Conflict", ""]
    for r in rels:
        tone = "close" if r["score"] >= 70 else "tense" if r["score"] <= 30 else "complex"
        lines.append(
            f"- **{r['a_name']} ↔ {r['b_name']}** | {r['relation_type']} | {tone} | relationship {r['score']} | trust {r['trust']} | attraction {r['attraction']} | jealousy {r['jealousy']} | dependency {r['dependency']} | resentment {r['resentment']} | {r['history']}"
        )
    lines += ["", "## 3. AI Director Notes", ""]
    for n in notes:
        lines.append(f"### Day {n['day']}")
        lines.append(n["diagnosis"])
        lines.append("")
        lines.append("**Next watch:**")
        lines.append(n["tomorrow_hooks"])
        lines.append("")
    lines += ["", "## 4. Chapter Outlines", ""]
    for c in chapters:
        lines.append(f"### Day {c['day']} | {c['title']}")
        lines.append(f"Theme: {c['theme']}")
        lines.append("")
        lines.append(c["outline"])
        lines.append("")
    lines += ["", "## 5. Daily Story Material", ""]
    scenes_by_day: dict[int, list] = defaultdict(list)
    for s in scenes:
        scenes_by_day[int(s["day"])].append(s)
    for j in journals:
        d = int(j["day"])
        lines.append(f"### Day {d}")
        lines.append("")
        lines.append(j["summary"])
        lines.append("")
        if j["notable"]:
            lines.append("**Notable:**")
            lines.append(j["notable"])
            lines.append("")
        if scenes_by_day.get(d):
            lines.append("**Expandable scenes:**")
            for s in scenes_by_day[d][:5]:
                vp = s["viewpoint_name"] or "town"
                lines.append(f"- {s['title']} | Viewpoint: {vp} | {s['emotional_turn']} | {s['summary']}")
            lines.append("")
    conversations = fetch_all(
        """
        SELECT c.*, vp.name AS viewpoint_name, pp.name AS partner_name, s.title AS scene_title
        FROM conversations c
        LEFT JOIN people vp ON vp.id = c.viewpoint_person_id
        LEFT JOIN people pp ON pp.id = c.partner_person_id
        LEFT JOIN scene_cards s ON s.id = c.scene_id
        ORDER BY c.day ASC, c.importance DESC, c.id ASC
        """
    )
    lines += ["", "## 6. Dialogue and Inner Monologue Material", ""]
    if conversations:
        for c in conversations:
            names = c["viewpoint_name"] or "town"
            if c["partner_name"]:
                names += f" / {c['partner_name']}"
            ai_flag = "local AI" if c["ai_generated"] else "rule-generated"
            lines.append(f"### Day {c['day']} | {c['title']} | {names} | {ai_flag}")
            lines.append("")
            lines.append(c["text"])
            lines.append("")
    else:
        lines.append("No dialogue or monologue generated yet. Open the Writer page and generate some, or advance one AI day.")
    if not journals:
        lines.append("No daily reports yet. Advance a few days first, ideally to Day 30, then export.")
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


# -----------------------------
# V4: key-scene dialogue / inner monologue writer
# -----------------------------

def _people_from_scene(scene_row) -> list[dict]:
    ids = decode_ids(scene_row["involved_ids"] or "[]")
    if scene_row["viewpoint_person_id"] and int(scene_row["viewpoint_person_id"]) not in ids:
        ids.insert(0, int(scene_row["viewpoint_person_id"]))
    if not ids:
        return []
    placeholders = ",".join("?" for _ in ids)
    rows = fetch_all(f"SELECT * FROM people WHERE id IN ({placeholders})", ids)
    by_id = {int(r["id"]): _row_to_person(r) for r in rows}
    return [by_id[i] for i in ids if i in by_id]


def _conversation_fallback(scene: dict, people: list[dict], mode: str) -> str:
    title = scene.get("title", "a scene")
    summary = scene.get("summary", "")
    turn = scene.get("emotional_turn", "from calm to undertow")
    if not people:
        return (
            f"[Scene] {title}\n"
            f"A subtle change moved through M6 Town today. {summary}\n"
            f"Emotional turn: {turn}. It was not an explosive twist, just the kind of small crack daily life leaves behind."
        )
    a = people[0]
    if mode == "monologue" or len(people) == 1:
        return (
            f"[Inner Monologue | {a['name']}]\n"
            f"I always thought that if I got through today, things would get lighter on their own. But after{title}I realized it had only moved to another place and kept pressing on me.\n"
            f"My goal is: {a.get('life_goal', 'a goal I have not said out loud')}. It sounds clear, but the hard part is not the goal. It is admitting that I need to {a.get('dramatic_need', 'face myself')}.\n"
            f"I have not said the secret out loud. Not because it does not matter, but because once I do, my relationships may never be the same.\n"
            f"Today felt like {turn}. I know this is not over."
        )
    b = people[1]
    if "conflict" in title.lower() or "breakdown" in title.lower() or "Secret" in title:
        return (
            f"[Dialogue Scene | {a['name']} and {b['name']}]\n"
            f"{a['name']}: What did you mean by that?\n"
            f"{b['name']}: Nothing. I just feel like you never said the real reason.\n"
            f"{a['name']}: Not everything needs an explanation.\n"
            f"{b['name']}: But if you don’t explain, people can only guess. If they guess long enough, trust breaks.\n"
            f"{a['name']} was silent for a while.{summary}\n"
            f"{a['name']}: It’s not that I don’t want to say it. I don’t know if we can go back after I do.\n"
            f"Emotional turn: {turn}. "
        )
    if "romantic" in title.lower() or "relationship " in title.lower() or "friend" in title.lower():
        return (
            f"[Dialogue Scene | {a['name']} and {b['name']}]\n"
            f"{b['name']}: You seem different today.\n"
            f"{a['name']}: Different how?\n"
            f"{b['name']}: Like you finally decided not to carry it alone.\n"
            f"{a['name']} gave a small smile but did not answer immediately. {summary}\n"
            f"{a['name']}: Maybe I am just tired.\n"
            f"{b['name']}: You can tell someone when you are tired.\n"
            f"That sentence made the air go quiet. Emotional turn: {turn}."
        )
    return (
        f"[Short Scene | {a['name']} and {b['name']}]\n"
        f"{summary}\n"
        f"{a['name']}: Sometimes I think this town is too small. Everything finds its way back to you.\n"
        f"{b['name']}: Or maybe you keep waiting for someone else to speak first.\n"
        f"{a['name']}: If I speak, will things get better?\n"
        f"{b['name']}: Not necessarily. But at least it will start.\n"
        f"Emotional turn: {turn}. "
    )


def _conversation_prompt(scene: dict, people: list[dict], mode: str) -> str:
    people_lines = []
    for p in people[:3]:
        people_lines.append(
            f"- {p['name']}: {p['age']} years old, {p['job']}, personality: {p['personality']}, Goal: {p['life_goal']}, Dramatic need: {p['dramatic_need']}, Secret: {p['secret_status']}. Memory: {p['memory_summary'][-350:]}"
        )
    task = "write an English dialogue scene" if mode == "dialogue" else "write an English first-person inner monologue"
    return (
        "You are a local simulation writing assistant. Do not imitate any specific living author. "
        "Style: restrained, realistic, suitable as literary life-fiction material. No fantasy, no power fantasy, no melodrama.\n"
        f"Task: {task}. Length: 250-550 words.\n"
        f"Scene title: {scene.get('title')}\n"
        f"Scene summary: {scene.get('summary')}\n"
        f"Emotional turn: {scene.get('emotional_turn')}\n"
        "Characters:\n" + "\n".join(people_lines) + "\n"
        "Output only the scene text, no explanation."
    )


def generate_conversation_for_scene(scene_id: int, use_ai: bool = False, mode: str = "auto", force: bool = False) -> int | None:
    scene_row = fetch_one("SELECT * FROM scene_cards WHERE id=?", (scene_id,))
    if not scene_row:
        return None
    scene = {k: scene_row[k] for k in scene_row.keys()}
    people = _people_from_scene(scene_row)
    final_mode = "dialogue" if mode == "auto" and len(people) >= 2 else "monologue" if mode == "auto" else mode
    if not force:
        existing = fetch_one("SELECT id FROM conversations WHERE scene_id=? AND mode=?", (scene_id, final_mode))
        if existing:
            return int(existing["id"])

    ai_text = None
    ai_generated = 0
    if use_ai:
        prompt = _conversation_prompt(scene, people, final_mode)
        ai_text = ollama_generate(prompt, timeout=120)
        if ai_text:
            ai_generated = 1
    text = (ai_text or _conversation_fallback(scene, people, final_mode)).strip()[:5000]
    viewpoint_id = int(people[0]["id"]) if people else scene.get("viewpoint_person_id")
    partner_id = int(people[1]["id"]) if len(people) >= 2 else None
    title = f"{scene['title']} | {'Dialogue' if final_mode == 'dialogue' else 'Inner Monologue'}"
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO conversations(day, scene_id, event_id, mode, title, viewpoint_person_id, partner_person_id, text, ai_generated, importance)
            VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(scene_id, mode) DO UPDATE SET
                title=excluded.title,
                viewpoint_person_id=excluded.viewpoint_person_id,
                partner_person_id=excluded.partner_person_id,
                text=excluded.text,
                ai_generated=excluded.ai_generated,
                importance=excluded.importance
            """,
            (int(scene["day"]), scene_id, final_mode, title, viewpoint_id, partner_id, text, ai_generated, int(scene.get("importance") or 5)),
        )
        conn.commit()
        return int(cur.lastrowid or (fetch_one("SELECT id FROM conversations WHERE scene_id=? AND mode=?", (scene_id, final_mode))["id"]))


def generate_key_scene_texts(day: int | None = None, use_ai: bool = False, limit: int = 4) -> int:
    if day is None:
        day = current_day()
    scenes = fetch_all(
        """
        SELECT s.*
        FROM scene_cards s
        LEFT JOIN conversations c ON c.scene_id = s.id AND c.mode IN ('dialogue','monologue')
        WHERE s.day=? AND c.id IS NULL
        ORDER BY s.importance DESC, s.id DESC
        LIMIT ?
        """,
        (day, max(1, min(limit, 12))),
    )
    count = 0
    for s in scenes:
        if generate_conversation_for_scene(int(s["id"]), use_ai=use_ai):
            count += 1
    return count


def generate_missing_conversations(limit: int = 8, use_ai: bool = False) -> int:
    scenes = fetch_all(
        """
        SELECT s.*
        FROM scene_cards s
        LEFT JOIN conversations c ON c.scene_id = s.id AND c.mode IN ('dialogue','monologue')
        WHERE c.id IS NULL
        ORDER BY s.day DESC, s.importance DESC, s.id DESC
        LIMIT ?
        """,
        (max(1, min(limit, 30)),),
    )
    count = 0
    for s in scenes:
        if generate_conversation_for_scene(int(s["id"]), use_ai=use_ai):
            count += 1
    return count



# -----------------------------
# V7: town gossip report with reveals
# -----------------------------

def _person_line(p: dict) -> str:
    return f"{p['name']} | {p['job']} | happiness {p['happiness']} | health {p['health']} | Goal: {p['life_goal']} | Secret: {p['secret_status']}"


def _gossip_hot_topics(day: int) -> list[str]:
    events = fetch_all("SELECT * FROM events WHERE day=? ORDER BY importance DESC, hour DESC LIMIT 12", (day,))
    topics = []
    for e in events:
        title = str(e["title"])
        if any(k in title for k in ["Secret revealed", "Secret leak", "Runaway", "Health crisis", "Public argument", "Relationship breakdown", "Romantic"]):
            topics.append(f"{e['title']}: {e['description']}")
    if not topics:
        for e in events[:5]:
            topics.append(f"{e['title']}: {e['description']}")
    return topics[:8]


def _gossip_relationship_bombs() -> list[str]:
    rows = fetch_all(
        """
        SELECT r.*, pa.name AS a_name, pb.name AS b_name
        FROM relationships r
        JOIN people pa ON pa.id=r.person_a
        JOIN people pb ON pb.id=r.person_b
        WHERE r.trust <= 25 OR r.resentment >= 75 OR r.score <= 20 OR r.attraction >= 80
        ORDER BY r.resentment DESC, r.attraction DESC, (100-r.trust) DESC
        LIMIT 10
        """
    )
    out=[]
    for r in rows:
        if int(r["resentment"]) >= 75 or int(r["trust"]) <= 25 or int(r["score"]) <= 20:
            tag="could explode any minute"
        elif int(r["attraction"]) >= 80:
            tag="romantic pressure"
        else:
            tag="complex"
        out.append(f"{r['a_name']} ↔ {r['b_name']} | {tag} | relationship {r['score']} trust {r['trust']} attraction {r['attraction']} resentment {r['resentment']}")
    return out


def _gossip_runaway_watch() -> list[str]:
    rows = fetch_all(
        """
        SELECT * FROM people
        WHERE life_goal LIKE '%leave%' OR secret LIKE '%leave%'
        ORDER BY (100-health) + (100-happiness) + (100-energy) DESC
        LIMIT 8
        """
    )
    return [_person_line(dict(r)) for r in rows]


def _gossip_secret_watch() -> list[str]:
    rows = fetch_all(
        """
        SELECT * FROM people
        WHERE secret_status IN ('suspected','revealed')
        ORDER BY CASE secret_status WHEN 'revealed' THEN 0 ELSE 1 END, happiness ASC, health ASC
        LIMIT 12
        """
    )
    if not rows:
        rows = fetch_all("SELECT * FROM people WHERE secret != '' ORDER BY happiness ASC LIMIT 8")
    return [f"{r['name']} | {r['secret_status']} | {r['secret']} | happiness {r['happiness']} health {r['health']}" for r in rows]


def _gossip_danger_people() -> list[str]:
    rows = protagonist_candidates(15)
    danger = []
    for p in rows:
        reason=[]
        if int(p["health"]) <= 5:
            reason.append("health at zero or near crisis")
        if int(p["happiness"]) <= 15:
            reason.append("happiness crash")
        if p.get("secret_status") == "revealed":
            reason.append("revealed secrets")
        elif p.get("secret_status") == "suspected":
            reason.append("suspected secrets")
        if reason:
            danger.append(f"{p['name']} | {';'.join(reason)} | story score {p['story_score']} | Goal: {p['life_goal']}")
    return danger[:10]


def generate_gossip_report(day: int | None = None) -> None:
    if day is None:
        day = current_day()
    if day <= 0:
        return
    candidates = protagonist_candidates(8)
    lead = candidates[0] if candidates else None
    hot = _gossip_hot_topics(day)
    danger = _gossip_danger_people()
    secrets = _gossip_secret_watch()
    runaways = _gossip_runaway_watch()
    bombs = _gossip_relationship_bombs()

    if lead:
        headline = f"Day {day} town hot list: {lead['name']} is currently the biggest drama source, story score {lead['story_score']}."
    else:
        headline = f"Day {day} town hot list: no single lead today, but relationships are fermenting."
    # Town mood is intentionally blunt; this is the user's gossip dashboard, not literary mode.
    revealed_count = fetch_one("SELECT COUNT(*) AS c FROM people WHERE secret_status='revealed'")
    suspected_count = fetch_one("SELECT COUNT(*) AS c FROM people WHERE secret_status='suspected'")
    low_health = fetch_one("SELECT COUNT(*) AS c FROM people WHERE health<=5")
    low_happy = fetch_one("SELECT COUNT(*) AS c FROM people WHERE happiness<=15")
    town_mood = (
        f"Town status: {int(suspected_count['c'] or 0)} suspected secrets, "
        f"{int(revealed_count['c'] or 0)} revealed secrets, "
        f"{int(low_health['c'] or 0)} people at health risk, "
        f"{int(low_happy['c'] or 0)} people in happiness crash."
    )
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO gossip_reports(day, headline, hot_topics, danger_people, secret_watch, runaway_watch, relationship_bombs, town_mood)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(day) DO UPDATE SET
                headline=excluded.headline,
                hot_topics=excluded.hot_topics,
                danger_people=excluded.danger_people,
                secret_watch=excluded.secret_watch,
                runaway_watch=excluded.runaway_watch,
                relationship_bombs=excluded.relationship_bombs,
                town_mood=excluded.town_mood
            """,
            (day, headline, "\n".join(hot), "\n".join(danger), "\n".join(secrets), "\n".join(runaways), "\n".join(bombs), town_mood),
        )
        conn.commit()


def get_gossip_room() -> dict:
    init_world()
    day = current_day()
    if day > 0 and not fetch_one("SELECT id FROM gossip_reports WHERE day=?", (day,)):
        generate_gossip_report(day)
    latest = fetch_one("SELECT * FROM gossip_reports ORDER BY day DESC LIMIT 1")
    reports = fetch_all("SELECT * FROM gossip_reports ORDER BY day DESC LIMIT 60")
    return {
        "day": day,
        "latest": dict(latest) if latest else None,
        "reports": reports,
        "protagonists": protagonist_candidates(10),
        "danger_people": _gossip_danger_people(),
        "secret_watch": _gossip_secret_watch(),
        "runaway_watch": _gossip_runaway_watch(),
        "relationship_bombs": _gossip_relationship_bombs(),
    }

def get_writer_room() -> dict:
    conversations = fetch_all(
        """
        SELECT c.*, vp.name AS viewpoint_name, pp.name AS partner_name, s.title AS scene_title
        FROM conversations c
        LEFT JOIN people vp ON vp.id = c.viewpoint_person_id
        LEFT JOIN people pp ON pp.id = c.partner_person_id
        LEFT JOIN scene_cards s ON s.id = c.scene_id
        ORDER BY c.day DESC, c.importance DESC, c.id DESC
        LIMIT 80
        """
    )
    missing_scenes = fetch_all(
        """
        SELECT s.*, p.name AS viewpoint_name
        FROM scene_cards s
        LEFT JOIN people p ON p.id = s.viewpoint_person_id
        LEFT JOIN conversations c ON c.scene_id = s.id AND c.mode IN ('dialogue','monologue')
        WHERE c.id IS NULL
        ORDER BY s.day DESC, s.importance DESC, s.id DESC
        LIMIT 30
        """
    )
    return {
        "day": current_day(),
        "conversations": conversations,
        "missing_scenes": missing_scenes,
        "protagonists": protagonist_candidates(8),
        "ai_enabled_hint": "run_with_ai_ollama.bat" if get_state("auto_use_ai", "0") != "1" else "Auto AI is enabled in settings",
    }


# -----------------------------
# V7: automatic daily serial story mode
# -----------------------------

def _as_dict(row) -> dict | None:
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


def _story_exports_dir() -> Path:
    path = Path(__file__).resolve().parent / "exports" / "serial"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _clean_markdown_filename(day: int) -> str:
    return f"day_{day:04d}.md"


def _get_story_people(ids: list[int]) -> dict[int, dict]:
    if not ids:
        return {}
    placeholders = ",".join("?" for _ in ids)
    rows = fetch_all(f"SELECT * FROM people WHERE id IN ({placeholders})", ids)
    return {int(r["id"]): dict(r) for r in rows}


def _supporting_ids_from_day(day: int, lead_id: int | None = None, limit: int = 4) -> list[int]:
    events = fetch_all("SELECT people_ids FROM events WHERE day=? ORDER BY importance DESC LIMIT 20", (day,))
    counts: Counter[int] = Counter()
    for e in events:
        for pid in decode_ids(e["people_ids"]):
            if lead_id is not None and pid == lead_id:
                continue
            counts[pid] += 1
    return [pid for pid, _ in counts.most_common(limit)]


def _compose_rule_story(day: int, lead: dict | None, support_people: list[dict], journal: dict | None,
                        director: dict | None, chapter: dict | None, events: list, scenes: list,
                        conversations: list) -> tuple[str, str, str, str]:
    title = chapter["title"] if chapter else f"Day {day} Story"
    theme = chapter["theme"] if chapter else _infer_theme(events)
    if lead:
        subtitle = f"Today’s lead: {lead['name']} | {lead['life_goal']}"
    else:
        subtitle = "Today’s lead: M6 Town"

    event_lines = [f"{e['hour']:02d}:00, {e['description']}" for e in events[:5]]
    scene_lines = [f"{s['title']}: {s['summary']}" for s in scenes[:3]]
    support_names = ", ".join([p["name"] for p in support_people]) or "several town residents"
    hook = "Keep watching whether this thread becomes the real main line."
    if director and director.get("tomorrow_hooks"):
        hook = str(director["tomorrow_hooks"]).splitlines()[0].lstrip("- ").strip() or hook

    lines = []
    lines.append(f"# Day {day} | {title}")
    lines.append("")
    lines.append(f"> Theme: {theme}. {subtitle}.")
    lines.append("")
    if lead:
        lines.append(
            f"{lead['name']} did not think this day would leave a mark. They woke up as usual, thinking about work, money, relationships, "
            f"and the goal that had never really been resolved: {lead['life_goal']}."
        )
        lines.append(
            f"But change in town rarely begins with a loud noise. It is more like someone pausing at a doorway, someone not replying, "
            f"someone hearing another meaning in an ordinary sentence. For {lead['name']}, the hard part was not the event itself, "
            f"but the growing realization that they needed to {lead['dramatic_need']}."
        )
    else:
        lines.append("M6 Town had no single lead today, but several relationship lines became unstable at the same time.")

    if event_lines:
        lines.append("")
        lines.append("A few small things surfaced first during the day:")
        for line in event_lines[:3]:
            lines.append(f"- {line}")

    if scenes:
        lines.append("")
        lines.append("What makes the day chapter-worthy is the emotional turn behind these small events:")
        for s in scenes[:2]:
            lines.append(f"- **{s['title']}**: {s['emotional_turn']}. {s['summary']}")

    if support_people:
        lines.append("")
        lines.append(f"{support_names} did not stand outside the story. Each of them tugged gently at today’s choices.")

    if conversations:
        lines.append("")
        lines.append("A scene fragment left behind today:")
        excerpt = str(conversations[0]["text"]).strip()
        excerpt = excerpt[:900] + ("..." if len(excerpt) > 900 else "")
        lines.append("")
        lines.append(excerpt)

    if journal:
        lines.append("")
        lines.append("The daily report records it carefully:")
        lines.append(f"> {journal['summary']}")

    if director:
        lines.append("")
        lines.append("Director’s note:")
        lines.append(f"> {director['diagnosis']}")

    lines.append("")
    lines.append("## Tomorrow’s Hook")
    lines.append(hook)
    lines.append("")
    story_text = "\n".join(lines)
    return title, subtitle, theme, story_text


def _story_prompt(day: int, lead: dict | None, support_people: list[dict], journal: dict | None,
                  director: dict | None, chapter: dict | None, events: list, scenes: list,
                  conversations: list) -> str:
    lead_line = "No clear protagonist"
    if lead:
        lead_line = (
            f"{lead['name']}: {lead['age']} years old, {lead['job']}, lives in {lead['home']}. "
            f"Goal: {lead['life_goal']}. Dramatic need: {lead['dramatic_need']}. "
            f"Secret status: {lead['secret_status']}. Memory: {lead['memory_summary'][-500:]}"
        )
    support_lines = [f"- {p['name']}: {p['job']}, Goal: {p['life_goal']}, relationship may affect the lead" for p in support_people[:4]]
    event_lines = [f"- {e['hour']:02d}:00 {e['title']}: {e['description']}, importance {e['importance']}" for e in events[:8]]
    scene_lines = [f"- {s['title']}: {s['summary']}, Emotional turn: {s['emotional_turn']}" for s in scenes[:5]]
    convo_lines = [str(c['text'])[:650] for c in conversations[:2]]
    return (
        "You are a local simulated-world serial writing assistant. Do not imitate any specific living author. "
        "Write an English serial chapter from the simulation data, 900-1500 words. "
        "Style: realistic, restrained, lived-in, like a daily life story that grew from the simulation. No fantasy, no power fantasy, no melodrama. "
        "Structure: title, body, and a final subheading 'Tomorrow’s Hook' with one or two sentences. Output only Markdown.\n\n"
        f"Day: {day}\n"
        f"Chapter outline: {chapter['title'] if chapter else ''} | Theme: {chapter['theme'] if chapter else ''}\n{chapter['outline'] if chapter else ''}\n\n"
        f"Today’s lead: {lead_line}\n\n"
        "Related people:\n" + "\n".join(support_lines) + "\n\n"
        "Important events today:\n" + "\n".join(event_lines) + "\n\n"
        "Scene cards:\n" + "\n".join(scene_lines) + "\n\n"
        f"Daily report: {journal['summary'] if journal else ''}\n{journal['notable'] if journal else ''}\n\n"
        f"Director diagnosis: {director['diagnosis'] if director else ''}\n{director['tomorrow_hooks'] if director else ''}\n\n"
        "Existing dialogue / monologue material:\n" + "\n---\n".join(convo_lines)
    )


def generate_daily_story(day: int | None = None, use_ai: bool = False, force: bool = False) -> int | None:
    init_world()
    if day is None:
        day = current_day()
    if day <= 0:
        return None
    existing = fetch_one("SELECT id FROM serial_stories WHERE day=?", (day,))
    if existing and not force:
        return int(existing["id"])

    # Ensure upstream writing material exists.
    if not fetch_one("SELECT id FROM journal WHERE day=?", (day,)):
        generate_daily_journal(day, use_ai=False)
    if not fetch_one("SELECT id FROM director_notes WHERE day=?", (day,)):
        generate_director_note(day, use_ai=False)
    if not fetch_one("SELECT id FROM chapter_outlines WHERE day=?", (day,)):
        generate_chapter_outline(day)
    generate_key_scene_texts(day, use_ai=use_ai, limit=3)

    journal = _as_dict(fetch_one("SELECT * FROM journal WHERE day=?", (day,)))
    director = _as_dict(fetch_one("SELECT * FROM director_notes WHERE day=?", (day,)))
    chapter = _as_dict(fetch_one("SELECT * FROM chapter_outlines WHERE day=?", (day,)))
    events = fetch_all("SELECT * FROM events WHERE day=? ORDER BY importance DESC, hour ASC LIMIT 20", (day,))
    scenes = fetch_all("SELECT * FROM scene_cards WHERE day=? ORDER BY importance DESC LIMIT 8", (day,))
    conversations = fetch_all(
        """
        SELECT c.*, vp.name AS viewpoint_name, pp.name AS partner_name
        FROM conversations c
        LEFT JOIN people vp ON vp.id = c.viewpoint_person_id
        LEFT JOIN people pp ON pp.id = c.partner_person_id
        WHERE c.day=? ORDER BY c.importance DESC, c.id DESC LIMIT 5
        """,
        (day,),
    )

    candidates = protagonist_candidates(5)
    lead = candidates[0] if candidates else None
    lead_id = int(lead["id"]) if lead else None
    support_ids = _supporting_ids_from_day(day, lead_id, 4)
    support_by_id = _get_story_people(support_ids)
    support_people = [support_by_id[i] for i in support_ids if i in support_by_id]

    title, subtitle, theme, story_text = _compose_rule_story(day, lead, support_people, journal, director, chapter, events, scenes, conversations)
    ai_generated = 0
    if use_ai:
        ai_text = ollama_generate(_story_prompt(day, lead, support_people, journal, director, chapter, events, scenes, conversations), timeout=180)
        if ai_text:
            ai_generated = 1
            story_text = ai_text.strip()[:12000]
            # Try to infer title from the first Markdown heading if the model supplied one.
            first_line = story_text.splitlines()[0].strip() if story_text.splitlines() else ""
            if first_line.startswith("#"):
                title = first_line.lstrip("#").strip()[:80] or title
    tomorrow_hook = ""
    if "## Tomorrow’s Hook" in story_text:
        tomorrow_hook = story_text.split("## Tomorrow’s Hook", 1)[1].strip().splitlines()[0][:500]
    elif director and director.get("tomorrow_hooks"):
        tomorrow_hook = str(director["tomorrow_hooks"]).splitlines()[0].lstrip("- ")[:500]

    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO serial_stories(day, title, subtitle, protagonist_id, supporting_ids, theme, story_text, tomorrow_hook, ai_generated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(day) DO UPDATE SET
                title=excluded.title,
                subtitle=excluded.subtitle,
                protagonist_id=excluded.protagonist_id,
                supporting_ids=excluded.supporting_ids,
                theme=excluded.theme,
                story_text=excluded.story_text,
                tomorrow_hook=excluded.tomorrow_hook,
                ai_generated=excluded.ai_generated
            """,
            (day, title, subtitle, lead_id, encode_ids(support_ids), theme, story_text, tomorrow_hook, ai_generated),
        )
        conn.commit()
        story_id = int(cur.lastrowid or (fetch_one("SELECT id FROM serial_stories WHERE day=?", (day,))["id"]))

    if get_state("auto_story_export", "1") == "1":
        _write_daily_story_file(day)
    return story_id


def _write_daily_story_file(day: int) -> Path | None:
    story = fetch_one(
        """
        SELECT ss.*, p.name AS protagonist_name
        FROM serial_stories ss
        LEFT JOIN people p ON p.id = ss.protagonist_id
        WHERE ss.day=?
        """,
        (day,),
    )
    if not story:
        return None
    path = _story_exports_dir() / _clean_markdown_filename(day)
    lines = [
        f"# Day {story['day']} | {story['title']}",
        "",
        f"- Theme: {story['theme']}",
        f"- Protagonist: {story['protagonist_name'] or 'M6 Town'}",
        f"- Generated by: {'local AI' if story['ai_generated'] else 'rule-generated'}",
        "",
        str(story["story_text"]).strip(),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def get_today_story() -> dict:
    init_world()
    day = current_day()
    if day > 0 and not fetch_one("SELECT id FROM serial_stories WHERE day=?", (day,)):
        generate_daily_story(day, use_ai=get_state("auto_story_use_ai", "0") == "1")
    story = fetch_one(
        """
        SELECT ss.*, p.name AS protagonist_name, p.job AS protagonist_job, p.life_goal AS protagonist_goal
        FROM serial_stories ss
        LEFT JOIN people p ON p.id = ss.protagonist_id
        ORDER BY ss.day DESC LIMIT 1
        """
    )
    latest = _as_dict(story)
    prev_story = None
    next_story = None
    support_people = []
    if story:
        prev_story = fetch_one("SELECT day, title FROM serial_stories WHERE day < ? ORDER BY day DESC LIMIT 1", (story["day"],))
        next_story = fetch_one("SELECT day, title FROM serial_stories WHERE day > ? ORDER BY day ASC LIMIT 1", (story["day"],))
        ids = decode_ids(story["supporting_ids"])
        support_by_id = _get_story_people(ids)
        support_people = [support_by_id[i] for i in ids if i in support_by_id]
    return {
        "day": day,
        "story": latest,
        "prev_story": _as_dict(prev_story),
        "next_story": _as_dict(next_story),
        "support_people": support_people,
        "recent_stories": get_serial_stories(limit=12),
    }


def get_story_by_day(day: int) -> dict | None:
    row = fetch_one(
        """
        SELECT ss.*, p.name AS protagonist_name, p.job AS protagonist_job, p.life_goal AS protagonist_goal
        FROM serial_stories ss
        LEFT JOIN people p ON p.id = ss.protagonist_id
        WHERE ss.day=?
        """,
        (day,),
    )
    if not row and 0 < day <= current_day():
        generate_daily_story(day, use_ai=False)
        row = fetch_one(
            """
            SELECT ss.*, p.name AS protagonist_name, p.job AS protagonist_job, p.life_goal AS protagonist_goal
            FROM serial_stories ss
            LEFT JOIN people p ON p.id = ss.protagonist_id
            WHERE ss.day=?
            """,
            (day,),
        )
    if not row:
        return None
    ids = decode_ids(row["supporting_ids"])
    support_by_id = _get_story_people(ids)
    return {
        "story": _as_dict(row),
        "support_people": [support_by_id[i] for i in ids if i in support_by_id],
        "prev_story": _as_dict(fetch_one("SELECT day, title FROM serial_stories WHERE day < ? ORDER BY day DESC LIMIT 1", (day,))),
        "next_story": _as_dict(fetch_one("SELECT day, title FROM serial_stories WHERE day > ? ORDER BY day ASC LIMIT 1", (day,))),
    }


def get_serial_stories(limit: int = 100) -> list[dict]:
    rows = fetch_all(
        """
        SELECT ss.*, p.name AS protagonist_name, p.job AS protagonist_job
        FROM serial_stories ss
        LEFT JOIN people p ON p.id = ss.protagonist_id
        ORDER BY ss.day DESC LIMIT ?
        """,
        (max(1, min(limit, 500)),),
    )
    return [dict(r) for r in rows]


def get_serial_room() -> dict:
    total = fetch_one("SELECT COUNT(*) AS c FROM serial_stories")
    latest = fetch_one("SELECT * FROM serial_stories ORDER BY day DESC LIMIT 1")
    missing_days = []
    max_day = current_day()
    if max_day > 0:
        existing = {int(r["day"]) for r in fetch_all("SELECT day FROM serial_stories")}
        missing_days = [d for d in range(1, max_day + 1) if d not in existing][:30]
    return {
        "day": max_day,
        "total": int(total["c"] or 0),
        "latest": _as_dict(latest),
        "stories": get_serial_stories(120),
        "missing_days": missing_days,
        "settings": app_settings(),
    }


def generate_missing_daily_stories(limit: int = 30, use_ai: bool = False) -> int:
    max_day = current_day()
    if max_day <= 0:
        return 0
    existing = {int(r["day"]) for r in fetch_all("SELECT day FROM serial_stories")}
    count = 0
    for d in range(1, max_day + 1):
        if d not in existing:
            if generate_daily_story(d, use_ai=use_ai):
                count += 1
            if count >= limit:
                break
    return count


def export_serial_markdown(output_path: str | Path | None = None) -> Path:
    init_world()
    if current_day() > 0:
        generate_missing_daily_stories(limit=500, use_ai=False)
    output = Path(output_path) if output_path else Path(__file__).resolve().parent / "simworld_serial_v7.md"
    stories = list(reversed(get_serial_stories(500)))
    lines = [
        "# M6 SimWorld v7: Auto-Serial Collection",
        "",
        f"Current simulation day: {current_day()}. Total chapters: {len(stories)}.",
        "",
    ]
    for s in stories:
        lines.append(f"## Day {s['day']} | {s['title']}")
        lines.append("")
        lines.append(f"Theme: {s['theme']} | Protagonist: {s.get('protagonist_name') or 'M6 Town'} | Generated by: {'local AI' if s['ai_generated'] else 'rule-generated'}")
        lines.append("")
        lines.append(str(s["story_text"]).strip())
        lines.append("")
        lines.append("---")
        lines.append("")
    output.write_text("\n".join(lines), encoding="utf-8")
    return output

# -----------------------------
# V7: share card / GitHub demo mode
# -----------------------------

def _share_exports_dir() -> Path:
    path = Path(__file__).resolve().parent / "exports" / "share"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _split_lines(text: str, limit: int = 5) -> list[str]:
    lines = [x.strip("-• 　\t") for x in str(text or "").splitlines() if x.strip()]
    return lines[:limit]


def _latest_gossip_report_dict() -> dict | None:
    day = current_day()
    if day > 0 and not fetch_one("SELECT id FROM gossip_reports WHERE day=?", (day,)):
        generate_gossip_report(day)
    row = fetch_one("SELECT * FROM gossip_reports ORDER BY day DESC LIMIT 1")
    return dict(row) if row else None


def _town_counts() -> dict:
    def count(sql: str) -> int:
        r = fetch_one(sql)
        return int(r["c"] or 0) if r else 0
    return {
        "suspected": count("SELECT COUNT(*) AS c FROM people WHERE secret_status='suspected'"),
        "revealed": count("SELECT COUNT(*) AS c FROM people WHERE secret_status='revealed'"),
        "low_health": count("SELECT COUNT(*) AS c FROM people WHERE health<=5"),
        "low_happiness": count("SELECT COUNT(*) AS c FROM people WHERE happiness<=15"),
        "runaway": count("SELECT COUNT(*) AS c FROM people WHERE life_goal LIKE '%leave%' OR secret LIKE '%leave%'"),
    }


def get_share_room() -> dict:
    init_world()
    latest = _latest_gossip_report_dict()
    top = protagonist_candidates(5)
    counts = _town_counts()
    day = current_day()
    headline = latest["headline"] if latest else f"Day {day}: no gossip report yet"
    hot_lines = _split_lines(latest.get("hot_topics", "") if latest else "", 5)
    secret_lines = _split_lines(latest.get("secret_watch", "") if latest else "", 4)
    danger_lines = _split_lines(latest.get("danger_people", "") if latest else "", 4)
    share_text_lines = [
        f"SimWorld Gossip Engine | Day {day}",
        headline,
        "",
        f"suspected secrets: {counts['suspected']} | revealed secrets: {counts['revealed']} | health risk: {counts['low_health']} | happiness crash: {counts['low_happiness']}",
        "",
        "Hot topics: ",
    ]
    share_text_lines += [f"- {x}" for x in hot_lines[:5]] or ["- No obvious hot topic yet. Advance one day first."]
    if top:
        share_text_lines += ["", "drama source ranking: "]
        for i, p in enumerate(top[:3], 1):
            share_text_lines.append(f"{i}. {p['name']} | {p['story_score']} | {p['life_goal']} | {p['secret_status']}")
    share_text_lines += ["", "A tiny AI fishbowl: open your phone and see who is falling apart today."]
    return {
        "day": day,
        "latest": latest,
        "top": top,
        "counts": counts,
        "hot_lines": hot_lines,
        "secret_lines": secret_lines,
        "danger_lines": danger_lines,
        "share_text": "\n".join(share_text_lines),
    }


def export_share_card_markdown(output_path: str | Path | None = None) -> Path:
    data = get_share_room()
    output = Path(output_path) if output_path else _share_exports_dir() / f"share_card_day_{data['day']:04d}.md"
    lines = [
        f"# SimWorld Gossip Engine | Day {data['day']} Share Card",
        "",
        data["latest"]["headline"] if data.get("latest") else "No gossip report yet.",
        "",
        "## Town Status",
        "",
        f"- suspected secrets: {data['counts']['suspected']}",
        f"- revealed secrets: {data['counts']['revealed']}",
        f"- health risk: {data['counts']['low_health']}",
        f"- happiness crash: {data['counts']['low_happiness']}",
        "",
        "## Hot topics",
        "",
    ]
    for x in data["hot_lines"] or ["No obvious hot topic yet."]:
        lines.append(f"- {x}")
    lines += ["", "## drama source ranking", ""]
    for i, p in enumerate(data["top"][:5], 1):
        lines.append(f"{i}. **{p['name']}** | {p['story_score']} | {p['life_goal']} | Secret: {p['secret_status']}")
    lines += ["", "> A tiny AI fishbowl: open your phone and see who is falling apart today.", ""]
    output.write_text("\n".join(lines), encoding="utf-8")
    return output
