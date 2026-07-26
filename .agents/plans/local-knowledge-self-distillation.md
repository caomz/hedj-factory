# Feature: Local Knowledge Self-Distillation

## Feature Description

Enhance the existing Nuwa self-distillation flow so a user can provide a large local knowledge directory, such as `/Volumes/WorkSSD/Dev/openclaw_mz/knowledge/raw`, and receive two coordinated outputs:

1. A compact runtime profile used by `baokuan-factory` to inject the user's positioning, judgment, taste, and voice.
2. A traceable personal asset library containing the user's core theses, operating principles, systems, evidence, content motifs, and reusable products.

The new mode must separate user-authored knowledge from private evidence, adapted material, and external references. It must not copy the original corpus, expose private chat content, or treat collected third-party material as the user's own intellectual property.

## User Story

As an AI creator with a mixed local knowledge base, I want Nuwa to identify and distill the parts that genuinely represent my thinking and practice, so that downstream content workflows can reuse my voice and judgment without leaking private data or confusing my collections with my original work.

## Problem Statement

Nuwa currently supports a small set of local books, transcripts, articles, or links, but its workflow is optimized for distilling public figures:

- Phase 0.5 copies or moves local material into the generated skill, which is unsafe and impractical for a 13,000-file corpus.
- The six research dimensions and `skill-template.md` center on public-person research, role-play, public timelines, and external reputation.
- There is no deterministic inventory, provenance policy, duplicate/version handling, or reading budget for a large mixed directory.
- Private chats and work records can contain names, internal context, identifiers, and credentials.
- The current output is one `SKILL.md`; putting all evidence and content assets there would make every downstream invocation expensive.
- The current onboarding writes `skills/<handle>/`, while `.gitignore` only safely generalizes personal profiles matching `skills/*-profile/`.
- Existing downstream consumers require sections such as core mental models, taste grading, expression DNA, and anti-patterns, but the general Nuwa template does not guarantee all of them for self profiles.

## Proposed Approach

Add a separate `self-local-corpus` branch to Nuwa while preserving the existing public-person and small-local-material paths.

The flow will:

1. Inventory the directory without copying or semantically reading it.
2. Produce a user-reviewable source policy classifying paths as authored, private evidence, adapted, external, or excluded.
3. Apply deterministic duplicate, file eligibility, privacy, and reading-budget rules.
4. Analyze the selected material across six self-distillation dimensions.
5. Generate a compact `SKILL.md` plus an on-demand `assets/` library.
6. Run self-profile-specific quality and privacy checks before updating `~/.baokuan-factory/profile`.

New self profiles will be stored as `skills/<handle>-profile/`, which already matches the repository's generic ignore rule. Existing `skills/<handle>/` profiles remain valid and are not migrated automatically.

## Metadata

**Feature Type:** enhancement
**Complexity:** high
**Affected Systems:** Nuwa skill instructions and templates, Nuwa helper scripts, baokuan onboarding, trigger evaluation cases, documentation, personal-profile storage convention
**Dependencies:** Python 3 standard library, Markdown/YAML conventions, existing `baokuan-factory` profile marker; no new package manager or runtime dependency

## Context References

### Files To Read Before Implementation

- `AGENTS.md` - repository-specific coding, verification, and safety rules; currently untracked and must not be committed implicitly.
- `skills/nuwa-skill/SKILL.md` - existing person/theme/local-material workflows, checkpoints, six research dimensions, update mode, and quality criteria.
- `skills/nuwa-skill/references/extraction-framework.md` - mental-model validation, expression DNA measurement, contradiction handling, and source-quality rules.
- `skills/nuwa-skill/references/skill-template.md` - public-person output contract that must remain unchanged for non-self distillation.
- `skills/nuwa-skill/scripts/merge_research.py` - current fixed `01`-`06` research summary convention.
- `skills/nuwa-skill/scripts/quality_check.py` - current person-profile quality gate and CLI behavior.
- `skills/baokuan-factory/SKILL.md` - onboarding route, profile marker, and downstream sections consumed at the two injection points.
- `docs/SOP.md` - documented relationship between self profile, benchmark distillation, script writing, rendering, and publishing.
- `.gitignore` - existing `skills/*-profile/` privacy rule and generated-media exclusions.
- `.optimize/trigger-evals.json` - current positive/negative routing examples for onboarding versus standalone Nuwa requests.

### Files To Create Or Update

