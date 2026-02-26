import { useState, useEffect } from 'react'
import './App.css'

function App() {
  const [message, setMessage] = useState('Loading...')

  useEffect(() => {
    fetch('http://localhost:8000/api/hello/')
      .then(res => res.json())
      .then(data => setMessage(data.message))
      .catch(err => setMessage('Error connecting to backend'))
  }, [])

  return (
    <div className="App">
      <header className="App-header">
        <h1>Burnout Risk Tracker</h1>
        <div className="card">
          <p>Message from backend: <strong>{message}</strong></p>
        </div>
      </header>
    </div>
  )
}

export default App
