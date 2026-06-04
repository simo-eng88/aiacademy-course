#!/usr/bin/env python3
"""Generate Notion-ready course exports from the existing static-site data."""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8-sig"))


def write_json(path: str, data: dict) -> None:
    (ROOT / path).write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def clean_text(value) -> str:
    if value is None:
        return ""
    text = repair_mojibake(str(value)).strip()
    text = re.sub(r"\s+", " ", text)
    return text


def repair_mojibake(text: str) -> str:
    """Repair UTF-8 Arabic/emoji text that was stored as mojibake.

    Some source fields contain characters like "Ù…" and "Ø§" because valid
    UTF-8 bytes were previously decoded as a single-byte Windows encoding.
    Keep this repair export-only so the website source files remain untouched.
    """
    if not any(marker in text for marker in ("Ù", "Ø", "Ã", "Â", "ðŸ")):
        return text
    raw = bytearray()
    try:
        for ch in text:
            code = ord(ch)
            if code <= 0xFF:
                raw.append(code)
            else:
                raw.extend(ch.encode("cp1252"))
        repaired = raw.decode("utf-8")
        if "�" not in repaired:
            return repaired
    except (UnicodeEncodeError, UnicodeDecodeError, ValueError):
        return text
    return text


def as_list(value) -> list:
    if not isinstance(value, list):
        return []
    return [repair_mojibake(item) if isinstance(item, str) else item for item in value]


def clean_list(value) -> list:
    return [clean_text(item) for item in as_list(value)]



def day_number(day: dict) -> int | None:
    match = re.search(r"\d+", str(day.get("id", "")))
    return int(match.group(0)) if match else None


def safe_course_settings(settings: dict) -> dict:
    public = {
        "course_title_ar": settings.get("course_title_ar", ""),
        "course_title_en": settings.get("course_title_en", ""),
        "instructor_ar": settings.get("instructor_ar", ""),
        "instructor_en": settings.get("instructor_en", ""),
        "developer_ar": settings.get("developer_ar", ""),
        "developer_en": settings.get("developer_en", ""),
        "total_days": settings.get("total_days"),
        "cohort_year": settings.get("cohort_year", ""),
        "padlet_url": settings.get("padlet_url", ""),
    }
    if settings.get("ga_id"):
        public["ga_id_present"] = True
    return public


def relation_id(prefix: str, value) -> str:
    return f"{prefix}-{str(value).strip().lower().replace(' ', '-')}"


