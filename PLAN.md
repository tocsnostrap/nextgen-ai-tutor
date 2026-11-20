# NextGen AI Tutor — Build Plan

Status: **draft for sign-off. Nothing is built yet.**
Base code: branch `claude/advance-ai-tutoring-platform-rPOYS` (newer than `main`).
Working branch: `claude/keen-ramanujan-0xfo9j`.

Research citations below are from memory and were not re-checked while writing this.
Phase 0 includes verifying each one and recording the link in `docs/research.md`.

---

## 1. Decisions needed before building

Each has a default. If you say nothing, the default is what gets built.

| # | Decision | Default | Why it matters |
|---|----------|---------|----------------|
| 1 | Tutor or full school? | **Tutor**: short sessions a few times a week, plus homework | The current code plans a 90–210 minute school day. That is a different product, and 90 min/day of screen time for ages 3–5 is above paediatric guidance |
| 2 | Which curriculum? | **None chosen. I need your country.** | The 122 seeded standards are hand-written and cite no published curriculum. Lessons, reports and "grade level" all hang off this |
| 3 | Your own children, or a public product? | Family pilot first, built so it can open up later | A public product for under-13s needs verified parental consent and a legal review before launch |
| 4 | Age range at launch | **6–12 first**, 3–5 later as a parent-led mode | Under-6s cannot type, speech recognition is weak on their voices, and the evidence favours adult-led play |
| 5 | Language of instruction | English only | Affects curriculum, speech vendors and reading instruction |
| 6 | Subjects at launch | Maths and reading/writing; science after | These have the strongest evidence and the clearest skill sequence |

---

## 2. What the product is

One AI tutor per child that does what a human tutor does across weeks, not one chat:

1. Finds out what the child knows (placement).
2. Plans a term, a week and each session.
3. Teaches the session live, checks understanding, adapts on the spot.
4. Sets and marks homework.
5. Remembers everything and uses it next time.
6. Reports to the parent.

The games and RPG world in the current code stay as a reward area. They stop being the main screen.

---

## 3. Research basis

### 3.1 Principles for every age

| Principle | Source | What the product does |
|-----------|--------|-----------------------|
| Daily review, small steps, guided practice, check understanding, aim for about 80% success | Rosenshine, *Principles of Instruction* (2012) | Fixed session structure in section 7 |
| Working memory is small; show worked examples, then fade them | Sweller, cognitive load theory; worked-example effect | One new idea per session. "I do, we do, you do" |
| Being quizzed beats re-reading | Roediger & Karpicke (2006) | Every session opens with recall questions |
| Spread practice out over time | Cepeda et al. (2006) | Review queue with expanding gaps |
| Mix problem types once basics are in | Rohrer & Taylor (2007) | Homework mixes old and new skills |
| Which study techniques work | Dunlosky et al. (2013) | Practice testing and spacing used; highlighting and re-reading not used |
| Teach just beyond what the child can do alone, with support that is withdrawn | Vygotsky; Wood, Bruner & Ross (1976) | Hint ladder: prompt, cue, partial step, worked example |
| Feedback must say what to do next | Hattie & Timperley (2007); Black & Wiliam (1998) | Marking returns a next step, not a score |
| Learners gain most when they produce and explain | Chi & Wylie, ICAP (2014) | Child explains back before the tutor moves on |
| Tutoring works, and structured computer tutors come close to human ones | Bloom (1984); VanLehn (2011) | The reason to build this. Bloom's "two sigma" is larger than later studies found |
| Tracking skill mastery from right/wrong answers | Corbett & Anderson (1995) | Already in the code as `bkt_lite`; kept and persisted |
| AI that hands over answers harms later performance; guard-railed tutors do not | Bastani et al. (2024); Kestin et al. (2024) | The tutor never gives the final answer to graded work |

### 3.2 Things the current code does that the evidence does not support

- **Learning styles** (visual/kinesthetic) in `claude_ai_service.py` and `adaptation_engine.py`. Pashler et al. (2008) found no support. Remove.
- **Emotion detection** as a model. Reading emotion from faces is unreliable (Barrett et al., 2019) and a camera on a child is a privacy cost. Replace with a one-tap mood check and behaviour signals (response time, hint use, error streaks).
- **"3–5 years ahead of state of the art"** claims in the docs. Remove; the product should claim only what it measures.

### 3.3 By age band

| | Ages 3–5 | Ages 6–8 | Ages 9–12 |
|---|----------|----------|-----------|
| How they learn best | Play, talk, adult alongside | Explicit teaching, concrete objects, lots of short practice | Explicit teaching, discussion, self-checking |
| Reading | Sounds in words, letter names, vocabulary through stories | Systematic phonics, then fluency | Comprehension strategies, background knowledge, writing |
| Maths | Counting, subitising, comparing, shape | Number sense, place value, fact fluency, concrete to pictorial to abstract | Fractions, proportion, multi-step problems |
| Input method | Tap and voice only | Tap, voice, short typing | Typing, voice, photo of written work |
| Parent role | In the room | Nearby; hears reading | Reviews reports |
| Sources | AAP media guidance (2016); NAEYC developmentally appropriate practice; National Early Literacy Panel (2008); Clements & Sarama learning trajectories | National Reading Panel (2000); EEF literacy and maths guidance for ages 5–7; Bruner's concrete-pictorial-abstract | EEF metacognition guidance; IES fractions practice guide (Siegler et al., 2010); Graham & Perin, *Writing Next* (2007) |

