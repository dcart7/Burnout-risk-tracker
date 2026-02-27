import { useState, useEffect } from 'react'
import './App.css'

function App() {
  return (
    <div className="app-container">
      <header>
        <div className="header-inner">
          <a href="/" className="logo">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
            </svg>
            Burnout Detector
          </a>
          <nav>
            <a href="#" className="nav-link">Features</a>
            <a href="#" className="nav-link">Log In</a>
            <a href="#" className="nav-btn">Sign Up</a>
          </nav>
        </div>
      </header>

      <div className="hero-wrapper">
        <main>
          <p className="hero-tagline animate-in">Early Detector</p>
          <h1 className="animate-in delay-1">Protect your team<br/>before they burn out.</h1>
          <p className="subtitle animate-in delay-2">
            An analytical system designed to prevent professional burnout through
            intuitive weekly surveys and real-time team insights.
          </p>

          <div className="cta-group animate-in delay-3">
            <button className="btn-primary">Start Weekly Survey</button>
            <a href="#" className="btn-secondary">HR Dashboard →</a>
          </div>

          <div className="stats-grid animate-in delay-3" style={{ animationDelay: '0.4s' }}>
            <div className="stat-item">
              <span className="stat-value">4</span>
              <span className="stat-label">Core Metrics</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">100%</span>
              <span className="stat-label">Privacy Protected</span>
            </div>
            <div className="stat-item">
              <span className="stat-value">Real-time</span>
              <span className="stat-label">Team Analytics</span>
            </div>
          </div>
        </main>
      </div>

      <div className="footer-spacer"></div>
      <footer>
        <div className="footer-content">
          <div className="footer-logo">Workforce Burnout Early Detector</div>
          <p className="footer-text">
            Empowering teams with anonymous, real-time insights to maintain a healthy and productive work environment. We care about your privacy and mental health.
          </p>
          <div className="footer-links">
            <a href="#">Privacy Policy</a>
            <a href="#">Terms of Service</a>
            <a href="#">Contact Support</a>
          </div>
          <p className="footer-copyright">© 2026 Your Company Name. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}

export default App
