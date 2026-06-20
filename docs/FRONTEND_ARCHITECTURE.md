# Frontend Architecture — Pathfinder

**Stack**: Next.js 14 (App Router) + TypeScript + Tailwind CSS + React Query
**API**: Pathfinder REST API (38 endpoints, 9 modules)
**Date**: 2026-06-20

---

## 1. Page Map

```
/                               → Landing / Redirect to Dashboard
/(auth)/login                   → Login
/(auth)/register                → Register

/(dashboard)                    → Dashboard Home (stats, recent activity)

/(dashboard)/profile            → Profile View
/(dashboard)/profile/import     → Resume Upload
/(dashboard)/resumes            → Resume List
/(dashboard)/resumes/[id]       → Resume Detail
/(dashboard)/resumes/new        → Create Resume

/(dashboard)/jobs               → Job Search (browse + filter)
/(dashboard)/jobs/[id]          → Job Detail
/(dashboard)/jobs/[id]/match    → Match Score Detail

/(dashboard)/tailoring          → Tailoring History
/(dashboard)/tailoring/[id]     → Tailored Resume View
/(dashboard)/tailoring/new      → New Tailor Request (select resume + job)
/(dashboard)/tailoring/compare  → Compare Versions

/(dashboard)/agent              → Agent Chat Interface
/(dashboard)/agent/history      → Agent Execution History

/(dashboard)/knowledge          → Knowledge Center (search + browse)
/(dashboard)/knowledge/upload   → Upload Knowledge Document

/(dashboard)/applications       → Job Applications Pipeline
/(dashboard)/applications/[id]  → Application Detail

/(dashboard)/admin              → Admin Dashboard (stats)
```

**Total**: 20 pages

---

## 2. Route Structure (Next.js App Router)

```
app/
├── layout.tsx                    # Root layout (providers)
├── page.tsx                      # Landing / redirect
│
├── (auth)/
│   ├── layout.tsx                # Auth layout (centered card, no nav)
│   ├── login/page.tsx
│   └── register/page.tsx
│
└── (dashboard)/
    ├── layout.tsx                # Dashboard layout (sidebar + header)
    ├── page.tsx                  # Dashboard home
    │
    ├── profile/
    │   ├── page.tsx              # Profile view
    │   └── import/page.tsx       # Resume upload
    │
    ├── resumes/
    │   ├── page.tsx              # Resume list
    │   ├── new/page.tsx          # Create resume
    │   └── [id]/page.tsx         # Resume detail
    │
    ├── jobs/
    │   ├── page.tsx              # Job search
    │   └── [id]/
    │       ├── page.tsx          # Job detail
    │       └── match/page.tsx    # Match score
    │
    ├── tailoring/
    │   ├── page.tsx              # Tailoring history
    │   ├── new/page.tsx          # New tailor (select resume + job)
    │   ├── [id]/page.tsx         # Tailored resume view
    │   └── compare/page.tsx      # Compare versions
    │
    ├── agent/
    │   ├── page.tsx              # Agent chat
    │   └── history/page.tsx      # Execution history
    │
    ├── knowledge/
    │   ├── page.tsx              # Knowledge center
    │   └── upload/page.tsx       # Upload document
    │
    ├── applications/
    │   ├── page.tsx              # Pipeline view
    │   └── [id]/page.tsx         # Application detail
    │
    └── admin/
        └── page.tsx              # Admin dashboard
```

---

## 3. Layouts

### Root Layout (`app/layout.tsx`)
- React Query Provider
- Auth Context Provider
- Toast notification provider
- Global Tailwind styles

### Auth Layout (`(auth)/layout.tsx`)
- Centered card on gradient background
- Logo + tagline
- No sidebar, no header nav
- Redirects to dashboard if already authenticated

### Dashboard Layout (`(dashboard)/layout.tsx`)
- **Sidebar** (fixed left, 260px):
  - Logo + brand name
  - Nav links with icons:
    - Dashboard (home)
    - Profile (user)
    - Resumes (document)
    - Jobs (briefcase)
    - Tailoring (wand)
    - Agent (sparkles)
    - Knowledge (book)
    - Applications (clipboard)
    - Admin (shield) — only if admin
  - User section at bottom (avatar, name, logout)
- **Header** (sticky top, 64px):
  - Page title (breadcrumb)
  - Command palette trigger (Ctrl+K)
  - Notification bell
  - User avatar dropdown
- **Main content area**: scrolling, max-w-7xl, padded

### Mobile: Sidebar becomes slide-over drawer with hamburger trigger.

---

## 4. Authentication Flow

```
User lands → Check localStorage for token
  ├─ No token → Redirect to /login
  └─ Has token → Validate by calling GET /v1/profile
       ├─ 200 → Render dashboard
       └─ 401 → Clear token, redirect to /login
```

### Token Management
- Store `access_token` in memory (zustand store) + localStorage persistence
- Refresh token stored in httpOnly cookie (if available) or localStorage
- Axios interceptor: on 401, attempt refresh; on refresh fail, redirect to login
- Logout: call POST /v1/auth/logout, clear all tokens

