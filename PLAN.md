# NextGen AI Tutor — Build Plan

Status: **draft for sign-off. Nothing is built yet.**
Base code: branch `claude/advance-ai-tutoring-platform-rPOYS` (newer than `main`).
Working branch: `claude/keen-ramanujan-0xfo9j`.

Research citations below are from memory and were not re-checked while writing this.
Phase 0 includes verifying each one and recording the link in `docs/research.md`.

---

## 1. Scope (decided)

| Question | Decision |
|----------|----------|
| Product | **Two modes, chosen by the parent per child and switchable at any time.** Tutor mode: 5–6 live sessions a week, with extra sessions on request. School mode: a full weekday timetable that replaces school |
| Curriculum | **England's National Curriculum**, Years 1–7 (Key Stages 1, 2 and the first year of 3). Scotland, Wales and Northern Ireland differ and are not covered |
| Ages | **6–12** |
| Subjects | English, maths, science, languages (Arabic, French, Spanish), art, cooking, life skills |
| Voice | **Required from the first usable version.** Children talk to the tutor and hear it reply |
| Approach | **Child-led** and **diverse** (section 4) |
| Who it is for | Not a deciding factor. It is built safely either way (section 11) |

Dropped from earlier drafts: ages 3–5, US curriculum. History and geography are added in school mode only, because a full school day needs them.

Assumptions I made that you can change:
- **Languages:** the parent picks one or more of Arabic, French and Spanish per child. Arabic is taught as Modern Standard Arabic, not a regional dialect, with a separate starting point for children who already speak it at home.
- **Life skills** follows the PSHE Association programme of study (money, health, safety, emotions, relationships). Relationships and health topics are parent-controlled.

---

## 2. What the product is

One AI tutor per child that does what a human tutor does across weeks, not one chat:

1. Finds out what the child knows (placement).
2. Plans a term, a week and each session, around the child's interests.
3. Teaches the session live, checks understanding, adapts on the spot.
4. Sets and marks homework.
5. Remembers everything and uses it next time.
6. Reports to the parent.

The games and RPG world in the current code stay as a reward area. They stop being the main screen.

---

## 3. Research basis

### 3.1 Principles for every subject

| Principle | Source | What the product does |
|-----------|--------|-----------------------|
| Daily review, small steps, guided practice, check understanding, aim for about 80% success | Rosenshine, *Principles of Instruction* (2012) | Fixed session structure in section 8 |
| Working memory is small; show worked examples, then fade them | Sweller, cognitive load theory | One new idea per session. "I do, we do, you do" |
| Being quizzed beats re-reading | Roediger & Karpicke (2006) | Every session opens with recall questions |
| Spread practice out over time | Cepeda et al. (2006) | Review queue with expanding gaps |
| Mix problem types once basics are in | Rohrer & Taylor (2007) | Homework mixes old and new skills |
| Teach just beyond what the child can do alone, then withdraw support | Vygotsky; Wood, Bruner & Ross (1976) | Hint ladder: prompt, cue, partial step, worked example |
| Feedback must say what to do next | Hattie & Timperley (2007); Black & Wiliam (1998) | Marking returns a next step, not a score |
| Learners gain most when they produce and explain | Chi & Wylie, ICAP (2014) | Child explains back before the tutor moves on |
| Tutoring works, and structured computer tutors come close to human ones | Bloom (1984); VanLehn (2011) | The reason to build this |
| Tracking skill mastery from right/wrong answers | Corbett & Anderson (1995) | Already in the code as `bkt_lite`; kept and persisted |
| AI that hands over answers harms later performance; guard-railed tutors do not | Bastani et al. (2024); Kestin et al. (2024) | The tutor never gives the final answer to graded work |
| Choice and interest raise motivation and persistence | Deci & Ryan, self-determination theory; Hidi & Renninger (2006) | Child-led design in section 4 |

UK-specific sources used for subject content: Education Endowment Foundation guidance reports; Ofsted subject research reviews; the DfE Reading Framework; NCETM teaching-for-mastery materials for maths.

