import { useState, useEffect } from 'react'
import axios from 'axios'
import EEGViewer from './EEGViewer'

function RatingMode({ rater }) {
  const [snippets, setSnippets] = useState([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [currentSnippet, setCurrentSnippet] = useState(null)
  const [selectedRating, setSelectedRating] = useState(null)
  const [ratedSnippets, setRatedSnippets] = useState(new Set())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  // Load snippet list and progress on mount
  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true)

        // Get list of snippets
        const snippetsRes = await axios.get('/api/snippets')
        const snippetList = snippetsRes.data.snippets || []
        setSnippets(snippetList)

        // Get progress for this rater
        const progressRes = await axios.get(`/api/progress/${encodeURIComponent(rater)}`)
        const ratedIds = new Set(progressRes.data.rated_snippet_ids || [])
        setRatedSnippets(ratedIds)

        // Find first unrated snippet
        const unratedIndex = snippetList.findIndex(s => !ratedIds.has(s.id))
        if (unratedIndex >= 0) {
          setCurrentIndex(unratedIndex)
        }

        setLoading(false)
      } catch (err) {
        console.error('Error loading data:', err)
        setError('Failed to load snippets. Is the backend running?')
        setLoading(false)
      }
    }
    loadData()
  }, [rater])

  // Load current snippet data when index changes
  useEffect(() => {
    async function loadSnippet() {
      if (snippets.length === 0 || currentIndex >= snippets.length) {
        setCurrentSnippet(null)
        return
      }

      const snippetId = snippets[currentIndex].id
      try {
        const res = await axios.get(`/api/snippets/${snippetId}`)
        setCurrentSnippet(res.data)
        // Reset rating selection if this snippet was already rated
        if (ratedSnippets.has(snippetId)) {
          setSelectedRating(null) // Could load previous rating here
        } else {
          setSelectedRating(null)
        }
      } catch (err) {
        console.error('Error loading snippet:', err)
        setCurrentSnippet(null)
      }
    }
    loadSnippet()
  }, [currentIndex, snippets])

  const handleRatingSelect = (rating) => {
    setSelectedRating(rating)
  }

  const handleSubmitRating = async () => {
    if (!selectedRating || !currentSnippet) return

    setSubmitting(true)
    try {
      await axios.post('/api/ratings', {
        snippet_id: currentSnippet.id,
        rater: rater,
        rating: selectedRating
      })

      // Update local state
      setRatedSnippets(prev => new Set([...prev, currentSnippet.id]))

      // Move to next snippet
      if (currentIndex < snippets.length - 1) {
        setCurrentIndex(currentIndex + 1)
      }
      setSelectedRating(null)
    } catch (err) {
      console.error('Error submitting rating:', err)
      alert('Failed to submit rating. Please try again.')
    }
    setSubmitting(false)
  }

  const handlePrevious = () => {
    if (currentIndex > 0) {
      setCurrentIndex(currentIndex - 1)
    }
  }

  const handleNext = () => {
    if (currentIndex < snippets.length - 1) {
      setCurrentIndex(currentIndex + 1)
    }
  }

  const handleSkip = () => {
    handleNext()
  }

  if (loading) {
    return <div className="loading">Loading snippets...</div>
  }

  if (error) {
    return (
      <div className="error-message">
        <h3>Error</h3>
        <p>{error}</p>
      </div>
    )
  }

  if (snippets.length === 0) {
    return (
      <div className="no-data">
        <h3>No EEG Snippets Available</h3>
        <p>Place EDF files in the data/edf_files directory and restart the backend.</p>
      </div>
    )
  }

  const progress = ratedSnippets.size
  const total = snippets.length
  const progressPercent = total > 0 ? (progress / total) * 100 : 0
  const isCurrentRated = currentSnippet && ratedSnippets.has(currentSnippet.id)

  return (
    <div className="rating-mode">
      <div className="progress-bar">
        <span className="progress-text">{progress} / {total} rated</span>
        <div className="progress-fill-container">
          <div
            className="progress-fill"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <span className="progress-text">{progressPercent.toFixed(0)}%</span>
      </div>

      <EEGViewer
        snippet={currentSnippet}
        title={currentSnippet ? `Snippet: ${currentSnippet.id} (${currentIndex + 1} of ${total})` : 'Loading...'}
      />

      <div className="rating-controls">
        <div className="rating-label">
          Rate this EEG snippet (1 = very abnormal, 10 = very normal)
          {isCurrentRated && <span style={{color: '#27ae60', marginLeft: '10px'}}>(Already rated)</span>}
        </div>

        <div className="rating-buttons">
          {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(rating => (
            <button
              key={rating}
              className={`rating-btn ${selectedRating === rating ? 'selected' : ''}`}
              onClick={() => handleRatingSelect(rating)}
            >
              {rating}
            </button>
          ))}
        </div>

        <div className="navigation-buttons">
          <button
            className="nav-btn prev"
            onClick={handlePrevious}
            disabled={currentIndex === 0}
          >
            Previous
          </button>

          <button
            className="nav-btn skip"
            onClick={handleSkip}
            disabled={currentIndex >= snippets.length - 1}
          >
            Skip
          </button>

          <button
            className="nav-btn next"
            onClick={handleSubmitRating}
            disabled={!selectedRating || submitting}
          >
            {submitting ? 'Submitting...' : 'Submit & Next'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default RatingMode