### Route Protection
- Middleware (`middleware.ts`) checks for token cookie/header
- Protected routes: everything under `/(dashboard)`
- Public routes: `/login`, `/register`, `/`

---

## 5. API Layer Design

```
lib/
├── api/
│   ├── client.ts              # Axios instance with interceptors
│   ├── auth.ts                # register, login, logout
│   ├── profile.ts             # getProfile, importResume
│   ├── resumes.ts             # list, create, get, delete
│   ├── jobs.ts                # list, search, getById
│   ├── companies.ts           # list, getById
│   ├── matching.ts            # computeMatch, sendFeedback
│   ├── agent.ts               # execute (stream), listExecutions, getExecution
│   ├── tailoring.ts           # analyze, tailor, listVersions, compare, accept
│   ├── knowledge.ts           # ingest, search, listDocs, deleteDoc
│   ├── applications.ts        # list, create, update, get, delete
│   └── admin.ts               # getStats
│
├── hooks/                     # React Query hooks
│   ├── useAuth.ts
│   ├── useProfile.ts
│   ├── useResumes.ts
│   ├── useJobs.ts
│   ├── useMatching.ts
│   ├── useAgent.ts
│   ├── useTailoring.ts
│   ├── useKnowledge.ts
│   └── useApplications.ts
│
└── types/
    ├── auth.ts
    ├── profile.ts
    ├── jobs.ts
    ├── matching.ts
    ├── agent.ts
    ├── tailoring.ts
    ├── knowledge.ts
    └── common.ts
```

### Axios Client (`client.ts`)
```typescript
// Base URL from env: NEXT_PUBLIC_API_URL=http://localhost:8000
// Timeout: 30s
// Request interceptor: attach Bearer token from store
// Response interceptor: parse error body, normalize to { code, message }
// On 401: attempt refresh, else redirect to /login
```

---

## 6. State Management

### Zustand Stores (client state)

| Store | Content |
|-------|---------|
| `authStore` | token, user, isAuthenticated, login(), logout() |
| `uiStore` | sidebarOpen, theme, commandPaletteOpen |
| `agentStore` | messages[], isStreaming, sendMessage() |

### React Query (server state)

| Query Key | Endpoint | Stale Time |
|-----------|----------|:----------:|
| `['profile']` | GET /v1/profile | 5 min |
| `['resumes']` | GET /v1/resumes | 5 min |
| `['resumes', id]` | GET /v1/resumes/{id} | 5 min |
| `['jobs', filters]` | GET /v1/jobs | 2 min |
| `['jobs', id]` | GET /v1/jobs/{id} | 5 min |
| `['match', jobId]` | POST /v1/match/compute | 2 min |
| `['agent', 'executions']` | GET /v1/agent/executions | 1 min |
| `['tailoring', 'versions', baseId, jobId]` | GET /v1/tailoring/versions | 2 min |
| `['knowledge', 'search', query]` | POST /v1/knowledge/search | 5 min |
| `['knowledge', 'documents']` | GET /v1/knowledge/documents | 5 min |
| `['applications']` | GET /v1/applications | 2 min |
| `['admin', 'stats']` | GET /v1/admin/stats | 30s |
| `['jobs']` | GET /v1/jobs | 2 min |

---

## 7. Component Hierarchy