- `skills/nuwa-skill/SKILL.md` - add the `self-local-corpus` routing branch, checkpoints, provenance rules, budgets, output contract, and failure handling.
- `skills/nuwa-skill/references/self-distill-workflow.md` - detailed source policy, research dimensions, asset-card schema, privacy rules, and incremental refresh behavior.
- `skills/nuwa-skill/references/self-profile-template.md` - runtime self-profile template without public-person role-play semantics.
- `skills/nuwa-skill/scripts/inventory_local_corpus.py` - deterministic metadata/hash inventory and policy application.
- `skills/nuwa-skill/scripts/merge_research.py` - support person and self research labels without breaking the existing CLI.
- `skills/nuwa-skill/scripts/quality_check.py` - auto-detect self profiles and add downstream-contract and privacy checks.
- `skills/baokuan-factory/SKILL.md` - accept a local folder during Phase O and use the new `skills/<handle>-profile/` convention for new profiles.
- `README.md` and `docs/SOP.md` - document folder-based self-distillation, outputs, privacy behavior, and compatibility.
- `.optimize/trigger-evals.json` - add positive local-folder onboarding cases and negative standalone-person cases.
- `tests/test_nuwa_local_corpus.py` - standard-library unit and integration tests for inventory, policy, and quality-gate behavior.
- `tests/fixtures/nuwa-self-distill/` - synthetic non-personal corpus and passing/failing profile fixtures.

### Relevant Docs

- No external API or package documentation is required. The implementation is local-only and uses Python's standard library.
- Current public behavior is defined by `README.md`, `docs/SOP.md`, and the two skill files above; they are the authoritative compatibility contract.

### Existing Patterns

- **Naming:** skills are top-level directories under `skills/`; private profiles should use the already ignored suffix `-profile`.
- **Error handling:** Python scripts print a concise actionable error and return non-zero for missing inputs or failed validation.
- **Logging:** helper scripts print human-readable Markdown or JSON summaries; the repository has no shared logging framework.
- **Tests:** there is no root test runner. Add `unittest` tests without introducing `pytest`, `pyproject.toml`, or a root dependency manifest.
- **Gotchas:** `install.sh` symlinks every top-level `skills/*/` directory; personal profiles therefore remain functional but must stay ignored. The trigger evaluator rewrites the installed skill and calls an external Claude model, so it is not a default validation command.

## Public Interfaces And Output Contract

### Inventory CLI

```bash
python3 skills/nuwa-skill/scripts/inventory_local_corpus.py \
  /absolute/path/to/raw \
  --profile-dir /absolute/path/to/skills/<handle>-profile \
  [--policy /absolute/path/to/source-policy.json] \
  [--max-file-bytes 2000000] \
  [--check]
```

Behavior:

- Resolve and validate the source root and profile output directory.
- Refuse a missing root, a non-directory root, or an output directory inside the source tree.
- Skip symlinks by default so a corpus cannot escape its declared root.
- Inventory all non-hidden regular files, but mark only supported text formats as semantically eligible.
- Supported semantic formats in v1: `.md`, `.markdown`, `.txt`, `.json`, `.jsonl`, `.html`, `.htm`, `.yaml`, `.yml`, and `.csv`.
- Record unsupported/binary files as counts only; never attempt to parse SQLite, images, video, audio, or unknown formats.
- Store relative paths, extension, byte size, modification time, SHA-256, top-level family, duplicate group, eligibility, policy class, and exclusion reason.
- Without `--policy`, assign `unclassified` and generate an inventory review.
- With `--policy`, apply ordered glob rules and report unmatched paths.
- `--check` prints statistics and performs no writes.

Generated private research files:

```text
skills/<handle>-profile/
└── references/
    ├── source-policy.json
    ├── source-manifest.json
    └── research/
        └── 00-source-inventory.md
```

The manifest may retain the absolute local root because the entire profile directory is private and ignored. `SKILL.md` and publishable assets must use relative source identifiers and must not expose that absolute path.

### Source Policy Schema

```json
{
  "schema_version": 1,
  "rules": [
    {"class": "authored", "globs": ["path/**"]},
    {"class": "private-evidence", "globs": ["path/**"]},
    {"class": "adapted", "globs": ["path/**"]},
    {"class": "external", "globs": ["path/**"]},
    {"class": "excluded", "globs": ["path/**"]}
  ]
}
```

Rules are evaluated in file order; first match wins. Unmatched files remain `unclassified` and block semantic distillation until reviewed or explicitly excluded.

### Self-Profile Directory

