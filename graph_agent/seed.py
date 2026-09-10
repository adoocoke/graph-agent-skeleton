"""Seed the in-memory survivor graph with demo data."""

from __future__ import annotations

from .graph import SurvivorGraph


def build_seed_graph() -> SurvivorGraph:
    g = SurvivorGraph()

    # --- Biomes ---
    g.add_node(
        "biome:mountains",
        "Biome",
        name="Mountains",
        region="northern ridge",
        description="High altitude rocky terrain, cold, FOSSILIZED ruins nearby",
        keywords="mountain alpine ridge high altitude fossilized",
    )
    g.add_node(
        "biome:fossilized",
        "Biome",
        name="FOSSILIZED",
        region="ancient basin",
        description="Petrified forest and fossil beds; sparse shelter, mineral dust",
        keywords="fossilized petrified fossils ancient ruins",
    )
    g.add_node(
        "biome:wetlands",
        "Biome",
        name="Wetlands",
        region="southern marsh",
        description="Humid marsh with insect hazards and soft ground",
        keywords="wetland marsh swamp humidity",
    )
    g.add_node(
        "biome:coast",
        "Biome",
        name="Coast",
        region="eastern shore",
        description="Rocky coastline with salvageable wreckage",
        keywords="coast shore beach salvage",
    )

    # --- Skills ---
    g.add_node(
        "skill:medical_training",
        "Skill",
        name="Medical Training",
        description="Advanced clinical care: trauma, burns, infection, triage",
        keywords="doctor medicine clinical trauma surgery burns healing injuries",
        aliases="MD medicine doctor",
    )
    g.add_node(
        "skill:first_aid",
        "Skill",
        name="First Aid",
        description="Basic field first aid for cuts, burns, fractures, bleeding",
        keywords="first aid bandages burns cuts wounds injuries healing emergency",
        aliases="basic aid EMT helper",
    )
    g.add_node(
        "skill:herbalism",
        "Skill",
        name="Herbalism",
        description="Plant-based remedies for burns, fever, and mild infection",
        keywords="herbs plants salve burns fever healing natural medicine",
        aliases="plant medicine remedies",
    )
    g.add_node(
        "skill:mountaineering",
        "Skill",
        name="Mountaineering",
        description="Navigation, rope work, and survival in mountain terrain",
        keywords="climbing rope alpine navigation mountain rescue",
        aliases="alpinism climbing",
    )
    g.add_node(
        "skill:scavenging",
        "Skill",
        name="Scavenging",
        description="Finding salvage, fuel, and medical supplies in ruins",
        keywords="scavenge salvage loot supplies fossils ruins",
        aliases="foraging salvage",
    )

    # --- Needs ---
    g.add_node(
        "need:burns",
        "Need",
        name="Burns",
        description="Urgent thermal or chemical burn injuries requiring dressing and care",
        urgency="critical",
        keywords="burns blister scald fire healing injuries wound",
    )
    g.add_node(
        "need:bleeding",
        "Need",
        name="Bleeding",
        description="Active hemorrhage or deep lacerations",
        urgency="critical",
        keywords="bleeding hemorrhage cut laceration injuries wound",
    )
    g.add_node(
        "need:fracture",
        "Need",
        name="Fracture",
        description="Suspected broken bone needing splint and immobilization",
        urgency="high",
        keywords="fracture broken bone splint injury",
    )
    g.add_node(
        "need:infection",
        "Need",
        name="Infection",
        description="Wound infection with fever risk",
        urgency="high",
        keywords="infection fever sepsis wound healing medicine",
    )
    g.add_node(
        "need:hypothermia",
        "Need",
        name="Hypothermia",
        description="Dangerous cold exposure in alpine biomes",
        urgency="high",
        keywords="cold hypothermia frost mountain alpine",
    )
    g.add_node(
        "need:supplies",
        "Need",
        name="Medical Supplies",
        description="Shortage of bandages, antiseptic, and burn ointment",
        urgency="medium",
        keywords="supplies bandage antiseptic ointment medicine",
    )

    # --- Survivors ---
    g.add_node(
        "survivor:elena",
        "Survivor",
        name="Dr. Elena Frost",
        role="field physician",
        description="Experienced doctor specializing in trauma and burn care",
        keywords="doctor elena frost medical healing injuries",
    )
    g.add_node(
        "survivor:kai",
        "Survivor",
        name="Kai Rivera",
        role="scout medic",
        description="Former EMT with solid first aid skills",
        keywords="kai first aid injuries helper",
    )
    g.add_node(
        "survivor:mira",
        "Survivor",
        name="Mira Chen",
        role="herbalist",
        description="Knows alpine flora and burn salves",
        keywords="mira herbs healing plants",
    )
    g.add_node(
        "survivor:jon",
        "Survivor",
        name="Jon Hale",
        role="mountain guide",
        description="Lives among the FOSSILIZED ridges; strong climber",
        keywords="jon mountain fossilized guide rescue",
    )
    g.add_node(
        "survivor:sam",
        "Survivor",
        name="Sam Okonkwo",
        role="salvager",
        description="Coastal scavenger who finds medical kits",
        keywords="sam scavenge supplies coast",
    )
    g.add_node(
        "survivor:rio",
        "Survivor",
        name="Rio Patel",
        role="patient",
        description="Injured survivor with urgent burn wounds in the mountains",
        keywords="rio patient burns injured mountain",
    )

    # --- Edges: skills ---
    g.add_edge("survivor:elena", "has_skill", "skill:medical_training")
    g.add_edge("survivor:elena", "has_skill", "skill:first_aid")
    g.add_edge("survivor:kai", "has_skill", "skill:first_aid")
    g.add_edge("survivor:mira", "has_skill", "skill:herbalism")
    g.add_edge("survivor:mira", "has_skill", "skill:first_aid")
    g.add_edge("survivor:jon", "has_skill", "skill:mountaineering")
    g.add_edge("survivor:jon", "has_skill", "skill:first_aid")
    g.add_edge("survivor:sam", "has_skill", "skill:scavenging")

    # --- Edges: biomes ---
    g.add_edge("survivor:elena", "in_biome", "biome:wetlands")
    g.add_edge("survivor:kai", "in_biome", "biome:coast")
    g.add_edge("survivor:mira", "in_biome", "biome:mountains")
    g.add_edge("survivor:jon", "in_biome", "biome:mountains")
    g.add_edge("survivor:jon", "in_biome", "biome:fossilized")
    g.add_edge("survivor:sam", "in_biome", "biome:coast")
    g.add_edge("survivor:rio", "in_biome", "biome:mountains")
    g.add_edge("survivor:rio", "in_biome", "biome:fossilized")

    # --- Edges: needs (who needs help) ---
    g.add_edge("survivor:rio", "has_need", "need:burns", urgency="critical")
    g.add_edge("survivor:rio", "has_need", "need:hypothermia", urgency="high")
    g.add_edge("survivor:kai", "has_need", "need:supplies", urgency="medium")

    # --- Edges: skill treats need ---
    g.add_edge("skill:medical_training", "skill_treats_need", "need:burns")
    g.add_edge("skill:medical_training", "skill_treats_need", "need:bleeding")
    g.add_edge("skill:medical_training", "skill_treats_need", "need:fracture")
    g.add_edge("skill:medical_training", "skill_treats_need", "need:infection")
    g.add_edge("skill:first_aid", "skill_treats_need", "need:burns")
    g.add_edge("skill:first_aid", "skill_treats_need", "need:bleeding")
    g.add_edge("skill:first_aid", "skill_treats_need", "need:fracture")
    g.add_edge("skill:herbalism", "skill_treats_need", "need:burns")
    g.add_edge("skill:herbalism", "skill_treats_need", "need:infection")
    g.add_edge("skill:mountaineering", "skill_treats_need", "need:hypothermia")
    g.add_edge("skill:scavenging", "skill_treats_need", "need:supplies")

    return g
