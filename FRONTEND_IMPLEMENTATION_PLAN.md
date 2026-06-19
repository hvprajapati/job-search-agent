# Frontend Implementation Plan — Pathfinder

**Stack**: Next.js 14 (App Router) + TypeScript + Tailwind CSS + React Query + Zustand
**API**: 38 endpoints across 9 modules
**Date**: 2026-06-20

---

## Phase 0: Foundation (Day 1-2)

Before any feature work, set up the project skeleton.

### Scaffold
```
npx create-next-app@latest pathfinder-ui --typescript --tailwind --app
```

### Install Dependencies
```
axios, @tanstack/react-query, zustand, react-hot-toast,
lucide-react, react-hook-form, zod, @hookform/resolvers,
date-fns, clsx, tailwind-merge, cmdk
```

### Files (25)
```
.env.local                          # NEXT_PUBLIC_API_URL
middleware.ts                       # Auth route protection
app/layout.tsx                      # Root layout + providers
app/page.tsx                        # Landing redirect
lib/api/client.ts                   # Axios instance
lib/types/common.ts                 # Shared types
lib/types/auth.ts                   # Auth types
lib/hooks/useAuth.ts                # Auth hooks
stores/authStore.ts                 # Zustand auth store
stores/uiStore.ts                   # UI state store
components/ui/Button.tsx
components/ui/Input.tsx
components/ui/Card.tsx
components/ui/Badge.tsx
components/ui/Avatar.tsx
components/ui/Dialog.tsx
components/ui/Dropdown.tsx
components/ui/Tabs.tsx
components/ui/Skeleton.tsx
components/ui/Toast.tsx
components/ui/EmptyState.tsx
components/ui/ErrorState.tsx
components/ui/Spinner.tsx
components/layout/Sidebar.tsx
components/layout/Header.tsx
```

### Effort: 2 days

---

## Phase 1: Authentication (Day 3-4)

### Pages (3)
| Route | Page | Purpose |
|-------|------|---------|
| `/(auth)/login` | `LoginPage` | Email + password login |
| `/(auth)/register` | `RegisterPage` | Registration form |
| `/(auth)/layout` | `AuthLayout` | Centered card layout |

### Components (3)
| Component | Purpose |
|-----------|---------|
| `LoginForm` | Email/password form with validation |
| `RegisterForm` | Registration with accept_terms checkbox |
| `ProtectedRoute` | Route guard wrapper |

### API Integration (3)
| Hook | Endpoint |
|------|----------|
| `useLogin` | POST /v1/auth/login |
| `useRegister` | POST /v1/auth/register |
| `useLogout` | POST /v1/auth/logout |

### Auth Flow
```
Register → auto-login → store token → redirect to dashboard
Login → store token → redirect to dashboard
Logout → clear token → redirect to login
Middleware → check token → redirect to login if missing
```

### Files: 8 new | Effort: 1.5 days

---

## Phase 2: Profile + Resume (Day 4-6)

### Pages (5)
| Route | Page | Purpose |
|-------|------|---------|
| `/(dashboard)/profile` | `ProfilePage` | View parsed profile |
| `/(dashboard)/profile/import` | `ResumeImportPage` | Upload resume |
| `/(dashboard)/resumes` | `ResumeListPage` | List all resumes |
| `/(dashboard)/resumes/[id]` | `ResumeDetailPage` | View resume content |
| `/(dashboard)/resumes/new` | `CreateResumePage` | Create manually |

### Components (8)
| Component | Purpose |
|-----------|---------|
| `ProfileCard` | Overview: name, headline, location |
| `SkillsList` | Skills with proficiency badges (color-coded) |
| `ExperienceTimeline` | Vertical timeline of work history |
| `EducationList` | Degree cards |
| `ResumeUploader` | Drag-drop zone + file validation |
| `ResumeCard` | Resume list item |
| `ResumeForm` | Manual resume creation |
| `ParsingConfidence` | Confidence bars per field |

