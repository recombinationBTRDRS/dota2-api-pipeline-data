// services/frontend/src/pages/HeroStatsPage.tsx
// Головна сторінка — таблиця всіх героїв з winrate/KDA.
// Клік по рядку → /heroes/:id/:pos

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { computedApi } from '../api'
import type { HeroStatsResponse } from '../types/api'
import { getPositionLabel } from '../types/api'
import WinrateBadge from '../components/WinrateBadge'
import './HeroStatsPage.css'

type SortKey = keyof HeroStatsResponse

export default function HeroStatsPage() {
  const [heroes, setHeroes] = useState<HeroStatsResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [pos, setPos] = useState<number | undefined>(undefined)
  const [sortKey, setSortKey] = useState<SortKey>('winrate')
  const [sortAsc, setSortAsc] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    let active = true          // cleanup flag — запобігає race condition при швидкій зміні pos

    setLoading(true)
    setError(null)

    computedApi.getTopHeroes({ primary_pos: pos, min_matches: 1, limit: 100 })
      .then(data => { if (active) setHeroes(data) })
      .catch(e => { if (active) setError(e instanceof Error ? e.message : String(e)) })
      .finally(() => { if (active) setLoading(false) })

    return () => { active = false }
  }, [pos])

  function handleSort(key: SortKey) {
    if (sortKey === key) setSortAsc(prev => !prev)
    else { setSortKey(key); setSortAsc(false) }
  }

  const sorted = [...heroes].sort((a, b) => {
    const av = a[sortKey] ?? 0
    const bv = b[sortKey] ?? 0
    const cmp = av < bv ? -1 : av > bv ? 1 : 0
    return sortAsc ? cmp : -cmp
  })

  function ariaSortFor(col: SortKey): 'ascending' | 'descending' | 'none' {
    if (sortKey !== col) return 'none'
    return sortAsc ? 'ascending' : 'descending'
  }

  function SortIcon({ col }: { col: SortKey }) {
    if (sortKey !== col) return <span className="sort-icon">↕</span>
    return <span className="sort-icon active">{sortAsc ? '↑' : '↓'}</span>
  }

  const cols: { label: string; key: SortKey }[] = [
    { label: 'Hero',    key: 'hero_name' },
    { label: 'Pos',     key: 'primary_pos' },
    { label: 'Matches', key: 'matches_played' },
    { label: 'Winrate', key: 'winrate' },
    { label: 'K',       key: 'avg_kills' },
    { label: 'D',       key: 'avg_deaths' },
    { label: 'A',       key: 'avg_assists' },
    { label: 'GPM',     key: 'avg_gpm' },
  ]

  return (
    <div>
      <div className="page-header">
        <h1>Hero Stats</h1>
        <div className="filters">
          <label htmlFor="position-select">Position:</label>
          <select
            id="position-select"
            value={pos ?? ''}
            onChange={e => setPos(e.target.value ? Number(e.target.value) : undefined)}
          >
            <option value="">All</option>
            {[1, 2, 3, 4, 5].map(p => (
              <option key={p} value={p}>{p} — {getPositionLabel(p)}</option>
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
              {cols.map(({ label, key }) => (
                <th key={key} aria-sort={ariaSortFor(key)}>
                  <button
                    type="button"
                    className="th-btn"
                    onClick={() => handleSort(key)}
                    onKeyDown={e => {
                      if (e.key === 'Enter' || e.key === ' ') handleSort(key)
                    }}
                    aria-label={`Sort by ${label}`}
                  >
                    {label} <SortIcon col={key} />
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map(h => (
              <tr
                key={`${h.hero_id}-${h.primary_pos}`}
                className="clickable-row"
                role="button"
                tabIndex={0}
                aria-label={`View ${h.hero_name ?? 'hero'} detail`}
                onClick={() => navigate(`/heroes/${h.hero_id}/${h.primary_pos}`)}
                onKeyDown={e => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    navigate(`/heroes/${h.hero_id}/${h.primary_pos}`)
                  }
                }}
              >
                <td className="hero-name">{h.hero_name ?? `Hero #${h.hero_id}`}</td>
                <td>
                  <span className={`pos pos-${h.primary_pos}`}>
                    {getPositionLabel(h.primary_pos)}
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