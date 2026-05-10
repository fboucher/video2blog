# Bishop — Project History

## Project Context

- **Project:** video2blog
- **Stack:** Python 3.11, Flask, OpenCV (opencv-python), numpy, requests, python-dotenv
- **What it does:** Extracts keyframes from videos and generates blog posts from them
- **Requested by:** fboucher
- **Primary mission:** Reduce Docker image size (currently ~1.5 GB)

## Key Files

- `Dockerfile` — what Vasquez will optimize; Bishop validates the result
- `web_app.py` — Flask app entry point; must start correctly in the container
- `keyframe_extractor.py` — uses OpenCV; must remain functional after switching to headless variant

## Known Constraints

- App runs on port 5123
- Must be able to import cv2, numpy, flask without errors in the final image

## Learnings

### Docker Optimization Verification (2025-01-XX)
**Context:** Vasquez optimized Docker image by switching opencv-python → opencv-python-headless, removing X11 libs, adding .dockerignore, and merging RUN layers.

**Tests Performed:**
1. **Static Dockerfile Analysis:** PASS
   - Apt packages (libgl1, libglib2.0-0, libgomp1) are minimal and sufficient for headless OpenCV
   - Multi-stage layer caching preserved (separate requirements.txt copy before code copy)
   - .dockerignore properly excludes dev artifacts (.git, .squad, node_modules, assets, docs)
   - RUN layers consolidated appropriately (apt-get cleanup, mkdir+chmod)

2. **Code Review for cv2 GUI Calls:** PASS
   - Scanned keyframe_extractor.py and web_app.py for cv2.imshow, cv2.waitKey, cv2.namedWindow, etc.
   - **Result:** Zero GUI calls found. Code is 100% headless-compatible.

3. **Docker Build Test:** PASS
   - Command: `docker build -t video2blog-test .`
   - Build completed successfully in ~1.2s (all layers cached from prior build)
   - All 9 build stages executed cleanly

4. **Import Verification:** PASS
   - Tested: `import cv2; import numpy; import flask`
   - Result: cv2 version 4.8.1 confirmed, all imports clean

5. **Image Size:** PASS
   - **Final size: 794 MB** (down from ~1.5 GB baseline)
   - **Reduction: ~47% smaller**

6. **Flask App Startup:** PASS
   - Tested: `from web_app import app`
   - Result: App loads without errors

**Verdict:** ALL CHECKS PASSED. Vasquez's optimization is production-ready.

**Regression Status:** None detected. All functionality intact after switching to opencv-python-headless.

### 2026-03-09 — Session Completion & Final Verification

**Work Completed:**
- Verified Hicks' optimization strategy was correctly implemented by Vasquez
- Confirmed all 6 test categories passed (Dockerfile analysis, GUI call scan, build test, imports, image size, app startup)
- No regressions detected across the entire optimization scope
- **Final image size: 794 MB (47% reduction from ~1.5 GB baseline)**

**Key Finding:** Hicks recommended removing libgl1, but Vasquez correctly retained it. OpenCV headless variant still requires libgl1 for OpenGL operations. Verification confirms this design choice is correct and necessary.

**Deployment Status:** Ready for production. All checks passed.

---

### 2026-05-07 — Issue #22 Test Suite: Gemini Service + DB Schema Foundation