### API Integration (6)
| Hook | Endpoint |
|------|----------|
| `useProfile` | GET /v1/profile |
| `useImportResume` | POST /v1/profile/import/resume |
| `useResumes` | GET /v1/resumes |
| `useCreateResume` | POST /v1/resumes |
| `useResume` | GET /v1/resumes/{id} |
| `useDeleteResume` | DELETE /v1/resumes/{id} |

### Files: 14 new | Effort: 2 days

---

## Phase 3: Jobs + Matching (Day 6-9)

### Pages (4)
| Route | Page | Purpose |
|-------|------|---------|
| `/(dashboard)/jobs` | `JobsPage` | Browse + search jobs |
| `/(dashboard)/jobs/[id]` | `JobDetailPage` | Full job description |
| `/(dashboard)/jobs/[id]/match` | `MatchPage` | Match score detail |

### Components (11)
| Component | Purpose |
|-----------|---------|
| `JobSearchBar` | Search with debounced input |
| `JobFilters` | Location, remote, seniority filters |
| `JobCard` | Title, company, location, salary, skills |
| `JobList` | Grid/list of JobCards |
| `JobDetail` | Full job: description, requirements, company |
| `MatchScoreGauge` | SVG circular gauge (0-100, color-coded) |
| `DimensionBar` | Horizontal bar per dimension with score |
| `StrengthsList` | Green checkmarked strengths |
| `SkillGapsList` | Red/gray missing skills with severity |
| `MatchCard` | Summary card with overall score |
| `FeedbackButton` | Thumbs up/down/dismiss |

### API Integration (6)
| Hook | Endpoint |
|------|----------|
| `useJobs` | GET /v1/jobs |
| `useJob` | GET /v1/jobs/{id} |
| `useCompanies` | GET /v1/companies |
| `useComputeMatch` | POST /v1/match/compute |
| `useMatchFeedback` | POST /v1/match/feedback |
| `useJobSearch` | GET /v1/jobs?query=... |

### Files: 16 new | Effort: 3 days

---

## Phase 4: Tailoring (Day 9-11)

### Pages (4)
| Route | Page | Purpose |
|-------|------|---------|
| `/(dashboard)/tailoring` | `TailoringHistoryPage` | Past tailored resumes |
| `/(dashboard)/tailoring/new` | `NewTailorPage` | Select resume + job + strategy |
| `/(dashboard)/tailoring/[id]` | `TailorDetailPage` | View tailored result |
| `/(dashboard)/tailoring/compare` | `ComparePage` | Side-by-side diff |

### Components (8)
| Component | Purpose |
|-----------|---------|
| `TailorRequestForm` | Resume picker + job picker + strategy dropdown |
| `DiffViewer` | Side-by-side before/after per section |
| `FactualityBadge` | Score badge: green (≥0.95), yellow, red |
| `ViolationList` | List of factuality violations |
| `VersionSelector` | Dropdown to pick version |
| `TailorPreview` | Formatted resume preview |
| `StrategyCard` | Conservative/Moderate/Aggressive selector |
| `ATSScoreBar` | ATS optimization score |

### API Integration (5)
| Hook | Endpoint |
|------|----------|
| `useTailorAnalyze` | POST /v1/tailoring/analyze |
| `useTailor` | POST /v1/tailoring/tailor |
| `useTailoringVersions` | GET /v1/tailoring/versions |
| `useTailoringCompare` | GET /v1/tailoring/compare |
| `useAcceptTailored` | POST /v1/tailoring/{id}/accept |

### Files: 14 new | Effort: 2.5 days

---

## Phase 5: Agent Chat (Day 11-13)

### Pages (2)
| Route | Page | Purpose |
|-------|------|---------|
| `/(dashboard)/agent` | `AgentPage` | Chat interface |
| `/(dashboard)/agent/history` | `AgentHistoryPage` | Past conversations |

### Components (6)
| Component | Purpose |
|-----------|---------|
| `ChatWindow` | Scrollable message container |
| `ChatMessage` | User/Agent message bubble with markdown |
| `ChatInput` | Text input + send button (Enter to send) |
| `IntentBadge` | Shows detected intent label |
| `StreamingIndicator` | Animated dots during response |
| `ExecutionCard` | History list item |