```text
skills/<handle>-profile/
├── SKILL.md
├── assets/
│   ├── index.md
│   ├── positioning.md
│   ├── core-theses.md
│   ├── operating-principles.md
│   ├── systems-and-workflows.md
│   ├── cases-and-evidence.md
│   ├── content-motifs.md
│   └── reusable-products.md
└── references/
    ├── source-policy.json
    ├── source-manifest.json
    └── research/
        ├── 00-source-inventory.md
        ├── 01-positioning.md
        ├── 02-core-theses.md
        ├── 03-decisions-and-behavior.md
        ├── 04-systems-and-cases.md
        ├── 05-expression-dna.md
        └── 06-tensions-and-evolution.md
```

`SKILL.md` is the only file loaded by default downstream and should target 3,000-6,000 tokens. The larger asset pages are loaded only when a task needs deeper evidence or content ideation.

### Asset Card Contract

Each distinct asset must include:

```yaml
origin: authored | co-created | private-derived | adapted | external
evidence: observation | repeated | validated
visibility: private | sanitized | public-ready
confidence: stated | high | medium | speculation
sources:
  - relative/source/path
```

The body records the asset statement, problem solved, evidence, applicability, limitations, reusable form, content opportunities, and next validation step. An external-only idea cannot be classified as a personal asset; it may only appear as context or comparison.

## Implementation Plan

### Phase 1: Preparation

- Add the self-distillation reference document and self-profile template before changing routing logic.
- Define the exact separation between the compact runtime profile, private research evidence, and reusable asset pages.
- Document source precedence, version selection, reading budgets, and privacy defaults.
- Preserve all existing person/theme behavior and the legacy `skills/<handle>/` profile path.

### Phase 2: Core Implementation

- Implement the local corpus inventory and policy CLI using only the Python standard library.
- Add the `self-local-corpus` branch to Nuwa:
  - Trigger when the user asks to distill themselves and supplies a directory.
  - Default to pure local analysis; do not browse the web unless the user asks for external corroboration.
  - Do not copy or move raw source files.
  - Pause after inventory so the user can confirm provenance and privacy classes.
- Run six self-specific research dimensions and preserve exact relative source references.
- Apply reading budgets:
  - Authored: all eligible files up to 20 MB total per pass; split larger sets into explicit batches.
  - Private evidence: prefer existing summaries/analysis files; default maximum 100 files or 5 MB per pass; do not quote raw chats.
  - Adapted: maximum 30 selected files per pass.
  - External: excluded from the first semantic pass; read only exact files needed to verify or contrast a personal claim.
- Skip exact hash duplicates. For filename versions such as `v0.1`, `v0.2`, `v0.3`, use the highest version as current and retain older versions only as evolution evidence.
- Require either two owned sources or one owned source plus a real decision/case before marking an asset `repeated` or `validated`.

### Phase 3: Integration

- Generate `SKILL.md` from the self template, not the public-person role-play template.
- Guarantee downstream sections:
  - positioning and audience,
  - core mental models,
  - decision heuristics,
  - expression DNA,
  - content taste / "from strong to weak" grading,
  - values and anti-patterns,
  - evidence boundaries,
  - links to deeper asset pages.
- Update baokuan Phase O to accept either social links/files or a local directory.
- For new self profiles, write `skills/<handle>-profile/SKILL.md` to `~/.baokuan-factory/profile`; continue accepting a valid legacy marker unchanged.
- Update README/SOP examples and trigger-eval cases.

### Phase 4: Testing And Verification

- Add unit tests for deterministic inventory, glob precedence, duplicates, symlink skipping, unsupported files, size limits, and invalid paths.
- Add regression tests for the existing public-person quality checks.
- Add self-profile quality tests for required sections, source traceability, token-size budget, and privacy rejection.
- Run a synthetic end-to-end flow using a temporary corpus; do not use or copy the user's real private corpus in automated tests.
- Run a read-only inventory check against the actual directory after implementation to verify scale and performance.
- Treat external trigger evaluation as optional because it rewrites installed state and consumes model quota.

## Ordered Tasks

### CREATE `skills/nuwa-skill/references/self-distill-workflow.md`

- **IMPLEMENT:** Define routing, source classes, review checkpoints, six analysis dimensions, reading budgets, version precedence, asset scoring, privacy redaction, incremental refresh, and output boundaries.
- **PATTERN:** Follow the detailed methodology style in `references/extraction-framework.md`, but describe self-distillation rather than public-person role-play.
- **IMPORTS:** None.
- **GOTCHA:** Do not hardcode the current user's Chinese directory names into the shared feature; use them only as an example.
- **VALIDATE:** `git diff --check -- skills/nuwa-skill/references/self-distill-workflow.md`

