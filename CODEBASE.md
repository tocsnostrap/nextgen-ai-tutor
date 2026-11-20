# Codebase Audit

Audited: branch `claude/advance-ai-tutoring-platform-rPOYS` at commit `43599ad`, on 2026-11-20.

How: read the code, built an import map from `backend/main.py`, matched every frontend API call to a backend route, then ran the app locally against Postgres 16 and called its endpoints. No Anthropic API key was set, so nothing that needs the model was exercised; those paths are marked **not tested**.

Local run caveat: the pinned versions in `requirements-deploy.txt` do not install on this machine's Python 3.13, so the run used current versions of the same packages. The Dockerfile uses Python 3.11, where the pins should install; that was not tested.

---

## 1. Verdict

It is a good-looking demo, not a working tutor. The screens load without errors and the game world is polished. Underneath, there are no real users, progress is not saved, several numbers on screen are invented, and there are security holes that must be closed before any child's data goes in.

About 60% of the backend is worth keeping as a starting point. The frontend is kept as the reward area and a new session room is built beside it.

---

## 2. Size and shape

| Part | Files | Lines | Notes |
|------|-------|-------|-------|
| Backend (FastAPI, Python) | 46 | about 15,600 | 38 modules reachable from the app; 4 do not compile |
| Frontend | 7 | about 8,400 | One 7,028-line `index.html` with 190 functions and all CSS inline |
| Database | 19 tables | | Created at startup with `create_all`; no migrations |
| Tests | 2 scripts | | Not real tests; one of them fails as shipped |
| Routes | 73 | | The frontend calls roughly a third of them |

---

## 3. What works (verified by running it)

- The app boots, creates 19 tables, and seeds 122 curriculum standards and 6 video records.
- The home screen, schedule, curriculum list, gamification profile, learning paths, video library and interest profile endpoints all return data.
- The page loads in a browser with no console errors and no failed requests.
- Chat history and the child's interest profile are stored in Postgres.
- Password hashing and JWT creation in `auth.py` are sound.

---

## 4. What is broken or fake (verified)

| # | Finding | Evidence |
|---|---------|----------|
| 1 | **The deploy as configured will not start.** `schedule.py` imports `ai_service.py`, which imports `openai`, and `openai` is not in `requirements-deploy.txt` | Boot fails with `ModuleNotFoundError: No module named 'openai'`; boots once it is installed |
| 2 | **Any file in the app folder can be downloaded by anyone.** The `/frontend/{path}` route does not stop `..` | `GET /frontend/../backend/core/config.py` returned the file, including the default secret keys. A `.env` file would be exposed the same way |
| 3 | **No real login.** Any token beginning `access_token_` is accepted as that user | `Bearer access_token_anyone_i_like` returned a profile for "anyone_i_like". The frontend hard-codes `access_token_user_123` at `index.html:2713`, so every child is the same user |
| 4 | **Anyone can register as an admin** | `POST /auth/register` with `"role":"admin"` returned an admin token |
| 5 | **Any "parent" can read any child** | `GET /parent/weekly-report/someone_else` returned 200 with the demo token |
| 6 | **Children can award themselves unlimited points** | `POST /gamification/award-xp` with 999,999 returned level 100 |
| 7 | **Without an API key the tutor silently gives nonsense.** No error is shown | "What is 7 x 8?" returned "math is an important math skill that helps us solve all kinds of problems" |
| 8 | **Skill and emotion numbers on the home screen are invented** | "Addition 85%, Division 15%" is hard-coded HTML shown to a brand-new user; the "emotion monitor" is `Math.random()` (`index.html:6985`) |
| 9 | **Skill mastery is lost on every restart** | `bkt_lite.py` keeps it in a Python dictionary; so does `metacognitive_coach.py` |
| 10 | **Four backend files do not compile** | `adaptation_engine.py`, `bkt_engine.py`, `conversational_memory.py`, `emotion_aware_teaching.py` all fail with an indentation error on line 1. Nothing imports them |
| 11 | **Default secret keys are in the code** and are used if the environment does not set them | `core/config.py:38-39` |
| 12 | **The API documentation page is public** and cross-origin requests are allowed from anywhere | `/docs` returned 200; CORS is `*` with credentials |
| 13 | **The shipped self-check fails** | `test_structure.py` reports "Docker Compose: FAIL" |

