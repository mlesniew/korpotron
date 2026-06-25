---
title: "Korpotron — Invariant Guardian Aggregate Refactor"
created: 2026-06-25
type: refactor-plan
---

# Korpotron — Invariant Guardian Aggregate Refactor

> A refactoring **PLAN**, not an implementation. No production code is modified here. Builds on
> `context/domain/01-domain-distillation.md` (the domain map), re-verifying every `path:line` citation against the
> working tree. The objective: take the single most core, most weakly enforced business invariant and give it **one**
> structural home — a guardian aggregate — so every present and future caller inherits it.

---

## Step 0 — Context (discovery, re-verified)

**Source documents:** `context/foundation/prd.md` (authoritative, status `implemented`), `context/foundation/roadmap.md`
(delivery history incl. post-MVP slices), `context/foundation/idea.md` (seed),
`context/domain/01-domain-distillation.md` (prior distillation), `CLAUDE.md` (stack/conventions).

**Stack:** Django 6.0.5 · Python 3.12 · uv · SQLite (dev) / Fly.io (prod) · OpenRouter via the `openai` SDK · pytest +
pytest-django · ruff · mypy (per `CLAUDE.md`).

**Where business logic lives (the layers the rule must cross):**

| Layer                | Location                                     | Role in the core flow                                       |
| -------------------- | -------------------------------------------- | ----------------------------------------------------------- |
| Persistence / model  | `core/models.py`                             | `Template`, `OptionGroup`, `Option`, `DailyGenerationCount` |
| Domain service       | `core/llm.py`                                | `build_messages`, `generate`, `parse_result`                |
| API / orchestration  | `core/views.py` → `generate_api` (`187-282`) | parse → validate → call LLM → respond                       |
| Forms / validation   | `core/forms.py`                              | `OptionFormSet`, option/registration validation             |
| Onboarding (event)   | `core/apps.py` → `seed_onboarding_defaults`  | seeds defaults via raw `.objects.create(...)`               |
| UI (client guardian) | `templates/core/generate.html` (`218-237`)   | radio-per-group selection logic in JS                       |

Single bounded context; the interesting structure is **within** the generation flow, not across modules.

---

## Step 1 — Business invariants (the rules that must always hold)

Extracted from the PRD and the code; each cites its source and current enforcement status — **enforced** (persistence
guarantees it), **declared** (validation exists but is bypassable), **client-only** (the UI is the sole guardian).

| #     | Invariant                                                            | Source (doc)                                                         | Source (code)                                                           | Status                     |
| ----- | -------------------------------------------------------------------- | -------------------------------------------------------------------- | ----------------------------------------------------------------------- | -------------------------- |
| INV-1 | **At most one option per group** in a single transformation.         | `prd.md:104-106,145-148` ("only one option per group can be active") | `core/views.py:238-242` (imperative `if`); `generate.html:218-237` (JS) | **Declared / client-only** |
| INV-2 | Every selected template & option **belongs to the requesting user**. | `prd.md:163-164` (per-user, no sharing)                              | `core/views.py:216,228-236`                                             | Enforced (this path)       |
| INV-3 | User input / model output is **never persisted or logged**.          | `prd.md:64,134`                                                      | `core/views.py:190-196`; `core/llm.py:4-8`                              | Enforced by discipline     |
| INV-4 | An option's instruction is a **single non-blank line**.              | `prd.md:100`; `idea.md:36`                                           | `core/models.py:59-68`; `core/forms.py:24-28`                           | Declared (form-only)       |
| INV-5 | A template's **base prompt is non-blank**.                           | `prd.md:88`                                                          | `core/models.py:22-25`                                                  | Declared (form-only)       |
| INV-6 | A group has **≥ 1 option**.                                          | `prd.md:100`                                                         | `core/forms.py:42-43`                                                   | Declared (form-only)       |
| INV-7 | Group name unique per user; option name unique per group.            | implied by per-user library                                          | `core/models.py:38,54`                                                  | **Enforced** (DB)          |
| INV-8 | Daily count increments **atomically and only on LLM success**.       | `roadmap.md` (S-05)                                                  | `core/views.py:248-280`                                                 | **Enforced** (txn)         |
| INV-9 | Output shown **verbatim** (faithfulness; content-is-data boundary).  | `prd.md:78,145-150`; `llm.py:30-53`                                  | `core/llm.py:30-53,125-151`                                             | Enforced by prompt         |

---

## Step 2 — Classify and choose #1

Three axes per the brief: **(a)** how core to the product's purpose; **(b)** how smeared across layers; **(c)** whether
actually enforced vs declared vs violable.

