# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Frontend test suite: Vitest configuration, test setup with browser-API shims, and unit tests for pose utilities and the user store.
- Frontend test coverage reporting (`npm run test:coverage`, `@vitest/coverage-v8`).
- CI: frontend test + coverage job, backend coverage report, and a real Docker Compose image build in CI.
- CodeQL security scanning workflow for Python and JavaScript.
- Release automation: tag-triggered workflow that builds the frontend and publishes GitHub Releases with generated notes.
- Local developer experience: `.pre-commit-config.yaml` (Black/isort/flake8 + ESLint/Prettier) and `commitlint` for Conventional Commits.
- Community health files: `CODEOWNERS`, `FUNDING.yml`, issue/PR labeler, stale-issue cleanup, `SUPPORT.md`, and `GOVERNANCE.md`.
- Documentation system: `docs/ARCHITECTURE.md`, `docs/DEVELOPMENT.md`, `docs/DEPLOYMENT.md`, and an archived folder for historical dev notes.
- Core algorithm: **per-muscle-group recovery model** (`backend/utils/recovery.py`) — set/rep volume spreads across a synergist matrix and decays with per-muscle exponential half-lives, producing recovery %, hours-to-ready, weekly set volume and a recommendation multiplier; 51 Django-free tests.
- Core algorithm: **strength & progression engine** (`backend/utils/strength.py`) — e1RM from three independent sources (conservative rep formulas, velocity-based rep capacity, RPE/RIR inversion), double-progression prescriptions, e1RM trend and deload-week detection; 63 Django-free tests.
- Core algorithm: **training periodization engine** (`backend/utils/periodization.py`) — splits a 3–6 week mesocycle into accumulation / intensification / realization / deload phases, derives weekly volume from the per-muscle recovery model (10–20 sets per muscle per week), derives intensity from the e1RM curve, discounts the whole cycle when readiness is low and distributes the volume across training days by movement pattern; 33 Django-free tests.
- `GET /api/growth/mesocycle/?weeks=&days_per_week=`: the mesocycle plan — weekly phases, per-day training load and the prescribed load for every muscle group.
- Data centre gained a 训练周期化 (中周期) card backed by `MesocyclePanel` and a shared `src/utils/periodization.ts` presentation layer (34 tests).
- `PersonalRecord.record_type` gained an `e1rm` option (migration `growth/0005`), so estimated one-rep maxes are tracked like any other record.
- **Closed loop**: training records accept an optional RIR (reps in reserve) and RPE, the RIR-based estimate feeds the e1RM curve, and the smart plan prescribes a concrete load per exercise from that e1RM (migration `training/0003`).
- `GET /api/growth/strength/?days=&exercise_id=&reps=&rir=`: per-exercise e1RM curve plus the prescribed load for the next session.
- Data centre gained a 力量曲线 card: exercise picker, e1RM trend chart, prescription callout and deload warnings.
- `GET /api/growth/muscle-recovery/`: today's recovery state for every muscle group plus the suggested `focus` / `avoid` lists.
- `MuscleRecoveryPanel` on the training page and a shared `src/utils/muscleRecovery.ts` presentation layer (25 tests).
- Core algorithm: velocity-based-training (VBT) metrics — per-rep duration, mean velocity and a tempo bucket — exposed from the pose engine and shown in the training preview.
- Synthetic demo data: a pure, deterministic generator (`utils/demo_data.py`) and the `seed_demo_history` command create reproducible training sessions, per-exercise records, interactions and aggregate stats; `seed_demo --with-history` wires it into setup.
- Form-metric composable: quality badge, standard-rep streak and fault tally moved out of `usePoseDetection` into a unit-tested `useFormMetrics` (with coach tips for every engine fault, including the new lunge and crunch ones).
- Pose engine: two new exercise modes — 弓步 (lunge, uses the more flexed knee as the primary signal with stride and symmetry checks) and 卷腹 (crunch, driven by hip flexion with knee-stability and hip-travel checks). Six modes are now supported.
- Accessibility & UX: skip-to-content link, `aria-current` navigation, global keyboard shortcuts (`?` and `g` leader keys), a redesigned 404 page, and a scroll-progress back-to-top control.
- Training history timeline (`/history`): month-grouped sessions with completion filter, pagination, an empty state,
  and a drill-down detail view (`/history/:id`) with a per-exercise breakdown.
