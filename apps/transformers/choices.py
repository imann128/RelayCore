"""
TRANSFORMER_CHOICES is imported by apps/core/models.py (the Route model).

It is intentionally a plain list — no imports from registry.py or from
any transformer class. This breaks the circular import chain:
  models.py → choices.py  (safe: no further imports)
  models.py ← registry.py (registry imports models, not the other way)

Adding a new transformer requires ONE line here + ONE line in registry.py.
"""

TRANSFORMER_CHOICES = [
    ('github_to_slack',   'GitHub → Slack'),
    ('github_to_discord', 'GitHub → Discord'),
    ('calendar_to_db',    'Google Calendar → Database'),
    ('form_to_email',     'HTML Form → Email'),
    ('passthrough',       'Passthrough (no transform)'),
]