| #         | (a) Core-ness                                                                                                                                                                | (b) Smear                                                                                     | (c) Enforcement                                                                                                              |
| --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| INV-1     | **Maximal.** The PRD elevates option groups to "a **load-bearing** design choice" precisely because exclusivity prevents conflicting, incoherent prompts (`prd.md:104-106`). | **3 layers**: JS (`generate.html`), endpoint (`views.py`), and **absent** from model/service. | **Weakest of the core rules.** A single imperative `if` at one endpoint; the data model permits exactly the forbidden state. |
| INV-2     | High                                                                                                                                                                         | endpoint only                                                                                 | Enforced (scoped querysets)                                                                                                  |
| INV-3     | High (trust/privacy)                                                                                                                                                         | view + service                                                                                | Enforced by discipline + a regression test                                                                                   |
| INV-4/5/6 | Supporting (data integrity)                                                                                                                                                  | model + form                                                                                  | Declared, bypassed on `.create()`                                                                                            |
| INV-8     | Generic (cost control)                                                                                                                                                       | endpoint                                                                                      | Enforced (row-locked txn)                                                                                                    |
| INV-9     | High (quality)                                                                                                                                                               | service                                                                                       | Enforced via the system prompt                                                                                               |

**Choice: INV-1 — "at most one option per group per transformation."**

It is at once the **most core** (the differentiator from a generic prompt library; the PRD says coherent output
_depends_ on it) and the **most weakly enforced** (declared at one endpoint plus a client-side UI guard, with **no**
structural backstop — divergence **D-2** in the distillation). The PRD's own words describe a guarantee the code does
not provide:

> "the composition rule is **enforced by the option group structure, not by the user at generation time**." —
> `prd.md:146-147`

Today that "structure" is fictional: exclusivity is enforced by the _user_ (the JS radio logic) and re-checked by _one
caller_ (`generate_api`). A second entry point — a future JSON API, a bulk action, a management command, a test helper —
silently reintroduces the incoherent-output failure mode the design exists to prevent.

---

## Step 3 — Diagnose INV-1 (where the rule lives today, across every layer)

### Layer 1 — Client (JavaScript): the _primary_ guardian today

`templates/core/generate.html:218-237` — a `selected` map keyed by `group_id`, with radio-per-group behaviour:

```js
// group_id -> option_id; single source of truth for the modifier payload.
const selected = {};
...
group.querySelectorAll('.opt-btn').forEach(function (btn) {
  btn.addEventListener('click', function () {
    ...
    selected[groupId] = btn.dataset.optionId;   // overwrites any prior pick for the group
  });
});
```

Because `selected` is keyed by group, the UI **cannot** submit two options of one group. This is the only place the rule
is _structurally_ impossible — and it lives on the **client**, the least trustworthy layer. The payload is plain JSON
(`generate.html:253-257`); any `curl` bypasses it entirely.

### Layer 2 — Endpoint: an imperative re-check (`core/views.py:238-242`)

```python
group_ids = [option.group.pk for option in options]
if len(group_ids) != len(set(group_ids)):
    return JsonResponse(
        {"error": "Only one option per group may be selected."}, status=400
    )
```

This is the server's _only_ enforcement. Observations:

- It is **endpoint-local.** `llm.build_messages` / `llm.generate` (`core/llm.py:92-122,154-167`) accept any
  `Sequence[Option]` and will happily assemble a conflicting prompt — the service layer trusts its caller.
- It is **positional / procedural** — correctness depends on this block running before `llm.generate` at `views.py:266`.
  Reorder or fork the function and the guard is gone.
- The ownership + existence checks (`views.py:216-218,228-236`) and the exclusivity check are **three separate scattered
  queries/checks** in one function, not a cohesive object.

### Layer 3 — Model / persistence: **silent on the rule**

`core/models.py` has **no** constraint linking a transformation to one-option-per-group (there is no Transformation
entity at all — INV-3 forbids persisting it). `Option.group` is a plain FK (`models.py:45-49`). Nothing in the data
model forbids assembling `{Formal, Casual}` from the same Tone group.

### Layer 4 — Service: trusts the caller

`build_messages(template, selected_options, text)` (`core/llm.py:92-122`) iterates `selected_options` and emits one
bullet per instruction with **no** group-awareness. The faithfulness/injection contract is enforced here (INV-9), but
INV-1 is assumed already satisfied upstream.

**Diagnosis summary:** the rule is real and load-bearing, but it lives in a **client guard + one imperative endpoint
check**, with the model and service both ignorant of it. No layer _owns_ it. Remove the JS or add a second server entry
point and the invariant evaporates — failing the brief's fail-fast principle (an illegal selection should _stop_, from
any caller).

