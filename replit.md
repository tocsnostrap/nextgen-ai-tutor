# NextGen AI Tutor — Complete School Platform

Enterprise-grade AI-powered school platform for children ages 3-12 with futuristic immersive UI. This IS the school — full K-6 structured curriculum, daily schedule, time tracking, and grade-level progress reports.

## Architecture

- **Backend**: FastAPI (Python) serving on port 5000
- **Frontend**: Futuristic single-page app at `frontend/index.html` served at `/`; legacy demo at `frontend/demo.html` served at `/demo`
- **Database**: PostgreSQL (Replit built-in) via SQLAlchemy + asyncpg
- **Redis**: Optional, gracefully disabled with no-op fallback when not available
- **AI**: OpenAI via Replit AI Integrations (`AI_INTEGRATIONS_OPENAI_BASE_URL`, `AI_INTEGRATIONS_OPENAI_API_KEY`)

## Key Features

### RPG Game World Theme (Full App Gamification)
- **Hero Card Sidebar**: HP bar (tied to mastery %), MP bar (tied to streak days), gold (XP), hero class title (Apprentice Explorer → Cosmic Champion based on level)
- **Zone Navigation**: All tabs renamed to RPG zones — Quest Board (Learn), Oracle (Chat), Battle Arena (Games), Trophy Hall (Progress), War Room (Analytics), World Map (new)
- **2D Adventure Map** (World Map tab — default landing): Full canvas-style map (1200x800) with 6 buildings (Home Base, Quest Board, Oracle Tower, Battle Arena, Trophy Hall, War Room) connected by animated dashed paths. Nova character sprite floats at current location with idle/walk animations, glowing ring, and shadow. Click any building → Nova walks there with walk animation → auto-enters the zone tab after arrival. Features: terrain blobs, firefly/sparkle particles, minimap with Nova dot tracking, interaction bubbles on arrival, "Return to Map" floating button on all other tabs.
- **Adventure Map Zones**: Home Base (hub, no tab), Quest Board→learn, Oracle Tower→chat, Battle Arena→games, Trophy Hall→knowledge, War Room→analytics. Each building has colored glow border, hover scale, and pulsing ring effect
- **Quest Board**: Schedule blocks rendered as quest cards with realm names, XP rewards, difficulty stars, adventure progress bar
- **Quest Completion Banner**: Animated gold overlay with XP reward on lesson complete

### School Platform (Core)
- **Full K-6 Curriculum**: 122 standards across Math, Reading, Science, Writing, Social Studies (grades K-6) seeded on startup via `curriculum_data.py`
- **Daily Schedule Engine**: `schedule_engine.py` generates personalized school days based on age/grade — Tiny (90min/7 blocks), Junior (150min/8 blocks), Rising (210min/9 blocks)
- **Today's Plan Dashboard**: Quest Board tab shows daily quests with quest cards, adventure progress bar, week calendar, subject stats
- **Lesson Viewer**: Full-screen overlay that opens when clicking a schedule block; shows AI-generated or fallback lesson content with intro, sections, examples, tips, vocabulary, comprehension quiz, summary, and challenge. Endpoint: `POST /api/v1/schedule/lesson`. AI generation has 5s client timeout + 6s server timeout with fallback; progress bar animation during load
- **Time-on-Task Tracking**: Per-subject time logging via `SubjectTimeLog` table for compliance reporting
- **Grade-Level Progress Reports**: Grade equivalency calculations, standards mastered/in-progress, AI summary, monthly reports

### Nova's Realm — Unified Immersive Game World
- **Concept**: One unified immersive world instead of separate mini-games. All subjects (math, reading, science, patterns) blend together within themed adventure zones.
- **Realm Entry**: Animated portal screen with particle effects, spinning cosmic gateway, "ENTER THE REALM" button
- **World Map**: Vertical zone path with 6 themed zones, star progress tracking, lock/unlock system based on total stars earned
- **6 Zones**: Stardust Garden (🌸), Crystal Cavern (💎), Cloud Kitchen (🍳), Ocean Deep (🐙), Moonlight Tower (🌙), Volcano Peak (🌋) — each with themed emojis, vocabulary words, science facts, and math contexts
- **Zone Unlock**: Stars earned based on accuracy (3★ = 80%+, 2★ = 50%+, 1★ = completion). Zones require cumulative stars (0, 3, 6, 10, 15, 20)
- **5 Challenge Types per Zone** (rotate each round):
  1. **Tap Count**: Toca-style — tap floating themed items in a scene to collect the exact target count
  2. **Math Quest**: Age-adaptive math problems with zone-themed context (story problems for tiny, operations for older)
  3. **Word Magic**: Missing letters (tiny) or word unscramble with multiple choice (junior/rising), zone-themed vocabulary
  4. **Science Discovery**: True/false or "which fact is true" with zone-themed science facts
  5. **Pattern Power**: Emoji pattern sequences (tiny), number sequences or growing patterns (junior/rising)
