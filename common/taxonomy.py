"""Concern taxonomy v0 (CLAUDE.md §6.5) — project-wide shared vocabulary.

Two apps validate against these keys: concerns.Concern.concern_type (choices)
and advisors.AdvisorApplication.advisable_concern_types (array elements).
It lives in common/ so advisors does not import from concerns, keeping the
app-by-app migration order of model.md §7.1 free of cross-app imports.

Do not add values without Owner approval (CLAUDE.md §6.5).
"""

from django.db import models


class ConcernType(models.TextChoices):
    CAREER_TRANSITION = "career_transition", "경력 전환"
    JOB_CHANGE = "job_change", "직종 전환"
    BURNOUT = "burnout", "번아웃"
    STARTUP_FAILURE = "startup_failure", "사업 실패"
    LEADERSHIP = "leadership", "리더십"
    RELATIONSHIP = "relationship", "관계"
    LIFE_DIRECTION = "life_direction", "인생 방향성(설계)"
    MAJOR_LIFE_DECISION = "major_life_decision", "인생의 중요한 의사결정"
    EDUCATION_CHOICE = "education_choice", "학업 선택"
    RELOCATION = "relocation", "이사"
    FINANCE_MAJOR_DECISION = "finance_major_decision", "중요한 재무 의사결정"
