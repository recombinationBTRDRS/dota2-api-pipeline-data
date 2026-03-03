// services/frontend/src/components/WinrateBadge.tsx
// Кольоровий badge для winrate: зелений >= 52%, жовтий 48-52%, червоний < 48%.
// Guard проти NaN/Infinity — безпечно рендериться навіть при пошкоджених даних.

interface Props { winrate: number }

export default function WinrateBadge({ winrate }: Props) {
  const safe = typeof winrate === 'number' && isFinite(winrate)
    ? Math.max(0, Math.min(1, winrate))
    : 0

  const pct = (safe * 100).toFixed(1)
  const color = safe >= 0.52 ? '#3fb950' : safe < 0.48 ? '#f85149' : '#f0883e'

  return (
    <span style={{ color, fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
      {pct}%
    </span>
  )
}