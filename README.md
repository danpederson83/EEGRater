# EEG Rater

A web application for rating and comparing EEG snippets. Designed for researchers and clinicians to evaluate EEG data through two different rating modes.

## Features

### Rating Mode
- Rate individual 10-second EEG snippets on a scale of 1-10 (very abnormal to very normal)
- Track progress through all available snippets
- Navigate between snippets freely

### Sort Mode
- Pairwise comparison to rank snippets by abnormality
- Uses merge sort algorithm for efficient comparisons
- Click any ranked snippet to preview it
- Results show final ranking from most to least abnormal

## Tech Stack

- **Frontend**: React + Vite + Chart.js
- **Backend**: FastAPI + Python
- **Data Format**: EDF (European Data Format) files

## Setup

### Prerequisites
- Python 3.10+
- Node.js 18+

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
python main.py
```

The API will run at `http://localhost:8000`

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The app will run at `http://localhost:5173`

### Adding EEG Data

Place your EDF files in the `data/edf_files/` directory. The backend will automatically parse them into 10-second snippets on startup.

## Project Structure

```
EEGRater/
├── backend/
│   ├── main.py           # FastAPI application
│   ├── edf_parser.py     # Custom EDF file parser
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── EEGViewer.jsx    # Chart.js EEG visualization
│   │   │   ├── RatingMode.jsx   # Individual rating interface
│   │   │   ├── SortMode.jsx     # Pairwise comparison interface
│   │   │   └── ...
│   │   └── ...
│   └── package.json
└── data/
    ├── edf_files/        # Place EDF files here
    ├── cache/            # Parsed snippet cache
    ├── ratings.json      # Stored ratings
    └── comparisons.json  # Stored comparisons
```

## License

MIT
