from fastapi import APIRouter
from fastapi import HTTPException
from pydantic import BaseModel, Field, ConfigDict

from app.config import TOP_K_DISEASES_DEFAULT, MEDIPOWER_DEMO_PRESETS_ONLY
from app.utils.demo_guard import is_public_demo_request
from app.services.disease_service import DiseaseService
from app.services.recommendation_service import RecommendationService
from app.utils.geocoding import geocode_location

router = APIRouter()

_disease_service: DiseaseService | None = None
_recommendation_service: RecommendationService | None = None
_NO_MATCH_MESSAGE = "No suitable information-retrieval match found. This is not a diagnosis or clinical triage."


def get_disease_service() -> DiseaseService:
    global _disease_service
    if _disease_service is None:
        _disease_service = DiseaseService()
    return _disease_service


def get_recommendation_service() -> RecommendationService:
    global _recommendation_service
    if _recommendation_service is None:
        _recommendation_service = RecommendationService()
    return _recommendation_service


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(..., min_length=3, max_length=2000)
    location: str | None = Field(default=None, max_length=160)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    top_k: int = Field(default=TOP_K_DISEASES_DEFAULT, ge=1, le=20)


@router.post("/predict")
def predict(payload: PredictRequest) -> dict:
    # Enforce the public sample-only demo on the FastAPI origin itself.
    # The Next.js frontend restriction cannot protect a directly accessed API.
    if MEDIPOWER_DEMO_PRESETS_ONLY and not is_public_demo_request(
        payload.text, payload.location, payload.top_k, payload.lat, payload.lon
    ):
        raise HTTPException(status_code=403, detail="Public research preview accepts fictional demo scenarios only.")

    disease_service = get_disease_service()
    recommendation_service = get_recommendation_service()

    resolved = None
    if payload.location:
        resolved = geocode_location(payload.location)
        if resolved is None:
            raise HTTPException(
                status_code=400,
                detail="Could not resolve location text. Try a clearer city or address.",
            )

    if resolved is not None:
        lat, lon = float(resolved["lat"]), float(resolved["lon"])
    elif payload.lat is not None and payload.lon is not None:
        lat, lon = float(payload.lat), float(payload.lon)
    else:
        raise HTTPException(
            status_code=422,
            detail="Provide either `location` text or both `lat` and `lon`.",
        )

    diseases = disease_service.get_diseases(payload.text, top_k=payload.top_k)
    message = ""
    recommendations_by_disease: dict[str, list[dict]] = {}
    if not diseases:
        recommendations = []
        message = _NO_MATCH_MESSAGE
    else:
        for disease in diseases:
            disease_name = str(disease.get("disease_name") or disease.get("Disease") or "Unknown")
            recommendations_by_disease[disease_name] = recommendation_service.recommend(
                diseases=[disease],
                user_location=(lat, lon),
                top_k=payload.top_k,
            )

        # Backward-compatible field for clients expecting a flat list.
        first_name = str(diseases[0].get("disease_name") or diseases[0].get("Disease") or "Unknown")
        recommendations = recommendations_by_disease.get(first_name, [])

    if message.lower().startswith("no reliable no reliable"):
        message = _NO_MATCH_MESSAGE

    return {
        "diseases": diseases,
        "recommendations": recommendations,
        "recommendations_by_disease": recommendations_by_disease,
        "retrieval_mode": disease_service.get_mode(),
        "resolved_location": resolved or {"lat": lat, "lon": lon, "source": "direct_coordinates"},
        "message": message,
        "research_use_only": True,
        "ranking_score_notice": "Scores are retrieval heuristics, not medical probabilities or clinical advice.",
    }
