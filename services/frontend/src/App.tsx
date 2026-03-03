// services/frontend/src/App.tsx
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import HeroStatsPage from './pages/HeroStatsPage'
import HeroDetailPage from './pages/HeroDetailPage'
import './App.css'
import MetaSnapshotPage from './pages/MetaSnapshotPage'

export default function App() {
  return (
    <BrowserRouter>
      <nav className="navbar" >
        <span className="navbar-brand">⚔️ Dota 2 Analytics</span>
        <div className="navbar-links">
          <Link to="/">Hero Stats</Link>
          <Link to="/meta">Meta</Link>
        </div>
      </nav>
      <main className="main-content">
        <Routes>
          <Route path="/" element={<HeroStatsPage />} />
          <Route path="/heroes/:id/:pos" element={<HeroDetailPage />} />
          <Route path="/meta" element={<MetaSnapshotPage />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}