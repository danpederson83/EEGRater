import { useState } from 'react'

function RaterLogin({ onLogin }) {
  const [name, setName] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (name.trim()) {
      onLogin(name.trim())
    }
  }

  return (
    <div className="login-container">
      <div className="login-box">
        <h2>EEG Rater</h2>
        <p>Enter your name to begin rating EEG snippets</p>
        <form onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder="Your name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoFocus
          />
          <button type="submit" disabled={!name.trim()}>
            Start Rating
          </button>
        </form>
      </div>
    </div>
  )
}

export default RaterLogin