def build_exports() -> tuple[dict, dict, str, str]:
    days_data = read_json("content/days.json")
    videos_data = read_json("content/videos.json")
    sites_data = read_json("content/sites.json")
    settings = read_json("content/settings.json")
    knowledge = read_json("knowledge.json")

    videos_by_day = {
        item.get("dayId"): as_list(item.get("videos")) for item in as_list(videos_data.get("days"))
    }
    tools_by_name = {tool.get("name"): tool for tool in as_list(sites_data.get("tools")) if tool.get("name")}
    pdf_files = sorted(p.name for p in ROOT.glob("day*-summary.pdf"))
    pdf_by_day = {}
    for name in pdf_files:
        match = re.match(r"day(\d+)-summary\.pdf$", name)
        if match:
            pdf_by_day[f"day{int(match.group(1))}"] = name

    modules = []
    lessons = []
    all_videos = []
    resources = []
    used_tool_names = Counter()

    for index, day in enumerate(as_list(days_data.get("days")), start=1):
        day_id = day.get("id") or f"day{index}"
        number = day_number(day) or index
        day_videos = videos_by_day.get(day_id, [])
        site_keys = as_list(day.get("siteKeys"))
        used_tool_names.update(site_keys)

        module = {
            "id": day_id,
            "module_number": number,
            "day_label_ar": clean_text(day.get("day_ar")),
            "day_label_en": clean_text(day.get("day_en")),
            "title_ar": clean_text(day.get("title_ar")),
            "title_en": clean_text(day.get("title_en")),
            "subtitle_ar": clean_text(day.get("subtitle_ar")),
            "subtitle_en": clean_text(day.get("subtitle_en")),
            "date": clean_text(day.get("date")),
            "read_time_ar": clean_text(day.get("readTime_ar")),
            "read_time_en": clean_text(day.get("readTime_en")),
            "emoji": clean_text(day.get("emoji")),
            "theme_colors": {
                "start": clean_text(day.get("c1")),
                "end": clean_text(day.get("c2")),
            },
            "status": "Not started",
            "progress": 0,
            "tool_names": clean_list(site_keys),
            "video_count": len(day_videos),
            "summary_pdf": pdf_by_day.get(day_id, ""),
            "source_file": "content/days.json",
        }
        modules.append(module)

        lesson = {
            "id": relation_id("lesson", day_id),
            "module_id": day_id,
            "lesson_number": number,
            "name_ar": clean_text(day.get("title_ar")),
            "name_en": clean_text(day.get("title_en")),
            "overview_ar": clean_text(day.get("overview_ar")),
            "overview_en": clean_text(day.get("overview_en")),
            "pdf_summary_ar": clean_text(day.get("pdfSummary_ar")),
            "pdf_summary_en": clean_text(day.get("pdfSummary_en")),
            "key_points_ar": clean_list(day.get("points_ar")),
            "key_points_en": clean_list(day.get("points_en")),
            "takeaways_ar": clean_list(day.get("takeaways_ar")),
            "takeaways_en": clean_list(day.get("takeaways_en")),
            "tips_ar": clean_list(day.get("tips_ar")),
            "tips_en": clean_list(day.get("tips_en")),
            "tool_names": clean_list(site_keys),
            "video_ids": [],
            "summary_pdf": pdf_by_day.get(day_id, ""),
            "status": "Not started",
            "source_file": "content/days.json",
        }

        for video_index, video in enumerate(day_videos, start=1):
            video_id = f"{day_id}-video-{video_index:02d}"
            lesson["video_ids"].append(video_id)
            all_videos.append(
                {
                    "id": video_id,
                    "module_id": day_id,
                    "lesson_id": lesson["id"],
                    "day_label": clean_text(videos_data.get("days", [])[number - 1].get("dayLabel"))
                    if number <= len(videos_data.get("days", []))
                    else "",
                    "part": clean_text(video.get("part")),
                    "title": clean_text(video.get("title")),
                    "duration": clean_text(video.get("duration") or video.get("dur") or "00:00"),
                    "topic": clean_text(video.get("topic")),
                    "url": clean_text(video.get("link")),
                    "platform": "Telegram" if "t.me/" in clean_text(video.get("link")) else "",
                    "status": "Not started",
                    "source_file": "content/videos.json",
                }
            )

        if pdf_by_day.get(day_id):
            resources.append(
                {
                    "id": relation_id("resource", pdf_by_day[day_id]),
                    "module_id": day_id,
                    "type": "PDF summary",
                    "title": f"Day {number} summary PDF",
                    "path": pdf_by_day[day_id],
                    "source_file": pdf_by_day[day_id],
                }
            )

        lessons.append(lesson)

    tools = []
    for tool in as_list(sites_data.get("tools")):
        name = tool.get("name", "")
        tools.append(
            {
                "id": relation_id("tool", name),
                "name": name,
                "domain": clean_text(tool.get("domain")),
                "url": f"https://{clean_text(tool.get('domain'))}" if tool.get("domain") else "",
                "category_ar": clean_text(tool.get("category_ar")),
                "category_en": clean_text(tool.get("category_en")),
                "benefit_ar": clean_text(tool.get("benefit_ar")),
                "benefit_en": clean_text(tool.get("benefit_en")),
                "usage_ar": clean_text(tool.get("usage_ar")),
                "usage_en": clean_text(tool.get("usage_en")),
                "mentioned_in_module_ids": [
                    module["id"] for module in modules if name in module.get("tool_names", [])
                ],
                "mention_count": used_tool_names.get(name, 0),
                "source_file": "content/sites.json",
            }
        )

    knowledge_rows = []
    for faq in as_list(knowledge.get("faqs")):
        knowledge_rows.append(
            {
                "id": relation_id("faq", faq.get("id")),
                "faq_id": faq.get("id"),
                "question_ar": clean_text(faq.get("question_ar")),
                "question_en": clean_text(faq.get("question_en")),
                "answer_ar": clean_text(faq.get("answer_ar")),
                "answer_en": clean_text(faq.get("answer_en")),
                "keywords": clean_list(faq.get("keywords")),
                "category": clean_text(faq.get("category")),
                "related_day": faq.get("day"),
                "related_module_id": f"day{faq.get('day')}" if faq.get("day") else "",
                "related_ids": as_list(faq.get("related_ids")),
                "source_file": "knowledge.json",
            }
        )

    normalized = {
        "export_metadata": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "source": "Existing AI Academy Netlify repository",
            "notion_connector_available": False,
            "sensitive_fields_omitted": [
                "content/settings.json: admin credential setting",
                "content/settings.json: analytics measurement identifier",
            ],
            "source_files": [
                "index.html",
                "content/days.json",
                "content/videos.json",
                "content/sites.json",
                "content/settings.json",
                "knowledge.json",
                "admin/config.yml",
                "netlify.toml",
            ],
        },
        "course": safe_course_settings(settings),
        "source_inventory": {
            "runtime_content": [
                {
                    "file": "index.html",
                    "role": "Static app shell, embedded day/tool fallbacks, UI, search, quiz, admin-mode logic",
                },
                {
                    "file": "content/videos.json",
                    "role": "Fetched by index.html to populate lesson video tables",
                },
                {
                    "file": "content/sites.json",
                    "role": "Fetched by index.html to merge the tools catalogue into the site guide/search",
                },
                {
                    "file": "knowledge.json",
                    "role": "Fetched by the FAQ bot for keyword-based answers",
                },
            ],
            "cms_content": [
                "content/days.json",
                "content/videos.json",
                "content/sites.json",
                "content/settings.json",
                "knowledge.json",
            ],
            "assets": pdf_files,
        },
        "modules": modules,
        "lessons": lessons,
        "videos": all_videos,
        "tools": tools,
        "knowledge_base": knowledge_rows,
        "resources": resources,
    }

    notion_schema = {
        "Course Modules": {
            "primary": "Title",
            "properties": {
                "Title": "title",
                "Module Number": "number",
                "Arabic Title": "rich_text",
                "English Title": "rich_text",
                "Date": "date or rich_text",
                "Status": "status",
                "Progress": "number",
                "Lessons": "relation -> Lessons",
                "Videos": "relation -> Videos",
                "Tools": "multi_select or relation -> Tools",
                "Summary PDF": "files or url/path",
            },
        },
        "Lessons": {
            "primary": "Name",
            "properties": {
                "Module": "relation -> Course Modules",
                "Overview AR": "rich_text",
                "Overview EN": "rich_text",
                "Key Points": "rich_text / child bullets",
                "Takeaways": "rich_text / child bullets",
                "Tips": "rich_text / child bullets",
                "Status": "status",
            },
        },
        "Videos": {
            "primary": "Title",
            "properties": {
                "Module": "relation -> Course Modules",
                "Lesson": "relation -> Lessons",
                "Part": "rich_text",
                "Duration": "rich_text",
                "Topic": "multi_select or rich_text",
                "URL": "url",
                "Status": "status",
            },
        },
        "Tools": {
            "primary": "Name",
            "properties": {
                "Domain": "url or rich_text",
                "Category AR": "select",
                "Category EN": "select",
                "Benefit": "rich_text",
                "Usage": "rich_text",
                "Modules": "relation -> Course Modules",
            },
        },
        "Knowledge Base": {
            "primary": "Question",
            "properties": {
                "FAQ ID": "number",
                "Question AR": "title",
                "Question EN": "rich_text",
                "Answer AR": "rich_text",
                "Answer EN": "rich_text",
                "Keywords": "multi_select",
                "Category": "select",
                "Related Module": "relation -> Course Modules",
                "Related FAQs": "relation -> Knowledge Base",
            },
        },
        "Resources": {
            "primary": "Title",
            "properties": {
                "Module": "relation -> Course Modules",
                "Type": "select",
                "Path": "files or rich_text",
            },
        },
    }

    notion_export = {
        "export_metadata": normalized["export_metadata"],
        "course": normalized["course"],
        "databases": {
            "Course Modules": {
                "schema": notion_schema["Course Modules"],
                "rows": [
                    {
                        "Title": f"{m['module_number']:02d}. {m['title_en'] or m['title_ar']}",
                        "Module Number": m["module_number"],
                        "Arabic Title": m["title_ar"],
                        "English Title": m["title_en"],
                        "Date": m["date"],
                        "Status": m["status"],
                        "Progress": m["progress"],
                        "Tool Names": m["tool_names"],
                        "Video Count": m["video_count"],
                        "Summary PDF": m["summary_pdf"],
                        "Source ID": m["id"],
                    }
                    for m in modules
                ],
            },
            "Lessons": {
                "schema": notion_schema["Lessons"],
                "rows": [
                    {
                        "Name": f"{lesson['lesson_number']:02d}. {lesson['name_en'] or lesson['name_ar']}",
                        "Module ID": lesson["module_id"],
                        "Overview AR": lesson["overview_ar"],
                        "Overview EN": lesson["overview_en"],
                        "PDF Summary AR": lesson["pdf_summary_ar"],
                        "PDF Summary EN": lesson["pdf_summary_en"],
                        "Key Points AR": lesson["key_points_ar"],
                        "Key Points EN": lesson["key_points_en"],
                        "Takeaways AR": lesson["takeaways_ar"],
                        "Takeaways EN": lesson["takeaways_en"],
                        "Tips AR": lesson["tips_ar"],
                        "Tips EN": lesson["tips_en"],
                        "Tool Names": lesson["tool_names"],
                        "Video IDs": lesson["video_ids"],
                        "Status": lesson["status"],
                        "Source ID": lesson["id"],
                    }
                    for lesson in lessons
                ],
            },
            "Videos": {"schema": notion_schema["Videos"], "rows": all_videos},
            "Tools": {"schema": notion_schema["Tools"], "rows": tools},
            "Knowledge Base": {"schema": notion_schema["Knowledge Base"], "rows": knowledge_rows},
            "Resources": {"schema": notion_schema["Resources"], "rows": resources},
        },
    }

    markdown = build_markdown(normalized, notion_schema)
    guide = build_guide(normalized, notion_schema)
    return normalized, notion_export, markdown, guide