### CREATE `skills/nuwa-skill/references/self-profile-template.md`

- **IMPLEMENT:** Provide a compact profile template containing all sections consumed by baokuan and links to the asset library.
- **PATTERN:** Reuse frontmatter and evidence conventions from `skill-template.md`, but replace role-play instructions with first-party collaboration rules and a strict "do not invent my experience" rule.
- **IMPORTS:** None.
- **GOTCHA:** Keep the generated runtime profile within the 3,000-6,000 token target and keep raw evidence in `references/`.
- **VALIDATE:** `rg -n '^## (定位与受众|核心心智模型|决策启发式|表达DNA|内容品味与评分标准|价值观与反模式|诚实边界)' skills/nuwa-skill/references/self-profile-template.md`

### CREATE `skills/nuwa-skill/scripts/inventory_local_corpus.py`

- **IMPLEMENT:** Add the inventory CLI, deterministic traversal, SHA-256 duplicate grouping, format/size eligibility, policy loading, ordered glob matching, Markdown summary, JSON manifest, and `--check`.
- **PATTERN:** Use `pathlib`, UTF-8, `argparse`, explicit validation, and non-zero exits as in the existing Nuwa scripts.
- **IMPORTS:** `argparse`, `fnmatch`, `hashlib`, `json`, `pathlib`, and other Python standard-library modules only.
- **GOTCHA:** Never follow symlinks, never parse source bodies during inventory, never write inside the source tree, and never copy source files.
- **VALIDATE:** `python3 -m unittest tests.test_nuwa_local_corpus.LocalCorpusInventoryTests`

### UPDATE `skills/nuwa-skill/SKILL.md`

- **IMPLEMENT:** Add self-local-corpus routing, inventory/policy checkpoint, pure-local default, reading budgets, six self-specific research notes, self-template selection, privacy rules, and incremental refresh semantics.
- **PATTERN:** Preserve existing Phase 0-5 person flow; add an explicit branch instead of rewriting shared phases ambiguously.
- **IMPORTS:** Reference the new workflow, template, and inventory script with paths relative to `skills/nuwa-skill/`.
- **GOTCHA:** The generic "all research must be self-contained" rule must gain a self-profile exception: sanitized summaries stay inside the profile, but private raw sources remain external and read-only.
- **VALIDATE:** `python3 -c 'from pathlib import Path; t=Path("skills/nuwa-skill/SKILL.md").read_text(); assert "self-local-corpus" in t and "inventory_local_corpus.py" in t and "self-profile-template.md" in t'`

### UPDATE `skills/nuwa-skill/scripts/merge_research.py`

- **IMPLEMENT:** Add `--mode person|self` or auto-detection so the existing `01`-`06` files retain public-person labels while self profiles receive the six self-specific labels and source-class counts.
- **PATTERN:** Preserve current default output and exit behavior for callers that pass only a skill directory.
- **IMPORTS:** Standard library only.
- **GOTCHA:** Local source evidence may not have URLs; count unique relative source references rather than equating source count with URL count in self mode.
- **VALIDATE:** `python3 -m unittest tests.test_nuwa_local_corpus.MergeResearchCompatibilityTests`

### UPDATE `skills/nuwa-skill/scripts/quality_check.py`

- **IMPLEMENT:** Auto-detect `profile_type: self`, accept either a profile directory or `SKILL.md`, keep current person checks, and add self checks for required downstream sections, asset index, evidence links, profile size, and privacy markers.
- **PATTERN:** Return zero only when all required checks pass and print actionable failures.
- **IMPORTS:** Standard library only.
- **GOTCHA:** Scan public-facing `SKILL.md` and `assets/*.md` for credential assignments, `wxid_`, `@chatroom`, and similar identifiers; do not falsely fail solely because private source family names appear in the private manifest.
- **VALIDATE:** `python3 -m unittest tests.test_nuwa_local_corpus.QualityCheckTests`

### CREATE `tests/test_nuwa_local_corpus.py` AND SYNTHETIC FIXTURES

- **IMPLEMENT:** Cover successful inventory, missing root, output-inside-source rejection, symlink skip, exact duplicate detection, ordered policy precedence, unsupported binary recording, oversized-file exclusion, deterministic relative paths, person-mode regression, self-mode pass, missing-section failure, and privacy failure.
- **PATTERN:** Use `unittest`, `tempfile.TemporaryDirectory`, and subprocess only where CLI exit behavior must be tested.
- **IMPORTS:** Python standard library only.
- **GOTCHA:** Fixtures must contain no real personal data or working secret; use unmistakably fake values.
- **VALIDATE:** `python3 -m unittest discover -s tests -p 'test_nuwa_*.py' -v`

