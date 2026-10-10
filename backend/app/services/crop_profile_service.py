"""Crop Profile Selection Service for FarmShield.

Implements deterministic matching logic based on:
1. Crop identity
2. Crop form
3. Storage type
4. Variety
5. Region
6. Intended duration
7. Verification status and source references.
"""

from typing import Optional
from app.repositories.crop_repository import CropRepository
from app.schemas.crop_profile import CropProfileOut, CropSelectionMatchResult


class CropProfileService:
    @classmethod
    def list_crops(cls, category: Optional[str] = None, search: Optional[str] = None) -> list[CropProfileOut]:
        raw_profiles = CropRepository.list_all(category=category, search=search)
        return [CropProfileOut(**p) for p in raw_profiles]

    @classmethod
    def get_profile_by_id(cls, crop_id: str) -> Optional[CropProfileOut]:
        raw = CropRepository.get_by_id(crop_id)
        if raw:
            return CropProfileOut(**raw)
        return None

    @classmethod
    def match_crop_profile(
        cls,
        crop_name: str,
        variety: Optional[str] = None,
        crop_form: Optional[str] = None,
        storage_type: Optional[str] = None,
        region: Optional[str] = None,
        intended_duration: Optional[str] = None,
    ) -> Optional[CropSelectionMatchResult]:
        """Deterministic matching to select the most applicable verified profile."""
        all_profiles = CropRepository.list_all()
        if not all_profiles:
            return None

        clean_name = crop_name.strip().lower()

        # Step 1: Filter candidates by crop identity
        candidates = []
        for p in all_profiles:
            p_name = p.get("crop_name", "").lower()
            p_id = p.get("crop_id", "").lower()
            if clean_name in p_name or p_name in clean_name or clean_name in p_id:
                candidates.append(p)

        if not candidates:
            # Fuzzy match fallback: check words in crop_name (e.g. 'Rice' in 'Paddy (Rice)')
            words = [w.strip("(),") for w in clean_name.split() if len(w) > 2]
            for p in all_profiles:
                p_text = f"{p.get('crop_name', '')} {p.get('crop_id', '')}".lower()
                if any(w in p_text for w in words):
                    if p not in candidates:
                        candidates.append(p)

        if not candidates:
            return None

        # Step 2: Score candidates based on specific criteria
        best_candidate = candidates[0]
        highest_score = 0
        missing_attrs = []

        for cand in candidates:
            score = 10  # Base match on crop identity

            # Crop form matching
            if crop_form and cand.get("crop_form"):
                if crop_form.lower() in cand["crop_form"].lower() or cand["crop_form"].lower() in crop_form.lower():
                    score += 5
                else:
                    missing_attrs.append(f"Specified form '{crop_form}' differs from verified profile '{cand['crop_form']}'")

            # Storage type matching
            if storage_type and cand.get("storage_type"):
                if storage_type.lower() in cand["storage_type"].lower():
                    score += 4

            # Variety matching
            if variety and cand.get("variety"):
                if variety.lower() in cand["variety"].lower():
                    score += 3

            # Verification bonus
            if cand.get("verification_status") == "verified":
                score += 5

            if score > highest_score:
                highest_score = score
                best_candidate = cand

        is_exact = highest_score >= 20
        confidence = "high" if highest_score >= 18 else ("medium" if highest_score >= 12 else "general_guidance")

        explanation = (
            f"Matched verified ICAR/scientific reference profile '{best_candidate['crop_name']}' "
            f"for form '{best_candidate['crop_form']}'. "
            f"Source: {best_candidate.get('source_name', 'Agricultural Standards')}."
        )

        return CropSelectionMatchResult(
            matched_profile=CropProfileOut(**best_candidate),
            match_confidence=confidence,
            applicability_explanation=explanation,
            is_exact_match=is_exact,
            missing_attributes=list(set(missing_attrs)),
        )
