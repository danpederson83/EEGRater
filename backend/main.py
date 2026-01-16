"""
FastAPI backend for EEG Rater application.
"""
import os
import random
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.edf_parser import EDFParser
from backend.database import init_db, get_db, Rating, Comparison

# Configuration
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
EDF_DIR = DATA_DIR / "edf_files"
CACHE_DIR = DATA_DIR / "cache"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
EDF_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

# Initialize parser
edf_parser = EDFParser(str(EDF_DIR), str(CACHE_DIR))

# FastAPI app
app = FastAPI(title="EEG Rater API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Initialize database on startup
@app.on_event("startup")
def startup_event():
    init_db()


# Pydantic models
class RatingSubmission(BaseModel):
    snippet_id: str
    rater: str
    rating: int  # 1-10


class ComparisonSubmission(BaseModel):
    snippet_a: str
    snippet_b: str
    winner: str  # snippet_a id, snippet_b id, or "tie"
    rater: str


class SnippetSummary(BaseModel):
    id: str
    source_file: str
    start_time: float
    duration: float


# API Endpoints
@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.get("/api/snippets")
def list_snippets():
    """List all available snippets (metadata only, not full data)."""
    snippets = edf_parser.get_all_snippets()
    summaries = [
        {
            "id": s["id"],
            "source_file": s["source_file"],
            "start_time": s["start_time"],
            "duration": s["duration"],
            "n_channels": len(s["channels"])
        }
        for s in snippets
    ]
    return {"snippets": summaries, "total": len(summaries)}


@app.get("/api/snippets/{snippet_id}")
def get_snippet(snippet_id: str):
    """Get full data for a specific snippet."""
    snippet = edf_parser.get_snippet_by_id(snippet_id)
    if snippet is None:
        raise HTTPException(status_code=404, detail="Snippet not found")
    return snippet


@app.get("/api/snippets-random-pair")
def get_random_pair():
    """Get two random snippets for comparison mode."""
    snippet_ids = edf_parser.get_snippet_ids()

    if len(snippet_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="Need at least 2 snippets for comparison"
        )

    # Select two random different snippets
    pair = random.sample(snippet_ids, 2)
    snippet_a = edf_parser.get_snippet_by_id(pair[0])
    snippet_b = edf_parser.get_snippet_by_id(pair[1])

    return {"snippet_a": snippet_a, "snippet_b": snippet_b}


@app.post("/api/ratings")
def submit_rating(submission: RatingSubmission, db: Session = Depends(get_db)):
    """Submit a rating for a snippet."""
    # Validate rating range
    if not 1 <= submission.rating <= 10:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 10")

    # Verify snippet exists
    if edf_parser.get_snippet_by_id(submission.snippet_id) is None:
        raise HTTPException(status_code=404, detail="Snippet not found")

    # Create rating record
    rating = Rating(
        snippet_id=submission.snippet_id,
        rater=submission.rater,
        rating=submission.rating
    )
    db.add(rating)
    db.commit()
    db.refresh(rating)

    return {
        "status": "success",
        "rating": {
            "snippet_id": rating.snippet_id,
            "rater": rating.rater,
            "rating": rating.rating,
            "timestamp": rating.timestamp.isoformat()
        }
    }


@app.post("/api/comparisons")
def submit_comparison(submission: ComparisonSubmission, db: Session = Depends(get_db)):
    """Submit a comparison result."""
    # Validate winner
    valid_winners = [submission.snippet_a, submission.snippet_b, "tie"]
    if submission.winner not in valid_winners:
        raise HTTPException(status_code=400, detail="Invalid winner value")

    # Verify snippets exist
    if edf_parser.get_snippet_by_id(submission.snippet_a) is None:
        raise HTTPException(status_code=404, detail="Snippet A not found")
    if edf_parser.get_snippet_by_id(submission.snippet_b) is None:
        raise HTTPException(status_code=404, detail="Snippet B not found")

    # Create comparison record
    comparison = Comparison(
        snippet_a=submission.snippet_a,
        snippet_b=submission.snippet_b,
        winner=submission.winner,
        rater=submission.rater
    )
    db.add(comparison)
    db.commit()
    db.refresh(comparison)

    return {
        "status": "success",
        "comparison": {
            "snippet_a": comparison.snippet_a,
            "snippet_b": comparison.snippet_b,
            "winner": comparison.winner,
            "rater": comparison.rater,
            "timestamp": comparison.timestamp.isoformat()
        }
    }


@app.get("/api/progress/{rater}")
def get_progress(rater: str, db: Session = Depends(get_db)):
    """Get rating progress for a specific rater."""
    all_snippets = edf_parser.get_snippet_ids()
    total_snippets = len(all_snippets)

    # Get ratings for this rater
    ratings = db.query(Rating).filter(Rating.rater == rater).all()
    rated_snippet_ids = set(r.snippet_id for r in ratings)

    # Get comparisons for this rater
    comparison_count = db.query(Comparison).filter(Comparison.rater == rater).count()

    return {
        "rater": rater,
        "total_snippets": total_snippets,
        "rated_count": len(rated_snippet_ids),
        "comparison_count": comparison_count,
        "rated_snippet_ids": list(rated_snippet_ids)
    }


@app.get("/api/unrated-snippets/{rater}")
def get_unrated_snippets(rater: str, db: Session = Depends(get_db)):
    """Get list of snippet IDs not yet rated by this rater."""
    all_snippet_ids = set(edf_parser.get_snippet_ids())

    ratings = db.query(Rating).filter(Rating.rater == rater).all()
    rated_ids = set(r.snippet_id for r in ratings)

    unrated_ids = list(all_snippet_ids - rated_ids)
    return {"unrated_snippet_ids": unrated_ids, "count": len(unrated_ids)}


@app.get("/api/ratings")
def get_all_ratings(db: Session = Depends(get_db)):
    """Get all ratings (for analysis)."""
    ratings = db.query(Rating).all()
    return {
        "ratings": [
            {
                "id": r.id,
                "snippet_id": r.snippet_id,
                "rater": r.rater,
                "rating": r.rating,
                "timestamp": r.timestamp.isoformat()
            }
            for r in ratings
        ],
        "total": len(ratings)
    }


@app.get("/api/comparisons")
def get_all_comparisons(db: Session = Depends(get_db)):
    """Get all comparisons (for analysis)."""
    comparisons = db.query(Comparison).all()
    return {
        "comparisons": [
            {
                "id": c.id,
                "snippet_a": c.snippet_a,
                "snippet_b": c.snippet_b,
                "winner": c.winner,
                "rater": c.rater,
                "timestamp": c.timestamp.isoformat()
            }
            for c in comparisons
        ],
        "total": len(comparisons)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