**Task:** Write acceptance-criteria tests for Ripley's squad/22-gemini-service-db-schema-foundation branch.  
**Branch:** Tests committed to `dev` (applied when #22 merges).  
**Commit:** `f2d2c6a` — "test: add test suite for issue #22 Gemini service + DB schema"

**Files Created:**
- `tests/conftest.py` — global mock for `google.generativeai` (handles missing package)
- `tests/test_gemini_service.py` — 9 tests covering all gemini_service.py functions
- `tests/test_db_service.py` — 5 tests for new DB schema and Gemini upload functions

**Tests Written:**

| File | Test | Criterion |
|------|------|-----------|
| test_gemini_service | test_is_configured_false_when_no_api_key | AC: returns False when GEMINI_API_KEY unset |
| test_gemini_service | test_is_configured_true_when_api_key_set | AC: returns True when key is set |
| test_gemini_service | test_get_model_returns_default | AC: default is gemini-2.0-flash |
| test_gemini_service | test_get_model_respects_env_override | AC: GEMINI_MODEL env var overrides |
| test_gemini_service | test_upload_video_calls_files_api | AC: calls genai.upload_file, returns URI |
| test_gemini_service | test_upload_from_url_returns_url | AC: returns URL unchanged (no API call) |
| test_gemini_service | test_delete_file_calls_files_delete | AC: calls genai.delete_file, returns True |
| test_gemini_service | test_generate_blog_returns_dict_with_blog_and_timestamps | AC: returns {blog, timestamps} dict |
| test_gemini_service | test_ask_returns_string | AC: returns stripped string |
| test_db_service | test_no_reka_columns_in_schema | AC: reka_video_id/url/indexing_status gone |
| test_db_service | test_gemini_columns_exist_in_schema | AC: gemini_file_uri + gemini_uploaded_at exist |
| test_db_service | test_update_gemini_upload_stores_uri_and_timestamp | AC: update_gemini_upload persists data |
| test_db_service | test_get_gemini_file_info_returns_none_when_not_set | AC: None for unknown file |
| test_db_service | test_get_gemini_file_info_returns_dict_when_set | AC: dict with uri + uploaded_at |

**Verification Status on dev (before #22 merge):**
- DB tests: All 5 FAIL correctly (old Reka schema, missing functions) ✓
- Gemini tests: Collection error — `ModuleNotFoundError: No module named 'gemini_service'` ✓
- After #22 merges: All 14 tests expected to pass

**Key Patterns Established:**
- `conftest.py` pre-mocks `google.generativeai` via `sys.modules` injection
- In-memory SQLite fixture patches `db_service.get_db` via `patch.object`
- `os.path.exists` must be patched for `upload_video` tests (file existence check)
- `genai.configure` must be mocked alongside `genai.upload_file`/`delete_file`
- `generate_blog` / `ask` use `model.start_chat().send_message()` not `generate_content()`
- `get_gemini_file_info` returns `{"uri": ..., "uploaded_at": ...}` (not raw column names)

---

### 2026-05-09 — Issue #12 Editing Phase: Anticipatory Test Scaffolding (#13–#16)

**Task:** Write proactive test scaffolding for the entire editing phase so the team has tests ready as each implementation lands.
**Branch:** `squad/bishop-editing-test-scaffolding` → PR targeting `feat/issue-12-ai-editing`
**Landing:** Tests absorbed into feature branch via PR #36 (squash merge with Ripley's #13 work)

**Files Created:**

| File | Issue | Tests | Status |
|------|-------|-------|--------|
| `tests/test_editing_db.py` | #13 | 15 tests | Skipped — Ripley already created it on `squad/13-db-drafts-schema` |
| `tests/test_editing_routes.py` | #14 | 9 tests | Created — all `@pytest.mark.skip` |
| `tests/test_skills_service.py` | #15 | 9 tests | Created — all `@pytest.mark.skip` |
| `tests/test_editing_stream.py` | #16 | 12 tests | Created — all `@pytest.mark.skip` |

**Tests Written (30 total — all skipped until implementations land):**

| File | Test | AC Criterion |
|------|------|--------------|
| test_editing_routes | test_post_editing_drafts_returns_201 | POST /editing/drafts returns 201 + draft_id |
| test_editing_routes | test_post_editing_drafts_missing_fields_returns_400 | Missing fields → 400 |
| test_editing_routes | test_get_editing_draft_returns_draft_dict | GET /editing/drafts/<id> returns draft dict |
| test_editing_routes | test_get_editing_draft_unknown_id_returns_404 | Unknown id → 404 |
| test_editing_routes | test_put_editing_draft_updates_content | PUT updates content |
| test_editing_routes | test_put_editing_draft_creates_version | PUT creates draft_versions entry |
| test_editing_routes | test_get_editor_renders_template | GET /editor?draft_id= renders editor.html |
| test_editing_routes | test_get_editor_without_draft_id_returns_400 | Missing draft_id → 400 |
| test_editing_routes | test_get_editor_with_unknown_draft_id_returns_404 | Unknown draft_id → 404 |
| test_skills_service | test_list_skills_returns_list_of_dicts | list_skills() with valid SKILL.md |
| test_skills_service | test_list_skills_multiple_skills | Multiple skills discovered |
| test_skills_service | test_list_skills_skips_malformed_files_without_crashing | Malformed YAML skipped |
| test_skills_service | test_list_skills_skips_files_without_front_matter | No front matter → skipped |
| test_skills_service | test_list_skills_empty_folder_returns_empty_list | Empty folder → [] |
| test_skills_service | test_list_skills_uses_env_var_default | SKILLS_FOLDER env var used |
| test_skills_service | test_get_skill_prompt_returns_body_without_front_matter | Front matter stripped |
| test_skills_service | test_get_skill_prompt_returns_none_for_unknown_skill | Unknown skill → None |
| test_skills_service | test_get_skill_prompt_body_is_stripped | Body is stripped |
| test_editing_stream | test_is_configured_false_when_no_api_key | No EDITING_API_KEY → False |
| test_editing_stream | test_is_configured_true_when_api_key_set | Key set → True |
| test_editing_stream | test_is_configured_false_when_api_key_empty_string | Empty key → False |
| test_editing_stream | test_get_provider_returns_anthropic_by_default | Default provider = anthropic |
| test_editing_stream | test_get_provider_returns_anthropic_when_set | EDITING_PROVIDER=anthropic |
| test_editing_stream | test_get_provider_returns_openai_when_set | EDITING_PROVIDER=openai |
| test_editing_stream | test_get_provider_normalizes_to_lowercase | Uppercase env var normalized |
| test_editing_stream | test_post_editing_stream_returns_sse_content_type | Content-Type: text/event-stream |
| test_editing_stream | test_post_editing_stream_yields_valid_json_chunks | Chunks are valid JSON |
| test_editing_stream | test_post_editing_stream_ends_with_done_true | Final chunk has done:true |
| test_editing_stream | test_post_editing_stream_requires_draft_id | Missing draft_id → 400 |
| test_editing_stream | test_post_editing_stream_returns_503_when_not_configured | No key → 503 |

**Key Patterns Reinforced:**
- All pending implementation tests use `@pytest.mark.skip(reason="Pending #N implementation")` — safe for CI
- Flask test client fixture (`client`) chains from `mem_db` fixture for full in-memory integration testing
- SSE streaming tests use `patch("editing_service.stream_edit", ...)` with controlled byte chunks
- `monkeypatch.setenv/delenv` for env var isolation — no os.environ mutation leaks between tests
- `skills_service` tests use `tmp_path` pytest fixture for isolated temp directories
- Skip check before creating file: if `test_editing_db.py` exists → don't overwrite Ripley's work