- **Shared Infrastructure**: gState, scoreAnswer, advanceRound, timer, HUD, power-ups, boss rounds, Nova mascot, confetti, sound effects
- **Star Persistence**: localStorage tracks per-zone stars and total realm stars
- All zones use `gState` global state, DOM-based rendering, CSS animations
- XP awarded via gamification endpoint on completion
- **Nova mascot** appears during all challenges with contextual reactions
- **Visual feedback**: confetti, screen flashes, floating XP, celebrations
- **Futuristic Upgrades** (retained):
  - Web Audio sound system, Power-Up system, Boss Rounds, Round Progress Pips, Combo Display

### Chat (AI Tutor)
- Age-adaptive prompts pulled from localStorage profile (no hardcoded age)
- Suggested topics from today's schedule blocks
- Quick-action buttons: Quiz Me, Tell a Story, Explain Like I'm [age], Draw It
- Modern bubble design with typing indicator

### My Progress Tab (formerly Knowledge Map)
- Visual curriculum progress per subject with progress rings/bars
- Standards checklist per subject, mastery tracking
- Weekly streak and daily completion history
- Data from `/schedule/curriculum` and `/schedule/progress-report` endpoints

### Claude AI Multi-Agent System (Primary AI)
- **Claude claude-opus-4-6**: Primary AI via `claude_ai_service.py` with adaptive thinking for complex problems
- **Multi-Agent Architecture**: 5 specialized agents in `multi_agent_tutor.py` — Orchestrator, Domain Expert, Socratic Guide, Metacognitive Coach, Error Analyst
- **Metacognitive Coaching**: `metacognitive_coach.py` tracks growth mindset, persistence, learning style, provides strategy tips
- **Causal Error Analysis**: `causal_error_analysis.py` diagnoses WHY students make mistakes, generates targeted remediation plans
- **Learning Trajectory**: `learning_trajectory.py` generates 4-week learning forecasts with skill predictions
- **Streaming Responses**: `POST /chat/stream` for real-time response streaming
- **Chat UI shows**: agent badges (which AI agent responded), model badge (Claude), deep thinking indicator, metacognitive coaching tips inline
- **Learning Insights Panel**: "My Insights" button opens panel with metacognitive profile, error patterns, learning trajectory
- **Fallback chain**: Claude multi-agent → direct Claude → OpenAI → template-based responses

### Tutoring & Learning
- **Primary AI**: Claude via Anthropic API (`ANTHROPIC_API_KEY`), OpenAI as fallback via `ai_service.py`
- **Onboarding Flow**: 5-step onboarding (welcome, name, age, subjects, avatar) with localStorage persistence + backend adaptive profile sync
- **Age-Adaptive Theming**: CSS custom properties change based on age group (Tiny Explorers 3-5, Junior Learners 6-8, Rising Stars 9-12)
- **SVG Icon System**: All icons use inline SVGs via `frontend/icons.js` (57 icons including brain, zap). Zero emojis
- **Voice Conversations**: Mic button for speech-to-text (Web Speech API), OpenAI TTS for responses
- **Video Avatar Tutor**: Animated AI tutor "Nova" with 5 expression states
- **Interactive Whiteboard**: Canvas-based drawing tool with AI-generated visual explanations
- **Video Lesson Library**: 6 seeded video lessons with progress tracking
- **AI Video Generation**: 11 AI-generated educational video clips stored in `attached_assets/generated_videos/`, served at `/generated-videos/`. Topics: counting, fractions, multiplication, phonics, text structure, states of matter, ecosystems, solar system, community helpers, geography, research writing. Videos auto-match to lesson topics and display in lesson viewer. "Generate AI Video" button in lessons for on-demand generation. API: `GET /api/v1/videos/generated` (list), `POST /api/v1/videos/generate` (request new). AI Video Grid in video library tab shows all generated clips with play functionality
- **Offline Mode**: Service worker caching, IndexedDB storage
- **Personalized Learning Paths**: Structured paths with milestones and PDF certificates
- **Bayesian Knowledge Tracing (BKT)**: Tracks skill mastery probabilities
- **Spaced Repetition**: SM-2 algorithm for optimal review scheduling
- **Gamification**: XP system, 100-level progression, 22 achievements, streaks, leaderboard
- **Unified Adaptive Engine**: Cross-feature AI memory
- **Parent/Teacher Dashboard**: Child progress, activity feed, learning goals, weekly reports + progress reports with grade equivalencies