### 3.2 By age band

| | Ages 6–8 (Years 1–3) | Ages 9–12 (Years 4–7) |
|---|----------------------|-----------------------|
| How they learn best | Explicit teaching, concrete objects, lots of short practice | Explicit teaching, discussion, self-checking, longer projects |
| English | Systematic synthetic phonics, then fluency; handwriting; sentence building | Comprehension, vocabulary, grammar, extended writing |
| Maths | Number sense, place value, number bonds, times tables; concrete to pictorial to abstract | Fractions, decimals, ratio, multi-step problems, early algebra |
| Science | Observing, sorting, simple tests | Fair tests, explaining with evidence |
| Languages | Songs, sounds, core words | Phonics of the language, vocabulary, simple grammar, short conversations |
| Input method | Tap, voice, short typing | Typing, voice, photo of written work |
| Parent role | Nearby; hears reading | Reviews reports |
| National checkpoints the plan prepares for | Year 1 phonics check; Year 4 times-tables check | Year 6 SATs |

### 3.3 Things the current code does that the evidence does not support

- **Learning styles** (visual/kinesthetic) in `claude_ai_service.py` and `adaptation_engine.py`. Pashler et al. (2008) found no support. Remove.
- **Emotion detection** as a model. Reading emotion from faces is unreliable (Barrett et al., 2019) and a camera on a child is a privacy cost. Replace with a one-tap mood check and behaviour signals.
- **A 150–210 minute day spent entirely on screen** in `schedule_engine.py`. Replaced by the timetables in section 7, where school mode is mostly off screen.
- **"3–5 years ahead of state of the art"** claims in the docs. Remove.

---

## 4. Child-led learning and diversity

### 4.1 Child-led

A caution first: for skills a child does not yet have, such as phonics or column subtraction, the research favours direct teaching over discovery (Kirschner, Sweller & Clark, 2006). So the tutor decides **what skill** comes next, and the child leads on everything around it.

| The child chooses | How |
|-------------------|-----|
| The context | Lessons are wrapped in the child's interests. A fractions lesson for a child who loves football uses match scores; the skill is the same |
| The order | At the start of the week the child picks which of the planned topics to do first |
| The project | Each half term the child picks a project that draws on several subjects |
| Tangents | A question off the plan gets a short answer now and is saved to a "wonder list". Wonder-list items become future lessons where they fit the curriculum |
| Pace | The child can ask for more practice, a harder challenge, or a break |
| Extra sessions | The child or parent can add a session on any topic at any time |
| Practical subjects | In art, cooking and life skills the child picks what to make or learn from a menu |

The existing "knowledge library" and interest profile in the code are kept and become the store for interests and the wonder list.

### 4.2 Diversity

- **Representation:** names, families, places, foods, festivals, authors, scientists and artists in examples and texts are drawn from a wide range of cultures and backgrounds, including the child's own.
- **Content:** reading lists, art references and recipes are chosen to cover many traditions, not one.
- **Languages at home:** the record notes other languages the child speaks, and the tutor treats them as an asset.
- **Access:** dyslexia-friendly text options, read-aloud for every instruction, adjustable pace, and no response that depends on typing speed.
- **Checks:** the test set (section 12.4) includes checks for stereotypes and for one-culture defaults.

The evidence that diverse content raises attainment is thinner than the evidence in section 3.1; the firmer case is engagement and belonging. It is included because you asked for it and it costs nothing in rigour.

---

## 5. Curriculum

1. Import the National Curriculum programmes of study for Years 1–7, statement by statement. It is Crown copyright under the Open Government Licence; the licence terms are confirmed in phase 0.
2. Store it as a **prerequisite graph**: each objective lists what must be known first.
3. Each objective carries success criteria, common misconceptions, representations to use, and a bank of checked practice items.
4. The 122 hand-written standards in the current code are US-style K–6. They are mapped to National Curriculum statements where they match and dropped where they do not.
5. Maths answers in the item bank are computed by code, never trusted from the model.