### UPDATE `skills/baokuan-factory/SKILL.md`

- **IMPLEMENT:** Let Phase O accept a local directory, route it to Nuwa self-local-corpus mode, use `skills/<handle>-profile/` for new profiles, and validate the marker before continuing.
- **PATTERN:** Keep baokuan as an orchestrator; all corpus analysis remains delegated to Nuwa.
- **IMPORTS:** None.
- **GOTCHA:** Do not rename or invalidate existing `skills/<handle>/SKILL.md` profiles.
- **VALIDATE:** `rg -n 'local directory|本地目录|<handle>-profile|self-local-corpus' skills/baokuan-factory/SKILL.md`

### UPDATE DOCUMENTATION AND TRIGGER CASES

- **IMPLEMENT:** Update `README.md`, `docs/SOP.md`, and `.optimize/trigger-evals.json` with local-folder onboarding, dual outputs, privacy defaults, ignored profile path, and compatibility notes.
- **PATTERN:** Preserve the existing five-layer pipeline and add the new input option under line A.
- **IMPORTS:** None.
- **GOTCHA:** Do not imply that every file is semantically read or that third-party archives become the user's personal assets.
- **VALIDATE:** `python3 -m json.tool .optimize/trigger-evals.json >/dev/null && git diff --check -- README.md docs/SOP.md .optimize/trigger-evals.json`

### RUN SYNTHETIC END-TO-END VERIFICATION

- **IMPLEMENT:** Create a temporary mixed corpus, run inventory without policy, apply a test policy, rerun inventory, populate a fixture self profile, run quality checks, and confirm no source file changes.
- **PATTERN:** Use a temporary directory and before/after SHA-256 inventory.
- **IMPORTS:** None.
- **GOTCHA:** Do not run `install.sh`, `sync.sh`, the external trigger evaluator, or publishing tools.
- **VALIDATE:** `python3 -m unittest discover -s tests -p 'test_nuwa_*.py' -v`

### RUN READ-ONLY SCALE CHECK ON THE REAL CORPUS

- **IMPLEMENT:** Use `--check` against `/Volumes/WorkSSD/Dev/openclaw_mz/knowledge/raw` and record file totals, eligible totals, skipped formats, duplicates, and elapsed time.
- **PATTERN:** The command must not create a profile or write into the knowledge base.
- **IMPORTS:** None.
- **GOTCHA:** Do not print file contents, private identifiers, or detected credential values in the report.
- **VALIDATE:** `python3 skills/nuwa-skill/scripts/inventory_local_corpus.py /Volumes/WorkSSD/Dev/openclaw_mz/knowledge/raw --check`

## Test Strategy

### Unit Tests

- Inventory traversal and source-root validation.
- Policy JSON schema, ordered matching, and unmatched-file blocking.
- Hash duplicate grouping and relative-path stability.
- Eligibility decisions for supported, oversized, hidden, symlinked, and binary files.
- Self/person research summary compatibility.
- Self-profile required-section, evidence, size, and privacy checks.
- Regression of the current public-person quality-check behavior.

### Integration Tests

- Synthetic mixed corpus through both inventory passes.
- Generated manifest and Markdown summary use relative file paths and contain no source body text.
- A passing self-profile fixture is accepted and a privacy-contaminated fixture is rejected.
- Existing baokuan routing language still treats standalone public-person distillation as Nuwa work rather than full-pipeline onboarding.

### Manual Verification

1. In the repository root, provide a temporary directory containing authored notes, a private summary, an adapted note, an external article, two exact duplicates, and a version sequence.
2. Run inventory without a policy.
3. Confirm the visible result contains counts and path families only, with all files initially unclassified.
4. Add a policy and rerun.
5. Confirm first-match precedence, duplicate grouping, current-version selection guidance, and zero copied raw files.
6. Generate or use the synthetic self-profile fixture and run the quality check.
7. Confirm downstream-required sections are present and privacy-contaminated output fails with an actionable message.
8. Run the real-corpus `--check`; confirm it performs no writes and does not reveal raw content.
9. Optionally, after explicit quota approval, run one-pass trigger evaluation and verify:
   - “阅读这个本地知识文件夹，蒸馏成我的个人资产和 profile” routes to Nuwa or baokuan onboarding as specified.
   - “蒸馏某个公众人物” does not route to the full baokuan pipeline.

