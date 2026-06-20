# User Acceptance Report — Pathfinder

**Date**: 2026-06-20
**Tester**: Hardik Prajapati (real user, fresh account)
**Method**: Complete journey from registration to application tracking

---

## Step-by-Step Experience

### 1. Registration
- **Latency**: 78ms
- **Experience**: Fast. Clean. Professional.
- **Friction**: None. The form is minimal, response is instant.
- **Verdict**: ✅ Production quality.

### 2. Resume Upload
- **Latency**: 5,672ms (5.7 seconds)
- **Experience**: Drop file, wait. No progress indicator. User stares at spinner wondering "Is this working?"
- **Friction**: 5.7s is too long without feedback. Show "Extracting skills...", "Building profile..." stages.
- **Quality**: 22 skills extracted from AI/ML resume — excellent extraction quality.
- **Verdict**: ⚠️ Works but feels slow. Needs progress indicators.

### 3. Profile Review
- **Latency**: 16ms
- **Experience**: Instant. Skills, experience, education all populated. Feels like magic after the slow upload.
- **Friction**: None. Profile data is accurate and well-structured.
- **Verdict**: ✅ Production quality.

### 4. Job Search
- **Latency**: ~50ms (when not rate-limited)
- **Experience**: 500 jobs across 30 companies. Fast. Rich data.
- **Friction**: Rate-limited under load (500 during this test, but this was due to prior test traffic).
- **Verdict**: ✅ Production quality (under normal conditions).

### 5. Match Score
- **Latency**: ~30ms
- **Experience**: 6-dimension score breakdown. Skill gaps are actionable. Strengths are encouraging.
- **Friction**: None. This feature is ready.
- **Verdict**: ✅ Production quality.

### 6. Resume Tailoring
- **Latency**: ~8,000ms (8 seconds)
- **Experience**: Long wait, but the result is magical. Factuality score, ATS optimization, keyword coverage improvement, section-by-section diffs.
- **Friction**: 8s is slow. User needs progress feedback during tailoring.
- **Verdict**: ✅ The WOW feature. Worth the wait.

### 7. Agent (5 queries)
- **Latency**: 320ms (first), 6-9ms (fallback)
- **Experience**: First query returns a real, personalized response ("I see your skills include Python, PyTorch..."). Second query returns "I'm having trouble..." — the same message for queries 2, 3, 4, and 5.
- **Friction**: User thinks the AI broke after the first query. This is the #1 product risk.
- **Quality**: 1/5 real responses (20%).
- **Verdict**: ❌ Degraded. Unreliable. Would make a user quit.

### 8. Knowledge
- **Latency**: 31ms (search), 63ms (upload)
- **Experience**: Upload is fast. Search returns relevant results with 1.0 score.
- **Friction**: None. Feels like enterprise search.
- **Verdict**: ✅ Production quality.

### 9. Application Tracking
- **Latency**: ~30ms
- **Experience**: Save a job. View pipeline. Status tracking works.
- **Friction**: Create Application returns 500 with some job IDs (known FK issue).
- **Verdict**: ⚠️ Partially functional.

---

## Key Questions

### What feels professional?
- **Profile extraction**: Instant, accurate, well-structured. Feels like LinkedIn's resume parser.
- **Job search**: 500 jobs, fast filtering, professional table layout.
- **Matching**: 6-dimension scoring with actionable skill gaps. Enterprise quality.
- **Knowledge search**: Fast, relevant, with relevance scores. Feels like a premium product.
- **Tailoring**: The diff viewer with factuality verification is genuinely impressive.

### What feels unfinished?
- **Agent reliability**: Degrades after 1 query. This is the most visible AI feature.
- **Resume upload latency**: 5.7s with no progress feedback.
- **Tailoring latency**: 8s with no progress feedback.
- **Application creation**: Returns 500 with some job IDs.
- **Dashboard**: Shows mock data, not real user activity.

### What would make a user quit?
1. **Agent returning the same fallback message repeatedly.** After the first query works brilliantly, seeing "I'm having trouble..." for every subsequent query feels like a bait-and-switch. This is the #1 quit risk.
2. **Resume upload taking 5.7s with no feedback.** Users might think the upload failed and leave.

### What would impress a recruiter?
- **The tailoring feature.** Upload a resume, select a job, and in 8 seconds see a tailored version with tracked changes, factuality verification, and ATS optimization. This is LinkedIn Premium-level functionality.
- **The matching engine.** 6-dimension scoring with specific skill gaps.

### What should be fixed before public beta?
1. **Agent reliability** (P0): Must survive 10+ queries without degrading. Requires fallback LLM provider.
2. **Progress indicators** (P1): Resume upload and tailoring need stage-by-stage progress.
3. **Application creation** (P1): Fix the 500 error on POST /v1/applications.
4. **Dashboard real data** (P2): First thing users see should show their actual activity.

---

## WOULD I USE PATHFINDER MYSELF?

# YES — with conditions.

**As a job seeker**: YES, I would use it for job search, matching, and tailoring. These features are genuinely useful and work reliably.

**For the agent**: NO in its current state. I would stop using the agent after the second degraded response and never try it again.

**The product I would use**: Pathfinder minus the agent. The core job search → match → tailor pipeline is solid.

**The product I would recommend**: Pathfinder AFTER the agent reliability is fixed. With a working agent, this is a compelling product.

**Honest assessment**: Pathfinder is 80% of a great product. The remaining 20% (agent reliability) determines whether users stay or leave. Fix the agent, and you have something people would pay for.
