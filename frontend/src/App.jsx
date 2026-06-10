import { useEffect, useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from './assets/vite.svg'
import './App.css'

function App() {
  const [apiStatus, setApiStatus] = useState('checking...')

  useEffect(() => {
    fetch('/api/health')
      .then((res) => res.json())
      .then((data) => setApiStatus(data.status))
      .catch(() => setApiStatus('offline'))
  }, [])

  return (
    <>
      <section id="center">
        <div className="hero">
          <img src={reactLogo} className="framework" alt="React logo" />
          <img src={viteLogo} className="vite" alt="Vite logo" />
        </div>
        <div>
          <h1>FinGuard</h1>
          <p>
            React + Vite frontend with Flask API backend
          </p>
          <p>
            API status: <code>{apiStatus}</code>
          </p>
        </div>
      </section>
    </>
  )
}

export default App