## Project Structure

```
backend/
  main.py                    - FastAPI app, serves frontend, parent dashboard, static assets
  ai_service.py              - OpenAI integration wrapper with fallback
  claude_ai_service.py       - Claude AI (Anthropic) primary tutor with adaptive thinking, streaming, ZPD targeting
  multi_agent_tutor.py       - 5-agent architecture: Orchestrator, Domain Expert, Socratic Guide, Metacog Coach, Error Analyst
  metacognitive_coach.py     - Growth mindset tracking, persistence scoring, strategy recommendations
  learning_trajectory.py     - 4-week learning plan forecasts, skill mastery predictions
  causal_error_analysis.py   - Misconception diagnosis, remediation plans, error pattern tracking
  schedule_engine.py         - Daily schedule generation, completion, time tracking, progress reports
  curriculum_data.py         - K-6 curriculum seed data (122 standards)
  knowledge_graph.py         - Knowledge graph engine with curriculum data
  conversational_ai.py       - Template-based conversational AI (fallback)
  spaced_repetition.py       - SM-2 spaced repetition algorithm
  bkt_lite.py                - Lightweight BKT engine
  game_manager.py            - Game session manager
  unified_adaptive_engine.py - Cross-feature adaptive engine
  emotion_aware_teaching.py  - Emotion-adaptive teaching
  adaptation_engine.py       - Difficulty adaptation engine
  conversational_memory.py   - Conversation memory management
  core/
    config.py                - Settings via pydantic-settings
    database.py              - SQLAlchemy models (User, Session, VideoLesson, CurriculumStandard, DailySchedule, SubjectTimeLog, ProgressReport, etc.)
    redis.py                 - No-op Redis fallback
  api/v1/
    api.py                   - API router aggregating all endpoints + WebSocket
    auth.py                  - JWT auth utilities
    endpoints/
      schedule.py            - Schedule & curriculum API (today, week, complete-block, time-log, progress-report, curriculum)
      auth.py                - Registration, login
      users.py               - User CRUD
      sessions.py            - Learning sessions
      analytics.py           - Analytics
      ai_models.py           - BKT, emotion, adaptation
      curriculum.py          - Knowledge graph, lessons, recommendations
      gamification.py        - XP, levels, achievements, leaderboard
      chat.py                - AI chat, TTS, whiteboard, quiz endpoints
      videos.py              - Video lesson library endpoints
      parent.py              - Parent/teacher dashboard endpoints
      learning_paths.py      - Learning paths, milestones, PDF certificates
      games.py               - Game endpoints
      adaptive.py            - Adaptive engine profile, recommendations, onboarding
  models/
    session.py               - SessionManager
  websocket/
    manager.py               - WebSocket connection manager
frontend/
  index.html                 - Main UI (Onboarding + Today's Plan/Chat/My Progress/Games/Analytics tabs)
  icons.js                   - SVG icon system (57 icons, all inline SVG, no emojis)
  demo.html                  - Legacy demo
  whiteboard.js              - Canvas-based interactive whiteboard
  offline-store.js           - IndexedDB wrapper for offline data
  sw.js                      - Service worker for offline caching
  parent_dashboard.html      - Parent/teacher dashboard
  assets/
    avatar-*.png             - AI tutor avatar expressions
run.py                       - Uvicorn entry point (port 5000)
```

## API Endpoints

### Schedule & Curriculum
- `GET /api/v1/schedule/today` - Today's personalized schedule (auto-generates)
- `POST /api/v1/schedule/complete-block` - Mark a schedule block as completed with time spent
- `GET /api/v1/schedule/week` - Week view with completion status per day
- `GET /api/v1/schedule/time-log?period=week|month` - Time-on-task summary per subject
- `GET /api/v1/schedule/progress-report?period=2026-03` - Grade-level progress report
- `GET /api/v1/schedule/curriculum?subject=math&grade=3` - Curriculum standards browser
- `POST /api/v1/schedule/lesson` - Generate lesson content for a schedule block (AI with fallback)