---

## Step 4 — Design: the guardian aggregate

### 4.1 The aggregate and where it lives

INV-3 (non-retention) means the transformation has **no persistent identity** — it exists only for one request. So the
aggregate is a **transient, in-memory consistency boundary**, not a Django model. New module: **`core/domain.py`** (pure
domain; imports models + llm, never imports `django.views` / `django.http`).

Two value objects + one aggregate root + one repository:

- **`Selection`** — a value object that makes INV-1 _structurally impossible_: it is keyed by group, so a second option
  for a group cannot exist in it.
- **`TransformationRequest`** (aggregate root) — bundles `template + Selection + text`; the **only** object that can
  produce the message list for the LLM. Its construction is the precondition gate.
- **`TransformationRepository`** — resolves request identity `(user, template_id, option_ids)` into the aggregate via
  ownership-scoped queries, in **one** place (collapsing the three scattered checks).
- Named **domain errors** — illegal operations raise; they never log-and-carry-on.

### 4.2 Named domain errors (`core/domain.py`)

```python
class DomainError(Exception):
    """Base for domain-rule violations. Carries a user-safe message."""
    user_message: str

class OptionConflictError(DomainError):       # INV-1 — two options, one group
    user_message = "Only one option per group may be selected."

class TemplateNotFoundError(DomainError):     # INV-2 — template not owned / missing
    user_message = "Template not found."

class UnknownOptionError(DomainError):        # INV-2 — option not owned / missing
    user_message = "One or more options were not found."

class EmptyTextError(DomainError):            # input precondition
    user_message = "Please enter some text to transform."
```

### 4.3 `Selection` — the structural home of INV-1

```python
@dataclass(frozen=True)
class Selection:
    """At most one Option per group. Constructing it is the enforcement point.

    Keyed by group_id, so a second option for a group is unrepresentable.
    """
    _by_group: Mapping[int, Option]

    @classmethod
    def from_options(cls, options: Iterable[Option]) -> "Selection":
        by_group: dict[int, Option] = {}
        for opt in options:
            gid = opt.group_id                      # FK id; no extra query
            if gid in by_group:                     # PRECONDITION: INV-1
                raise OptionConflictError()         # fail-fast, named, stops here
            by_group[gid] = opt
        return cls(by_group)

    @property
    def options(self) -> list[Option]:
        # Deterministic order → stable prompts (group name, then option id).
        return sorted(self._by_group.values(),
                      key=lambda o: (o.group.name, o.pk))

    def __len__(self) -> int:
        return len(self._by_group)
```

> Once a `Selection` exists, INV-1 _cannot_ be false — there is no API to add a duplicate. This is the "enforced by the
> structure" the PRD promised (`prd.md:146-147`), now true in code rather than aspirational (closes **D-2**).

### 4.4 `TransformationRequest` — aggregate root

```python
@dataclass(frozen=True)
class TransformationRequest:
    template: Template
    selection: Selection
    text: str

    def __post_init__(self) -> None:
        if not self.text.strip():                   # PRECONDITION
            raise EmptyTextError()

    def messages(self) -> list[ChatCompletionMessageParam]:
        # The ONLY path from a request to an LLM prompt. Delegates the proven
        # assembly + injection/faithfulness contract (INV-9) to the service.
        return llm.build_messages(self.template, self.selection.options, self.text)
```

The aggregate is the **only** way to reach `build_messages` for a real request, so INV-1 and the text precondition are
unconditionally satisfied before any prompt is built — from _any_ caller.

### 4.5 `TransformationRepository` — load the aggregate, ownership in one place

```python
class TransformationRepository:
    def __init__(self, user: User) -> None:
        self._user = user

    def build(self, template_id: int, option_ids: Collection[int], text: str
              ) -> TransformationRequest:
        template = Template.objects.filter(user=self._user, pk=template_id).first()
        if template is None:
            raise TemplateNotFoundError()                       # INV-2

        wanted = set(option_ids)
        options = list(
            Option.objects.filter(group__user=self._user, pk__in=wanted)
            .select_related("group")
        )
        if len(options) != len(wanted):
            raise UnknownOptionError()                          # INV-2

        selection = Selection.from_options(options)             # INV-1 (raises)
        return TransformationRequest(template, selection, text)
```

This replaces the three scattered fragments in the view (`views.py:216-218,228-236,238-242`) with one cohesive loader.
Every ownership/existence/exclusivity decision now lives behind one method.

### 4.6 Atomicity

