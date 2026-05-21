# Korpotron

## Main problem

I often use LLM tools to rewrite and polish text such as emails, documentation, and comments.

Today, I store reusable prompts in text files, but using them is slow and inconvenient:
* I need to copy and paste prompts into a chat tool every time
* I often adjust prompts slightly (for tone, style, or context)
* This makes simple, repetitive tasks take more time than needed

I want a faster and easier way to transform text using predefined instructions.

## Main Features

* Create and manage templates for common use cases (e.g. email, Jira ticket, announcement, documentation).  Each template defines:
 * A display name
 * A base prompt
 * A "generate title" flag, which specifies whether a title/subject should be generated
 * A "is reponse" flag, which specifies whether the text is a response to another message
* Create reusable extra option groups (e.g. tone, style, language).  Each option group contains:
 * A display name
 * A set of selectable options that inject specific instructions into the prompt.  Each of them has:
   * A display name
   * The instructions themselves
* Primary feature is to allow users to:
 * Select a template
 * Optionally add any number of extra options
 * Enter the text they want to transform
 * Provide the original message (for templates with the "is response" flag)
 * Hit a button to generate rewritten text using an LLM
 * Show the result in a simple text box
 * Allow quick copy to clipboard

## Additional Requirements

* The tool should be fast and easy to use
* The main flow should require only a few clicks
* No need to edit prompts during normal use
* UI should be clean and minimal
* Optimized for short, practical text (emails, comments, messages)
* The full process (select → input → generate → copy) should take less than a minute

## Out of Scope (MVP)

* Mobile app
* Mobile-first browser experience
* Integrations with external systems (email, Jira, Teams, etc.)
* Multiple user roles or shared workspaces
* Import/export functionality
* Sharing templates or options between users
* Advanced workflow features (history, automation, etc.)
