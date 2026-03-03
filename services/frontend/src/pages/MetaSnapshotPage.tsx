// services/frontend/src/pages/MetaSnapshotPage.tsx
// Meta Snapshot — топ героїв по кожній позиції в поточному меті.
// 5 колонок паралельно: GET /computed/heroes/top?primary_pos=N

import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { computedApi } from '../api'
import type { HeroStatsResponse } from '../types/api'
import { POSITION_LABELS } from '../types/api'
import WinrateBadge from '../components/WinrateBadge'
import './MetaSnapshotPage.css'

const POSITIONS = [1, 2, 3, 4, 5] as const

interface ColumnState {
  data: HeroStatsResponse[]
  loading: boolean
  error: string | null
}

const EMPTY_COL: ColumnState = { data: [], loading: true, error: null }

export default function MetaSnapshotPage() {
  const [columns, setColumns] = useState<Record<number, ColumnState>>(
    Object.fromEntries(POSITIONS.map(p => [p, EMPTY_COL]))
  )
  const navigate = useNavigate()

  useEffect(() => {
    // Паралельний fetch для всіх 5 позицій
    POSITIONS.forEach(pos => {
      computedApi.getTopHeroes({ primary_pos: pos, min_matches: 1, limit: 10 })
        .then(data => setColumns(prev => ({ ...prev, [pos]: { data, loading: false, error: null } })))
        .catch(e => setColumns(prev => ({ ...prev, [pos]: { data: [], loading: false, error: e.message } })))
    })
  }, [])

  return (
    <div>
      <div className="page-header">
        <h1>Meta Snapshot</h1>
        <span className="page-subtitle">Top heroes by winrate per position</span>
      </div>

      <div className="meta-grid">
        {POSITIONS.map(pos => {
          const col = columns[pos]
          return (
            <div key={pos} className="meta-column">
              <div className={`col-header col-header-${pos}`}>
                <span className="col-pos">{pos}</span>
                <span className="col-label">{POSITION_LABELS[pos]}</span>
              </div>

              {col.loading && <div className="col-state">Loading...</div>}
              {col.error && <div className="col-state error">{col.error}</div>}
              {!col.loading && !col.error && col.data.length === 0 && (
                <div className="col-state muted">No data</div>
              )}

              {col.data.length > 0 && (
                <ol className="hero-col-list">
                  {col.data.map((h, i) => (
                    <li
                      key={h.hero_id}
                      className="hero-col-row"
                      onClick={() => navigate(`/heroes/${h.hero_id}/${pos}`)}
                    >
                      <span className="hero-rank">{i + 1}</span>
                      <span className="hero-col-name">
                        {h.hero_name ?? `Hero #${h.hero_id}`}
                      </span>
                      <span className="hero-col-meta">
                        <WinrateBadge winrate={h.winrate} />
                        <span className="hero-col-matches">{h.matches_played}g</span>
                      </span>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}