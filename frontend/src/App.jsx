import { useState, useEffect } from 'react'
import RaterLogin from './components/RaterLogin'
import SortMode from './components/SortMode'

function App() {
  const [rater, setRater] = useState(null)

  useEffect(() => {
    // Check for saved rater name
    const savedRater = localStorage.getItem('eegRaterName')
    if (savedRater) {
      setRater(savedRater)
    }
  }, [])

  const handleLogin = (name) => {
    localStorage.setItem('eegRaterName', name)
    setRater(name)
  }

  const handleLogout = () => {
    localStorage.removeItem('eegRaterName')
    setRater(null)
  }

  if (!rater) {
    return <RaterLogin onLogin={handleLogin} />
  }

  return (
    <div className="app-container">
      <header className="header">
        <h1>EEG Rater</h1>
        <div className="rater-info">
          <span className="rater-name">Rater: {rater}</span>
          <button className="logout-btn" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </header>

      <main className="content-area">
        <SortMode rater={rater} />
      </main>
    </div>
  )
}

export default App
