// services/frontend/src/pages/HeroDetailPage.tsx
// Hero Detail — stats + items + matchups + synergies для конкретного героя на позиції.
// URL: /heroes/:id/:pos

import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { computedApi } from '../api'
import type {
  HeroStatsResponse,
  ItemBuildResponse,
  MatchupResponse,
  SynergyResponse,
} from '../types/api'
import { POSITION_LABELS } from '../types/api'
import WinrateBadge from '../components/WinrateBadge'
import './HeroDetailPage.css'

// ── Generic section hook ──────────────────────────────────────────────────────

interface SectionState<T> {
  data: T | null
  loading: boolean
  error: string | null
}

function useSection<T>(fetch: () => Promise<T>): SectionState<T> {
  const [state, setState] = useState<SectionState<T>>({
    data: null, loading: true, error: null,
  })
  useEffect(() => {
    setState({ data: null, loading: true, error: null })
    fetch()
      .then(data => setState({ data, loading: false, error: null }))
      .catch(e => setState({ data: null, loading: false, error: e.message }))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  return state
}

// ── Shared UI ─────────────────────────────────────────────────────────────────

function SectionBox({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="section-box">
      <h2 className="section-title">{title}</h2>
      {children}
    </div>
  )
}

function SectionLoading() {
  return <div className="section-state">Loading...</div>
}
function SectionError({ msg }: { msg: string }) {
  return <div className="section-state error">{msg}</div>
}
function SectionEmpty() {
  return <div className="section-state muted">No data available</div>
}

// ── Stats card ────────────────────────────────────────────────────────────────

function StatsCard({ stats }: { stats: HeroStatsResponse }) {
  return (
    <div className="stats-grid">
      {[
        { label: 'Matches', value: stats.matches_played },
        { label: 'Winrate', value: <WinrateBadge winrate={stats.winrate} /> },
        {
          label: 'KDA',
          value: `${stats.avg_kills.toFixed(1)} / ${stats.avg_deaths.toFixed(1)} / ${stats.avg_assists.toFixed(1)}`,
        },
        { label: 'GPM', value: stats.avg_gpm.toFixed(0) },
        { label: 'XPM', value: stats.avg_xpm.toFixed(0) },
      ].map(({ label, value }) => (
        <div key={label} className="stat-item">
          <span className="stat-label">{label}</span>
          <span className="stat-value">{value}</span>
        </div>
      ))}
    </div>
  )
}

// ── Items list ────────────────────────────────────────────────────────────────

function ItemsList({ items }: { items: ItemBuildResponse[] }) {
  return (
    <ol className="items-list">
      {items.map(item => (
        <li key={item.item_id} className="item-row">
          <span className="item-name">{item.item_name ?? `Item #${item.item_id}`}</span>
          <span className="item-meta">
            <WinrateBadge winrate={item.win_rate} />
            <span className="item-bought">{item.times_bought}×</span>
          </span>
        </li>
      ))}
    </ol>
  )
}

// ── Matchup list ──────────────────────────────────────────────────────────────

function MatchupList({
  rows,
  heroId,
  label,
}: {
  rows: MatchupResponse[]
  heroId: number
  label: string
}) {
  const navigate = useNavigate()
  return (
    <div>
      <p className="list-label">{label}</p>
      <ol className="matchup-list">
        {rows.map(r => {
          const opponentId = r.hero_id === heroId ? r.opponent_id : r.hero_id
          return (
            <li
              key={opponentId}
              className="matchup-row"
              onClick={() => navigate(`/heroes/${opponentId}/1`)}
            >
              <span className="matchup-name">Hero #{opponentId}</span>
              <span className="matchup-meta">
                <WinrateBadge winrate={r.winrate} />
                <span className="matchup-matches">{r.matches} games</span>
              </span>
            </li>
          )
        })}
      </ol>
    </div>
  )
}

// ── Synergy list ──────────────────────────────────────────────────────────────

function SynergyList({ rows, heroId }: { rows: SynergyResponse[]; heroId: number }) {
  const navigate = useNavigate()
  return (
    <ol className="matchup-list">
      {rows.map(r => {
        const allyId = r.hero_id === heroId ? r.ally_id : r.hero_id
        return (
          <li
            key={allyId}
            className="matchup-row"
            onClick={() => navigate(`/heroes/${allyId}/1`)}
          >
            <span className="matchup-name">Hero #{allyId}</span>
            <span className="matchup-meta">
              <WinrateBadge winrate={r.winrate} />
              <span className="matchup-matches">{r.matches} games</span>
            </span>
          </li>
        )
      })}
    </ol>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function HeroDetailPage() {
  const { id, pos } = useParams<{ id: string; pos: string }>()
  const navigate = useNavigate()

  const heroId = Number(id)
  const primaryPos = Number(pos)

  const statsSection = useSection(() =>
    computedApi.getHeroStats(heroId).then(rows =>
      rows.find(r => r.primary_pos === primaryPos) ?? rows[0] ?? null
    )
  )
  const itemsSection = useSection(() => computedApi.getHeroItems(heroId, primaryPos))
  const matchupsSection = useSection(() => computedApi.getHeroMatchups(heroId, 10))
  const countersSection = useSection(() => computedApi.getHeroCounters(heroId, 10))
  const synergiesSection = useSection(() => computedApi.getHeroSynergies(heroId, 10))

  const heroName = statsSection.data?.hero_name ?? `Hero #${heroId}`

  return (
    <div>
      <div className="detail-header">
        <button className="back-btn" onClick={() => navigate('/')}>← Back</button>
        <div className="detail-title">
          <h1>{heroName}</h1>
          <span className={`pos pos-${primaryPos}`}>{POSITION_LABELS[primaryPos]}</span>
        </div>
      </div>

      <div className="detail-grid-top">
        <SectionBox title="Stats">
          {statsSection.loading && <SectionLoading />}
          {statsSection.error && <SectionError msg={statsSection.error} />}
          {!statsSection.loading && !statsSection.error && !statsSection.data && <SectionEmpty />}
          {statsSection.data && <StatsCard stats={statsSection.data} />}
        </SectionBox>

        <SectionBox title={`Item Build — ${POSITION_LABELS[primaryPos]}`}>
          {itemsSection.loading && <SectionLoading />}
          {itemsSection.error && <SectionError msg={itemsSection.error} />}
          {!itemsSection.loading && !itemsSection.error && !itemsSection.data?.length && <SectionEmpty />}
          {itemsSection.data && itemsSection.data.length > 0 && <ItemsList items={itemsSection.data} />}
        </SectionBox>
      </div>

      <div className="detail-grid-bottom">
        <SectionBox title="Best Against">
          {matchupsSection.loading && <SectionLoading />}
          {matchupsSection.error && <SectionError msg={matchupsSection.error} />}
          {!matchupsSection.loading && !matchupsSection.error && !matchupsSection.data?.length && <SectionEmpty />}
          {matchupsSection.data && matchupsSection.data.length > 0 && (
            <MatchupList rows={matchupsSection.data} heroId={heroId} label="Highest winrate vs:" />
          )}
        </SectionBox>

        <SectionBox title="Hardest Counters">
          {countersSection.loading && <SectionLoading />}
          {countersSection.error && <SectionError msg={countersSection.error} />}
          {!countersSection.loading && !countersSection.error && !countersSection.data?.length && <SectionEmpty />}
          {countersSection.data && countersSection.data.length > 0 && (
            <MatchupList rows={countersSection.data} heroId={heroId} label="Lowest winrate vs:" />
          )}
        </SectionBox>

        <SectionBox title="Best Synergies">
          {synergiesSection.loading && <SectionLoading />}
          {synergiesSection.error && <SectionError msg={synergiesSection.error} />}
          {!synergiesSection.loading && !synergiesSection.error && !synergiesSection.data?.length && <SectionEmpty />}
          {synergiesSection.data && synergiesSection.data.length > 0 && (
            <SynergyList rows={synergiesSection.data} heroId={heroId} />
          )}
        </SectionBox>
      </div>
    </div>
  )
}