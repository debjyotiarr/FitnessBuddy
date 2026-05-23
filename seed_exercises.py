#!/usr/bin/env python3
"""Seed the exercise library. Run once before deploying.

    SUPABASE_URL=<url> SUPABASE_KEY=<key> python seed_exercises.py
"""
import os
from supabase import create_client

client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

EXERCISES = [
    # Back
    {"name": "Lat Pulldown",        "muscle_group": "Back",      "category": "compound"},
    {"name": "Cable Row",           "muscle_group": "Back",      "category": "compound"},
    {"name": "Barbell Row",         "muscle_group": "Back",      "category": "compound"},
    {"name": "Pull-ups",            "muscle_group": "Back",      "category": "compound"},
    {"name": "Face Pulls",          "muscle_group": "Back",      "category": "isolation"},
    {"name": "Deadlift",            "muscle_group": "Back",      "category": "compound"},
    {"name": "Single Arm DB Row",   "muscle_group": "Back",      "category": "compound"},
    # Chest
    {"name": "Bench Press",         "muscle_group": "Chest",     "category": "compound"},
    {"name": "Incline DB Press",    "muscle_group": "Chest",     "category": "compound"},
    {"name": "Cable Fly",           "muscle_group": "Chest",     "category": "isolation"},
    {"name": "Dips",                "muscle_group": "Chest",     "category": "compound"},
    {"name": "Pec Deck",            "muscle_group": "Chest",     "category": "isolation"},
    # Shoulders
    {"name": "Overhead Press",      "muscle_group": "Shoulders", "category": "compound"},
    {"name": "Lateral Raises",      "muscle_group": "Shoulders", "category": "isolation"},
    {"name": "Rear Delt Fly",       "muscle_group": "Shoulders", "category": "isolation"},
    {"name": "Cable Lateral Raise", "muscle_group": "Shoulders", "category": "isolation"},
    # Arms
    {"name": "Bicep Curl",          "muscle_group": "Arms",      "category": "isolation"},
    {"name": "Hammer Curl",         "muscle_group": "Arms",      "category": "isolation"},
    {"name": "Preacher Curl",       "muscle_group": "Arms",      "category": "isolation"},
    {"name": "Tricep Pushdown",     "muscle_group": "Arms",      "category": "isolation"},
    {"name": "Skull Crusher",       "muscle_group": "Arms",      "category": "isolation"},
    {"name": "Overhead Tricep Ext", "muscle_group": "Arms",      "category": "isolation"},
    # Legs
    {"name": "Squat",               "muscle_group": "Legs",      "category": "compound"},
    {"name": "Romanian Deadlift",   "muscle_group": "Legs",      "category": "compound"},
    {"name": "Leg Press",           "muscle_group": "Legs",      "category": "compound"},
    {"name": "Leg Curl",            "muscle_group": "Legs",      "category": "isolation"},
    {"name": "Leg Extension",       "muscle_group": "Legs",      "category": "isolation"},
    {"name": "Calf Raise",          "muscle_group": "Legs",      "category": "isolation"},
    {"name": "Hip Thrust",          "muscle_group": "Legs",      "category": "compound"},
    {"name": "Bulgarian Split Squat","muscle_group": "Legs",     "category": "compound"},
    # Core
    {"name": "Plank",               "muscle_group": "Core",      "category": "isolation"},
    {"name": "Cable Crunch",        "muscle_group": "Core",      "category": "isolation"},
    {"name": "Hanging Leg Raise",   "muscle_group": "Core",      "category": "isolation"},
    {"name": "Ab Wheel Rollout",    "muscle_group": "Core",      "category": "compound"},
]

result = client.table("exercises").upsert(EXERCISES, on_conflict="name").execute()
print(f"Seeded {len(result.data)} exercises.")