### Two kinds of subject

| Kind | Subjects | How progress is tracked |
|------|----------|-------------------------|
| **Mastery subjects** | English, maths, science, languages | Mastery score per objective, spaced review, exit questions |
| **Practical subjects** | Art, cooking, life skills | Skills checklist and a portfolio of photos; feedback on the work, no scores |

Subject notes:
- **Cooking** is the "cooking and nutrition" strand of design and technology. Every task involving heat or knives requires an adult to confirm they are present before the steps are shown.
- **Art** is done off screen. The child uploads a photo; the tutor gives feedback on technique and asks about choices.
- **Languages** are taught through listening and speaking first, so they are built after voice. Automated scoring of children's pronunciation is unreliable, so speaking gets encouragement and modelling, not a mark.
- **Arabic** needs extra work the other two do not: a new alphabet with letters that change shape by position, right-to-left text on every screen that shows it, vowel marks shown for learners, handwriting practice on the whiteboard, and speech services that handle Arabic well. These are checked when the voice vendor is chosen.
- **Science** includes off-screen investigations with household items, recorded by photo.

---

## 6. Learner record ("keeps learning about the child")

One record per child in Postgres, read at the start of every session and written at the end.

| Part | Contents | Updated by |
|------|----------|------------|
| Mastery | Probability per objective, attempts, last seen | Every answered question |
| Retention | Next review date per objective | Spaced-review scheduler |
| Misconceptions | Named error patterns with evidence | Marking and in-session errors |
| Session log | Summary of each session: taught, struggled, what worked | Tutor at session end |
| Interests and wonder list | What the child likes and has asked about | Tutor and child |
| Portfolio | Photos and notes for practical subjects | Child uploads |
| Goals | Parent goals and school targets | Parent |
| Homework | Set, submitted, marked, outstanding | Homework service |

**Mastered** means: mastery estimate at or above 0.95, and a correct answer on a check at least a week later.

Review gaps expand after each success: 1, 3, 7, 21, 60 days. A failure resets the gap.

---

## 7. Planning and timetable

### 7.1 Planning levels

| Level | Made when | Contents |
|-------|-----------|----------|
| Placement | First 2–3 sessions | Adaptive questions that walk the prerequisite graph to find the edge of what the child knows |
| Half-term plan (6 weeks) | After placement, then every half term | Target objectives per subject, the child's chosen project, parent goals |
| Week plan | Each weekend | Which objective each session covers, review slots; the child picks the order |
| Session plan | Night before | Objective, success criteria, recall questions, explanation in the child's chosen context, worked examples, practice items with answers, exit questions, homework |

Session plans are generated as structured data, checked by code (answers verified, reading level in range, length fits the slot), and stored. The parent can see them in advance.

### 7.2 Re-planning rules

- Exit questions passed: advance.
- Failed once: re-teach next session with a different representation.
- Failed twice: step back to the prerequisite.
- Session missed: the week plan shifts; nothing is silently skipped.
- Homework not done: the next session starts with it.
- Extra session added: it takes the next item from the week plan, a review, or the child's chosen topic.

### 7.3 Tutor mode timetable

| | Ages 6–8 | Ages 9–12 |
|---|----------|-----------|
| Live sessions | 5–6 a week, 25 min | 5–6 a week, 40 min |
| Extra sessions | On request, same length; capped by the daily screen limit | Same |
| Homework | 10–15 min, 3 days a week, plus daily reading aloud | 20–30 min, 4 days a week |
| Daily screen cap (parent can change) | 60 min | 90 min |

Example week, with the parent setting the days and times:

| Day | Main subject | Also in the session |
|-----|--------------|---------------------|
| Mon | Maths | 5 min language practice |
| Tue | English | Recall from Monday |
| Wed | Science | 5 min language practice |
| Thu | Maths | Recall |
| Fri | English | 10 min language lesson |
| Sat (optional 6th) | Art, cooking or life skills, rotating | Project time |