---

## 4. Curriculum

1. Adopt one published curriculum (decision 2) and import its objectives with their official codes.
2. Store it as a **prerequisite graph**: each objective lists what must be known first. The existing `prerequisites` field becomes real edges.
3. Each objective carries: success criteria, common misconceptions, representations to use, and a bank of checked practice items.
4. The 122 existing standards are mapped onto the published ones where they match and dropped where they do not.
5. Maths answers in the item bank are computed by code, never trusted from the model.

---

## 5. Learner record ("keeps learning about the child")

One record per child in Postgres, read at the start of every session and written at the end.

| Part | Contents | Updated by |
|------|----------|------------|
| Mastery | Probability per objective, attempts, last seen | Every answered question |
| Retention | Next review date per objective | Spaced-review scheduler |
| Misconceptions | Named error patterns with evidence | Marking and in-session errors |
| Session log | Summary of each session: taught, struggled, what worked | Tutor at session end |
| Preferences | Interests, pace, which explanations landed | Tutor, from behaviour |
| Goals | Parent goals and school targets | Parent |
| Homework | Set, submitted, marked, outstanding | Homework service |

**Mastered** means: mastery estimate at or above 0.95, and a correct answer on a check at least a week later. Passing once in the session is not mastery.

Review gaps expand after each success: 1, 3, 7, 21, 60 days. A failure resets the gap.

---

## 6. Planning and timetable

### 6.1 Planning levels

| Level | Made when | Contents |
|-------|-----------|----------|
| Placement | First 2–3 sessions | Adaptive questions that walk the prerequisite graph to find the edge of what the child knows |
| Term plan (6 weeks) | After placement, then every 6 weeks | Target objectives per subject, chosen from those whose prerequisites are mastered, weighted by parent goals |
| Week plan | Each weekend | Which objective each session covers, plus review slots |
| Session plan | Night before | Objective, success criteria, recall questions, explanation, worked examples, practice items with answers, exit questions, homework |

Session plans are generated as structured data, checked by code (answers verified, reading level in range, length fits the slot), and stored. The parent can see them in advance.

### 6.2 Re-planning rules

- Exit questions passed: advance.
- Exit questions failed once: re-teach next session with a different representation.
- Failed twice: step back to the prerequisite.
- Session missed: the week plan shifts; nothing is silently skipped.
- Homework not done: the next session starts with it.

### 6.3 Default timetable (tutor mode)

| | Ages 3–5 | Ages 6–8 | Ages 9–12 |
|---|----------|----------|-----------|
| Live sessions | 3 a week, 10–15 min, parent present | 4 a week, 20–25 min | 4 a week, 35–45 min |
| Homework | None. Optional off-screen activity for the parent | 10–15 min, 3 days a week, plus daily reading aloud | 20–30 min, 4 days a week |
| Daily screen cap | 20 min | 45 min | 75 min |

The parent sets available days and times; the system places sessions and sends reminders. Homework length follows Cooper, Robinson & Patall (2006): little measured benefit in primary years, so it stays short and is mostly practice and reading.

---

## 7. A live session

Same skeleton for every age; lengths scale with the band.

1. **Check-in.** One-tap mood, one sentence about the day.
2. **Recall.** 3–5 questions from the review queue.
3. **Homework review.** Go over what was marked; fix one error together.
4. **Teach.** Tutor models one worked example on the whiteboard, thinking aloud.
5. **Together.** Child does the next with hints from the ladder.
6. **Alone.** Child does 3–6 items; tutor intervenes only on error.
7. **Exit questions.** 2–3 items, no hints. These drive re-planning.
8. **Wrap.** Child says what they learned; tutor sets homework and says what is next.
9. **After the child leaves.** Tutor writes the session summary and updates the learner record.

Tutor behaviour rules: ask before telling; never give the final answer to an exit or homework item; praise effort and method, not ability; stop and suggest a break after three errors in a row; stay on the lesson but allow one short tangent.

---

## 8. Homework

1. Generated from the session plan: mostly today's objective, some older ones mixed in.
2. Appears on the child's home screen with a due date.
3. Child answers on screen or uploads a photo of written work.
4. Marking: maths checked against computed answers; written work marked against the success criteria; photos read by the model's vision.
5. Feedback names one thing done well and one next step.
6. Results update mastery and misconceptions, and feed the next session's homework review.
7. Low-confidence marking is flagged for the parent instead of guessed.

---

## 9. Parent side