Findings 2–6, 11 and 12 are security holes. None of them matters while the data is fake; all of them must be fixed in phase 0 and 1 before a real child uses it.

---

## 5. Module by module

### Keep and build on

| Module | What it does | State |
|--------|--------------|-------|
| `core/database.py` | 19 table models | Sound. Needs migrations, and new tables for the learner record, plans and homework |
| `core/config.py` | Settings | Sound once default secrets are removed |
| `api/v1/auth.py`, `endpoints/auth.py` | JWT and password login | Sound once the `access_token_` bypass and role self-selection are removed |
| `claude_ai_service.py` | Claude calls: tutor reply, quiz, error analysis, problem generation | Works in structure; **not tested**. Uses an old model ID and a learning-styles prompt. Becomes the base of the new tutor |
| `bkt_lite.py` | Mastery estimate from right/wrong answers | Correct maths; needs to be saved to the database |
| `spaced_repetition.py` | Review scheduling | Small and usable |
| `knowledge_graph.py` | Skill prerequisite links | Hand-written; replaced by the National Curriculum graph but the structure is reusable |
| `endpoints/knowledge_library.py` | Child's interests and discoveries | Works and is saved. Becomes the interest store and wonder list |
| `endpoints/gamification.py` | XP, levels, achievements | Works. Needs the self-award hole closed |
| `endpoints/parent.py`, `parent_dashboard.html` | Parent view | Skeleton only; rebuilt on real data |
| `frontend/whiteboard.js` | Drawing canvas | Usable start for the shared whiteboard |
| Games, Nova assets, RPG world | Reward area | Keep as is |

### Replace

| Module | Why |
|--------|-----|
| `multi_agent_tutor.py` | A router plus four specialist prompts, several model calls per message, no shared state. Replaced by one tutor with tools |
| `schedule_engine.py` | Fills a fixed age template with the next standard. Does not look at what the child got wrong. Replaced by the planner |
| `curriculum_data.py` | 122 hand-written US-style standards. Replaced by the National Curriculum import |
| `ai_service.py` | OpenAI through Replit; the source of the deploy failure |
| `unified_adaptive_engine.py` | Mixes real signals with learning-style guesses; replaced by the learner record |
| `metacognitive_coach.py`, `causal_error_analysis.py`, `learning_trajectory.py` | Large rule-based modules whose output is not saved or shown. Their useful ideas (naming a misconception, a remediation step) move into the tutor's tools |
| `websocket/manager.py`, `game_manager.py` | Multiplayer game plumbing with a demo user. Rewritten for the live voice session |
| `/chat/tts` | Depends on Replit-only settings |

### Delete

`adaptation_engine.py`, `bkt_engine.py`, `conversational_memory.py`, `emotion_aware_teaching.py` (do not compile), `models/lstm_temporal_model.py` (never trained or called), `endpoints/ai_models.py` emotion detection, `demo.html`, `test_structure.py`, `test_system.py`, `replit.md`, and the three overlapping architecture documents, which describe features that do not exist.

---

## 6. Structural weaknesses

- **One 7,028-line HTML file.** Hard to change safely and untestable. The session room is built as separate files; the existing page is left alone.
- **No migrations.** A changed table definition will not reach an existing database. Alembic is added before any schema change.
- **No tests, no CI.** Added in phase 0.
- **No background jobs.** Planning, marking and reports need a worker.
- **`innerHTML` is used 85 times** in the frontend. Once real model output and children's text are shown, each one is a possible script-injection point and must be reviewed.
- **Two requirements files that disagree,** one listing PyTorch and other large packages nothing uses.

---

## 7. Hosting

The Railway account has three projects (`family-hq` and two named `tct-probability-system`). None is this app and none has a Postgres database. The tutor needs its own new Railway project with a web service, a worker and Postgres. Nothing was changed on Railway during this audit.

The current `render.yaml` and Render instructions become unused once it is on Railway.