Languages are taught little and often because short, frequent practice suits vocabulary learning. Homework stays short: Cooper, Robinson & Patall (2006) found little measured benefit in the primary years.

### 7.4 School mode timetable

A weekday plan that replaces a school day. Most of it is **off screen**: the tutor sets the task by voice, the child does it on paper or with objects, then returns to show the work by photo.

| | Ages 6–8 | Ages 9–12 |
|---|----------|-----------|
| Total learning day | 2.5–3 hours | 3.5–4 hours |
| Tutor-led on screen | 60–75 min in 3 blocks | 90–120 min in 3–4 blocks |
| Off screen (reading, handwriting, making, investigating, moving) | The rest | The rest |
| Breaks | Every 25 min | Every 45 min |
| Daily | Maths, English, a language | Maths, English, a language |
| Across the week | Science twice; art, cooking, life skills, history and geography once each | Same, plus a half-day project |
| Homework | None; the off-screen blocks replace it | None |

Example day, ages 9–12: maths with the tutor (35 min), maths practice on paper (25 min), break, English with the tutor (35 min), reading a book (30 min), lunch, language (20 min), science investigation off screen (45 min), show-and-reflect with the tutor (15 min).

School mode also produces attendance and progress records. Home education is legal in England and parents are not required to follow the National Curriculum, but the parent remains legally responsible for the child receiving a suitable full-time education; the product supports that and does not take it over.

---

## 8. A live session

Same skeleton for every mastery subject; lengths scale with the age band.

1. **Check-in.** One-tap mood, one sentence about the day.
2. **Recall.** 3–5 questions from the review queue.
3. **Homework review.** Go over what was marked; fix one error together.
4. **Teach.** Tutor models one worked example on the whiteboard, thinking aloud.
5. **Together.** Child does the next with hints from the ladder.
6. **Alone.** Child does 3–6 items; tutor intervenes only on error.
7. **Exit questions.** 2–3 items, no hints. These drive re-planning.
8. **Wrap.** Child says what they learned; tutor sets homework and says what is next.
9. **After the child leaves.** Tutor writes the session summary and updates the record.

Practical sessions use a different shape: look at an example, plan, make (off screen), share a photo, reflect.

Tutor behaviour rules: ask before telling; never give the final answer to an exit or homework item; praise effort and method, not ability; suggest a break after three errors in a row; answer one tangent briefly and save the rest to the wonder list.

---

## 9. Homework

1. Generated from the session plan: mostly today's objective, some older ones mixed in.
2. Appears on the child's home screen with a due date.
3. Child answers on screen or uploads a photo of written or practical work.
4. Marking: maths checked against computed answers; written work marked against the success criteria; photos read by the model's vision.
5. Feedback names one thing done well and one next step.
6. Results update mastery and misconceptions, and feed the next session's homework review.
7. Low-confidence marking is flagged for the parent instead of guessed.

---

## 10. Parent side

- Weekly report: time spent, objectives mastered and in progress by National Curriculum year, misconceptions, homework completion, portfolio additions, what is planned next.
- Full transcripts of every session.
- Choose tutor mode or school mode, and which languages the child learns.
- Set goals, available days and times, screen caps, and which life-skills topics are allowed.
- Add an extra session.
- Alerts: missed sessions, repeated struggle on one objective, any safety flag.
- Export and delete all of a child's data.

---

## 11. Safety (must pass before any child uses it)

- Real accounts: parent owns the account, children are profiles under it. The hard-coded demo token is removed.
- Screening of what the child types and what the tutor says.
- The tutor never asks for personal details and has no open web access.
- If a child says something that suggests harm or distress, the tutor responds supportively, ends the topic, and alerts the parent.
- No camera stream. Photos are taken deliberately by the child. Microphone only while the talk button is held.
- Adult-present confirmation for cooking with heat or knives.
- Children's data is not used to train anything.
- If this is ever offered to other families, UK GDPR and the ICO Children's Code apply and need a legal review first. This plan is not legal advice.

---

## 12. How it is built

### 12.1 Stack