- Weekly report: time spent, objectives mastered, objectives in progress, misconceptions, homework completion, what is planned next.
- Full transcripts of every session.
- Set goals, availability and screen caps.
- Alerts: missed sessions, repeated struggle on one objective, any safety flag.
- Export and delete all of a child's data.

---

## 10. Safety (must pass before any child uses it)

- Real accounts: parent owns the account, children are profiles under it. The hard-coded demo token is removed.
- Screening of what the child types and what the tutor says.
- The tutor never asks for personal details and has no open web access.
- If a child says something that suggests harm or distress, the tutor responds supportively, ends the topic, and alerts the parent.
- No camera. Microphone only while the child holds the talk button.
- Children's data is not used to train anything.
- Public launch only: verified parental consent (COPPA in the US, the Children's Code in the UK, GDPR in the EU) and a legal review. This plan is not legal advice.

---

## 11. How it is built

### 11.1 Stack

- **Keep:** FastAPI, Postgres, the Nova character, games, gamification.
- **Change:** all in-memory state moves to Postgres; schema changes go through Alembic migrations; one AI provider.
- **Remove:** the four files that do not compile, the LSTM and emotion stubs, the OpenAI/Replit path, learning-style code.
- **Add:** a background worker for planning, marking and reports; a session room page separate from the 7,000-line `index.html`; automated tests and CI.

### 11.2 The tutor

One tutor agent running on the Claude Messages API with tools. It replaces the current router plus four sub-agents, which cost several model calls per message and share no state.

Tools the tutor can call:

| Tool | Does |
|------|------|
| `get_learner_record` | Mastery, misconceptions, last sessions |
| `get_session_plan` | Today's plan |
| `present_item` / `record_attempt` | Show a question; log the answer and update mastery |
| `give_hint` | Next rung of the hint ladder, logged |
| `draw_on_whiteboard` | Structured drawing commands |
| `check_answer` | Computed check for maths |
| `assign_homework` | Create the homework set |
| `end_session` | Write summary, trigger re-planning |
| `flag_for_parent` | Safety or concern alert |

Model IDs live in config, not code. Default `claude-opus-5-5` for teaching, planning and marking. Whether to use a cheaper model for screening and routine marking is a cost decision to make after measuring real usage. The stable system prompt and curriculum are prompt-cached; replies stream to the screen.

### 11.3 Voice and whiteboard

- Claude handles text and images. Speech needs separate speech-to-text and text-to-speech services, chosen in the voice phase.
- First version is push-to-talk with streamed spoken replies. Open-microphone conversation with interruption comes after that works.
- The whiteboard is shared: the tutor draws through a tool, the child draws by touch, and the tutor can see a snapshot of the child's drawing.

### 11.4 How the system itself keeps improving

- A test set of scripted child conversations per age band, scored on: did it teach instead of tell, was it correct, was it age-appropriate, did it follow the session structure. Run before every prompt or model change.
- Each session plan records whether the exit questions were passed, so explanations that work are reused and ones that fail are retired.
- Parent thumbs up/down on reports and child end-of-session rating.
- The research register is reviewed every quarter.

---

## 12. Build order

Each phase ends with a check that must pass before the next starts.

| Phase | Work | Done when |
|-------|------|-----------|
| 0. Base | Make the feature branch the base; delete dead code; fix the deploy; add tests, CI and migrations; verify research citations | App starts from a clean checkout and deploys; tests run in CI |
| 1. Accounts | Parent and child accounts, real login, all state in Postgres | Two children on one parent account have separate records that survive a restart |
| 2. Curriculum | Import the chosen curriculum as a graph; item bank with computed answers; placement | A new child finishes placement and gets a mastery map |
| 3. Tutor | Learner record, tutor tools, the section 7 session flow in text, safety screening, eval set | A scripted session runs end to end and the record updates correctly; evals pass |
| 4. Planning | Term, week and session plans; timetable; re-planning rules | A simulated 6-week child gets sensible plans that react to pass and fail |
| 5. Homework | Assign, submit (typed and photo), mark, feed back | Homework from one session is reviewed in the next |
| 6. Parent | Reports, transcripts, goals, alerts, export and delete | Parent sees an accurate weekly report |
| 7. Pilot | Real use with your own children for 2–4 weeks | Issues list worked through |
| 8. Voice | Push-to-talk, spoken replies, shared whiteboard | A full session with no typing |
| 9. Ages 3–5 | Parent-led mode, tap and voice only | A 10-minute session a 4-year-old can complete with a parent |

---

## 13. Risks

| Risk | Handling |
|------|----------|
| The model teaches something wrong | Computed maths answers; checked item bank; evals; parent-visible transcripts |
| The model gives answers away | Tool design withholds answers on graded items; eval measures it |
| Speech recognition fails on young voices | Tap alternatives for every response; ages 3–5 last |
| Running cost per child | Prompt caching; measure in the pilot before choosing cheaper models |
| Scope | Phases 0–6 are the product. Voice and under-6s wait until those work |
| Child safety and privacy | Section 10 is a gate, not a phase |
