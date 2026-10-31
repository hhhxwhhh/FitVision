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
- Core algorithm: velocity-based-training (VBT) metrics — per-rep duration, mean velocity and a tempo bucket — exposed from the pose engine and shown in the training preview.
- Synthetic demo data: a pure, deterministic generator (`utils/demo_data.py`) and the `seed_demo_history` command create reproducible training sessions, per-exercise records, interactions and aggregate stats; `seed_demo --with-history` wires it into setup.
- Pose engine: two new exercise modes — 弓步 (lunge, uses the more flexed knee as the primary signal with stride and symmetry checks) and 卷腹 (crunch, driven by hip flexion with knee-stability and hip-travel checks). Six modes are now supported.
- Accessibility & UX: skip-to-content link, `aria-current` navigation, global keyboard shortcuts (`?` and `g` leader keys), a redesigned 404 page, and a scroll-progress back-to-top control.
- Training history timeline (`/history`): month-grouped sessions with completion filter, pagination, an empty state,
  and a drill-down detail view (`/history/:id`) with a per-exercise breakdown.
- Training data export: CSV download of the loaded sessions (RFC 4180 escaping, UTF-8 BOM) plus period stat cards for the last 7 days and the current month.
- Bundle budget guard: `npm run size` fails the build when gzip budgets for the entry chunk, critical CSS or any single JS chunk are exceeded.

### Fixed
- Security: AI-generated rich text is now sanitised before every `v-html` binding, closing HTML-injection paths in the training report and AI plan views.

### Changed
- Recommendation diversity re-ranking now uses **Maximal Marginal Relevance (MMR)** instead of a fixed per-muscle penalty, balancing relevance against redundancy with a tested pure-Python implementation.
- Visual language refreshed to a warm-neutral, sporty theme: burnt-orange accent, flat surfaces, crisp borders and tighter radii; removed aurora gradients, glass blur, coloured glows and gradient text.
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
