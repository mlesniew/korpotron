# Korpotron

## Problem

I regularly use LLM tools to rewrite and polish text — emails, documentation, comments, and similar short-form content.

Currently, I store reusable prompts in text files, but the workflow is slow and inconvenient:

- Every use requires copying and pasting a prompt into a chat tool.
- Prompts often need small adjustments for tone, style, or context.
- This turns simple, repetitive tasks into friction-heavy chores.

I want a faster, purpose-built tool to transform text using predefined instructions.

## Features

### Templates

Users can create and manage templates for common use cases (e.g. email, Jira ticket, announcement, documentation). Each
template defines:

- **Name** — a human-readable label
- **Base prompt** — the core instruction sent to the LLM
- **Generate title** — whether a title or subject line should be produced
- **Is response** — whether the text is a reply to another message

### Option Groups

Users can create reusable option groups to layer additional instructions on top of a template (e.g. tone, style,
language). Each group contains:

- **Name** — a human-readable label
- **Options** — a set of selectable items, each with:
  - A display name
  - The instruction text to inject into the prompt

### Core Workflow

The primary user flow:

1. Select a template.
2. Optionally select options from any number of option groups.
3. Enter the text to transform.
4. Provide the original message (only for templates marked as a response).
5. Click a button to generate the rewritten text.
6. Review the result and copy it to the clipboard.

## Non-Functional Requirements

- Fast and easy to use — the full flow (select → input → generate → copy) should take under a minute.
- Minimal UI with no unnecessary chrome.
- No prompt editing during normal use.
- Optimized for short, practical content (emails, comments, messages).

## Out of Scope (MVP)

- Mobile app or mobile-first browser experience
- Integrations with external systems (email, Jira, Teams, etc.)
- Multiple user roles or shared workspaces
- Import/export functionality
- Sharing templates or option groups between users
- Advanced workflow features (history, automation, etc.)
