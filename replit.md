# NextGen AI Tutor — Complete School Platform

Enterprise-grade AI-powered school platform for children ages 3-12 with futuristic immersive UI. This IS the school — full K-6 structured curriculum, daily schedule, time tracking, and grade-level progress reports.

## Architecture

- **Backend**: FastAPI (Python) serving on port 5000
- **Frontend**: Futuristic single-page app at `frontend/index.html` served at `/`; legacy demo at `frontend/demo.html` served at `/demo`
- **Database**: PostgreSQL (Replit built-in) via SQLAlchemy + asyncpg
- **Redis**: Optional, gracefully disabled with no-op fallback when not available
- **AI**: OpenAI via Replit AI Integrations (`AI_INTEGRATIONS_OPENAI_BASE_URL`, `AI_INTEGRATIONS_OPENAI_API_KEY`)

## Key Features

### School Platform (Core)
- **Full K-6 Curriculum**: 122 standards across Math, Reading, Science, Writing, Social Studies (grades K-6) seeded on startup via `curriculum_data.py`
- **Daily Schedule Engine**: `schedule_engine.py` generates personalized school days based on age/grade — Tiny (90min/7 blocks), Junior (150min/8 blocks), Rising (210min/9 blocks)
- **Today's Plan Dashboard**: Learn tab shows daily schedule with time blocks, progress bar, week calendar, subject stats
- **Lesson Viewer**: Full-screen overlay that opens when clicking a schedule block; shows AI-generated or fallback lesson content with intro, sections, examples, tips, vocabulary, comprehension quiz, summary, and challenge. Endpoint: `POST /api/v1/schedule/lesson`
- **Time-on-Task Tracking**: Per-subject time logging via `SubjectTimeLog` table for compliance reporting
- **Grade-Level Progress Reports**: Grade equivalency calculations, standards mastered/in-progress, AI summary, monthly reports

### Interactive Games (5 Mini-Games) — Toca Boca-Inspired Discovery Play
- **Number Lab**: Discovery math — Tiny: tap-to-count animated objects with number line; Junior: equation builder with draggable number orbs; Rising: multi-step pipeline challenges
- **Word Forge**: Creative word workshop — Tiny: letter discovery with emoji associations & matching; Junior: themed word smithing (animals/food/nature); Rising: vocabulary fill-in-the-blank with definitions
- **Science Explorer**: Interactive experiments — Tiny: color mixing lab & living/nonliving sorting; Junior: states of matter thermometer slider & trivia; Rising: element mixing lab (H+O=Water) with reaction animations
- **Pattern Quest**: Pattern recognition — simple sequences for tiny, number/shape patterns for junior, complex logic for rising
- **Speed Challenge**: Age-adaptive timed quiz across subjects — easy questions for tiny, mixed math/spelling/science for junior/rising
- All games use `gState` global state, DOM-based rendering, CSS animations, no canvas/WebSocket dependency
- XP awarded via gamification endpoint on completion with celebrations
- **Nova mascot** appears during all games with contextual reactions and speech bubbles
- **Visual feedback system**: confetti explosions, screen flashes, floating XP indicators, starbursts on streaks
- **AI-generated game card images** in `frontend/assets/game-*.png`

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

### Tutoring & Learning
- **Real AI Integration**: OpenAI-powered tutoring via `ai_service.py`, falls back to template-based responses
- **Onboarding Flow**: 5-step onboarding (welcome, name, age, subjects, avatar) with localStorage persistence + backend adaptive profile sync
- **Age-Adaptive Theming**: CSS custom properties change based on age group (Tiny Explorers 3-5, Junior Learners 6-8, Rising Stars 9-12)
- **SVG Icon System**: All icons use inline SVGs via `frontend/icons.js` (57 icons including brain, zap). Zero emojis
- **Voice Conversations**: Mic button for speech-to-text (Web Speech API), OpenAI TTS for responses
- **Video Avatar Tutor**: Animated AI tutor "Nova" with 5 expression states
- **Interactive Whiteboard**: Canvas-based drawing tool with AI-generated visual explanations
- **Video Lesson Library**: 6 seeded video lessons with progress tracking
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
- `POST /api/v1/chat/message`, `POST /api/v1/chat/tts`, `POST /api/v1/chat/whiteboard`, `POST /api/v1/chat/quiz`
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
