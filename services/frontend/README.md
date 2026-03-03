# Dota 2 Analytics — Frontend

React + Vite + TypeScript frontend для Dota 2 Analytics API.

## Вимоги

- Node.js 20.19+ або 22.12+
- Backend запущений на `http://localhost:8000`

## Запуск

```bash
cd services/frontend
npm install
npm run dev
# → http://localhost:5173
```

## Build

```bash
npm run build
npm run preview
```

## Змінні середовища

Frontend не потребує `.env` — API проксується через Vite:

```
/api/* → http://localhost:8000/*
```

Конфіг проксі: `vite.config.ts`.

## Сторінки

| Route | Сторінка | Опис |
|-------|----------|------|
| `/` | Hero Stats | Таблиця всіх героїв з winrate/KDA, фільтр по позиції |
| `/meta` | Meta Snapshot | Топ героїв по кожній з 5 позицій |
| `/heroes/:id/:pos` | Hero Detail | Stats + items + matchups + synergies |

## Структура

```
src/
├── api/
│   ├── client.ts      # fetch wrapper з ApiError
│   ├── computed.ts    # /computed endpoints
│   └── index.ts
├── components/
│   └── WinrateBadge.tsx
├── pages/
│   ├── HeroStatsPage.tsx + .css
│   ├── HeroDetailPage.tsx + .css
│   └── MetaSnapshotPage.tsx + .css
├── types/
│   └── api.ts         # TypeScript типи (синхронізовані з backend Pydantic)
├── App.tsx
└── main.tsx
```

## Lint / TypeScript

```bash
npm run lint
npx tsc --noEmit
```