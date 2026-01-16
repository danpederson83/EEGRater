function Navigation({ mode, setMode }) {
  return (
    <div className="nav-tabs">
      <button
        className={mode === 'rating' ? 'active' : ''}
        onClick={() => setMode('rating')}
      >
        Rating Mode
      </button>
      <button
        className={mode === 'sort' ? 'active' : ''}
        onClick={() => setMode('sort')}
      >
        Sort Mode
      </button>
    </div>
  )
}

export default Navigation
