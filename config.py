# =============================
# File: config.py
# =============================

# Toggle to bypass the login screen for development.
DEVELOPMENT_MODE = True

# --- Business Logic Constants ---

# Skill level thresholds
EXPERT_THRESHOLD = 0.8
BEGINNER_THRESHOLD = 0.4
PIPELINE_MIN = 0.6
PIPELINE_MAX = 0.79
HIDDEN_STAR_THRESHOLD = 0.9

# Risk & Opportunity thresholds
CRITICAL_AVG_SCORE = 0.6
OPPORTUNITY_AVG_SCORE = 0.75
HIGH_RISK_INDEX = 2.0

# License expiration window (in days)
LICENSE_EXPIRATION_WINDOW_DAYS = 90

# Archetype Emojis (cleaned up)
ARCHETYPE_NEEDS_SUPPORT = "🎯 Needs Support"
ARCHETYPE_VERSATILE_LEADER = "🏆 Versatile Leader"
ARCHETYPE_NICHE_SPECIALIST = "🌟 Niche Specialist"
ARCHETYPE_CONSISTENT_LEARNER = "🌱 Consistent Learner"