- Training insights: CSV export, last-7-day and current-month stat cards, and current / longest consecutive-day streaks on the history page. of the loaded sessions (RFC 4180 escaping, UTF-8 BOM) plus period stat cards for the last 7 days and the current month.
- Bundle budget guard: `npm run size` fails the build when gzip budgets for the entry chunk, critical CSS or any single JS chunk are exceeded.
- Component tests (happy-dom + `@vue/test-utils`) for `TrainingCalendar`, `BackToTop`, `ThemeToggle` and `NextExerciseRecommendation`, plus a `useTheme` composable test covering persistence, root-class mirroring and `meta[theme-color]` sync.
- **Training readiness / load engine** (`backend/utils/readiness.py`): a pure-Python, Django-free model combining the Banister fitness–fatigue impulse response (TSB), an EWMA-based ACWR (acute:chronic workload ratio), Foster monotony/strain, a least-squares form-quality trend and the rest gap — returning a 0–100 readiness score, a suggested intensity, a volume multiplier and human-readable reasons. 38 unit tests run without Django.
- Readiness is no longer a hand-waved `94 - fatigue * 55`: `growth.readiness_snapshot` now aggregates daily session loads (`daily_training_loads`) and delegates to the engine, and exposes `acwr / fitness / fatigue / tsb / monotony / strain / form_trend / rest_days / intensity / volume_multiplier / reasons`.
- Load-management UI: the home readiness card shows the workload ratio, TSB, rest gap and suggested intensity with the engine's reasons; the growth page gained a 训练负荷 panel with acute/chronic load, fitness, fatigue, form trend, suggested volume, an ACWR position bar against the 0.8–1.3 sweet spot and a last-4-weeks load bar chart (`weekly_loads`).
- The training page header shows today's readiness chip (score · suggested intensity · volume), fetched from `/growth/overview/` and hidden when the model is unavailable.
- Smart plan generation (`/api/training/plan/create_smart/`) now adapts to today's load: sets are scaled by the readiness volume multiplier via `utils.readiness.plan_volume` (7 tests), a recovery day is inserted when the model says `rest`, and the response carries a `readiness` block plus state-aware suggestions.
- `GET /api/growth/load-curve/?days=90&step=1` returns a per-day replay of fitness / fatigue / TSB / acute / chronic load / ACWR (`utils.readiness.load_curve`), and the analytics page draws it as a three-line chart. Params are clamped (`days` 7–180, `step` 1–7) and a failure degrades silently.
- The analytics CSV export now reuses `src/utils/csv.ts` (RFC 4180 escaping, BOM, consistent filename) instead of its own inline encoder.
- Synthetic training history is now **periodized** (`utils.demo_data.week_load_factor`): a 4-week cycle with three progressive-overload weeks and a deload week, so the readiness / ACWR / weekly-load views show real variation on demo data. `periodization=False` / `--no-periodization` restores the flat behaviour.
- Fatigue is now resolved through one entry point (`recommendations.services.resolve_fatigue_level`): the load model wins when it has seen training history, otherwise it falls back to the legacy `UserState` counter, and any failure degrades gracefully. The RL over-fatigue guard and the goal/fatigue re-rank both use it.
- `src/utils/loadModel.ts`: shared, unit-tested presentation layer for the readiness payload (safe narrowing of the API shape, ACWR tone/position, TSB / rest / intensity / trend / volume copy, weekly bar normalisation) — HomeView and GrowthView no longer duplicate that logic.

### Fixed
- Security: AI-generated rich text is now sanitised before every `v-html` binding, closing HTML-injection paths in the training report and AI plan views.
- Vitest no longer writes a throwaway `components.d.ts` into the project root (`dts: false` in the test config).
- The demo generator wrote `performance_score` on a 0–100 scale into a 0–5 field, which silently maxed out the growth XP quality bonus; it now emits the documented 0–5 scale.
- An all-zero load series was misread as "extremely monotonous", penalising brand-new accounts; the readiness engine now short-circuits when there is no training history at all.

### Changed
- Recommendation diversity re-ranking now uses **Maximal Marginal Relevance (MMR)** instead of a fixed per-muscle penalty, balancing relevance against redundancy with a tested pure-Python implementation.
- The recommendation engines no longer read the crude `UserState.fatigue_level` accumulator directly; fatigue now comes from the load model via a single resolver with graceful fallback.
- Recommendation ranking is additionally weighted by **local muscle recovery** (`_rerank_by_muscle_recovery`, 60% influence): exercises targeting a muscle group still inside its soreness window are pushed down, fully recovered groups get a small bonus.
- Growth test helpers now keep a synthetic session inside one local day, so the suite no longer trips over the midnight boundary.
- The `UserDailyStats` post-save signal no longer nudges fatigue by ±0.2/0.1 based on form score; it re-syncs `UserState.fatigue_level` from the load model (idempotent, keeps the old value when the model has no history).
- Visual language refreshed to a warm-neutral, sporty theme: burnt-orange accent, flat surfaces, crisp borders and tighter radii; removed aurora gradients, glass blur, coloured glows and gradient text.
- De-AI-ification pass 2: the last hardcoded blue/slate tones (AI 智能接力 card, algorithm badges, pose stats panel, timer ring, rest overlay, graph palette) now use the warm design tokens, and status halos follow `--fv-success` / `--fv-warning`.
- Navigation copy now uses coach-style wording (训练计划 / 动作纠错 / 训练数据 / 成长) with a "训练助手" product title.
- Performance: Element Plus and echarts are imported on demand, removing the 898KB `element-plus` chunk and shrinking the charts chunk from 1134KB to 399KB (dist 3.0M → 2.2M).

## [1.1.1] - 2026-04-19

### Added
- AI training closed loop: browser-side pose estimation, VLM-based form correction, AI training plans, and post-session coach-style reports.
- Hybrid recommendation engine: DL sequence (GRU + attention), knowledge graph (GCN), content-based (M3E + Chroma), RL adaptive re-ranking, time-travel collaborative filtering, and cold-start fallback.
- Growth & motivation: XP/levels, daily quests, limited-time challenges, achievement system, personal records, and a weekly leaderboard.
- Modern web experience: unified `--fv-*` design tokens with light/dark themes, command palette, training cockpit, growth center, installable PWA, and CSV data export.
- Backend foundation: Django 5 + DRF, JWT auth with throttling, PostgreSQL/SQLite fallback, Redis/LocMem cache fallback, and drf-spectacular OpenAPI docs.

[Unreleased]: https://github.com/hhhxwhhh/FitVision/compare/v1.1.1...HEAD
[1.1.1]: https://github.com/hhhxwhhh/FitVision/releases/tag/v1.1.1