The generation itself persists nothing (INV-3), so the _aggregate_ needs no transaction. The **one** thing that must be
atomic — the daily-count check-and-increment (INV-8) — already runs correctly inside `transaction.atomic()` with
`select_for_update` (`views.py:248-280`) and is **kept verbatim**. Aggregate construction is pure and in-memory; it sits
_before_ the transaction. No atomicity regression.

### 4.7 The thin endpoint (after)

`generate_api` shrinks to: parse input → build aggregate (domain enforces) → map `DomainError` → run the (unchanged)
rate-limited LLM transaction → respond.

```python
@login_required
@require_POST
def generate_api(request):
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid request."}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({"error": "Invalid request."}, status=400)

    template_id, option_ids = _parse_ids(payload)   # 400 on malformed shape
    if template_id is None:
        return JsonResponse({"error": "Please choose a template."}, status=400)
    if option_ids is None:
        return JsonResponse({"error": "Invalid options."}, status=400)
    text = payload.get("text")
    if not isinstance(text, str):
        return JsonResponse({"error": "Please enter some text to transform."}, status=400)

    try:
        req = TransformationRepository(request.user).build(template_id, option_ids, text)
    except DomainError as exc:                       # INV-1 + INV-2 + text, in ONE place
        return JsonResponse({"error": exc.user_message}, status=400)

    # --- INV-8 block kept verbatim from views.py:244-282, but calling: ---
    #     result = llm.generate_from(req)   # see Step 5 note
    ...
```

Enforcement has moved **off the client and out of the procedural endpoint** into the domain. The JS in `generate.html`
stays as a UX affordance, but it is no longer the guardian — the server now refuses a conflicting payload by
construction, from any caller.

---

## Step 5 — Before/after, plan, tests, names

### 5.1 Before / after, per place the rule lives today

| Place                                   | Before                                                             | After                                                                              |
| --------------------------------------- | ------------------------------------------------------------------ | ---------------------------------------------------------------------------------- |
| `core/views.py:238-242`                 | imperative `len(group_ids) != len(set(...))` check, endpoint-local | **removed** — replaced by `Selection.from_options` inside the repository           |
| `core/views.py:216-218,228-236`         | scattered template/option ownership + existence checks             | **moved** into `TransformationRepository.build` (one cohesive loader)              |
| `core/llm.py:92-122` (`build_messages`) | accepts any `Sequence[Option]`, group-unaware, trusts caller       | unchanged signature, but reached **only** via `TransformationRequest.messages()`   |
| `templates/core/generate.html:218-237`  | client `selected` map is the _primary_ guardian                    | unchanged code, **demoted** to UX affordance; server no longer depends on it       |
| `core/models.py`                        | silent on INV-1                                                    | still silent (transient rule), but the rule now has a home in `core/domain.py`     |
| `core/domain.py`                        | **does not exist**                                                 | **new** — `Selection`, `TransformationRequest`, `TransformationRepository`, errors |

### 5.2 Refactoring phases (test-first where the discipline fits)

The repo has a real runner (`uv run pytest`, pytest-django) and existing coverage of this exact rule
(`tests/test_generate.py:203-214`, `test_generate_two_options_same_group_rejected`). So phases that add behaviour go
**test-first**; the endpoint rewrite is covered by the _existing_ suite acting as a characterization harness.

- **Phase 1 — `core/domain.py` scaffold (test-first).** Write `tests/test_domain.py` first (cases in 5.3), then
  implement `Selection`, `TransformationRequest`, errors. No view changes yet. Net-new, isolated, fully TDD-able.
- **Phase 2 — `TransformationRepository` (test-first).** DB-backed tests for ownership/existence/conflict resolution
  (5.3), then implement. Still no view change.
- **Phase 3 — rewire `generate_api` (characterization-first).** The full `tests/test_generate.py` suite must stay green
  before and after; rewrite the view to call the repository and map `DomainError`. Delete the now-dead
  `views.py:238-242` block. **Behaviour-preserving** — same status codes, same error strings (keep the wording in
  `user_message` byte-identical to today's so `test_generate_two_options_same_group_rejected` and siblings pass
  unchanged). Add `llm.generate_from(req)` or have the view call
  `llm.generate(req.template, req.selection.options, req.text)` — keep `llm.generate`'s patch target stable so
  `patch("core.views.llm.generate", ...)` in the existing tests still works.
- **Phase 4 (paired, optional) — close D-4 on the seeding path.** `core/apps.py:40-52` writes via `.objects.create(...)`
  with no `full_clean()`, so INV-4/INV-5 are form-only. Add `full_clean()` (or a `Selection`/`Option` factory) so the
  declared model invariants become real. Test-first: a malformed fixture row must raise, not silently persist. Separate
  commit; not required for INV-1.

