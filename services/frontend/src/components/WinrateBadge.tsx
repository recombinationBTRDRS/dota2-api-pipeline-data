// services/frontend/src/components/WinrateBadge.tsx
// Кольоровий badge для winrate: зелений >= 52%, жовтий 48-52%, червоний < 48%.

interface Props { winrate: number }  // winrate: 0..1

export default function WinrateBadge({ winrate }: Props) {
  const pct = (winrate * 100).toFixed(1)
  const color = winrate >= 0.52 ? '#3fb950' : winrate < 0.48 ? '#f85149' : '#f0883e'
  return (
    <span style={{ color, fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
      {pct}%
    </span>
  )
}