```
Components/
├── ui/                          # Reusable primitives (shadcn/ui style)
│   ├── Button.tsx
│   ├── Input.tsx
│   ├── Card.tsx
│   ├── Badge.tsx
│   ├── Avatar.tsx
│   ├── Dialog.tsx
│   ├── Dropdown.tsx
│   ├── Tabs.tsx
│   ├── Skeleton.tsx
│   ├── Toast.tsx
│   ├── EmptyState.tsx
│   ├── ErrorState.tsx
│   └── Spinner.tsx
│
├── layout/
│   ├── Sidebar.tsx              # Navigation sidebar
│   ├── Header.tsx               # Top header bar
│   ├── DashboardLayout.tsx      # Shell layout
│   ├── AuthLayout.tsx           # Auth pages layout
│   └── MobileNav.tsx            # Mobile drawer navigation
│
├── auth/
│   ├── LoginForm.tsx
│   ├── RegisterForm.tsx
│   └── ProtectedRoute.tsx
│
├── profile/
│   ├── ProfileCard.tsx          # Profile overview card
│   ├── SkillsList.tsx           # Skills with proficiency badges
│   ├── ExperienceTimeline.tsx   # Work experience timeline
│   ├── EducationList.tsx        # Education entries
│   └── ResumeUploader.tsx       # Drag-and-drop resume upload
│
├── jobs/
│   ├── JobCard.tsx              # Job listing card
│   ├── JobList.tsx              # Job list with filters
│   ├── JobFilters.tsx           # Filter bar (query, location, remote)
│   ├── JobDetail.tsx            # Full job description
│   └── JobSearchBar.tsx         # Search input with suggestions
│
├── matching/
│   ├── MatchScoreGauge.tsx      # Circular score gauge (0-100)
│   ├── DimensionBar.tsx         # Individual dimension bar
│   ├── StrengthsList.tsx        # Match strengths
│   ├── SkillGapsList.tsx        # Missing skills
│   └── MatchCard.tsx            # Match summary card
│
├── tailoring/
│   ├── TailoringRequest.tsx     # Select resume + job + strategy
│   ├── DiffViewer.tsx           # Before/after diff for each section
│   ├── FactualityBadge.tsx      # Factuality score indicator
│   ├── VersionSelector.tsx      # Version dropdown
│   └── TailorPreview.tsx        # Tailored resume preview
│
├── agent/
│   ├── ChatWindow.tsx           # Chat messages container
│   ├── ChatMessage.tsx          # Single message bubble
│   ├── ChatInput.tsx            # Message input with send
│   ├── IntentBadge.tsx          # Shows detected intent
│   └── StreamingIndicator.tsx   # Typing dots during stream
│
├── knowledge/
│   ├── KnowledgeSearch.tsx      # Search bar with results
│   ├── KnowledgeCard.tsx        # Document card
│   ├── KnowledgeUpload.tsx      # Document upload form
│   └── KnowledgeList.tsx        # Document grid/list
│
├── applications/
│   ├── PipelineKanban.tsx       # Kanban board by status
│   ├── ApplicationCard.tsx      # Application card
│   └── StatusBadge.tsx          # Color-coded status badge
│
├── admin/
│   ├── StatCard.tsx             # Single stat with label + value
│   ├── StatsGrid.tsx            # Grid of stat cards
│   ├── TierDistribution.tsx     # Users by tier chart
│   └── StatusPieChart.tsx       # Applications by status
│
└── shared/
    ├── LoadingSkeleton.tsx      # Page-level skeleton
    ├── ErrorFallback.tsx        # Error boundary fallback
    ├── EmptyState.tsx           # "No data yet" with CTA
    └── ConfirmDialog.tsx        # Delete/action confirmation
```

**Total**: ~55 components

---

## 8. Loading States

| Pattern | When | Implementation |
|---------|------|---------------|
| Page skeleton | Initial page load | `<LoadingSkeleton />` with card shapes |
| Inline spinner | Button actions (save, submit) | `<Spinner />` replacing button text |
| Skeleton cards | List/card loading | `<Skeleton className="h-48 w-full" />` |
| Streaming dots | Agent typing | Animated `...` in chat bubble |
| Progress bar | Resume upload | File upload progress bar |
| Shimmer | Dashboard widgets loading | Tailwind animate-pulse |

---

## 9. Error States

| Pattern | When | Implementation |
|---------|------|---------------|
| Error banner | API call fails | Toast notification (top-right, auto-dismiss) |
| Error card | Section fails to load | `<ErrorState />` with retry button |
| Empty state | No data (not error) | `<EmptyState />` with illustration + CTA |
| 401 redirect | Token expired | Silent redirect to /login |
| 429 feedback | Rate limited | Toast: "Too many requests. Try again in X seconds" |
| Validation errors | Form submission | Inline field errors from 422 response |

---

## 10. Mobile Responsiveness

| Breakpoint | Layout |
|:----------:|--------|
| < 768px | Sidebar → hamburger drawer, single column, stacked cards |
| 768-1024px | Sidebar collapsed (icons only), 2-column grid |
| > 1024px | Full sidebar, multi-column grid, max-w-7xl |

Key mobile adaptations:
- Job list: cards stack vertically
- Match gauge: smaller, below job title
- Agent chat: full-screen mode
- Resume upload: single-column, larger touch targets
- Tables → cards with key-value rows

---

## 11. Dashboard Structure

```
/(dashboard)/page.tsx
┌─────────────────────────────────────────────┐
│  Welcome back, {name}!                       │
├──────────┬──────────┬──────────┬────────────┤
│  Profile │ Jobs     │ Match    │ Resumes    │  ← Quick stat cards
│  Score   │ Found    │ Ready    │ Created    │
├──────────┴──────────┴──────────┴────────────┤
│  Recent Activity                             │
│  ┌─────────────────────────────────────────┐ │
│  │ 2h ago — Matched with Senior ML Eng    │ │
│  │ 5h ago — Resume tailored for Data Eng  │ │
│  │ 1d ago — Uploaded new resume           │ │
│  └─────────────────────────────────────────┘ │
├──────────────────────┬───────────────────────┤
│  Recommended Jobs    │  Quick Actions        │
│  ┌─────────────────┐ │  [Upload Resume]      │
│  │ Senior ML Eng   │ │  [Search Jobs]        │
│  │ 84% match       │ │  [Ask Agent]          │
│  │ Data Engineer   │ │  [Tailor Resume]      │
│  │ Backend Eng     │ │                       │
│  └─────────────────┘ │                       │
└──────────────────────┴───────────────────────┘
```