- **Keep:** FastAPI, Postgres, the Nova character, games, gamification, the interest profile.
- **Change:** all in-memory state moves to Postgres; schema changes go through Alembic migrations; one AI provider.
- **Remove:** the four files that do not compile, the LSTM and emotion stubs, the OpenAI/Replit path, learning-style code.
- **Add:** a background worker for planning, marking and reports; a session room page separate from the 7,000-line `index.html`; automated tests and CI.

### 12.2 The tutor

One tutor agent running on the Claude Messages API with tools. It replaces the current router plus four sub-agents, which cost several model calls per message and share no state.

| Tool | Does |
|------|------|
| `get_learner_record` | Mastery, misconceptions, interests, last sessions |
| `get_session_plan` | Today's plan |
| `present_item` / `record_attempt` | Show a question; log the answer and update mastery |
| `give_hint` | Next rung of the hint ladder, logged |
| `draw_on_whiteboard` | Structured drawing commands |
| `check_answer` | Computed check for maths |
| `add_to_wonder_list` | Save a child's question for later |
| `review_photo` | Look at uploaded work |
| `assign_homework` | Create the homework set |
| `end_session` | Write summary, trigger re-planning |
| `flag_for_parent` | Safety or concern alert |

Model IDs live in config, not code. Default `claude-opus-5-5` for teaching, planning and marking. Whether to use a cheaper model for screening and routine marking is a cost decision to make after measuring real usage. The stable system prompt and curriculum are prompt-cached; replies stream to the screen.

### 12.3 Voice and whiteboard

Voice is part of the core product, built straight after the text tutor works.

- Claude handles text and images. Speech needs two separate services: speech-to-text for the child and text-to-speech for the tutor. They are chosen in the voice phase by testing with real children's speech in English, Arabic, French and Spanish.
- First version: the child holds a button to talk, and the tutor's reply is spoken as it is generated. Hands-free conversation where the child can interrupt comes next.
- Every spoken reply is also shown as text, and every question can be answered by tapping, so a recognition error never blocks a child.
- The whiteboard is shared: the tutor draws through a tool, the child draws by touch, and the tutor can see a snapshot of the child's drawing.
- The text tutor is built first because the automated tests run on text. Voice is a layer over the same tutor, not a second one.

### 12.4 How the system itself keeps improving

- A test set of scripted child conversations per age band and subject, scored on: did it teach instead of tell, was it correct, was it age-appropriate, did it follow the session structure, was it free of stereotypes. Run before every prompt or model change.
- Each session plan records whether the exit questions were passed, so explanations that work are reused and ones that fail are retired.
- Parent thumbs up/down on reports and a child end-of-session rating.
- The research register is reviewed every quarter.

---

## 13. Build order

Each phase ends with a check that must pass before the next starts.

| Phase | Work | Done when |
|-------|------|-----------|
| 0. Base | Make the feature branch the base; delete dead code; fix the deploy; add tests, CI and migrations; verify research citations and the curriculum licence | App starts from a clean checkout and deploys; tests run in CI |
| 1. Accounts | Parent and child accounts, real login, all state in Postgres | Two children on one parent account have separate records that survive a restart |
| 2. Curriculum | Import maths and English for Years 1–7 as a graph; item bank with computed answers; placement | A new child finishes placement and gets a mastery map |
| 3. Tutor | Learner record, tutor tools, the section 8 session flow in text, child-led choices, safety screening, test set | A scripted session runs end to end and the record updates correctly; tests pass |
| 4. Voice | Hold-to-talk, spoken replies, shared whiteboard, in English | A full session with no typing |
| 5. Planning | Half-term, week and session plans; tutor-mode timetable; extra sessions; re-planning rules | A simulated 6-week child gets sensible plans that react to pass and fail |
| 6. Homework | Assign, submit (typed and photo), mark, feed back | Homework from one session is reviewed in the next |
| 7. Parent | Reports, transcripts, goals, mode and language choices, alerts, export and delete | Parent sees an accurate weekly report |
| 8. Science and practical subjects | Science content; art, cooking and life-skills menus, portfolio, adult-present check | A practical session runs from choice to photo to feedback |
| 9. Languages | Arabic, French, Spanish: right-to-left display, alphabet and handwriting for Arabic, vocabulary, listening and speaking | A 10-minute lesson in each language runs by voice |
| 10. School mode | Full-day timetable with off-screen blocks, history and geography content, attendance records | A simulated school week runs for each age band |
| 11. Real use | 2–4 weeks with real children | Issues list worked through |

