# Pathfinder — REST API Design

**Document Version:** 1.0
**Date:** 2026-06-17
**Role:** Senior Backend Architect
**Protocol:** HTTPS / REST / JSON
**Base URL:** `https://api.pathfinder.com/v1`

---

## Table of Contents

1. [API Conventions](#1-api-conventions)
2. [Authentication & Authorization](#2-authentication--authorization)
3. [Profiles & Resumes](#3-profiles--resumes)
4. [Job Search & Discovery](#4-job-search--discovery)
5. [Job Matching](#5-job-matching)
6. [Applications & Tracking](#6-applications--tracking)
7. [Interviews](#7-interviews)
8. [Documents — Resume Tailoring & Cover Letters](#8-documents--resume-tailoring--cover-letters)
9. [User Preferences](#9-user-preferences)
10. [Agent Execution](#10-agent-execution)
11. [Career Goals & Learning](#11-career-goals--learning)
12. [Communications](#12-communications)
13. [Analytics & Reporting](#13-analytics--reporting)
14. [Webhooks & Events](#14-webhooks--events)
15. [Error Reference](#15-error-reference)
16. [Rate Limiting & Tier Access](#16-rate-limiting--tier-access)

---

## 1. API Conventions

### 1.1 General Rules

| Rule | Detail |
|------|--------|
| **Protocol** | HTTPS only. HTTP requests receive 301 redirect. |
| **Base URL** | `https://api.pathfinder.com/v1` |
| **Content-Type** | `application/json` for all request and response bodies. Multipart for file uploads. |
| **Encoding** | UTF-8 |
| **Versioning** | URL prefix (`/v1/`). Breaking changes increment version. Deprecation via `Sunset` header. |
| **Timestamps** | ISO 8601 in UTC (`2026-06-17T14:30:00Z`). Millisecond precision. |
| **IDs** | UUID v7 (time-ordered) for all resource identifiers. |
| **Pagination** | Cursor-based for lists. Query params: `cursor` (opaque string), `limit` (default 20, max 100). |
| **Sorting** | Query param `sort` with descending prefix `-`. Example: `sort=-created_at`. |
| **Language** | `Accept-Language` header respected. Default `en-US`. |
| **Compression** | `Accept-Encoding: gzip, br` supported for responses > 1KB. |

### 1.2 Response Envelope

All responses use a consistent envelope:

```
SUCCESS (2xx):
{
  "data": { ... },                  // Resource or collection
  "meta": {                         // Present on list endpoints
    "cursor_next": "opaque_string", // Null if last page
    "count": 47,                    // Total matching (if computed)
    "limit": 20
  },
  "links": {                        // HATEOAS (present on resource endpoints)
    "self": "/v1/resource/id",
    "related": { ... }
  }
}

ERROR (4xx/5xx):
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "User-facing description",
    "details": [ ... ],             // Field-level errors (validation)
    "request_id": "uuid",           // For support correlation
    "docs_url": "https://docs.pathfinder.com/errors/RESOURCE_NOT_FOUND"
  }
}
```

### 1.3 Pagination

Cursor-based pagination on all list endpoints:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `cursor` | `string` | null | Opaque cursor from previous response `meta.cursor_next` |
| `limit` | `integer` | 20 | Items per page. Max 100. |
| `sort` | `string` | varies | Sort field. Prefix `-` for descending. |

Response includes `meta.cursor_next` — pass as `cursor` to get the next page. When `cursor_next` is `null`, you've reached the end.

### 1.4 Field Selection & Expansion

| Parameter | Type | Description |
|-----------|------|-------------|
| `fields` | `string` | Comma-separated field names to return (sparse fieldsets) |
| `expand` | `string` | Comma-separated related resources to embed (e.g., `expand=company,job`) |

---

## 2. Authentication & Authorization

### 2.1 Auth Endpoints

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ POST /v1/auth/register                                                        │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Create a new user account                                  │  │
│ │ AUTH:         None (public)                                              │  │
│ │ RATE LIMIT:   5 requests / minute / IP                                   │  │
│ │                                                                          │  │
│ │ REQUEST BODY:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "email": "string",              // REQUIRED. Valid email format│    │  │
│ │ │   "password": "string",           // REQUIRED. Min 8 chars,      │    │  │
│ │ │                                   //  1 upper, 1 lower, 1 number │    │  │
│ │ │   "full_name": "string",          // REQUIRED. 1-255 chars       │    │  │
│ │ │   "locale": "string",             // Optional. Default "en-US"   │    │  │
│ │ │   "timezone": "string",           // Optional. IANA tz format    │    │  │
│ │ │   "referral_code": "string",      // Optional                     │    │  │
│ │ │   "accept_terms": true            // REQUIRED. Must be true      │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ │                                                                          │  │
│ │ RESPONSE 201:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "data": {                                                      │    │  │
│ │ │     "user_id": "uuid",                                           │    │  │
│ │ │     "email": "string",                                           │    │  │
│ │ │     "full_name": "string",                                       │    │  │
│ │ │     "tier": "free",                                              │    │  │
│ │ │     "email_verified": false,                                     │    │  │
│ │ │     "created_at": "ISO8601"                                      │    │  │
│ │ │   },                                                             │    │  │
│ │ │   "links": { "verify_email": "/v1/auth/verify-email" }           │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ │                                                                          │  │
│ │ ERRORS:                                                                  │  │
│ │ · 400 VALIDATION_ERROR — email invalid, password too weak, name empty    │  │
│ │ · 409 RESOURCE_EXISTS — email already registered                         │  │
│ │ · 429 RATE_LIMIT_EXCEEDED — too many registration attempts               │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ POST /v1/auth/login                                                           │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Authenticate and receive tokens                            │  │
│ │ AUTH:         None (public)                                              │  │
│ │ RATE LIMIT:   10 requests / minute / IP                                  │  │
│ │                                                                          │  │
│ │ REQUEST BODY:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "email": "string",              // REQUIRED                     │    │  │
│ │ │   "password": "string",           // REQUIRED                     │    │  │
│ │ │   "remember_me": false            // Optional. Extends refresh    │    │  │
│ │ │                                   //   token TTL to 30 days       │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ │                                                                          │  │
│ │ RESPONSE 200:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "data": {                                                      │    │  │
│ │ │     "access_token": "jwt_string",    // 15 min TTL               │    │  │
│ │ │     "refresh_token": "opaque_string", // 7 day TTL, httpOnly     │    │  │
│ │ │     "token_type": "Bearer",                                       │    │  │
│ │ │     "expires_in": 900,              // seconds                    │    │  │
│ │ │     "user": {                                                     │    │  │
│ │ │       "user_id": "uuid",                                          │    │  │
│ │ │       "email": "string",                                          │    │  │
│ │ │       "full_name": "string",                                      │    │  │
│ │ │       "tier": "free",                                             │    │  │
│ │ │       "has_profile": false                                        │    │  │
│ │ │     }                                                             │    │  │
│ │ │   }                                                              │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ │                                                                          │  │
│ │ Set-Cookie: refresh_token=<token>; HttpOnly; Secure; SameSite=Strict;    │  │
│ │              Path=/v1/auth; Max-Age=604800                                │  │
│ │                                                                          │  │
│ │ ERRORS:                                                                  │  │
│ │ · 401 INVALID_CREDENTIALS — email or password incorrect                  │  │
│ │ · 423 ACCOUNT_LOCKED — too many failed attempts, try again in 15 min     │  │
│ │ · 403 EMAIL_NOT_VERIFIED — email verification required                   │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ POST /v1/auth/refresh                                                         │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Exchange refresh token for new access token                │  │
│ │ AUTH:         Refresh token cookie                                        │  │
│ │ RATE LIMIT:   30 requests / minute                                        │  │
│ │                                                                          │  │
│ │ REQUEST:      Cookie: refresh_token=<token>                              │  │
│ │                                                                          │  │
│ │ RESPONSE 200:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "data": {                                                      │    │  │
│ │ │     "access_token": "jwt_string",                                │    │  │
│ │ │     "refresh_token": "new_opaque_string", // Rotated             │    │  │
│ │ │     "token_type": "Bearer",                                      │    │  │
│ │ │     "expires_in": 900                                           │    │  │
│ │ │   }                                                              │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ │                                                                          │  │
│ │ ERRORS:                                                                  │  │
│ │ · 401 INVALID_TOKEN — refresh token expired, revoked, or reused          │  │
│ │   (token reuse triggers full session revocation — anti-theft)            │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ POST /v1/auth/logout                                                          │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Revoke current session tokens                              │  │
│ │ AUTH:         Bearer token (Authorization header)                        │  │
│ │                                                                          │  │
│ │ RESPONSE 204: No content. Session revoked. Refresh token cookie cleared. │  │
│ │                                                                          │  │
│ │ ERRORS:                                                                  │  │
│ │ · 401 UNAUTHORIZED — invalid or expired access token                     │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ POST /v1/auth/oauth/google                                                    │
│ POST /v1/auth/oauth/github                                                    │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Authenticate via OAuth provider                            │  │
│ │ AUTH:         None                                                       │  │
│ │                                                                          │  │
│ │ REQUEST BODY:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "code": "string",               // OAuth authorization code    │    │  │
│ │ │   "redirect_uri": "string",       // Must match registered URI   │    │  │
│ │ │   "code_verifier": "string"       // PKCE verifier               │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ │                                                                          │  │
│ │ RESPONSE 200: Same structure as POST /v1/auth/login                     │  │
│ │ RESPONSE 201: New account created (first OAuth login)                    │  │
│ │                                                                          │  │
│ │ ERRORS:                                                                  │  │
│ │ · 400 INVALID_OAUTH_CODE — code expired or invalid                       │  │
│ │ · 409 OAUTH_EMAIL_CONFLICT — email already registered with password      │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ POST /v1/auth/verify-email                                                    │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Verify email address via token                             │  │
│ │ AUTH:         None (token in body)                                       │  │
│ │                                                                          │  │
│ │ REQUEST BODY: { "token": "string" }   // From verification email         │  │
│ │ RESPONSE 200: { "data": { "email_verified": true } }                     │  │
│ │ ERRORS: 400 EXPIRED_TOKEN, 400 INVALID_TOKEN                             │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ POST /v1/auth/forgot-password                                                 │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Request password reset email                                │  │
│ │ AUTH:         None                                                       │  │
│ │ RATE LIMIT:   3 requests / hour / email                                   │  │
│ │                                                                          │  │
│ │ REQUEST BODY: { "email": "string" }                                      │  │
│ │ RESPONSE 202: { "data": { "message": "If the email exists, a reset       │  │
│ │              link has been sent." } }                                     │  │
│ │              // Always returns 202 to prevent email enumeration          │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ POST /v1/auth/reset-password                                                  │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Reset password with token                                   │  │
│ │ AUTH:         None (token in body)                                       │  │
│ │                                                                          │  │
│ │ REQUEST BODY:                                                            │  │
│ │ {                                                                        │  │
│ │   "token": "string",               // From reset email                   │  │
│ │   "password": "string"             // New password, same strength rules  │  │
│ │ }                                                                        │  │
│ │                                                                          │  │
│ │ RESPONSE 200: { "data": { "message": "Password updated." } }             │  │
│ │ ERRORS: 400 EXPIRED_TOKEN (1 hour TTL), 400 WEAK_PASSWORD                │  │
│ │                                                                          │  │
│ │ SIDE EFFECT: All existing sessions for this user are revoked.            │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Authentication Header

All authenticated requests require:

```
Authorization: Bearer <access_token>
```

### 2.3 Token Structure (JWT)

```
HEADER:  { "alg": "RS256", "typ": "JWT", "kid": "2026-06-01" }
PAYLOAD: {
  "sub": "user_uuid",           // Subject (user ID)
  "tenant_id": "tenant_uuid",   // Multi-tenant scope
  "tier": "pro",                // Subscription tier
  "roles": ["user"],            // RBAC roles
  "permissions": [              // Fine-grained permissions
    "jobs:read",
    "jobs:match",
    "resume:write",
    "applications:read",
    "applications:write",
    "agent:invoke",
    "analytics:read"
  ],
  "iat": 1718572800,            // Issued at
  "exp": 1718573700,            // Expires (15 min)
  "jti": "unique_token_id"      // For revocation checking
}
```

---

## 3. Profiles & Resumes

### 3.1 Profile Endpoints

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ GET /v1/profile                                                               │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Get the authenticated user's profile                       │  │
│ │ AUTH:         Bearer token                                               │  │
│ │ PERMISSION:   (implicit — own profile only)                              │  │
│ │                                                                          │  │
│ │ QUERY PARAMS:                                                            │  │
│ │ · expand: "skills,work_history,education,projects" — embeds sub-resources│  │
│ │                                                                          │  │
│ │ RESPONSE 200:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "data": {                                                      │    │  │
│ │ │     "profile_id": "uuid",                                        │    │  │
│ │ │     "version": 3,                                                │    │  │
│ │ │     "full_name": "David Chen",                                   │    │  │
│ │ │     "headline": "Senior Full-Stack Engineer",                    │    │  │
│ │ │     "email": "david@example.com",                                │    │  │
│ │ │     "phone": "+1-555-0123",                                      │    │  │
│ │ │     "location": { "city": "San Francisco", "state": "CA",        │    │  │
│ │ │                    "country": "US" },                             │    │  │
│ │ │     "summary": "LLM-generated professional summary...",           │    │  │
│ │ │     "work_experiences": [ ... ],     // if expand=work_history    │    │  │
│ │ │     "education": [ ... ],            // if expand=education       │    │  │
│ │ │     "skills": [ ... ],               // if expand=skills          │    │  │
│ │ │     "projects": [ ... ],             // if expand=projects        │    │  │
│ │ │     "certifications": [ ... ],                                    │    │  │
│ │ │     "languages": [ ... ],                                         │    │  │
│ │ │     "links": { ... },                                             │    │  │
│ │ │     "parsing_confidence": { "skills": 0.92, ... },                │    │  │
│ │ │     "created_at": "ISO8601",                                      │    │  │
│ │ │     "updated_at": "ISO8601"                                       │    │  │
│ │ │   },                                                              │    │  │
│ │ │   "links": {                                                      │    │  │
│ │ │     "self": "/v1/profile",                                        │    │  │
│ │ │     "versions": "/v1/profile/versions",                           │    │  │
│ │ │     "resumes": "/v1/resumes"                                      │    │  │
│ │ │   }                                                               │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ │                                                                          │  │
│ │ ERRORS: 401 UNAUTHORIZED                                                 │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ PUT /v1/profile                                                               │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Create or fully replace the user's profile                 │  │
│ │ AUTH:         Bearer token                                               │  │
│ │ PERMISSION:   profile:write                                              │  │
│ │                                                                          │  │
│ │ REQUEST BODY: (all fields optional — partial update via PATCH)           │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "full_name": "string",          // 1-255 chars                  │    │  │
│ │ │   "headline": "string",           // Max 200 chars                │    │  │
│ │ │   "phone": "string",              // E.164 format or null         │    │  │
│ │ │   "location": {                   // All fields optional          │    │  │
│ │ │     "city": "string",                                             │    │  │
│ │ │     "state": "string",                                            │    │  │
│ │ │     "country": "string"           // ISO 3166-1 alpha-2           │    │  │
│ │ │   },                                                              │    │  │
│ │ │   "work_experiences": [ ... ],                                     │    │  │
│ │ │   "education": [ ... ],                                            │    │  │
│ │ │   "skills": [ ... ],                                               │    │  │
│ │ │   "projects": [ ... ],                                             │    │  │
│ │ │   "certifications": [ ... ],                                       │    │  │
│ │ │   "languages": [ ... ],                                            │    │  │
│ │ │   "links": { ... }                                                │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ │                                                                          │  │
│ │ RESPONSE 200: Full profile resource (same structure as GET)              │  │
│ │ RESPONSE 201: Profile created (first time)                               │  │
│ │                                                                          │  │
│ │ VALIDATION:                                                              │  │
│ │ · work_experiences[].start_date ≤ end_date (if both present)             │  │
│ │ · work_experiences[].start_date ≥ 1950-01-01                             │  │
│ │ · education[].graduation_year: 1950–2035                                 │  │
│ │ · skills[].proficiency: one of [beginner, intermediate, advanced, expert]│  │
│ │ · Duplicate skill names rejected                                        │  │
│ │                                                                          │  │
│ │ ERRORS: 400 VALIDATION_ERROR, 401 UNAUTHORIZED                           │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ PATCH /v1/profile                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Partially update the user's profile                        │  │
│ │ AUTH:         Bearer token                                               │  │
│ │ PERMISSION:   profile:write                                              │  │
│ │                                                                          │  │
│ │ REQUEST BODY: JSON Merge Patch (RFC 7396) — only include changed fields  │  │
│ │ RESPONSE 200: Full updated profile                                      │  │
│ │                                                                          │  │
│ │ SIDE EFFECT: Profile version incremented. Embedding regenerated async.   │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ GET /v1/profile/versions                                                      │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      List profile version history                               │  │
│ │ AUTH:         Bearer token                                               │  │
│ │ PAGINATION:   Cursor-based, 20 per page                                  │  │
│ │                                                                          │  │
│ │ RESPONSE 200:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "data": [                                                      │    │  │
│ │ │     {                                                            │    │  │
│ │ │       "version": 3,                                              │    │  │
│ │ │       "change_summary": "Added Senior SWE role at Stripe",       │    │  │
│ │ │       "changed_fields": ["work_experiences"],                     │    │  │
│ │ │       "created_at": "ISO8601"                                    │    │  │
│ │ │     },                                                           │    │  │
│ │ │     { "version": 2, ... },                                       │    │  │
│ │ │     { "version": 1, ... }                                        │    │  │
│ │ │   ],                                                             │    │  │
│ │ │   "meta": { "cursor_next": null, "count": 3, "limit": 20 }      │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ GET /v1/profile/versions/{version}                                            │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Get a specific profile version snapshot                    │  │
│ │ PATH PARAMS:  version: integer (1-based)                                 │  │
│ │ RESPONSE 200: Full profile at that version                               │  │
│ │ ERRORS: 404 VERSION_NOT_FOUND                                            │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ POST /v1/profile/import/resume                                                │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Upload and parse a resume file to populate profile         │  │
│ │ AUTH:         Bearer token                                               │  │
│ │ PERMISSION:   profile:write                                              │  │
│ │ CONTENT-TYPE: multipart/form-data                                        │  │
│ │                                                                          │  │
│ │ REQUEST:                                                                 │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ file:    binary              // REQUIRED. PDF, DOCX, TXT          │    │  │
│ │ │          Max 10MB.           // Allowed: application/pdf,         │    │  │
│ │ │                              // application/vnd.openxmlformats-   │    │  │
│ │ │                              // officedocument.wordprocessingml.  │    │  │
│ │ │                              // document, text/plain              │    │  │
│ │ │ merge_strategy: "string"     // Optional. "replace" (default) or  │    │  │
│ │ │                              // "merge" (deduplicate + combine)   │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ │                                                                          │  │
│ │ RESPONSE 200:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "data": {                                                      │    │  │
│ │ │     "profile_id": "uuid",                                        │    │  │
│ │ │     "extracted_profile": { ... },  // Parsed, not yet saved      │    │  │
│ │ │     "parsing_confidence": {                                       │    │  │
│ │ │       "full_name": 0.98,                                         │    │  │
│ │ │       "work_experiences": 0.85,                                  │    │  │
│ │ │       "skills": 0.92,                                            │    │  │
│ │ │       "education": 0.96                                          │    │  │
│ │ │     },                                                           │    │  │
│ │ │     "conflicts": [               // Fields needing user review   │    │  │
│ │ │       { "field": "work_experiences[0].title",                     │    │  │
│ │ │         "resume_says": "Sr Software Engineer",                    │    │  │
│ │ │         "existing_profile": "Software Engineer II" }             │    │  │
│ │ │     ],                                                           │    │  │
│ │ │     "missing_fields": ["phone", "languages"]                     │    │  │
│ │ │   },                                                             │    │  │
│ │ │   "links": { "confirm": "/v1/profile/import/resume/confirm" }    │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ │                                                                          │
│ │ ERRORS:                                                                  │
│ │ · 400 UNSUPPORTED_FILE_TYPE — file is not PDF/DOCX/TXT                   │
│ │ · 400 FILE_TOO_LARGE — exceeds 10MB limit                                │
│ │ · 400 UNREADABLE_FILE — file corrupted or encrypted                      │
│ │ · 422 PARSING_FAILED — LLM extraction returned no usable data            │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ POST /v1/profile/import/resume/confirm                                        │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Confirm and apply the parsed profile from resume upload    │  │
│ │ AUTH:         Bearer token                                               │  │
│ │                                                                          │  │
│ │ REQUEST BODY:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "profile_id": "uuid",           // From import response         │    │  │
│ │ │   "confirmed_profile": { ... },   // User-edited version          │    │  │
│ │ │   "resolve_conflicts": {          // Conflict resolutions         │    │  │
│ │ │     "work_experiences[0].title": "use_resume" | "keep_existing"   │    │  │
│ │ │   }                                                              │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ │                                                                          │  │
│ │ RESPONSE 200: Updated profile. Embedding regenerated.                    │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ POST /v1/profile/import/linkedin                                              │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Import profile data from LinkedIn export                   │  │
│ │ AUTH:         Bearer token                                               │  │
│ │ CONTENT-TYPE: multipart/form-data                                        │  │
│ │                                                                          │  │
│ │ REQUEST: file: binary (PDF export from LinkedIn)                         │  │
│ │ RESPONSE 200: Same structure as resume import — extracted + conflicts    │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ POST /v1/profile/import/github                                                │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Import profile data from GitHub                            │  │
│ │ AUTH:         Bearer token                                               │  │
│ │                                                                          │  │
│ │ REQUEST BODY: { "username": "string" }  // GitHub username               │  │
│ │ RESPONSE 200:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "data": {                                                      │    │  │
│ │ │     "extracted": {                                               │    │  │
│ │ │       "languages": ["Python", "TypeScript", "Go"],               │    │  │
│ │ │       "repos_count": 47,                                         │    │  │
│ │ │       "top_repos": [ ... ],                                      │    │  │
│ │ │       "contributions_last_year": 312,                             │    │  │
│ │ │       "pinned_projects": [ ... ]                                 │    │  │
│ │ │     }                                                            │    │  │
│ │ │   }                                                              │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ │                                                                          │  │
│ │ ERRORS: 400 GITHUB_USERNAME_NOT_FOUND, 429 GITHUB_RATE_LIMITED          │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Resume Management Endpoints

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ GET /v1/resumes                                                               │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      List all resumes for the authenticated user                │  │
│ │ AUTH:         Bearer token                                               │  │
│ │ PAGINATION:   Cursor-based                                               │  │
│ │                                                                          │  │
│ │ QUERY PARAMS:                                                            │  │
│ │ · is_base: boolean — filter to base resume only                          │  │
│ │ · tailored_for_job_id: uuid — filter to resume for specific job          │  │
│ │ · sort: "-created_at" (default), "name", "-updated_at"                   │  │
│ │                                                                          │  │
│ │ RESPONSE 200:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "data": [                                                      │    │  │
│ │ │     {                                                            │    │  │
│ │ │       "resume_id": "uuid",                                       │    │  │
│ │ │       "name": "Base Resume — Full-Stack",                        │    │  │
│ │ │       "is_base": true,                                           │    │  │
│ │ │       "template_id": "modern_professional",                      │    │  │
│ │ │       "tailored_for_job_id": null,                               │    │  │
│ │ │       "tailored_for_role": null,                                 │    │  │
│ │ │       "file_format": "pdf",                                      │    │  │
│ │ │       "ats_parse_score": 92,                                     │    │  │
│ │ │       "created_at": "ISO8601",                                   │    │  │
│ │ │       "updated_at": "ISO8601"                                    │    │  │
│ │ │     }                                                            │    │  │
│ │ │   ],                                                             │    │  │
│ │ │   "meta": { "cursor_next": "...", "count": 5, "limit": 20 }     │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ POST /v1/resumes                                                              │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Create a new base resume                                   │  │
│ │ AUTH:         Bearer token                                               │  │
│ │ PERMISSION:   resume:write                                               │  │
│ │                                                                          │  │
│ │ REQUEST BODY:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "name": "string",               // REQUIRED. 1-255 chars       │    │  │
│ │ │   "template_id": "string",        // REQUIRED. See template list │    │  │
│ │ │   "content": { ... },             // REQUIRED. Structured resume │    │  │
│ │ │   "is_base": true                 // Default true                │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ │                                                                          │  │
│ │ RESPONSE 201: Created resume resource                                    │  │
│ │ VALIDATION: content must include required sections (summary, experience, │  │
│ │             education, skills). template_id must be a valid template.    │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ GET /v1/resumes/{resume_id}                                                   │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Get a specific resume with full content                    │  │
│ │ PATH PARAMS:  resume_id: uuid                                            │  │
│ │ QUERY PARAMS: expand: "versions" — includes edit history                 │  │
│ │ RESPONSE 200: Full resume resource                                       │  │
│ │ ERRORS: 404 RESUME_NOT_FOUND, 403 NOT_OWNER                              │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ PUT /v1/resumes/{resume_id}                                                   │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Update an existing resume                                  │  │
│ │ AUTH:         Bearer token                                               │  │
│ │ REQUEST BODY: Same as POST                                               │  │
│ │ RESPONSE 200: Updated resume                                             │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ DELETE /v1/resumes/{resume_id}                                                │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Delete a resume                                            │  │
│ │ RESPONSE 204: Resume deleted. Cannot delete resume linked to active app. │  │
│ │ VALIDATION: Cannot delete if resume is linked to an active application   │  │
│ │   (status != rejected, withdrawn, accepted). Must unlink first.          │  │
│ │ ERRORS: 409 RESUME_IN_USE — linked to N active applications              │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ GET /v1/resumes/{resume_id}/download                                         │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Download resume as formatted PDF                           │  │
│ │ QUERY PARAMS: format: "pdf" (default), "docx", "txt"                     │  │
│ │ RESPONSE 200: Binary file download                                       │  │
│ │   Content-Type: application/pdf (or corresponding MIME)                  │  │
│ │   Content-Disposition: attachment; filename="resume-name.pdf"            │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ GET /v1/resumes/templates                                                     │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      List available resume templates                             │  │
│ │ AUTH:         Bearer token                                               │  │
│ │                                                                          │  │
│ │ RESPONSE 200:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "data": [                                                      │    │  │
│ │ │     {                                                            │    │  │
│ │ │       "template_id": "modern_professional",                      │    │  │
│ │ │       "name": "Modern Professional",                             │    │  │
│ │ │       "description": "Clean, modern layout. Best for tech roles.",│   │  │
│ │ │       "preview_url": "https://cdn.pathfinder.com/...",           │    │  │
│ │ │       "ats_score": 94,                                           │    │  │
│ │ │       "tier_required": "free"                                    │    │  │
│ │ │     },                                                           │    │  │
│ │ │     { ... }                                                      │    │  │
│ │ │   ]                                                              │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Job Search & Discovery

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ GET /v1/jobs                                                                  │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Search and browse job listings                             │  │
│ │ AUTH:         Bearer token                                               │  │
│ │ PERMISSION:   jobs:read                                                  │  │
│ │ PAGINATION:   Cursor-based, 20 per page                                  │  │
│ │                                                                          │  │
│ │ QUERY PARAMS:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ PARAM              │ TYPE    │ DESCRIPTION                        │    │  │
│ │ │ ──────────────────┼────────┼─────────────────────────────────── │    │  │
│ │ │ q                  │ string  │ Free-text search (title, company,  │    │  │
│ │ │                    │         │  description). Uses FTS + vector.   │    │  │
│ │ │ title              │ string  │ Filter by job title (fuzzy match)  │    │  │
│ │ │ company_id         │ uuid    │ Filter by company                   │    │  │
│ │ │ location           │ string  │ "San Francisco, CA" or "Remote US" │    │  │
│ │ │ remote_policy      │ string  │ "remote", "hybrid", "onsite"       │    │  │
│ │ │ seniority          │ string  │ "junior","mid","senior","staff",   │    │  │
│ │ │                    │         │  "principal","lead","manager"       │    │  │
│ │ │ salary_min         │ integer │ Minimum salary filter               │    │  │
│ │ │ salary_max         │ integer │ Maximum salary filter               │    │  │
│ │ │ industry           │ string  │ "fintech","devtools","healthtech",  │    │  │
│ │ │                    │         │  ...                                │    │  │
│ │ │ company_size       │ string  │ "startup","mid","large","enterprise"│   │  │
│ │ │ funding_stage      │ string  │ "seed","series_a","series_b",...    │    │  │
│ │ │ posted_after       │ ISO8601 │ Jobs posted after this date         │    │  │
│ │ │ source_type        │ string  │ "linkedin","indeed","greenhouse",..│     │  │
│ │ │ sort               │ string  │ "-first_seen_at" (default),         │    │  │
│ │ │                    │         │  "-match_score" (when matching),     │    │  │
│ │ │                    │         │  "salary_max"                        │    │  │
│ │ │ cursor             │ string  │ Pagination cursor                   │    │  │
│ │ │ limit              │ integer │ 1-100, default 20                   │    │  │
│ │ │ fields             │ string  │ Sparse fieldsets                    │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ │                                                                          │  │
│ │ RESPONSE 200:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "data": [                                                      │    │  │
│ │ │     {                                                            │    │  │
│ │ │       "job_id": "uuid",                                          │    │  │
│ │ │       "canonical_job_id": "hash_string",                         │    │  │
│ │ │       "title": "Senior Software Engineer",                       │    │  │
│ │ │       "normalized_title": "Senior Software Engineer",            │    │  │
│ │ │       "company": {                                               │    │  │
│ │ │         "company_id": "uuid",                                    │    │  │
│ │ │         "name": "Stripe",                                        │    │  │
│ │ │         "logo_url": "https://cdn.pathfinder.com/...",            │    │  │
│ │ │         "industry": "fintech",                                   │    │  │
│ │ │         "size_range": "5001-10000",                              │    │  │
│ │ │         "funding_stage": "public"                                │    │  │
│ │ │       },                                                         │    │  │
│ │ │       "location": { "city": "San Francisco", "state": "CA",      │    │  │
│ │ │                      "country": "US" },                           │    │  │
│ │ │       "remote_policy": "hybrid",                                 │    │  │
│ │ │       "description_summary": "LLM-generated 3-sentence summary", │    │  │
│ │ │       "salary_range": { "min": 180000, "max": 260000,            │    │  │
│ │ │                          "currency": "USD", "source": "listed" },│    │  │
│ │ │       "tech_stack": ["Ruby", "Java", "AWS", "PostgreSQL"],       │    │  │
│ │ │       "seniority": "senior",                                     │    │  │
│ │ │       "source_type": "greenhouse",                               │    │  │
│ │ │       "source_url": "https://...",                               │    │  │
│ │ │       "application_url": "https://...",                          │    │  │
│ │ │       "first_seen_at": "ISO8601",                                │    │  │
│ │ │       "is_verified": true,                                       │    │  │
│ │ │       "urgency_flag": false                                      │    │  │
│ │ │     }                                                            │    │  │
│ │ │   ],                                                             │    │  │
│ │ │   "meta": {                                                      │    │  │
│ │ │     "cursor_next": "opaque_string",                              │    │  │
│ │ │     "count": 2347,                                               │    │  │
│ │ │     "limit": 20                                                  │    │  │
│ │ │   }                                                              │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ │                                                                          │  │
│ │ ERRORS: 400 INVALID_FILTER (unknown filter key), 422 (invalid value)     │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ GET /v1/jobs/{job_id}                                                         │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Get full job details                                       │  │
│ │ PATH PARAMS:  job_id: uuid                                               │  │
│ │ QUERY PARAMS: expand: "company,enrichment,similar_jobs"                  │  │
│ │                                                                          │  │
│ │ RESPONSE 200: Full job resource with description_clean, all enrichments  │  │
│ │   When expand=similar_jobs: embeds top-10 similar jobs via vector search │  │
│ │                                                                          │  │
│ │ ERRORS: 404 JOB_NOT_FOUND, 410 JOB_EXPIRED                               │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ GET /v1/jobs/{job_id}/similar                                                 │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Find similar jobs via vector embedding                     │  │
│ │ QUERY PARAMS: limit: 10 (default), max 50                                │  │
│ │ RESPONSE 200: List of similar job listings with similarity scores        │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ GET /v1/companies                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Search and browse companies                                │  │
│ │ AUTH:         Bearer token                                               │  │
│ │ PAGINATION:   Cursor-based                                               │  │
│ │                                                                          │  │
│ │ QUERY PARAMS: q, industry, size_range, funding_stage, location           │  │
│ │                                                                          │  │
│ │ RESPONSE 200: List of companies with basic info, logo, industry tags     │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ GET /v1/companies/{company_id}                                                │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Get full company details                                   │  │
│ │ QUERY PARAMS: expand: "jobs,reviews,culture"                             │  │
│ │                                                                          │  │
│ │ RESPONSE 200:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "data": {                                                      │    │  │
│ │ │     "company_id": "uuid",                                        │    │  │
│ │ │     "name": "Stripe",                                            │    │  │
│ │ │     "canonical_name": "stripe",                                  │    │  │
│ │ │     "website": "https://stripe.com",                             │    │  │
│ │ │     "industry": "fintech",                                       │    │  │
│ │ │     "industry_tags": ["payments", "developer-tools", "api"],     │    │  │
│ │ │     "size_range": "5001-10000",                                  │    │  │
│ │ │     "employee_count": 8500,                                      │    │  │
│ │ │     "funding_stage": "public",                                   │    │  │
│ │ │     "total_funding": 2200000000,                                 │    │  │
│ │ │     "founded_year": 2010,                                        │    │  │
│ │ │     "headquarters": { "city": "South San Francisco",             │    │  │
│ │ │                        "state": "CA", "country": "US" },          │    │  │
│ │ │     "tech_stack": ["Ruby", "Java", "Scala", "AWS", ...],         │    │  │
│ │ │     "culture_tags": {                                            │    │  │
│ │ │       "engineering_driven": 0.95,                                │    │  │
│ │ │       "remote_friendly": 0.85,                                   │    │  │
│ │ │       "fast_paced": 0.70                                         │    │  │
│ │ │     },                                                           │    │  │
│ │ │     "glassdoor_rating": 4.3,                                     │    │  │
│ │ │     "career_page_url": "https://stripe.com/jobs",                │    │  │
│ │ │     "active_jobs_count": 234,        // if expand=jobs            │    │  │
│ │ │     "created_at": "ISO8601"                                      │    │  │
│ │ │   }                                                              │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Job Matching

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ POST /v1/match                                                                │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Compute match scores for jobs against the user's profile   │  │
│ │ AUTH:         Bearer token                                               │  │
│ │ PERMISSION:   jobs:match                                                 │  │
│ │                                                                          │  │
│ │ REQUEST BODY:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "job_ids": ["uuid", ...],        // OPTIONAL. Max 100.         │    │  │
│ │ │                                    // If omitted: match against   │    │  │
│ │ │                                    // user's saved/discovered     │    │  │
│ │ │                                    // jobs (auto-scope)           │    │  │
│ │ │   "filters": {                    // OPTIONAL. Narrow job pool   │    │  │
│ │ │     "location": "string",                                          │    │  │
│ │ │     "remote_policy": "string",                                     │    │  │
│ │ │     "seniority": "string",                                         │    │  │
│ │ │     "salary_min": 150000,                                          │    │  │
│ │ │     "industry": "fintech"                                          │    │  │
│ │ │   },                                                              │    │  │
│ │ │   "include_explanation": true,     // Default true                │    │  │
│ │ │   "include_salary_estimate": true, // Default false               │    │  │
│ │ │   "limit": 20                     // Default 20, max 50           │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ │                                                                          │  │
│ │ RESPONSE 200:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "data": {                                                      │    │  │
│ │ │     "matches": [                                                 │    │  │
│ │ │       {                                                          │    │  │
│ │ │         "job_id": "uuid",                                        │    │  │
│ │ │         "job": { ... },            // Condensed job resource     │    │  │
│ │ │         "overall_score": 87,       // 0-100                      │    │  │
│ │ │         "dimensions": {                                          │    │  │
│ │ │           "skill_match": 91,                                     │    │  │
│ │ │           "experience_match": 82,                                │    │  │
│ │ │           "tech_stack_overlap": 88,                              │    │  │
│ │ │           "location_fit": 95,                                    │    │  │
│ │ │           "compensation_alignment": 78,                          │    │  │
│ │ │           "culture_fit_estimate": 85                             │    │  │
│ │ │         },                                                       │    │  │
│ │ │         "explanation": [                                         │    │  │
│ │ │           "Strong Python match — your #1 skill (8 years)",       │    │  │
│ │ │           "Remote policy aligns with your preference",           │    │  │
│ │ │           "Fintech — your highest-response industry (3.7×)",     │    │  │
│ │ │           "Concern: They want 5+ years management experience"    │    │  │
│ │ │         ],                                                       │    │  │
│ │ │         "salary_estimate": {       // if requested               │    │  │
│ │ │           "min": 185000, "max": 255000,                          │    │  │
│ │ │           "confidence": 0.72, "source": "ml_prediction"          │    │  │
│ │ │         },                                                       │    │  │
│ │ │         "ranking_signals": {                                     │    │  │
│ │ │           "freshness_boost": 0.05,                               │    │  │
│ │ │           "urgency_flag": false,                                 │    │  │
│ │ │           "company_preference_match": true                       │    │  │
│ │ │         },                                                       │    │  │
│ │ │         "dealbreakers_hit": [],                                  │    │  │
│ │ │         "match_generated_at": "ISO8601"                          │    │  │
│ │ │       }                                                          │    │  │
│ │ │     ],                                                           │    │  │
│ │ │     "matches_computed": 234,                                     │    │  │
│ │ │     "profile_used_version": 3,                                   │    │  │
│ │ │     "preferences_used_version": 12                               │    │  │
│ │ │   },                                                             │    │  │
│ │ │   "meta": { "cursor_next": "...", "limit": 20 }                 │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ │                                                                          │  │
│ │ PERFORMANCE: P95 < 2s for batch of 100 jobs. Streamed via SSE if > 50.  │  │
│ │                                                                          │  │
│ │ ERRORS:                                                                  │  │
│ │ · 400 NO_PROFILE — user has no profile, matching impossible              │  │
│ │ · 400 JOB_IDS_LIMIT — more than 100 job_ids provided                     │  │
│ │ · 422 INVALID_FILTER — unrecognized filter key                           │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ POST /v1/match/feedback                                                       │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Submit explicit feedback on a match for learning           │  │
│ │ AUTH:         Bearer token                                               │  │
│ │                                                                          │  │
│ │ REQUEST BODY:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "job_id": "uuid",               // REQUIRED                     │    │  │
│ │ │   "feedback_type": "string",      // REQUIRED                     │    │  │
│ │ │                                   // "thumbs_up", "thumbs_down",  │    │  │
│ │ │                                   // "not_interested", "save",    │    │  │
│ │ │                                   // "dismiss"                    │    │  │
│ │ │   "reason": "string",             // OPTIONAL. "Wrong location"   │    │  │
│ │ │   "match_id": "uuid"              // From the match response      │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ │                                                                          │  │
│ │ RESPONSE 202: Feedback accepted. Triggers real-time re-ranking.          │  │
│ │                                                                          │  │
│ │ SIDE EFFECTS:                                                            │  │
│ │ · Episodic memory stored (feedback_explicit)                             │  │
│ │ · User preference weights updated asynchronously                         │  │
│ │ · Job re-ranked in subsequent match queries                               │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Applications & Tracking

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ GET /v1/applications                                                          │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      List all applications for the authenticated user           │  │
│ │ AUTH:         Bearer token                                               │  │
│ │ PERMISSION:   applications:read                                          │  │
│ │ PAGINATION:   Cursor-based, 20 per page                                  │  │
│ │                                                                          │  │
│ │ QUERY PARAMS:                                                            │  │
│ │ · status: string — filter by status (comma-separated for multiple)       │  │
│ │ · is_archived: boolean — default false                                   │  │
│ │ · sort: "-last_updated_at" (default), "-applied_at", "company_name"      │  │
│ │ · expand: "job,company,resume,cover_letter,interviews,tasks"             │  │
│ │                                                                          │  │
│ │ RESPONSE 200:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "data": [                                                      │    │  │
│ │ │     {                                                            │    │  │
│ │ │       "application_id": "uuid",                                  │    │  │
│ │ │       "status": "technical_interview",                           │    │  │
│ │ │       "job": { "job_id": "uuid", "title": "...",                 │    │  │
│ │ │                "company": { "name": "Stripe", "logo_url":"..." }},│   │  │
│ │ │       "resume": { "resume_id": "uuid", "name": "..." },          │    │  │
│ │ │       "cover_letter": { "cover_letter_id": "uuid" },             │    │  │
│ │ │       "match_score_at_apply": 87,                                │    │  │
│ │ │       "source_channel": "pathfinder_match",                      │    │  │
│ │ │       "applied_at": "ISO8601",                                   │    │  │
│ │ │       "last_updated_at": "ISO8601",                              │    │  │
│ │ │       "next_follow_up_at": "ISO8601",                            │    │  │
│ │ │       "is_archived": false,                                      │    │  │
│ │ │       "interviews": [ ... ],        // if expand=interviews      │    │  │
│ │ │       "tasks": [ ... ],             // if expand=tasks           │    │  │
│ │ │       "status_history": [                                        │    │  │
│ │ │         { "status": "applied", "at": "ISO8601" },                │    │  │
│ │ │         { "status": "phone_screen", "at": "ISO8601" },           │    │  │
│ │ │         { "status": "technical_interview", "at": "ISO8601" }     │    │  │
│ │ │       ]                                                          │    │  │
│ │ │     }                                                            │    │  │
│ │ │   ],                                                             │    │  │
│ │ │   "meta": {                                                      │    │  │
│ │ │     "cursor_next": "...",                                        │    │  │
│ │ │     "count": 47,                                                 │    │  │
│ │ │     "limit": 20,                                                 │    │  │
│ │ │     "pipeline_summary": {                                        │    │  │
│ │ │       "saved": 12, "applied": 8, "phone_screen": 3,             │    │  │
│ │ │       "technical_interview": 2, "onsite": 1, "offer": 0,        │    │  │
│ │ │       "rejected": 15, "withdrawn": 6                             │    │  │
│ │ │     }                                                            │    │  │
│ │ │   }                                                              │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ POST /v1/applications                                                         │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Create a new application (save or apply to a job)          │  │
│ │ AUTH:         Bearer token                                               │  │
│ │ PERMISSION:   applications:write                                         │  │
│ │                                                                          │  │
│ │ REQUEST BODY:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "job_id": "uuid",               // REQUIRED                     │    │  │
│ │ │   "status": "string",             // REQUIRED. "saved" or         │    │  │
│ │ │                                   // "applied"                    │    │  │
│ │ │   "resume_id": "uuid",            // REQUIRED if status=applied   │    │  │
│ │ │   "cover_letter_id": "uuid",      // OPTIONAL                     │    │  │
│ │ │   "source_channel": "string",     // OPTIONAL. Default            │    │  │
│ │ │                                   // "pathfinder_match"           │    │  │
│ │ │   "notes": "string"               // OPTIONAL                     │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ │                                                                          │  │
│ │ RESPONSE 201: Created application                                        │  │
│ │                                                                          │  │
│ │ VALIDATION:                                                              │  │
│ │ · job_id must reference an active job listing                            │  │
│ │ · Duplicate application (same user + same job) returns 409               │  │
│ │ · resume_id must belong to the authenticated user                        │  │
│ │                                                                          │  │
│ │ ERRORS:                                                                  │  │
│ │ · 400 MISSING_RESUME — status=applied but no resume_id provided          │  │
│ │ · 404 JOB_NOT_FOUND — job_id doesn't exist or is expired                 │  │
│ │ · 409 DUPLICATE_APPLICATION — already applied to this job                │  │
│ │ · 403 NOT_RESUME_OWNER — resume belongs to different user                │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ GET /v1/applications/{application_id}                                         │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Get full application details                               │  │
│ │ PATH PARAMS:  application_id: uuid                                       │  │
│ │ QUERY PARAMS: expand: "job,company,resume,cover_letter,interviews,       │  │
│ │                        tasks,communications,documents"                   │  │
│ │ RESPONSE 200: Full application resource with all requested expansions    │  │
│ │ ERRORS: 404 APPLICATION_NOT_FOUND, 403 NOT_OWNER                         │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ PATCH /v1/applications/{application_id}                                       │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Update application status or details                       │  │
│ │ AUTH:         Bearer token                                               │  │
│ │ PERMISSION:   applications:write                                         │  │
│ │                                                                          │  │
│ │ REQUEST BODY (JSON Merge Patch):                                         │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "status": "phone_screen",       // Status transition            │    │  │
│ │ │   "notes": "Recruiter reached out via email",                    │    │  │
│ │ │   "next_follow_up_at": "ISO8601",                                │    │  │
│ │ │   "is_archived": true                                            │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ │                                                                          │  │
│ │ VALID STATUS TRANSITIONS:                                                │  │
│ │ · saved → applied, withdrawn                                             │  │
│ │ · applied → phone_screen, technical_interview, onsite, take_home,       │  │
│ │            rejected, withdrawn, ghosted                                  │  │
│ │ · phone_screen → technical_interview, onsite, rejected, withdrawn        │  │
│ │ · technical_interview → onsite, offer, rejected, withdrawn               │  │
│ │ · onsite → offer, rejected, withdrawn                                    │  │
│ │ · offer → accepted, rejected, withdrawn                                  │  │
│ │ · accepted/rejected/withdrawn/ghosted → (terminal — no further changes)  │  │
│ │                                                                          │  │
│ │ RESPONSE 200: Updated application                                        │  │
│ │                                                                          │  │
│ │ SIDE EFFECTS:                                                            │  │
│ │ · Status change recorded in status_history                               │  │
│ │ · Episodic memory stored (application_event)                             │  │
│ │ · Event emitted to stream:applications                                   │  │
│ │ · If status → offer: triggers interview prep suggestions                │  │
│ │                                                                          │  │
│ │ ERRORS: 400 INVALID_STATUS_TRANSITION, 404 NOT_FOUND, 403 NOT_OWNER     │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ DELETE /v1/applications/{application_id}                                      │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Delete a saved application (applied cannot be deleted)     │  │
│ │ VALIDATION: Only applications with status = "saved" can be deleted.      │  │
│ │   Applied applications must be archived or marked withdrawn instead.     │  │
│ │ RESPONSE 204: Deleted                                                    │  │
│ │ ERRORS: 409 CANNOT_DELETE_APPLIED — archive or withdraw instead          │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ GET /v1/applications/{application_id}/tasks                                   │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      List tasks for an application                              │  │
│ │ RESPONSE 200: List of tasks with due dates, completion status            │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ POST /v1/applications/{application_id}/tasks                                  │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Create a task for an application                           │  │
│ │ REQUEST: { "title": "string", "description": "string",                   │  │
│ │            "due_at": "ISO8601", "task_type": "follow_up" }               │  │
│ │ RESPONSE 201: Created task                                               │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ PATCH /v1/applications/{application_id}/tasks/{task_id}                       │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Complete or update a task                                  │  │
│ │ REQUEST: { "is_completed": true, "completed_at": "ISO8601" }             │  │
│ │ RESPONSE 200: Updated task                                               │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ POST /v1/applications/{application_id}/link-email                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Link an email thread to an application (for auto-tracking) │  │
│ │ AUTH:         Bearer token + email_integration scope                     │  │
│ │ REQUEST: { "email_thread_id": "string", "email_provider": "gmail" }      │  │
│ │ RESPONSE 200: Email linked. Future emails in thread auto-classified.     │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Interviews

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ GET /v1/applications/{application_id}/interviews                              │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      List all interviews for an application                     │  │
│ │ RESPONSE 200: List of interviews with stage, schedule, status, outcome   │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ POST /v1/applications/{application_id}/interviews                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Schedule or log an interview                               │  │
│ │ AUTH:         Bearer token                                               │  │
│ │                                                                          │  │
│ │ REQUEST BODY:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "stage": "string",              // REQUIRED                     │    │  │
│ │ │   "scheduled_at": "ISO8601",      // REQUIRED                     │    │  │
│ │ │   "duration_minutes": 45,         // Default 60                   │    │  │
│ │ │   "interviewer_name": "string",                                    │    │  │
│ │ │   "interviewer_role": "string",   // "hiring_manager","peer",etc. │    │  │
│ │ │   "location": "zoom",             // "zoom","phone","onsite",etc. │    │  │
│ │ │   "meeting_link": "string",                                        │    │  │
│ │ │   "notes": "string"                                               │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ │                                                                          │  │
│ │ RESPONSE 201: Created interview                                          │  │
│ │                                                                          │  │
│ │ SIDE EFFECTS: Interview prep material generation triggered async.        │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ PATCH /v1/applications/{application_id}/interviews/{interview_id}             │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Update interview details, record notes/feedback/outcome    │  │
│ │ REQUEST BODY (JSON Merge Patch):                                         │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "status": "completed",                                          │    │  │
│ │ │   "outcome": "passed",           // "passed","failed","pending"   │    │  │
│ │ │   "notes": "Discussed system design...",                          │    │  │
│ │ │   "feedback": {                                                   │    │  │
│ │ │     "technical_rating": 4,       // 1-5                           │    │  │
│ │ │     "communication_rating": 5,                                    │    │  │
│ │ │     "strengths": ["System design", "Problem solving"],            │    │  │
│ │ │     "weaknesses": ["Could improve on explaining trade-offs"],     │    │  │
│ │ │     "interviewer_notes": "Strong candidate..."                   │    │  │
│ │ │   }                                                              │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ │ RESPONSE 200: Updated interview                                          │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ POST /v1/interviews/{interview_id}/prep                                      │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Generate interview preparation materials                   │  │
│ │ AUTH:         Bearer token                                               │  │
│ │ PERMISSION:   agent:invoke (triggers Interview Agent)                    │  │
│ │                                                                          │  │
│ │ REQUEST BODY:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "include": ["company_brief", "behavioral_questions",            │    │  │
│ │ │              "technical_questions", "questions_to_ask",           │    │  │
│ │ │              "salary_talking_points"],                            │    │  │
│ │ │   "focus_areas": ["system_design", "leadership"]                  │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ │                                                                          │  │
│ │ RESPONSE 200:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "data": {                                                      │    │  │
│ │ │     "interview_id": "uuid",                                      │    │  │
│ │ │     "company_brief": {                                           │    │  │
│ │ │       "summary": "Stripe is a global payments infrastructure...",│    │  │
│ │ │       "recent_news": [...],                                      │    │  │
│ │ │       "tech_stack": [...],                                       │    │  │
│ │ │       "culture_signals": [...],                                  │    │  │
│ │ │       "interview_process": "Typically: phone screen → ..."       │    │  │
│ │ │     },                                                           │    │  │
│ │ │     "behavioral_questions": [                                    │    │  │
│ │ │       {                                                          │    │  │
│ │ │         "question": "Tell me about a time you led a complex      │    │  │
│ │ │                      technical project.",                        │    │  │
│ │ │         "star_outline": {                                        │    │  │
│ │ │           "situation": "At Stripe, payment API redesign...",     │    │  │
│ │ │           "task": "Lead migration from monolith to microservices",│   │  │
│ │ │           "action": "Designed phased rollout, coordinated 4 teams",│  │  │
│ │ │           "result": "40% latency reduction, zero downtime"       │    │  │
│ │ │         },                                                       │    │  │
│ │ │         "tips": ["Emphasize cross-team coordination", ...]       │    │  │
│ │ │       }                                                          │    │  │
│ │ │     ],                                                           │    │  │
│ │ │     "technical_questions": [ ... ],                              │    │  │
│ │ │     "questions_to_ask": [                                        │    │  │
│ │ │       {                                                          │    │  │
│ │ │         "question": "How does the engineering team handle        │    │  │
│ │ │                      technical debt alongside feature work?",    │    │  │
│ │ │         "who_to_ask": "hiring_manager",                          │    │  │
│ │ │         "why_relevant": "Signals engineering culture maturity"   │    │  │
│ │ │       }                                                          │    │  │
│ │ │     ],                                                           │    │  │
│ │ │     "salary_talking_points": { ... },                            │    │  │
│ │ │     "generated_at": "ISO8601"                                    │    │  │
│ │ │   },                                                             │    │  │
│ │ │   "links": { "regenerate": "/v1/interviews/{id}/prep" }          │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ │                                                                          │  │
│ │ TIER RESTRICTION: Free tier — 5 prep generations/month                   │  │
│ │                   Pro/Premium — unlimited                                │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Documents — Resume Tailoring & Cover Letters

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ POST /v1/documents/tailor-resume                                              │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Generate a job-tailored resume variant (invokes Resume     │  │
│ │               Agent via Supervisor)                                      │  │
│ │ AUTH:         Bearer token                                               │  │
│ │ PERMISSION:   agent:invoke, resume:write                                 │  │
│ │                                                                          │  │
│ │ REQUEST BODY:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "job_id": "uuid",               // REQUIRED                     │    │  │
│ │ │   "base_resume_id": "uuid",       // REQUIRED. Base to tailor    │    │  │
│ │ │   "template_id": "string",        // OPTIONAL. Override template │    │  │
│ │ │   "emphasis": ["skills", "achievements"], // OPTIONAL. What to   │    │  │
│ │ │                                         // emphasize in tailoring│    │  │
│ │ │   "tone": "professional"           // OPTIONAL. Default from prefs│   │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ │                                                                          │  │
│ │ RESPONSE 200 (streaming via SSE if supported, or polling):               │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "data": {                                                      │    │  │
│ │ │     "tailored_resume_id": "uuid",                                │    │  │
│ │ │     "base_resume_id": "uuid",                                    │    │  │
│ │ │     "job_id": "uuid",                                            │    │  │
│ │ │     "content": { ... },            // Full structured resume     │    │  │
│ │ │     "diff": {                      // Changes from base resume   │    │  │
│ │ │       "summary": { "before": "...", "after": "..." },            │    │  │
│ │ │       "skills_order": { "before": [...], "after": [...] },       │    │  │
│ │ │       "modified_bullets": [                                      │    │  │
│ │ │         { "section": "work_experiences[0]",                      │    │  │
│ │ │           "before": "Built REST APIs...",                        │    │  │
│ │ │           "after": "Designed and built payment REST APIs         │    │  │
│ │ │                    handling $1B+ annually..." }                  │    │  │
│ │ │       ],                                                         │    │  │
│ │ │       "added_keywords": ["payment systems", "API design"],        │    │  │
│ │ │       "removed_nothing": true                                    │    │  │
│ │ │     },                                                           │    │  │
│ │ │     "ats_keyword_coverage": {                                    │    │  │
│ │ │       "before": 42, "after": 78, "target_threshold": 70          │    │  │
│ │ │     },                                                           │    │  │
│ │ │     "honest_gaps": [                                             │    │  │
│ │ │       { "requirement": "Kubernetes experience",                  │    │  │
│ │ │         "user_has": false,                                       │    │  │
│ │ │         "suggestion": "Consider adding 'Learning Kubernetes' or  │    │  │
│ │ │                        be prepared to address in interview" }    │    │  │
│ │ │     ],                                                           │    │  │
│ │ │     "factuality_score": 1.0,                                     │    │  │
│ │ │     "generation_cost": { "tokens": 4200, "cost_usd": 0.008 }    │    │  │
│ │ │   },                                                             │    │  │
│ │ │   "links": {                                                     │    │  │
│ │ │     "accept": "/v1/documents/tailor-resume/{id}/accept",         │    │  │
│ │ │     "reject": "/v1/documents/tailor-resume/{id}/reject",         │    │  │
│ │ │     "download": "/v1/documents/tailor-resume/{id}/download"      │    │  │
│ │ │   }                                                              │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ │                                                                          │  │
│ │ ERRORS:                                                                  │  │
│ │ · 400 NO_BASE_RESUME — user has no base resume to tailor from            │  │
│ │ · 404 JOB_NOT_FOUND                                                      │  │
│ │ · 422 TAILORING_FAILED — LLM unable to generate (e.g., empty profile)   │  │
│ │ · 429 AGENT_RATE_LIMITED — tier limit reached                            │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ POST /v1/documents/tailor-resume/{tailored_id}/accept                         │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Accept the tailored resume (saves as a variant)            │  │
│ │ REQUEST:      { "name": "Stripe — Senior SWE", "make_base": false }     │  │
│ │ RESPONSE 200: Resume saved. Returns resume_id for use in applications.   │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ POST /v1/documents/generate-cover-letter                                      │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Generate a personalized cover letter (invokes Cover Letter │  │
│ │               Agent via Supervisor)                                      │  │
│ │ AUTH:         Bearer token                                               │  │
│ │ PERMISSION:   agent:invoke                                               │  │
│ │                                                                          │  │
│ │ REQUEST BODY:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "job_id": "uuid",               // REQUIRED                     │    │  │
│ │ │   "resume_id": "uuid",            // For consistency              │    │  │
│ │ │   "tone": "professional",         // "professional","enthusiastic"│    │  │
│ │ │                                  //  "concise","creative"         │    │  │
│ │ │   "emphasize": ["fintech experience", "API design"],              │    │  │
│ │ │   "additional_notes": "string"    // User-provided context        │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ │                                                                          │  │
│ │ RESPONSE 200:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "data": {                                                      │    │  │
│ │ │     "cover_letter_id": "uuid",                                   │    │  │
│ │ │     "content": "Dear Hiring Manager,\n\n...",                    │    │  │
│ │ │     "tone": "professional",                                      │    │  │
│ │ │     "company_research_used": [                                   │    │  │
│ │ │       "Recent $2.2B funding round (Series I, March 2026)",       │    │  │
│ │ │       "Tech blog post on payment API redesign"                   │    │  │
│ │ │     ],                                                           │    │  │
│ │ │     "factuality_score": 1.0,                                     │    │  │
│ │ │     "personalization_score": 0.92                                │    │  │
│ │ │   },                                                             │    │  │
│ │ │   "links": {                                                     │    │  │
│ │ │     "accept": "/v1/documents/cover-letter/{id}/accept",           │    │  │
│ │ │     "edit": "/v1/documents/cover-letter/{id}/edit"               │    │  │
│ │ │   }                                                              │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ GET /v1/documents/cover-letters                                               │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      List user's cover letters                                  │  │
│ │ QUERY PARAMS: application_id (filter), sort                             │  │
│ │ RESPONSE 200: Paginated list                                             │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ GET /v1/documents/cover-letters/{id}                                          │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Get a specific cover letter                                │  │
│ │ RESPONSE 200: Full cover letter with content                              │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ PUT /v1/documents/cover-letters/{id}                                          │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Edit a cover letter manually                               │  │
│ │ REQUEST: { "content": "string", "tone": "string" }                       │  │
│ │ RESPONSE 200: Updated cover letter                                       │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ DELETE /v1/documents/cover-letters/{id}                                       │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Delete a cover letter                                      │  │
│ │ VALIDATION: Cannot delete if linked to active application                │  │
│ │ RESPONSE 204                                                             │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. User Preferences

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ GET /v1/preferences                                                           │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Get current user preferences                                │  │
│ │ AUTH:         Bearer token                                               │  │
│ │                                                                          │  │
│ │ RESPONSE 200:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "data": {                                                      │    │  │
│ │ │     "preference_id": "uuid",                                     │    │  │
│ │ │     "version": 12,                                               │    │  │
│ │ │     "preferences": {                                             │    │  │
│ │ │       "role_preferences": {                                      │    │  │
│ │ │         "target_titles": ["Senior SWE", "Staff Engineer"],       │    │  │
│ │ │         "excluded_titles": ["Principal Engineer"]                │    │  │
│ │ │       },                                                         │    │  │
│ │ │       "compensation": { "minimum_base": 180000, ... },           │    │  │
│ │ │       "location": { "regions": [...], "remote_policy": "..." },  │    │  │
│ │ │       "company_preferences": { "size": {...}, "industry": {...} },│   │  │
│ │ │       "culture_priorities": { ... },                              │    │  │
│ │ │       "priority_weights": {                                       │    │  │
│ │ │         "compensation": 0.30, "growth": 0.25, "tech_stack": 0.20,│    │  │
│ │ │         "culture": 0.15, "location": 0.10                        │    │  │
│ │ │       },                                                         │    │  │
│ │ │       "dealbreakers": [...],                                     │    │  │
│ │ │       "communication_style": { "tone": "...", "verbosity": "..." },│  │  │
│ │ │       "search_behavior": { "mode": "active", ... }               │    │  │
│ │ │     },                                                           │    │  │
│ │ │     "source_breakdown": {                                        │    │  │
│ │ │       "compensation.minimum_base": { "explicit": 1.0, "implicit": 0.0 }││
│ │ │     },                                                           │    │  │
│ │ │     "confidence_scores": { ... },                                │    │  │
│ │ │     "updated_at": "ISO8601"                                      │    │  │
│ │ │   },                                                             │    │  │
│ │ │   "links": { "versions": "/v1/preferences/versions" }            │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ PUT /v1/preferences                                                           │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Replace all preferences                                    │  │
│ │ AUTH:         Bearer token                                               │  │
│ │ PERMISSION:   preferences:write                                          │  │
│ │                                                                          │  │
│ │ REQUEST BODY: Full preference object (same structure as GET response)    │  │
│ │                                                                          │  │
│ │ RESPONSE 200: Updated preferences. Version incremented.                  │  │
│ │                                                                          │  │
│ │ SIDE EFFECTS:                                                            │  │
│ │ · Episodic memory stored (preference_signal — explicit)                  │  │
│ │ · Previous version archived                                              │  │
│ │ · Matching cache invalidated for this user                               │  │
│ │                                                                          │  │
│ │ ERRORS: 400 VALIDATION_ERROR — invalid weight values (must sum to 1.0    │  │
│ │         for priority_weights), invalid enum values                       │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ PATCH /v1/preferences                                                         │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Partially update preferences                               │  │
│ │ REQUEST BODY: JSON Merge Patch — only include changed sections           │  │
│ │ RESPONSE 200: Updated preferences                                        │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ GET /v1/preferences/versions                                                  │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      List preference version history                            │  │
│ │ PAGINATION:   Cursor-based                                               │  │
│ │ RESPONSE 200: List of versions with change_summary and timestamps        │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ GET /v1/preferences/versions/{version}                                        │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Get a specific preference version snapshot                 │  │
│ │ RESPONSE 200: Full preferences at that version                           │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ POST /v1/preferences/dealbreakers                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Add a dealbreaker (convenience endpoint)                    │  │
│ │ REQUEST: { "field": "industry", "value": "defense" }                     │  │
│ │ RESPONSE 200: Updated preferences with new dealbreaker                   │  │
│ │                                                                          │  │
│ │ VALIDATION: field must be one of [industry, company, location,           │  │
│ │             requires_relocation_to, requires_clearance, requires_onsite] │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ DELETE /v1/preferences/dealbreakers/{dealbreaker_index}                       │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Remove a dealbreaker by its array index                    │  │
│ │ RESPONSE 200: Updated preferences                                        │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 10. Agent Execution

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ POST /v1/agent/execute                                                        │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Invoke the AI agent system for a user intent               │  │
│ │ AUTH:         Bearer token                                               │  │
│ │ PERMISSION:   agent:invoke                                               │  │
│ │                                                                          │  │
│ │ This is the PRIMARY entry point for all AI agent interactions.           │  │
│ │ The Supervisor Agent routes to the appropriate specialized agents.       │  │
│ │                                                                          │  │
│ │ REQUEST BODY:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "intent": "string",             // REQUIRED. See intent list   │    │  │
│ │ │   "message": "string",            // REQUIRED. User's natural    │    │  │
│ │ │                                   // language request            │    │  │
│ │ │   "context": {                    // OPTIONAL. Structured context│    │  │
│ │ │     "job_id": "uuid",             //   for targeted intents      │    │  │
│ │ │     "application_id": "uuid",                                     │    │  │
│ │ │     "resume_id": "uuid",                                          │    │  │
│ │ │     "interview_id": "uuid"                                        │    │  │
│ │ │   },                                                              │    │  │
│ │ │   "options": {                    // OPTIONAL                      │    │  │
│ │ │     "stream": true,               // Default true. SSE streaming  │    │  │
│ │ │     "auto_approve": false,        // For Premium tier autopilot   │    │  │
│ │ │     "bypass_cache": false,        // Force fresh LLM call         │    │  │
│ │ │     "tone": "professional"        // Override default tone        │    │  │
│ │ │   }                                                              │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ │                                                                          │  │
│ │ INTENT VALUES:                                                           │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ discover_jobs         — Find new jobs for the user                │    │  │
│ │ │ match_me              — Score and rank jobs against profile       │    │  │
│ │ │ tailor_resume         — Generate job-tailored resume              │    │  │
│ │ │ generate_cover_letter — Generate personalized cover letter        │    │  │
│ │ │ prep_interview        — Generate interview preparation materials  │    │  │
│ │ │ track_applications    — View/update application pipeline          │    │  │
│ │ │ follow_up             — Generate follow-up communication          │    │  │
│ │ │ analyze_skill_gap     — Identify and plan skill development       │    │  │
│ │ │ career_advice         — Get career guidance                       │    │  │
│ │ │ update_profile        — Modify user profile                       │    │  │
│ │ │ general_question      — Any other question or request             │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ │                                                                          │  │
│ │ RESPONSE 200 (non-streaming):                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "data": {                                                      │    │  │
│ │ │     "execution_id": "uuid",                                      │    │  │
│ │ │     "intent": "tailor_resume",                                   │    │  │
│ │ │     "intent_confidence": 0.94,                                   │    │  │
│ │ │     "agents_invoked": ["supervisor", "resume"],                  │    │  │
│ │ │     "status": "completed",                                       │    │  │
│ │ │     "response": {                                                │    │  │
│ │ │       "message": "I've tailored your resume for the Senior SWE   │    │  │
│ │ │                   role at Stripe. Here's a summary of changes:", │    │  │
│ │ │       "artifacts": [                                             │    │  │
│ │ │         { "type": "resume_diff", "data": { ... } },              │    │  │
│ │ │         { "type": "actions", "data": [                           │    │  │
│ │ │             { "label": "Accept & Save", "action": "accept" },    │    │  │
│ │ │             { "label": "Edit", "action": "edit" },               │    │  │
│ │ │             { "label": "Regenerate", "action": "regenerate" }    │    │  │
│ │ │           ]                                                      │    │  │
│ │ │         }                                                        │    │  │
│ │ │       ]                                                          │    │  │
│ │ │     },                                                           │    │  │
│ │ │     "pending_approval": {         // If HITL gate triggered      │    │  │
│ │ │       "approval_id": "uuid",                                      │    │  │
│ │ │       "action_type": "save_resume",                               │    │  │
│ │ │       "summary": "Save tailored resume for Stripe — Senior SWE?",│    │  │
│ │ │       "risk_level": "low"                                        │    │  │
│ │ │     },                                                           │    │  │
│ │ │     "metadata": {                                                │    │  │
│ │ │       "tokens_used": 4200,                                       │    │  │
│ │ │       "latency_ms": 3800,                                        │    │  │
│ │ │       "model": "deepseek-chat",                                  │    │  │
│ │ │       "cost_usd": 0.008                                          │    │  │
│ │ │     }                                                            │    │  │
│ │ │   },                                                             │    │  │
│ │ │   "links": { "approve": "/v1/agent/approvals/{id}" }             │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ │                                                                          │  │
│ │ RESPONSE 200 (streaming via SSE: text/event-stream):                     │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ event: status                                                     │    │  │
│ │ │ data: {"status": "thinking", "agent": "supervisor"}               │    │  │
│ │ │                                                                  │    │  │
│ │ │ event: status                                                     │    │  │
│ │ │ data: {"status": "invoking_agent", "agent": "resume"}             │    │  │
│ │ │                                                                  │    │  │
│ │ │ event: token                                                      │    │  │
│ │ │ data: {"text": "I've analyzed the job description"}              │    │  │
│ │ │                                                                  │    │  │
│ │ │ event: token                                                      │    │  │
│ │ │ data: {"text": " and tailored your resume accordingly."}          │    │  │
│ │ │                                                                  │    │  │
│ │ │ event: artifact                                                   │    │  │
│ │ │ data: {"type": "resume_diff", "data": {...}}                      │    │  │
│ │ │                                                                  │    │  │
│ │ │ event: done                                                       │    │  │
│ │ │ data: {"execution_id": "uuid", "metadata": {...}}                 │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ │                                                                          │
│ │ ERRORS:                                                                  │  │
│ │ · 400 UNKNOWN_INTENT — intent not recognized                             │  │
│ │ · 400 MISSING_CONTEXT — intent requires context (e.g., job_id for        │  │
│ │   tailor_resume) that wasn't provided                                    │  │
│ │ · 429 AGENT_RATE_LIMITED — daily agent invocation limit reached          │  │
│ │ · 500 AGENT_EXECUTION_FAILED — all retries exhausted                     │  │
│ │ · 503 CIRCUIT_BREAKER_OPEN — LLM provider unavailable, try later         │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ POST /v1/agent/approvals/{approval_id}                                        │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Respond to a pending HITL approval request                 │  │
│ │ AUTH:         Bearer token                                               │  │
│ │                                                                          │  │
│ │ REQUEST BODY:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "decision": "approved" | "rejected" | "edited",                │    │  │
│ │ │   "edits": { ... },              // If decision=edited            │    │  │
│ │ │   "rejection_reason": "string"   // If decision=rejected          │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ │                                                                          │  │
│ │ RESPONSE 200:                                                            │  │
│ │ · If approved: Action executed. Resume saved / email sent / etc.         │  │
│ │ · If edited: Merged edits applied, then executed.                         │  │
│ │ · If rejected: Agent receives feedback, generates alternative or aborts. │  │
│ │                                                                          │  │
│ │ ERRORS: 404 APPROVAL_NOT_FOUND, 409 APPROVAL_EXPIRED (7 day TTL)         │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ GET /v1/agent/executions                                                      │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      List agent execution history for the user                  │  │
│ │ AUTH:         Bearer token                                               │  │
│ │ PAGINATION:   Cursor-based, 20 per page                                  │  │
│ │                                                                          │  │
│ │ QUERY PARAMS:                                                            │  │
│ │ · agent_type: string — filter by agent                                   │  │
│ │ · intent: string — filter by intent                                      │  │
│ │ · is_success: boolean — filter by success/failure                        │  │
│ │ · created_after: ISO8601 — time range filter                             │  │
│ │ · sort: "-created_at" (default)                                          │  │
│ │                                                                          │  │
│ │ RESPONSE 200:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "data": [                                                      │    │  │
│ │ │     {                                                            │    │  │
│ │ │       "execution_id": "uuid",                                    │    │  │
│ │ │       "agent_type": "resume",                                    │    │  │
│ │ │       "action_type": "tailor_resume",                            │    │  │
│ │ │       "is_success": true,                                        │    │  │
│ │ │       "tokens_used": {"input": 3500, "output": 1200},            │    │  │
│ │ │       "latency_ms": 4200,                                        │    │  │
│ │ │       "cost_usd": 0.008,                                         │    │  │
│ │ │       "created_at": "ISO8601"                                    │    │  │
│ │ │     }                                                            │    │  │
│ │ │   ],                                                             │    │  │
│ │ │   "meta": { "cursor_next": "...", "limit": 20 }                 │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ GET /v1/agent/executions/{execution_id}                                       │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Get full agent execution details                           │  │
│ │ QUERY PARAMS: expand: "input_context,output_summary,tools_called"        │  │
│ │ RESPONSE 200: Full execution record with all details                     │  │
│ │ ERRORS: 404 EXECUTION_NOT_FOUND, 403 NOT_OWNER                           │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ POST /v1/agent/feedback                                                       │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Submit feedback on an agent execution                       │  │
│ │ AUTH:         Bearer token                                               │  │
│ │                                                                          │  │
│ │ REQUEST BODY:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "execution_id": "uuid",         // REQUIRED                     │    │  │
│ │ │   "rating": 4,                    // 1-5                           │    │  │
│ │ │   "was_helpful": true,                                             │    │  │
│ │ │   "comment": "string"             // OPTIONAL                     │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ │                                                                          │  │
│ │ RESPONSE 202: Feedback recorded. Used for agent evaluation and           │  │
│ │              continuous improvement.                                     │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 11. Career Goals & Learning

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ GET /v1/goals                                                                 │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      List career goals for the user                             │  │
│ │ AUTH:         Bearer token                                               │  │
│ │ QUERY PARAMS: status (filter), sort, pagination                         │  │
│ │ RESPONSE 200: List of career goals with progress                        │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ POST /v1/goals                                                                │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Create a new career goal                                   │  │
│ │ REQUEST: { "goal_type": "role_transition", "title": "Become Staff SWE",  │  │
│ │            "description": "...", "target_date": "2027-06",               │  │
│ │            "priority": 1 }                                                │  │
│ │ RESPONSE 201: Created goal                                               │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ PATCH /v1/goals/{goal_id}                                                     │
│ DELETE /v1/goals/{goal_id}                                                    │
│                                                                              │
│ GET /v1/learning-plans                                                        │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      List learning plans                                        │  │
│ │ RESPONSE 200: List of plans with status                                  │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ POST /v1/agent/execute   (with intent: analyze_skill_gap)                    │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Generate skill gap analysis + learning plan                │  │
│ │               (Invokes Career Coach Agent)                               │  │
│ │ REQUEST: { "intent": "analyze_skill_gap", "message": "...",              │  │
│ │            "context": { "target_role": "Staff Engineer" } }              │  │
│ │ RESPONSE 200: Structured skill gap report with suggested learning plan   │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 12. Communications

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ POST /v1/agent/execute   (with intent: follow_up)                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Generate follow-up communication (invokes Follow-up Agent) │  │
│ │ REQUEST: { "intent": "follow_up",                                        │  │
│ │            "context": { "application_id": "uuid",                        │  │
│ │                         "communication_type": "follow_up" } }             │  │
│ │ RESPONSE 200: Generated email/message draft for user review              │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ GET /v1/applications/{application_id}/communications                          │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      List all communications for an application                 │  │
│ │ RESPONSE 200: List with comm_type, subject, content, sent_at             │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ POST /v1/applications/{application_id}/communications                         │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Record a sent communication                                │  │
│ │ REQUEST: { "comm_type": "follow_up", "subject": "...", "content": "...", │  │
│ │            "sent_at": "ISO8601", "sent_via": "email" }                   │  │
│ │ RESPONSE 201: Communication recorded                                    │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 13. Analytics & Reporting

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ GET /v1/analytics/pipeline                                                    │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Get application pipeline analytics                          │  │
│ │ AUTH:         Bearer token                                               │  │
│ │ PERMISSION:   analytics:read                                             │  │
│ │                                                                          │  │
│ │ QUERY PARAMS:                                                            │  │
│ │ · date_from: ISO8601 — default 90 days ago                               │  │
│ │ · date_to: ISO8601 — default now                                         │  │
│ │                                                                          │  │
│ │ RESPONSE 200:                                                            │  │
│ │ ┌──────────────────────────────────────────────────────────────────┐    │  │
│ │ │ {                                                                │    │  │
│ │ │   "data": {                                                      │    │  │
│ │ │     "funnel": {                                                  │    │  │
│ │ │       "saved": 52, "applied": 38, "phone_screen": 8,             │    │  │
│ │ │       "technical_interview": 5, "onsite": 2, "offer": 1,        │    │  │
│ │ │       "accepted": 1                                              │    │  │
│ │ │     },                                                           │    │  │
│ │ │     "rates": {                                                   │    │  │
│ │ │       "application_to_interview": 0.21,    // 21%                │    │  │
│ │ │       "interview_to_offer": 0.20,          // 20%                │    │  │
│ │ │       "industry_average_application_to_interview": 0.05          │    │  │
│ │ │     },                                                           │    │  │
│ │ │     "time_in_stage": {                                           │    │  │
│ │ │       "applied_to_phone_screen_avg_days": 8.3,                   │    │  │
│ │ │       "phone_screen_to_onsite_avg_days": 14.2                    │    │  │
│ │ │     },                                                           │    │  │
│ │ │     "source_breakdown": [                                        │    │  │
│ │ │       { "source": "pathfinder_match", "applications": 22,        │    │  │
│ │ │         "interviews": 5 },                                        │    │  │
│ │ │       { "source": "linkedin", "applications": 8,                 │    │  │
│ │ │         "interviews": 1 }                                        │    │  │
│ │ │     ],                                                           │    │  │
│ │ │     "resume_performance": [                                      │    │  │
│ │ │       { "resume_name": "Base — Full Stack",                      │    │  │
│ │ │         "applications": 15, "interviews": 2, "rate": 0.13 },     │    │  │
│ │ │       { "resume_name": "Tailored — Fintech",                     │    │  │
│ │ │         "applications": 8, "interviews": 3, "rate": 0.38 }      │    │  │
│ │ │     ]                                                            │    │  │
│ │ │   }                                                              │    │  │
│ │ │ }                                                                │    │  │
│ │ └──────────────────────────────────────────────────────────────────┘    │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ GET /v1/analytics/agent-usage                                                 │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Get agent usage and cost analytics                          │  │
│ │ RESPONSE 200: Agent executions by type, token usage, cost breakdown      │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ GET /v1/analytics/market-insights                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Get market intelligence for user's target roles            │  │
│ │ RESPONSE 200: Salary ranges, demand trends, top skills, top companies    │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 14. Webhooks & Events

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ GET /v1/webhooks                                                              │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      List registered webhooks                                    │  │
│ │ AUTH:         Bearer token (or API key)                                   │  │
│ │ RESPONSE 200: List of webhook endpoints                                  │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ POST /v1/webhooks                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐  │
│ │ SUMMARY:      Register a webhook endpoint                                 │  │
│ │ REQUEST: { "url": "https://...", "events": ["application.updated",       │  │
│ │            "match.high_score"], "secret": "whsec_..." }                   │  │
│ │ RESPONSE 201: Created webhook                                            │  │
│ └─────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ WEBHOOK EVENT TYPES:                                                         │
│ ┌──────────────────────────────────────────────────────────────────────────┐│
│ │ application.updated      — Status change, note added                     ││
│ │ application.interview    — Interview scheduled/completed                 ││
│ │ application.offer        — Offer received                                ││
│ │ match.high_score         — Job match ≥ 85%                               ││
│ │ match.dream_job          — Job match ≥ 95%                               ││
│ │ resume.tailored          — New tailored resume generated                 ││
│ │ cover_letter.generated   — New cover letter generated                    ││
│ │ agent.execution_complete — Agent task finished                           ││
│ └──────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 15. Error Reference

### 15.1 HTTP Status Code Usage

| Code | When Used |
|------|-----------|
| **200** | Successful read or update |
| **201** | Resource created |
| **202** | Accepted for async processing |
| **204** | Successful deletion (no body) |
| **301** | HTTP → HTTPS redirect |
| **400** | Validation error, malformed request |
| **401** | Missing or invalid authentication |
| **403** | Authenticated but not authorized |
| **404** | Resource not found |
| **409** | Conflict (duplicate, invalid state transition) |
| **410** | Resource gone (expired job) |
| **422** | Unprocessable — valid syntax, semantic error |
| **429** | Rate limit exceeded |
| **500** | Internal server error |
| **503** | Service unavailable (circuit breaker open, maintenance) |

### 15.2 Error Code Catalog

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ERROR CODE                        │ HTTP │ DESCRIPTION                       │
│ ─────────────────────────────────┼──────┼────────────────────────────────── │
│ VALIDATION_ERROR                  │ 400  │ Request body fails schema         │
│ INVALID_FILTER                    │ 400  │ Unknown filter parameter          │
│ MISSING_REQUIRED_FIELD            │ 400  │ Required field not provided       │
│ INVALID_STATUS_TRANSITION         │ 400  │ Application status change invalid │
│ UNSUPPORTED_FILE_TYPE             │ 400  │ Upload not PDF/DOCX/TXT           │
│ FILE_TOO_LARGE                    │ 400  │ File exceeds size limit           │
│ UNREADABLE_FILE                   │ 400  │ Corrupted or encrypted file       │
│ UNKNOWN_INTENT                    │ 400  │ Agent intent not recognized       │
│ MISSING_CONTEXT                   │ 400  │ Required context for intent missing│
│ INVALID_CREDENTIALS               │ 401  │ Wrong email or password           │
│ INVALID_TOKEN                     │ 401  │ Expired, revoked, or reused token │
│ UNAUTHORIZED                      │ 401  │ Missing or invalid auth header    │
│ NOT_OWNER                         │ 403  │ Resource belongs to other user    │
│ NOT_RESUME_OWNER                  │ 403  │ Resume belongs to other user      │
│ EMAIL_NOT_VERIFIED                │ 403  │ Email verification required       │
│ TIER_NOT_ALLOWED                  │ 403  │ Feature requires higher tier      │
│ RESOURCE_NOT_FOUND                │ 404  │ Generic not found                 │
│ JOB_NOT_FOUND                     │ 404  │ Job listing doesn't exist         │
│ JOB_EXPIRED                       │ 410  │ Job listing is no longer active   │
│ RESOURCE_EXISTS                   │ 409  │ Duplicate resource                │
│ DUPLICATE_APPLICATION             │ 409  │ Already applied to this job       │
│ RESUME_IN_USE                     │ 409  │ Cannot delete — linked to apps    │
│ CANNOT_DELETE_APPLIED             │ 409  │ Archive or withdraw instead       │
│ APPROVAL_EXPIRED                  │ 409  │ HITL approval expired (7d)        │
│ PARSING_FAILED                    │ 422  │ Resume parsing returned no data   │
│ TAILORING_FAILED                  │ 422  │ Resume tailoring failed           │
│ RATE_LIMIT_EXCEEDED               │ 429  │ Too many requests                 │
│ AGENT_RATE_LIMITED                │ 429  │ Agent invocation limit reached    │
│ ACCOUNT_LOCKED                    │ 423  │ Too many failed login attempts    │
│ INTERNAL_ERROR                    │ 500  │ Unexpected server error           │
│ AGENT_EXECUTION_FAILED            │ 500  │ All agent retries exhausted       │
│ CIRCUIT_BREAKER_OPEN              │ 503  │ LLM provider unavailable          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 16. Rate Limiting & Tier Access

### 16.1 Rate Limits by Tier

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ENDPOINT CATEGORY          │ FREE       │ PRO         │ PREMIUM     │ ENT   │
│ ──────────────────────────┼───────────┼────────────┼────────────┼────── │
│ Auth (login, register)     │ 10/min/IP  │ 10/min/IP   │ 10/min/IP   │ N/A   │
│ Profile CRUD               │ 30/min     │ 100/min     │ 300/min     │ 500   │
│ Job search/browse          │ 60/min     │ 300/min     │ 1000/min    │ 2000  │
│ Job matching               │ 10/min     │ 50/min      │ 200/min     │ 500   │
│ Application CRUD           │ 30/min     │ 100/min     │ 300/min     │ 500   │
│ Resume/CL generation       │ 5/day      │ 50/day      │ unlimited   │ unlim │
│ Agent execution            │ 20/day     │ 100/day     │ 500/day     │ 2000  │
│ Interview prep             │ 5/day      │ 30/day      │ unlimited   │ unlim │
│ Analytics                  │ Basic      │ Full        │ Full+Export │ Full  │
│ Webhooks                   │ -          │ 3 endpoints │ 10 endpoints│ 50    │
│ API Keys                   │ -          │ 1 key       │ 5 keys      │ 20    │
│ Concurrent sessions        │ 2          │ 5           │ 10          │ Unlim │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 16.2 Rate Limit Headers

All responses include:

```
X-RateLimit-Limit: 100           // Max requests in window
X-RateLimit-Remaining: 87        // Remaining in current window
X-RateLimit-Reset: 1718574000    // Unix timestamp when window resets
X-RateLimit-Tier: pro            // Current tier
```

When exceeded (429):

```
Retry-After: 45                  // Seconds until next available request
```

---

> *"An API is a product. Its users are developers. Design it with the same care you'd design a UI."*

**End of API Design Document**
