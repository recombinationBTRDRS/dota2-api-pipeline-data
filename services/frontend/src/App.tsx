// services/frontend/src/App.tsx
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import HeroStatsPage from './pages/HeroStatsPage'
import './App.css'

export default function App() {
  return (
    <BrowserRouter>
      <nav className="navbar">
        <span className="navbar-brand">⚔️ Dota 2 Analytics</span>
        <div className="navbar-links">
          <Link to="/">Hero Stats</Link>
        </div>
      </nav>
      <main className="main-content">
        <Routes>
          <Route path="/" element={<HeroStatsPage />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}