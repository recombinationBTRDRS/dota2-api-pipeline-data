// services/frontend/src/types/api.ts
// TypeScript типи синхронізовані з Pydantic response моделями backend.
// При зміні backend моделей — оновлювати тут.

export interface HeroStatsResponse {
  hero_id: number
  hero_name: string | null
  primary_pos: number
  patch: number | null
  region: number | null
  matches_played: number
  wins: number
  losses: number
  winrate: number
  avg_kills: number
  avg_deaths: number
  avg_assists: number
  avg_gpm: number
  avg_xpm: number
  computed_at: number
}

export interface ItemBuildResponse {
  item_id: number
  item_name: string | null
  times_bought: number
  times_won: number
  win_rate: number
  computed_at: number
}

export interface MatchupResponse {
  hero_id: number
  opponent_id: number
  matches: number
  wins: number
  losses: number
  winrate: number
  computed_at: number
}

export interface SynergyResponse {
  hero_id: number
  ally_id: number
  matches: number
  wins: number
  losses: number
  winrate: number
  computed_at: number
}

export interface StalenessResponse {
  hero_stats_computed: number | null
  hero_item_build_computed: number | null
  hero_matchup_computed: number | null
  hero_synergy_computed: number | null
}

export interface RebuildResponse {
  status: string
  hero_stats_rows: number
  item_build_rows: number
  matchup_rows: number
  synergy_rows: number
}

export const POSITION_LABELS: Record<number, string> = {
  1: 'Carry',
  2: 'Mid',
  3: 'Offlane',
  4: 'Support',
  5: 'Hard Support',
}