## Verification Commands

```bash
git status --short --branch
git diff --check

bash -n install.sh \
  skills/baokuan-factory/scripts/sync.sh \
  skills/nuwa-skill/scripts/download_subtitles.sh

python3 -c 'import ast,pathlib; [ast.parse(p.read_text(encoding="utf-8")) for p in pathlib.Path("skills/nuwa-skill/scripts").glob("*.py")]'
python3 -m unittest discover -s tests -p 'test_nuwa_*.py' -v
python3 -m json.tool .optimize/trigger-evals.json >/dev/null

python3 skills/nuwa-skill/scripts/inventory_local_corpus.py \
  /Volumes/WorkSSD/Dev/openclaw_mz/knowledge/raw \
  --check
```

Optional, only after explicit approval because it rewrites the installed skill and consumes external model quota:

```bash
BKF_RUNS=1 BKF_WORKERS=1 \
  python3 .optimize/bkf_eval.py \
  .optimize/trigger-evals.json \
  .optimize/desc_v2.txt
```

## Acceptance Criteria

- [ ] A user can supply an absolute local directory during self-distillation without copying or modifying that directory.
- [ ] Inventory handles the current 13,000+ file corpus in `--check` mode and reports metadata only.
- [ ] Every eligible file is classified by an approved source policy or blocks semantic distillation as `unclassified`.
- [ ] Exact duplicates are read once, and versioned drafts have an explicit current-version rule.
- [ ] External-only material is never labeled as the user's authored personal asset.
- [ ] Private chat-derived assets contain no names, chat identifiers, credentials, internal addresses, or source excerpts.
- [ ] New self profiles are written under `skills/<handle>-profile/` and remain ignored by Git.
- [ ] Existing public-person Nuwa flows and legacy profile markers continue to work.
- [ ] The runtime `SKILL.md` contains all sections consumed by baokuan and stays within the defined size target.
- [ ] The asset library contains positioning, theses, principles, workflows, evidence, content motifs, and reusable-product pages with traceable sources.
- [ ] Self-profile and person-profile quality checks both pass their corresponding fixtures.
- [ ] Unit/integration tests, Python AST parsing, JSON validation, and `git diff --check` pass.
- [ ] No install, sync, publish, commit, push, or external model-quota action occurs without separate authorization.

## Risks And Rollback

- **Risk:** Private messages or credentials leak into generated assets.
  - **Mitigation:** Private-evidence default, no raw chat quotes, public-facing privacy scan, source-policy checkpoint, and user review before marking anything public-ready.
  - **Rollback:** Restore the previous profile marker and stop using the generated profile; leave the raw corpus untouched.
- **Risk:** Third-party collections are misrepresented as original thought.
  - **Mitigation:** Required provenance classes, external-only exclusion from personal assets, and evidence thresholds.
  - **Rollback:** Reclassify source policy and regenerate only research/assets; do not rewrite raw data.
- **Risk:** Large corpus processing overruns context or produces shallow synthesis.
  - **Mitigation:** Deterministic inventory, exact duplicate elimination, explicit reading budgets, dimension-specific batches, and review checkpoints.
  - **Rollback:** Fall back to the current small-local-material flow with a curated subset.
- **Risk:** New self logic changes public-person behavior.
  - **Mitigation:** Separate templates, explicit mode branch, regression fixtures, and default-compatible CLI changes.
  - **Rollback:** Remove the self-local-corpus branch and new helpers while retaining the unchanged public-person template and flow.
- **Risk:** Personal profile is accidentally committed.
  - **Mitigation:** Standardize new outputs on the existing ignored `skills/*-profile/` pattern and verify with `git status --ignored`.
  - **Rollback:** Unstage the exact profile path if needed; do not use broad reset or deletion commands.
- **Risk:** Existing `AGENTS.md` from the interrupted prior workflow is unintentionally included.
  - **Mitigation:** Treat it as an independent untracked file and exclude it from this feature's commit or patch unless the user separately requests otherwise.
  - **Rollback:** Leave the file untouched; no action is required for this feature.

## Confidence

8/10 for first-pass implementation success.

The file inventory, provenance, compatibility, and privacy gates are straightforward. The remaining uncertainty is semantic quality: a prompt-driven self-model can still overfit polished drafts or self-description, so evidence thresholds and the two user review checkpoints are essential.