def md_escape(value) -> str:
    return clean_text(value).replace("|", "\\|")


def bullets(items: list) -> str:
    if not items:
        return "- None recorded"
    return "\n".join(f"- {clean_text(item)}" for item in items)


def build_markdown(normalized: dict, notion_schema: dict) -> str:
    course = normalized["course"]
    lines = [
        "# AI Academy Course - Notion Export",
        "",
        f"Arabic title: {course.get('course_title_ar', '')}",
        f"English title: {course.get('course_title_en', '')}",
        f"Instructor: {course.get('instructor_en', '')} / {course.get('instructor_ar', '')}",
        f"Cohort year: {course.get('cohort_year', '')}",
        "",
        "## Course Modules",
        "",
        "| # | Module | Date | Videos | Tools | PDF |",
        "|---:|---|---|---:|---|---|",
    ]
    for module in normalized["modules"]:
        lines.append(
            "| {num} | {title} / {title_ar} | {date} | {videos} | {tools} | {pdf} |".format(
                num=module["module_number"],
                title=md_escape(module["title_en"]),
                title_ar=md_escape(module["title_ar"]),
                date=md_escape(module["date"]),
                videos=module["video_count"],
                tools=md_escape(", ".join(module["tool_names"])),
                pdf=md_escape(module["summary_pdf"]),
            )
        )

    lessons_by_module = {lesson["module_id"]: lesson for lesson in normalized["lessons"]}
    videos_by_module = {}
    for video in normalized["videos"]:
        videos_by_module.setdefault(video["module_id"], []).append(video)

    for module in normalized["modules"]:
        lesson = lessons_by_module.get(module["id"], {})
        lines.extend(
            [
                "",
                f"## Module {module['module_number']}: {module['title_en'] or module['title_ar']}",
                "",
                f"Arabic: {module['title_ar']}",
                f"Subtitle: {module['subtitle_en'] or module['subtitle_ar']}",
                f"Date: {module['date']}",
                f"Read time: {module['read_time_en'] or module['read_time_ar']}",
                f"Summary PDF: {module['summary_pdf'] or 'None recorded'}",
                "",
                "### Overview",
                "",
                lesson.get("overview_en") or lesson.get("overview_ar") or "No overview recorded.",
                "",
                "### Key Points",
                "",
                bullets(lesson.get("key_points_en") or lesson.get("key_points_ar") or []),
                "",
                "### Takeaways",
                "",
                bullets(lesson.get("takeaways_en") or lesson.get("takeaways_ar") or []),
                "",
                "### Tips",
                "",
                bullets(lesson.get("tips_en") or lesson.get("tips_ar") or []),
                "",
                "### Videos",
                "",
            ]
        )
        module_videos = videos_by_module.get(module["id"], [])
        if module_videos:
            lines.extend(["| Part | Title | Duration | Topic | URL |", "|---|---|---|---|---|"])
            for video in module_videos:
                lines.append(
                    "| {part} | {title} | {duration} | {topic} | {url} |".format(
                        part=md_escape(video["part"]),
                        title=md_escape(video["title"]),
                        duration=md_escape(video["duration"]),
                        topic=md_escape(video["topic"]),
                        url=md_escape(video["url"]),
                    )
                )
        else:
            lines.append("- None recorded")
        lines.extend(
            [
                "",
                "### Tools",
                "",
                bullets(module["tool_names"]),
            ]
        )

    lines.extend(
        [
            "",
            "## Tools Catalogue",
            "",
            "| Tool | Category | Domain | Benefit | Usage |",
            "|---|---|---|---|---|",
        ]
    )
    for tool in normalized["tools"]:
        lines.append(
            "| {name} | {cat} | {domain} | {benefit} | {usage} |".format(
                name=md_escape(tool["name"]),
                cat=md_escape(tool["category_en"] or tool["category_ar"]),
                domain=md_escape(tool["domain"]),
                benefit=md_escape(tool["benefit_en"] or tool["benefit_ar"]),
                usage=md_escape(tool["usage_en"] or tool["usage_ar"]),
            )
        )

    lines.extend(
        [
            "",
            "## Knowledge Base FAQs",
            "",
            "| ID | Category | Related Day | Question | Keywords |",
            "|---:|---|---:|---|---|",
        ]
    )
    for faq in normalized["knowledge_base"]:
        lines.append(
            "| {id} | {category} | {day} | {question} | {keywords} |".format(
                id=faq["faq_id"],
                category=md_escape(faq["category"]),
                day=faq["related_day"] or "",
                question=md_escape(faq["question_en"] or faq["question_ar"]),
                keywords=md_escape(", ".join(map(str, faq["keywords"]))),
            )
        )

    lines.extend(
        [
            "",
            "## Proposed Notion Schema",
            "",
        ]
    )
    for db_name, db_schema in notion_schema.items():
        lines.append(f"### {db_name}")
        for prop, prop_type in db_schema["properties"].items():
            lines.append(f"- {prop}: {prop_type}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def build_guide(normalized: dict, notion_schema: dict) -> str:
    counts = {
        "modules": len(normalized["modules"]),
        "lessons": len(normalized["lessons"]),
        "videos": len(normalized["videos"]),
        "tools": len(normalized["tools"]),
        "faqs": len(normalized["knowledge_base"]),
        "resources": len(normalized["resources"]),
    }
    lines = [
        "# Notion Course Database Import Guide",
        "",
        "This repository does not currently have an authenticated Notion connector available in Codex, so the course data was exported into Notion-ready files instead of being written directly to Notion.",
        "",
        "## Source Of Truth",
        "",
        "- `content/days.json`: course day/module content, lesson overviews, summaries, points, takeaways, tips, and tool references.",
        "- `content/videos.json`: runtime video list loaded by `index.html`.",
        "- `content/sites.json`: runtime tools catalogue loaded by `index.html`.",
        "- `knowledge.json`: FAQ chatbot knowledge base loaded by `index.html`.",
        "- `content/settings.json`: public course metadata. Sensitive values are not exported.",
        "- `index.html`: static app shell and embedded fallback content; it also fetches videos, sites, and knowledge data.",
        "- `admin/config.yml`: Decap CMS schema for editing content through `/admin`.",
        "",
        "## Generated Export Files",
        "",
        "- `course-data-normalized.json`: canonical structured data for another CMS, automation, or future sync script.",
        "- `notion-course-export.json`: Notion database-style export with database schemas and rows.",
        "- `notion-course-export.md`: Markdown page export that can be imported directly into Notion.",
        "- `NOTION_IMPORT_GUIDE.md`: this import and maintenance guide.",
        "",
        "## Extracted Counts",
        "",
        f"- Modules/course days: {counts['modules']}",
        f"- Lessons: {counts['lessons']}",
        f"- Videos: {counts['videos']}",
        f"- Tools: {counts['tools']}",
        f"- Chatbot FAQ entries: {counts['faqs']}",
        f"- PDF resources: {counts['resources']}",
        "",
        "## Recommended Notion Databases",
        "",
    ]
    for db_name, db_schema in notion_schema.items():
        lines.append(f"### {db_name}")
        lines.append(f"Primary property: `{db_schema['primary']}`")
        lines.append("")
        for prop, prop_type in db_schema["properties"].items():
            lines.append(f"- `{prop}`: {prop_type}")
        lines.append("")

    lines.extend(
        [
            "## Import Options",
            "",
            "### Option 1: Markdown Import",
            "",
            "1. In Notion, create a new page named `AI Academy Course`.",
            "2. Use Notion's import feature and choose `notion-course-export.md`.",
            "3. Review the generated sections for each module.",
            "4. Optionally turn module/video/tool tables into Notion databases.",
            "",
            "### Option 2: JSON-Based Database Build",
            "",
            "1. Create databases matching the schema above.",
            "2. Use `notion-course-export.json` as the row source.",
            "3. Import in this order: Course Modules, Lessons, Videos, Tools, Knowledge Base, Resources.",
            "4. Reconnect relations in Notion using `Source ID`, `Module ID`, `Lesson ID`, and related day fields.",
            "",
            "### Option 3: Future API Sync",
            "",
            "1. Store a Notion integration token outside the repo as an environment variable.",
            "2. Store target database IDs outside the repo as environment variables.",
            "3. Use `course-data-normalized.json` as the canonical payload.",
            "4. Sync by stable IDs such as `day1`, `lesson-day1`, `day1-video-01`, and `tool-chatgpt`.",
            "",
            "## Safest Maintenance Workflow",
            "",
            "1. Continue editing the website through Decap CMS or the existing JSON files.",
            "2. Keep `content/days.json`, `content/videos.json`, `content/sites.json`, and `knowledge.json` as the website source of truth.",
            "3. Regenerate exports after content changes with `python scripts/generate_notion_exports.py`.",
            "4. Import or sync the regenerated files into Notion.",
            "5. Avoid making Notion the only source of truth until a tested two-way sync exists.",
            "",
            "## Limitations",
            "",
            "- No Notion connector was available in this Codex environment, so no Notion page/database was created directly.",
            "- The export intentionally omits the admin credential setting and raw analytics measurement identifier from `content/settings.json`.",
            "- Notion relation properties must be connected manually unless a future Notion API sync is added.",
            "- Telegram video URLs may require access to the private course channel.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    normalized, notion_export, markdown, guide = build_exports()
    write_json("course-data-normalized.json", normalized)
    write_json("notion-course-export.json", notion_export)
    (ROOT / "notion-course-export.md").write_text(markdown, encoding="utf-8")
    (ROOT / "NOTION_IMPORT_GUIDE.md").write_text(guide, encoding="utf-8")


if __name__ == "__main__":
    main()