### Existing
- `GET /` - Main frontend dashboard
- `GET /parent` - Parent/teacher dashboard
- `GET /health` - Health check
- `GET /docs` - Swagger UI
- `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`
- `POST /api/v1/chat/message` - Claude multi-agent chat (primary), `POST /api/v1/chat/stream` - Streaming chat
- `POST /api/v1/chat/analyze-error` - Causal error diagnosis + remediation
- `POST /api/v1/chat/generate-problem` - Personalized ZPD-targeted problem generation
- `POST /api/v1/chat/metacognitive-coaching` - Learning strategy coaching
- `GET /api/v1/chat/learning-trajectory` - 4-week learning forecast
- `GET /api/v1/chat/metacognitive-profile` - Student metacognitive profile
- `GET /api/v1/chat/error-patterns` - Error pattern tracking
- `POST /api/v1/chat/tts`, `POST /api/v1/chat/whiteboard`, `POST /api/v1/chat/quiz`
- `GET /api/v1/videos/library`, `GET/POST /api/v1/videos/{id}`
- `GET/POST /api/v1/learning-paths/*`
- `GET /api/v1/parent/child-progress/{id}`, `POST /api/v1/parent/learning-goals`
- `GET /api/v1/gamification/profile`, `POST /api/v1/gamification/award-xp`
- `GET /api/v1/adapt/profile`, `GET /api/v1/adapt/recommendations`, `POST /api/v1/adapt/onboarding`
- `WS /api/v1/ws` - WebSocket (tutoring)

## Database

PostgreSQL with tables: `users`, `learning_sessions`, `session_interactions`, `emotion_detections`, `learning_progress`, `assessments`, `analytics_events`, `gamification_profiles`, `chat_messages`, `video_lessons`, `video_progress`, `learning_goals`, `learning_paths`, `student_adaptive_profiles`, `curriculum_standards`, `daily_schedules`, `subject_time_logs`, `progress_reports`.

## Age Groups & Schedule Structure

| Group | Ages | Grade | Daily Minutes | Blocks |
|-------|------|-------|---------------|--------|
| Tiny Explorers | 3-5 | K | 90 | 7 (short sessions) |
| Junior Learners | 6-8 | 1-3 | 150 | 8 (mixed activities) |
| Rising Stars | 9-12 | 4-6 | 210 | 9 (full school day) |

## Games Architecture

- **Game State**: `gState` global object tracks round, score, streak, XP, answered status
- **Flow**: `renderGameSelect()` → game card click → `launchGame(id)` → setup function → per-round rendering → `showGameOver()`
- **Age detection**: `getAgeGroup()` reads from localStorage `ob_profile`, returns 'tiny'/'junior'/'rising'
- **No WebSocket**: `connectGameWs()` is now a stub that calls `renderGameSelect()` directly
- **Scoring**: `scoreAnswer(correct)` handles XP, streaks, combo multipliers
- **XP award**: Posts to `/gamification/award-xp` on game completion

## Authentication

- **Real JWT**: PyJWT with HS256 signing, 30-min access tokens, 7-day refresh tokens
- **Legacy fallback**: `access_token_{user_id}` format accepted with warning
- **Frontend default**: Uses `Authorization: Bearer access_token_user_123` (legacy format)

## Important Notes

- **OpenAI params**: Use `max_completion_tokens` NOT `max_tokens`; do NOT pass `temperature` parameter
- **UUID columns**: `LearningProgress.user_id` and `Assessment.user_id` are UUID columns — wrap queries in try/except with `await db.rollback()`
- **Service worker caching**: Frontend HTML changes may be served stale until SW cache refreshes
- **Grade calculation**: grade = age - 5, clamped to 0-6
- **FORBIDDEN**: Web Speech API SpeechSynthesis — use OpenAI TTS first, fallback to browser

## Dependencies

fastapi, uvicorn, sqlalchemy, asyncpg, pydantic, pydantic-settings, email-validator, python-dotenv, websockets, starlette, python-multipart, PyJWT, bcrypt, openai, fpdf2, python_openai_ai_integrations
