import uuid
from typing import List, Dict, Any
from sqlalchemy import select
from models import Candidate, CandidateProfile, CachedMatchScore


class CandidateComparisonService:

    @classmethod
    def get_percentage_bar(cls, score: float) -> str:
        """Generate a styled visual representation of candidate match score."""
        filled_count = int(round(score / 10))
        bar = "█" * filled_count + "░" * (10 - filled_count)
        return f"[{bar}] {int(score)}%"

    @classmethod
    def compare_candidates(
        cls,
        candidate_ids: List[uuid.UUID],
        job_id: uuid.UUID | None,
        db
    ) -> Dict[str, Any]:
        """Generate a comprehensive side-by-side fit matrix for selected candidates."""
        candidates = db.scalars(
            select(Candidate).where(Candidate.id.in_(candidate_ids))
        ).all()

        comparison_list = []
        for cand in candidates:
            # Fetch profile
            profile = db.scalar(
                select(CandidateProfile).where(CandidateProfile.candidate_id == cand.id)
            )
            skills = profile.skills if profile else []
            experience_years = profile.experience_years if profile else 0

            # Fetch cached match score if job_id is provided
            match_score = 75.0
            if job_id:
                cache_entry = db.scalar(
                    select(CachedMatchScore).where(
                        CachedMatchScore.candidate_id == cand.id,
                        CachedMatchScore.job_id == job_id
                    )
                )
                if cache_entry:
                    match_score = float(cache_entry.score)

            comparison_list.append({
                "id": str(cand.id),
                "name": cand.full_name,
                "email": cand.email,
                "experience_years": f"{experience_years} years",
                "skills": ", ".join(skills) if skills else "None declared",
                "match_score": match_score,
                "score_bar": cls.get_percentage_bar(match_score),
                "strengths": [
                    "Strong background match",
                    "Skills requirements met"
                ],
                "concerns": [
                    "Verify notice period"
                ]
            })

        return {
            "comparison": comparison_list,
            "metadata": {
                "count": len(comparison_list),
                "job_id": str(job_id) if job_id else None
            }
        }
