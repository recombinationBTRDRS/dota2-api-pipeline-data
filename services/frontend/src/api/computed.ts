// services/frontend/src/api/computed.ts
// API client для /computed endpoints (pre-computed таблиці Epic 5).

import { apiFetch } from './client'
import type {
  HeroStatsResponse, ItemBuildResponse, MatchupResponse,
  SynergyResponse, StalenessResponse, RebuildResponse,
} from '../types/api'

export const computedApi = {
  getTopHeroes: (params?: {
    primary_pos?: number; patch?: number; min_matches?: number; limit?: number
  }): Promise<HeroStatsResponse[]> => {
    const q = new URLSearchParams()
    if (params?.primary_pos != null) q.set('primary_pos', String(params.primary_pos))
    if (params?.patch != null) q.set('patch', String(params.patch))
    if (params?.min_matches != null) q.set('min_matches', String(params.min_matches))
    if (params?.limit != null) q.set('limit', String(params.limit))
    const qs = q.toString()
    return apiFetch<HeroStatsResponse[]>(`/computed/heroes/top${qs ? `?${qs}` : ''}`)
  },

  getHeroStats: (heroId: number, patch?: number, region?: number): Promise<HeroStatsResponse[]> => {
    const q = new URLSearchParams()
    if (patch != null) q.set('patch', String(patch))
    if (region != null) q.set('region', String(region))
    const qs = q.toString()
    return apiFetch<HeroStatsResponse[]>(`/computed/heroes/${heroId}/stats${qs ? `?${qs}` : ''}`)
  },

  getHeroItems: (heroId: number, primaryPos: number, limit = 6): Promise<ItemBuildResponse[]> =>
    apiFetch(`/computed/heroes/${heroId}/items/${primaryPos}?limit=${limit}`),

  getHeroMatchups: (heroId: number, limit = 20): Promise<MatchupResponse[]> =>
    apiFetch(`/computed/heroes/${heroId}/matchups?limit=${limit}`),

  getHeroCounters: (heroId: number, limit = 10): Promise<MatchupResponse[]> =>
    apiFetch(`/computed/heroes/${heroId}/counters?limit=${limit}`),

  getHeroSynergies: (heroId: number, limit = 20): Promise<SynergyResponse[]> =>
    apiFetch(`/computed/heroes/${heroId}/synergies?limit=${limit}`),

  getStaleness: (): Promise<StalenessResponse> =>
    apiFetch('/computed/staleness'),

  triggerRebuild: (): Promise<RebuildResponse> =>
    apiFetch('/computed/rebuild', { method: 'POST' }),
}