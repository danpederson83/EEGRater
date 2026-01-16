import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import EEGViewer from './EEGViewer'

// Merge sort implementation that yields pairs for comparison
class InteractiveMergeSort {
  constructor(items) {
    this.items = [...items]
    this.n = items.length
    // Estimated comparisons for merge sort: n * ceil(log2(n))
    this.estimatedComparisons = Math.ceil(this.n * Math.log2(this.n))
    this.comparisonsMade = 0
    this.comparisonCache = new Map() // Cache comparison results
    this.sorted = false
    this.result = null
  }

  // Get cache key for a pair
  getCacheKey(a, b) {
    return `${a.id}:${b.id}`
  }

  // Check if we have a cached comparison
  hasComparison(a, b) {
    return this.comparisonCache.has(this.getCacheKey(a, b)) ||
           this.comparisonCache.has(this.getCacheKey(b, a))
  }

  // Get cached comparison result (1 if a > b, -1 if a < b)
  getComparison(a, b) {
    if (this.comparisonCache.has(this.getCacheKey(a, b))) {
      return this.comparisonCache.get(this.getCacheKey(a, b))
    }
    if (this.comparisonCache.has(this.getCacheKey(b, a))) {
      return -this.comparisonCache.get(this.getCacheKey(b, a))
    }
    return null
  }

  // Record a comparison result (1 if a is more abnormal, -1 if b is more abnormal)
  recordComparison(a, b, result) {
    this.comparisonCache.set(this.getCacheKey(a, b), result)
    this.comparisonseMade++
  }

  // Get progress as percentage
  getProgress() {
    if (this.sorted) return 100
    return Math.min(99, Math.round((this.comparisonseMade / this.estimatedComparisons) * 100))
  }

  // Perform merge sort and return next needed comparison or final result
  async sort(getComparison) {
    const merge = async (left, right) => {
      const result = []
      let i = 0, j = 0

      while (i < left.length && j < right.length) {
        const cmp = await getComparison(left[i], right[j])
        if (cmp >= 0) {
          // left[i] is more abnormal or equal, put it first (descending order)
          result.push(left[i])
          i++
        } else {
          result.push(right[j])
          j++
        }
      }

      return [...result, ...left.slice(i), ...right.slice(j)]
    }

    const mergeSort = async (arr) => {
      if (arr.length <= 1) return arr

      const mid = Math.floor(arr.length / 2)
      const left = await mergeSort(arr.slice(0, mid))
      const right = await mergeSort(arr.slice(mid))

      return merge(left, right)
    }

    this.result = await mergeSort(this.items)
    this.sorted = true
    return this.result
  }
}

