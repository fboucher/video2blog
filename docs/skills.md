# Writing Skills

Skills are AI-powered editing actions that can be applied to blog drafts. Each skill lives in its own subfolder under `skills/` and is defined by a single `SKILL.md` file.

## Basic structure

```
skills/
  my-skill/
    SKILL.md
```

A `SKILL.md` file has two parts: a YAML front matter block (between `---` delimiters) and a prompt body.

```markdown
---
name: my-skill
description: A short description shown in the UI
---
Your system prompt goes here. Tell the AI what to do with the draft.
```

The **prompt body** becomes the system prompt sent to the model. The current draft content is always provided automatically as the user message.

---

## Adding modes

Modes let a single skill expose multiple variations in the UI (e.g. a quick pass vs. a deep edit).

```markdown
---
name: text-editor
description: General-purpose text editing and proofreading
modes:
  - name: full-edit
    label: "Full Edit"
  - name: quick-pass
    label: "Quick Pass"
  - name: tone-check
    label: "Tone Check"
---
You are an expert copy editor ...
```

Each mode has a `name` (used internally) and a `label` (shown in the UI). When a mode is selected, the backend automatically prepends `Mode: <label>` to the system prompt, so the model knows which mode is active — no extra work needed in the prompt body.

---

## Adding parameters

Parameters let users provide extra context before a skill runs. They are rendered as form fields in the UI and automatically appended to the user message sent to the model.

### Skill-level parameters

These appear for every invocation of the skill, regardless of mode.

```markdown
---
name: fact-checker
description: Verify factual claims in the draft
parameters:
  - name: audience
    label: "Target audience"
    placeholder: "e.g. software engineers, general public"
  - name: goal
    label: "Goal of the piece"
    placeholder: "e.g. inform, persuade, convert"
    required: true
---
You are a fact-checking assistant ...
```

### Mode-level parameters

These appear only when a specific mode is selected.

```markdown
---
name: text-editor
description: General-purpose text editing and proofreading
modes:
  - name: full-edit
    label: "Full Edit"
  - name: rewrite-section
    label: "Rewrite Section"
    parameters:
      - name: section
        label: "Which section to rewrite?"
        placeholder: "e.g. Introduction"
        required: true
---
You are an expert copy editor ...
```

### Parameter fields

| Field | Required | Description |
|---|---|---|
| `name` | ✅ | Internal key, passed to the model |
| `label` | ✅ | Shown as the form field label |
| `placeholder` | — | Hint text inside the input |
| `required` | — | If `true`, the request is rejected if the value is empty |

---

## How parameters reach the model

Parameter values are automatically appended to the user message. For example, if the user fills in `section: Introduction`, the model receives:

```
Draft:

[draft content here]

Parameters:
- section: Introduction
```

No special syntax is needed in the prompt body — just write your prompt naturally and the model will use the provided context.

---

## Full example: persuasion editor

A skill that always asks for audience and goal, and offers two modes:

```markdown
---
name: persuasion-editor
description: Rewrite a draft to better persuade a specific audience
parameters:
  - name: audience
    label: "Who is the target audience?"
    placeholder: "e.g. CTOs at mid-size startups"
    required: true
  - name: goal
    label: "What should the reader do or believe after reading?"
    placeholder: "e.g. Book a demo, trust the author's expertise"
    required: true
modes:
  - name: subtle
    label: "Subtle — preserve the author's voice"
  - name: aggressive
    label: "Aggressive — optimise purely for conversion"
    parameters:
      - name: cta
        label: "Call-to-action text"
        placeholder: "e.g. Start your free trial"
---
You are a conversion copywriter. The user will provide a draft blog post along with the target audience and goal.

Rewrite the draft so it speaks directly to that audience and drives them toward the stated goal. Keep all factual claims intact.
```