---

## 14. Risks

| Risk | Handling |
|------|----------|
| The model teaches something wrong | Computed maths answers; checked item bank; tests; parent-visible transcripts |
| The model gives answers away | Tool design withholds answers on graded items; the test set measures it |
| Child-led drifts away from the curriculum | The tutor owns the skill sequence; the child owns context, order and projects |
| Speech recognition struggles with children's voices and with learners' Arabic, French and Spanish | Vendors tested on real children's speech before choosing; tap alternatives for every response; no marks for pronunciation |
| Voice is now on the critical path | Built in phase 4 on top of a tested text tutor; text and tap remain as fallback |
| Cooking injuries | Adult-present confirmation; age-graded tasks |
| Running cost per child | Prompt caching; measure in real use before choosing cheaper models |
| Scope: seven subjects, three languages, two modes | Phase order; nothing later starts until the earlier check passes |

---

## 15. Costs

Vendors bill in US dollars, so figures are in dollars; UK VAT may be added. AI figures are my estimates from published token prices and assumed usage; expect them to be off by up to 2x until real sessions are measured. Hosting and speech prices come from third-party listings found on 2026-11-20 and must be confirmed on the vendors' own pricing pages.

### 15.1 One-off setup

| Item | Cost | Basis |
|------|------|-------|
| Building the software | No extra charge | Done in these sessions under your existing Claude plan |
| National Curriculum data | $0 | Published free under the Open Government Licence; to be confirmed |
| Generating and checking the item bank, running tests during the build | $120–350 | My estimate of API spend, for seven subjects and three languages |
| Domain name | $10–15 a year | From memory, not checked |
| **Total** | **about $130–365** | |

### 15.2 Fixed monthly running cost

| Item | Cost |
|------|------|
| Web server (Render Starter) | $7 |
| Background worker | $7 |
| Postgres database | $7–19 |
| Email, error tracking, file storage | $0 on free tiers (from memory) |
| **Total** | **about $21–33** |

The free Render plan in the current `render.yaml` sleeps when idle and cannot run a background worker, so it is not usable for this.

### 15.3 AI and voice cost per child per month

Assumptions: about $2 per hour of live tutoring on Claude Opus 5.5 ($4 in / $20 out per million tokens, with prompt caching), plus planning, marking and reports. Voice is $0.50–2.50 per tutoring hour: speech-to-text at about $0.005–0.008 per minute, and text-to-speech from $15 per million characters (OpenAI) to $40–100 (ElevenLabs, better voices and faster). Claude Sonnet 5.5 would halve the AI column.

| Mode | Age | Tutor-led hours a month | AI (Opus 5.5) | Voice | Total |
|------|-----|-------------------------|---------------|-------|-------|
| Tutor | 6–8 | about 10 | $23–28 | $5–25 | $28–53 |
| Tutor | 9–12 | about 16 | $36–42 | $8–40 | $44–82 |
| School | 6–8 | about 24 | $55–65 | $12–60 | $67–125 |
| School | 9–12 | about 38 | $85–100 | $19–95 | $104–195 |

Each extra tutor-mode session adds about $1.25–2.50 including voice.

### 15.4 Worked example

Two children, aged 7 and 10, with mid-priced voice, after about $130–365 of one-off setup:

| | Hosting | AI | Voice | Total a month |
|---|---------|----|-------|---------------|
| Both in tutor mode | $28 | $60–70 | $35–40 | **about $125–140** |
| Both in school mode | $28 | $140–165 | $90–95 | **about $260–290** |