function SortMode({ rater }) {
  const [allSnippets, setAllSnippets] = useState([])
  const [selectedSnippets, setSelectedSnippets] = useState([])
  const [snippetA, setSnippetA] = useState(null)
  const [snippetB, setSnippetB] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  // Sorting state
  const [sorter, setSorter] = useState(null)
  const [comparisonResolver, setComparisonResolver] = useState(null)
  const [comparisonsCount, setComparisonsCount] = useState(0)
  const [estimatedTotal, setEstimatedTotal] = useState(0)
  const [sortComplete, setSortComplete] = useState(false)
  const [finalRanking, setFinalRanking] = useState([])

  // Load all snippets on mount
  useEffect(() => {
    async function loadSnippets() {
      try {
        setLoading(true)
        const res = await axios.get('/api/snippets')
        const snippetList = res.data.snippets || []
        setAllSnippets(snippetList)

        if (snippetList.length < 2) {
          setError('Need at least 2 snippets for comparison mode.')
          setLoading(false)
          return
        }

        // Select 10 random snippets (or all if less than 10)
        const count = Math.min(10, snippetList.length)
        const shuffled = [...snippetList].sort(() => Math.random() - 0.5)
        const selected = shuffled.slice(0, count)

        // Load full data for selected snippets
        const fullSnippets = await Promise.all(
          selected.map(s => axios.get(`/api/snippets/${s.id}`).then(r => r.data))
        )

        setSelectedSnippets(fullSnippets)
        setLoading(false)
      } catch (err) {
        console.error('Error loading snippets:', err)
        setError('Failed to load snippets. Is the backend running?')
        setLoading(false)
      }
    }
    loadSnippets()
  }, [rater])

  // Start sorting when snippets are loaded
  useEffect(() => {
    if (selectedSnippets.length < 2) return

    const newSorter = new InteractiveMergeSort(selectedSnippets)
    setSorter(newSorter)
    setEstimatedTotal(newSorter.estimatedComparisons)
    setComparisonsCount(0)
    setSortComplete(false)
    setFinalRanking([])

    // Start the sorting process
    const runSort = async () => {
      try {
        const result = await newSorter.sort((a, b) => {
          return new Promise((resolve) => {
            setSnippetA(a)
            setSnippetB(b)
            setComparisonResolver(() => resolve)
          })
        })

        setSortComplete(true)
        setFinalRanking(result)
        setSnippetA(null)
        setSnippetB(null)
      } catch (err) {
        console.error('Sorting error:', err)
      }
    }

    runSort()
  }, [selectedSnippets])

  const handleChoice = async (choice) => {
    if (!comparisonResolver || !snippetA || !snippetB) return

    setSubmitting(true)

    // Determine winner based on choice
    // choice: 'left' means A is more abnormal, 'right' means B is more abnormal
    let result
    let winnerValue

    if (choice === 'left') {
      result = 1 // A is more abnormal
      winnerValue = snippetA.id
    } else if (choice === 'right') {
      result = -1 // B is more abnormal
      winnerValue = snippetB.id
    } else {
      result = 0 // Tie
      winnerValue = 'tie'
    }

    // Save comparison to backend
    try {
      await axios.post('/api/comparisons', {
        snippet_a: snippetA.id,
        snippet_b: snippetB.id,
        winner: winnerValue,
        rater: rater
      })
    } catch (err) {
      console.error('Error saving comparison:', err)
    }

    setComparisonsCount(prev => prev + 1)
    setSubmitting(false)

    // Resolve the comparison for the sorter
    comparisonResolver(result)
  }

  const handleStartOver = (skipConfirm = false) => {
    // Show confirmation unless skipped (e.g., from completion screen)
    if (!skipConfirm && !window.confirm('Are you sure you want to restart? All your current sorting progress will be lost.')) {
      return
    }

    // Re-shuffle and start again
    const count = Math.min(10, allSnippets.length)
    const shuffled = [...allSnippets].sort(() => Math.random() - 0.5)
    const selected = shuffled.slice(0, count)

    // Load full data for new selection
    Promise.all(
      selected.map(s => axios.get(`/api/snippets/${s.id}`).then(r => r.data))
    ).then(fullSnippets => {
      setSelectedSnippets(fullSnippets)
    })
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

  // Calculate progress
  const progress = estimatedTotal > 0
    ? Math.min(100, Math.round((comparisonsCount / estimatedTotal) * 100))
    : 0

  if (sortComplete) {
    return (
      <div className="sort-container">
        <div className="sort-complete">
          <h2>Sorting Complete!</h2>
          <p>You made {comparisonsCount} comparisons to rank {finalRanking.length} snippets.</p>

          <div className="ranking-list">
            <h3>Final Ranking (Most Abnormal to Least Abnormal)</h3>
            <ol>
              {finalRanking.map((snippet, index) => (
                <li key={snippet.id} className="ranking-item">
                  <span className="rank-number">#{index + 1}</span>
                  <span className="snippet-id">Snippet {index + 1}</span>
                </li>
              ))}
            </ol>
          </div>

          <button className="sort-btn new-pair" onClick={() => handleStartOver(true)}>
            Start New Sorting Session
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="sort-container">
      <div className="progress-bar">
        <span className="progress-text">
          Comparison {comparisonsCount} of ~{estimatedTotal}
        </span>
        <div className="progress-fill-container">
          <div
            className="progress-fill"
            style={{ width: `${progress}%` }}
          />
        </div>
        <span className="progress-text">{progress}%</span>
      </div>

      <div className="sort-instruction">
        <h3>Which EEG looks MORE ABNORMAL?</h3>
        <p>Sorting {selectedSnippets.length} snippets from most to least abnormal</p>
      </div>

      <div className="sort-comparison">
        <div className="sort-panel">
          <div className="sort-panel-label">Snippet A</div>
          <EEGViewer snippet={snippetA} />
        </div>

        <div className="sort-panel">
          <div className="sort-panel-label">Snippet B</div>
          <EEGViewer snippet={snippetB} />
        </div>
      </div>

      <div className="sort-controls">
        <button
          className="sort-btn left"
          onClick={() => handleChoice('left')}
          disabled={submitting || !snippetA || !snippetB}
        >
          A is more abnormal
        </button>

        <button
          className="sort-btn tie"
          onClick={() => handleChoice('tie')}
          disabled={submitting || !snippetA || !snippetB}
        >
          Can't tell / Equal
        </button>

        <button
          className="sort-btn right"
          onClick={() => handleChoice('right')}
          disabled={submitting || !snippetA || !snippetB}
        >
          B is more abnormal
        </button>
      </div>

      <div className="sort-restart">
        <button
          className="sort-btn restart"
          onClick={() => handleStartOver(false)}
          disabled={submitting}
        >
          Restart
        </button>
      </div>
    </div>
  )
}

export default SortMode
