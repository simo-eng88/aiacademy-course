# Notion Course Database Import Guide

This repository does not currently have an authenticated Notion connector available in Codex, so the course data was exported into Notion-ready files instead of being written directly to Notion.

## Source Of Truth

- `content/days.json`: course day/module content, lesson overviews, summaries, points, takeaways, tips, and tool references.
- `content/videos.json`: runtime video list loaded by `index.html`.
- `content/sites.json`: runtime tools catalogue loaded by `index.html`.
- `knowledge.json`: FAQ chatbot knowledge base loaded by `index.html`.
- `content/settings.json`: public course metadata. Sensitive values are not exported.
- `index.html`: static app shell and embedded fallback content; it also fetches videos, sites, and knowledge data.
- `admin/config.yml`: Decap CMS schema for editing content through `/admin`.

## Generated Export Files

- `course-data-normalized.json`: canonical structured data for another CMS, automation, or future sync script.
- `notion-course-export.json`: Notion database-style export with database schemas and rows.
- `notion-course-export.md`: Markdown page export that can be imported directly into Notion.
- `NOTION_IMPORT_GUIDE.md`: this import and maintenance guide.

## Extracted Counts

- Modules/course days: 13
- Lessons: 13
- Videos: 81
- Tools: 58
- Chatbot FAQ entries: 53
- PDF resources: 13

## Recommended Notion Databases

### Course Modules
Primary property: `Title`

- `Title`: title
- `Module Number`: number
- `Arabic Title`: rich_text
- `English Title`: rich_text
- `Date`: date or rich_text
- `Status`: status
- `Progress`: number
- `Lessons`: relation -> Lessons
- `Videos`: relation -> Videos
- `Tools`: multi_select or relation -> Tools
- `Summary PDF`: files or url/path

### Lessons
Primary property: `Name`

- `Module`: relation -> Course Modules
- `Overview AR`: rich_text
- `Overview EN`: rich_text
- `Key Points`: rich_text / child bullets
- `Takeaways`: rich_text / child bullets
- `Tips`: rich_text / child bullets
- `Status`: status

### Videos
Primary property: `Title`

- `Module`: relation -> Course Modules
- `Lesson`: relation -> Lessons
- `Part`: rich_text
- `Duration`: rich_text
- `Topic`: multi_select or rich_text
- `URL`: url
- `Status`: status

### Tools
Primary property: `Name`

- `Domain`: url or rich_text
- `Category AR`: select
- `Category EN`: select
- `Benefit`: rich_text
- `Usage`: rich_text
- `Modules`: relation -> Course Modules

### Knowledge Base
Primary property: `Question`

- `FAQ ID`: number
- `Question AR`: title
- `Question EN`: rich_text
- `Answer AR`: rich_text
- `Answer EN`: rich_text
- `Keywords`: multi_select
- `Category`: select
- `Related Module`: relation -> Course Modules
- `Related FAQs`: relation -> Knowledge Base

### Resources
Primary property: `Title`

- `Module`: relation -> Course Modules
- `Type`: select
- `Path`: files or rich_text

## Import Options

### Option 1: Markdown Import

1. In Notion, create a new page named `AI Academy Course`.
2. Use Notion's import feature and choose `notion-course-export.md`.
3. Review the generated sections for each module.
4. Optionally turn module/video/tool tables into Notion databases.

### Option 2: JSON-Based Database Build

1. Create databases matching the schema above.
2. Use `notion-course-export.json` as the row source.
3. Import in this order: Course Modules, Lessons, Videos, Tools, Knowledge Base, Resources.
4. Reconnect relations in Notion using `Source ID`, `Module ID`, `Lesson ID`, and related day fields.

### Option 3: Future API Sync

1. Store a Notion integration token outside the repo as an environment variable.
2. Store target database IDs outside the repo as environment variables.
3. Use `course-data-normalized.json` as the canonical payload.
4. Sync by stable IDs such as `day1`, `lesson-day1`, `day1-video-01`, and `tool-chatgpt`.

## Safest Maintenance Workflow

1. Continue editing the website through Decap CMS or the existing JSON files.
2. Keep `content/days.json`, `content/videos.json`, `content/sites.json`, and `knowledge.json` as the website source of truth.
3. Regenerate exports after content changes with `python scripts/generate_notion_exports.py`.
4. Import or sync the regenerated files into Notion.
5. Avoid making Notion the only source of truth until a tested two-way sync exists.

## Limitations

- No Notion connector was available in this Codex environment, so no Notion page/database was created directly.
- The export intentionally omits the admin credential setting and raw analytics measurement identifier from `content/settings.json`.
- Notion relation properties must be connected manually unless a future Notion API sync is added.
- Telegram video URLs may require access to the private course channel.