### 5.3 Test cases for the invariant (legal vs illegal)

**Domain unit tests — `tests/test_domain.py` (new):**

- `Selection.from_options([])` → empty selection, `len == 0`. _(legal)_
- one option per group, two groups → `Selection` with both; `.options` deterministically ordered. _(legal)_
- two options, **same group** → raises `OptionConflictError`. _(illegal — the core case)_
- three options where two share a group → raises `OptionConflictError`. _(illegal)_
- `TransformationRequest` with blank/whitespace `text` → raises `EmptyTextError`. _(illegal)_
- `TransformationRequest.messages()` delegates to `llm.build_messages` with `selection.options`. _(legal)_

**Repository tests — `tests/test_domain.py` (DB):**

- valid template + one option → returns a `TransformationRequest`. _(legal)_
- template owned by another user → `TemplateNotFoundError`. _(illegal — INV-2)_
- option owned by another user / nonexistent id → `UnknownOptionError`. _(illegal — INV-2)_
- two options of the same owned group → `OptionConflictError` surfaces through `.build`. _(illegal — INV-1)_

**Endpoint regression — `tests/test_generate.py` (existing, must stay green):**

- `test_generate_two_options_same_group_rejected` (`:203-214`) → still **400**, same error string. _(illegal)_
- `test_generate_happy_path` (`:149`), `test_generate_cross_user_template_rejected` (`:181`),
  `test_generate_cross_user_option_rejected` (`:191`), `test_generate_creates_no_db_rows` (`:247`) → unchanged.
- Add `test_generate_conflict_blocked_without_client_js` (new): POST a same-group payload directly (bypassing the UI)
  → 400. Proves enforcement moved server-side and no longer relies on `generate.html`.

### 5.4 New load-bearing names to register

For the contract registry / ubiquitous language (extends `01-domain-distillation.md` Step 1):

| Name                       | Kind           | Meaning                                                                       |
| -------------------------- | -------------- | ----------------------------------------------------------------------------- |
| `Selection`                | value object   | The set of chosen options, **at most one per group** (INV-1 made structural). |
| `TransformationRequest`    | aggregate root | template + Selection + text; sole producer of the LLM message list.           |
| `TransformationRepository` | repository     | Resolves `(user, template_id, option_ids)` → aggregate; owns INV-2 checks.    |
| `DomainError`              | error base     | Domain-rule violation carrying a user-safe message.                           |
| `OptionConflictError`      | domain error   | INV-1 violated — two options in one group.                                    |
| `TemplateNotFoundError`    | domain error   | Template missing or not owned (INV-2).                                        |
| `UnknownOptionError`       | domain error   | Option missing or not owned (INV-2).                                          |
| `EmptyTextError`           | domain error   | Transformation text precondition violated.                                    |

---

## Summary

Korpotron's single most load-bearing rule — **at most one option per group per transformation** (INV-1) — is also its
most weakly enforced: the PRD calls option groups "a load-bearing design choice" because exclusivity is what keeps
assembled prompts coherent (`prd.md:104-106,145-148`), yet in code the rule lives only in client-side JS
(`generate.html:218-237`) and a single imperative endpoint check (`views.py:238-242`), with the model and service layers
entirely unaware of it. The PRD claims the rule is "enforced by the option group structure, not by the user at
generation time," but no such structure exists — any second caller (a future API, bulk action, or management command)
silently reintroduces conflicting-prompt output. This plan gives the invariant one structural home: a transient guardian
aggregate in a new `core/domain.py`, built around a `Selection` value object keyed by group so a duplicate is
_unrepresentable_, a `TransformationRequest` root that is the only path to the LLM prompt, and a
`TransformationRepository` that collapses the scattered ownership/existence/exclusivity checks into one loader and
raises named, fail-fast `DomainError`s instead of re-checking inline. The endpoint becomes thin — parse, build, map
error, run the unchanged rate-limited transaction — and the proven faithfulness/injection contract
(`llm.build_messages`, INV-9) and atomic daily-count logic (INV-8) are preserved verbatim. Delivery is phased and
test-first: new domain and repository tests precede their code, while the existing `tests/test_generate.py` suite acts
as a characterization harness keeping the endpoint rewrite behaviour-exact. The result moves enforcement off the
least-trustworthy layer (the browser) and out of one procedural endpoint into the domain, so every present and future
caller inherits the guarantee by construction — closing divergence D-2, with an optional paired phase to close D-4
(`full_clean()` on the onboarding seeding path).
