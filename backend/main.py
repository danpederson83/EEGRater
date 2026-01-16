"""
FastAPI backend for EEG Rater application.
"""
import os
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from edf_parser import EDFParser

# Configuration
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
EDF_DIR = DATA_DIR / "edf_files"
CACHE_DIR = DATA_DIR / "cache"
RATINGS_FILE = DATA_DIR / "ratings.json"
COMPARISONS_FILE = DATA_DIR / "comparisons.json"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
EDF_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

# Initialize parser
edf_parser = EDFParser(str(EDF_DIR), str(CACHE_DIR))

# FastAPI app
app = FastAPI(title="EEG Rater API", version="1.0.0")

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


# Helper functions
def load_json_file(filepath: Path) -> list:
    """Load JSON array from file, return empty list if doesn't exist."""
    if filepath.exists():
        with open(filepath, 'r') as f:
            return json.load(f)
    return []


def save_json_file(filepath: Path, data: list):
    """Save data as JSON array to file."""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)


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
def submit_rating(submission: RatingSubmission):
    """Submit a rating for a snippet."""
    # Validate rating range
    if not 1 <= submission.rating <= 10:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 10")

    # Verify snippet exists
    if edf_parser.get_snippet_by_id(submission.snippet_id) is None:
        raise HTTPException(status_code=404, detail="Snippet not found")

    # Load existing ratings
    ratings = load_json_file(RATINGS_FILE)

    # Add new rating
    rating_entry = {
        "snippet_id": submission.snippet_id,
        "rater": submission.rater,
        "rating": submission.rating,
        "timestamp": datetime.now().isoformat()
    }
    ratings.append(rating_entry)

    # Save
    save_json_file(RATINGS_FILE, ratings)

    return {"status": "success", "rating": rating_entry}


@app.post("/api/comparisons")
def submit_comparison(submission: ComparisonSubmission):
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

    # Load existing comparisons
    comparisons = load_json_file(COMPARISONS_FILE)

    # Add new comparison
    comparison_entry = {
        "snippet_a": submission.snippet_a,
        "snippet_b": submission.snippet_b,
        "winner": submission.winner,
        "rater": submission.rater,
        "timestamp": datetime.now().isoformat()
    }
    comparisons.append(comparison_entry)

    # Save
    save_json_file(COMPARISONS_FILE, comparisons)

    return {"status": "success", "comparison": comparison_entry}


@app.get("/api/progress/{rater}")
def get_progress(rater: str):
    """Get rating progress for a specific rater."""
    all_snippets = edf_parser.get_snippet_ids()
    total_snippets = len(all_snippets)

    # Load ratings for this rater
    ratings = load_json_file(RATINGS_FILE)
    rater_ratings = [r for r in ratings if r["rater"] == rater]
    rated_snippet_ids = set(r["snippet_id"] for r in rater_ratings)

    # Load comparisons for this rater
    comparisons = load_json_file(COMPARISONS_FILE)
    rater_comparisons = [c for c in comparisons if c["rater"] == rater]

    return {
        "rater": rater,
        "total_snippets": total_snippets,
        "rated_count": len(rated_snippet_ids),
        "comparison_count": len(rater_comparisons),
        "rated_snippet_ids": list(rated_snippet_ids)
    }


@app.get("/api/unrated-snippets/{rater}")
def get_unrated_snippets(rater: str):
    """Get list of snippet IDs not yet rated by this rater."""
    all_snippet_ids = set(edf_parser.get_snippet_ids())

    ratings = load_json_file(RATINGS_FILE)
    rated_ids = set(r["snippet_id"] for r in ratings if r["rater"] == rater)

    unrated_ids = list(all_snippet_ids - rated_ids)
    return {"unrated_snippet_ids": unrated_ids, "count": len(unrated_ids)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
