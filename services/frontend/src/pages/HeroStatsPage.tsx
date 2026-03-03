// services/frontend/src/pages/HeroStatsPage.tsx
// Головна сторінка — таблиця всіх героїв з winrate/KDA.
// Дані: GET /computed/heroes/top. Фільтр по позиції, сортування по колонках.

import { useState, useEffect } from 'react'
import { computedApi } from '../api'
import type { HeroStatsResponse } from '../types/api'
import { POSITION_LABELS } from '../types/api'
import WinrateBadge from '../components/WinrateBadge'
import './HeroStatsPage.css'
import { useNavigate } from 'react-router-dom'

export default function HeroStatsPage() {
  const [heroes, setHeroes] = useState<HeroStatsResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [pos, setPos] = useState<number | undefined>(undefined)
  const [sortKey, setSortKey] = useState<keyof HeroStatsResponse>('winrate')
  const [sortAsc, setSortAsc] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    setLoading(true)
    setError(null)
    computedApi.getTopHeroes({ primary_pos: pos, min_matches: 1, limit: 100 })
      .then(setHeroes)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [pos])

  function handleSort(key: keyof HeroStatsResponse) {
    if (sortKey === key) setSortAsc(!sortAsc)
    else { setSortKey(key); setSortAsc(false) }
  }

  const sorted = [...heroes].sort((a, b) => {
    const av = a[sortKey] ?? 0
    const bv = b[sortKey] ?? 0
    const cmp = av < bv ? -1 : av > bv ? 1 : 0
    return sortAsc ? cmp : -cmp
  })

  function SortIcon({ col }: { col: keyof HeroStatsResponse }) {
    if (sortKey !== col) return <span className="sort-icon">↕</span>
    return <span className="sort-icon active">{sortAsc ? '↑' : '↓'}</span>
  }

  return (
    <div>
      <div className="page-header">
        <h1>Hero Stats</h1>
        <div className="filters">
          <label>Position:</label>
          <select
            value={pos ?? ''}
            onChange={e => setPos(e.target.value ? Number(e.target.value) : undefined)}
          >
            <option value="">All</option>
            {[1, 2, 3, 4, 5].map(p => (
              <option key={p} value={p}>{p} — {POSITION_LABELS[p]}</option>
            ))}
          </select>
        </div>
      </div>

      {loading && <div className="state-msg">Loading...</div>}
      {error && <div className="state-msg error">Error: {error}</div>}
      {!loading && !error && heroes.length === 0 && (
        <div className="state-msg">
          No data. Run <code>POST /computed/rebuild</code> first.
        </div>
      )}

      {!loading && !error && heroes.length > 0 && (
        <table className="hero-table">
          <thead>
            <tr>
              <th onClick={() => handleSort('hero_name')}>Hero <SortIcon col="hero_name" /></th>
              <th onClick={() => handleSort('primary_pos')}>Pos <SortIcon col="primary_pos" /></th>
              <th onClick={() => handleSort('matches_played')}>Matches <SortIcon col="matches_played" /></th>
              <th onClick={() => handleSort('winrate')}>Winrate <SortIcon col="winrate" /></th>
              <th onClick={() => handleSort('avg_kills')}>K <SortIcon col="avg_kills" /></th>
              <th onClick={() => handleSort('avg_deaths')}>D <SortIcon col="avg_deaths" /></th>
              <th onClick={() => handleSort('avg_assists')}>A <SortIcon col="avg_assists" /></th>
              <th onClick={() => handleSort('avg_gpm')}>GPM <SortIcon col="avg_gpm" /></th>
            </tr>
          </thead>
          <tbody>
            {sorted.map(h => (
              <tr
                key={`${h.hero_id}-${h.primary_pos}`}
                className="clickable-row"
                onClick={() => navigate(`/heroes/${h.hero_id}/${h.primary_pos}`)}
              >
                <td className="hero-name">{h.hero_name ?? `Hero #${h.hero_id}`}</td>
                <td>
                  <span className={`pos pos-${h.primary_pos}`}>
                    {POSITION_LABELS[h.primary_pos]}
                  </span>
                </td>
                <td>{h.matches_played}</td>
                <td><WinrateBadge winrate={h.winrate} /></td>
                <td>{h.avg_kills.toFixed(1)}</td>
                <td>{h.avg_deaths.toFixed(1)}</td>
                <td>{h.avg_assists.toFixed(1)}</td>
                <td>{h.avg_gpm.toFixed(0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}