### API Integration (3)
| Hook | Endpoint |
|------|----------|
| `useAgent` | POST /v1/agent/execute (stream: false) |
| `useAgentStream` | POST /v1/agent/execute (stream: true, SSE) |
| `useAgentExecutions` | GET /v1/agent/executions |
| `useAgentExecution` | GET /v1/agent/executions/{id} |

### SSE Streaming
- Use `EventSource` or fetch with `ReadableStream`
- Parse `event:` and `data:` lines
- Update chat message in real-time as tokens arrive

### Files: 10 new | Effort: 2 days

---

## Phase 6: Knowledge Center (Day 13-14)

### Pages (2)
| Route | Page | Purpose |
|-------|------|---------|
| `/(dashboard)/knowledge` | `KnowledgePage` | Search + browse |
| `/(dashboard)/knowledge/upload` | `KnowledgeUploadPage` | Upload document |

### Components (5)
| Component | Purpose |
|-----------|---------|
| `KnowledgeSearch` | Search bar with instant results |
| `KnowledgeCard` | Document card with relevance score |
| `KnowledgeList` | Grid of document cards |
| `KnowledgeUpload` | File upload + title form |
| `RelevanceBadge` | Score badge for search results |

### API Integration (4)
| Hook | Endpoint |
|------|----------|
| `useKnowledgeSearch` | POST /v1/knowledge/search |
| `useKnowledgeIngest` | POST /v1/knowledge/ingest/document |
| `useKnowledgeDocuments` | GET /v1/knowledge/documents |
| `useDeleteKnowledgeDocument` | DELETE /v1/knowledge/documents/{id} |

### Files: 10 new | Effort: 1.5 days

---

## Phase 7: Admin Dashboard (Day 15)

### Pages (1)
| Route | Page | Purpose |
|-------|------|---------|
| `/(dashboard)/admin` | `AdminPage` | Stats dashboard |

### Components (5)
| Component | Purpose |
|-----------|---------|
| `StatCard` | Single metric card |
| `StatsGrid` | Responsive grid of cards |
| `TierDistribution` | Bar chart (free/pro/premium) |
| `StatusBreakdown` | Applications by status pie |
| `RecentActivityFeed` | Latest events list |

### API Integration (1)
| Hook | Endpoint |
|------|----------|
| `useAdminStats` | GET /v1/admin/stats (polling 30s) |

### Files: 7 new | Effort: 1 day

---

## Summary

| Phase | Feature | Pages | Components | API Hooks | Files | Effort |
|:-----:|---------|:-----:|:----------:|:---------:|:-----:|:------:|
| 0 | Foundation | 2 | 13 | 0 | 25 | 2 days |
| 1 | Auth | 3 | 3 | 3 | 8 | 1.5 days |
| 2 | Profile + Resume | 5 | 8 | 6 | 14 | 2 days |
| 3 | Jobs + Matching | 4 | 11 | 6 | 16 | 3 days |
| 4 | Tailoring | 4 | 8 | 5 | 14 | 2.5 days |
| 5 | Agent Chat | 2 | 6 | 4 | 10 | 2 days |
| 6 | Knowledge | 2 | 5 | 4 | 10 | 1.5 days |
| 7 | Admin | 1 | 5 | 1 | 7 | 1 day |
| **Total** | | **23** | **59** | **29** | **104** | **15.5 days** |

### Timeline: 3 weeks (with buffer)

```
Week 1: Phase 0-2 (Foundation + Auth + Profile/Resume)
Week 2: Phase 3-4 (Jobs/Matching + Tailoring)
Week 3: Phase 5-7 (Agent + Knowledge + Admin)
```

### Parallelizable Work
If multiple developers:
- Dev A: Phase 3 (Jobs) + Phase 6 (Knowledge) — data display heavy
- Dev B: Phase 4 (Tailoring) + Phase 5 (Agent) — interaction heavy
- Foundation (Phase 0-2) must be done first by either dev

### Critical Path
```
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4
                              ↘ Phase 5 → Phase 6
                              ↘ Phase 7 (can be done anytime after Phase 1)
```
