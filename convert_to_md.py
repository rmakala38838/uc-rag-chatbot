"""
Convert scraped JSON pages to clean Markdown files.
Preserves: headings, links, list structure, tables, metadata.
"""

import json
from pathlib import Path
from tqdm import tqdm


SCRAPED_DIR = Path("scraped_data/pages")
OUTPUT_DIR = Path("markdown_data")
BASE_URL = "https://www.ucumberlands.edu"


NOISE_LINES = {
    "Move Left", "Move Right", "Move left", "Move right",
    "Skip to main content", "Back to top", "Toggle navigation",
}


def convert_page_to_markdown(data):
    """Convert a single page's structured JSON into markdown."""
    title = data.get("title", "Untitled")
    url = data.get("url", "")
    meta_description = data.get("meta_description", "")
    full_text = data.get("full_text", "")
    headings = data.get("headings", [])
    links = data.get("links", [])
    tables = data.get("tables", [])

    if not full_text.strip():
        return ""

    # Build heading lookup: text -> level
    heading_map = {}
    for h in headings:
        heading_map[h["text"].strip()] = h["level"]

    # Build link lookup: anchor text -> href (normalized)
    link_map = {}
    for link in links:
        text = link.get("text", "").strip()
        href = link.get("href", "")
        if text and href:
            if href.startswith("/"):
                href = BASE_URL + href
            link_map[text] = href

    # Front matter
    md_parts = []
    md_parts.append("---")
    md_parts.append(f"title: \"{title}\"")
    md_parts.append(f"url: {url}")
    if meta_description:
        md_parts.append(f"description: \"{meta_description}\"")
    md_parts.append(f"category: {data.get('category', 'unknown')}")
    path_h = data.get("path_hierarchy", [])
    if path_h:
        md_parts.append(f"path: {' > '.join(path_h)}")
    md_parts.append("---")
    md_parts.append("")

    # Pre-process: fix obfuscated emails in full_text
    full_text = _fix_obfuscated_emails(full_text)

    # Process lines
    lines = full_text.split("\n")
    md_lines = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        i += 1

        if not line:
            md_lines.append("")
            continue

        # Skip navigation/template noise
        if line in NOISE_LINES:
            continue
        if line == "[at]" or line == "(":
            continue

        # Heading
        if line in heading_map:
            level = heading_map[line]
            prefix = "#" * min(level, 4)
            md_lines.append("")
            md_lines.append(f"{prefix} {line}")
            md_lines.append("")
            continue

        # Exact link match (standalone link line)
        if line in link_map:
            md_lines.append(f"[{line}]({link_map[line]})")
            continue

        # List item detection
        if _is_list_item(line, lines, i - 1, heading_map):
            md_lines.append(f"- {_linkify_line(line, link_map)}")
            continue

        # Regular paragraph
        md_lines.append(_linkify_line(line, link_map))

    md_parts.extend(md_lines)

    # Tables
    for table in tables:
        if not table or len(table) < 1:
            continue
        md_parts.append("")
        for row_idx, row in enumerate(table):
            cells = [str(c).replace("|", "\\|").strip() for c in row]
            md_parts.append("| " + " | ".join(cells) + " |")
            if row_idx == 0:
                md_parts.append("| " + " | ".join(["---"] * len(cells)) + " |")
        md_parts.append("")

    return "\n".join(md_parts)


def _linkify_line(text, link_map):
    """Replace known anchor texts within a line with markdown links."""
    for anchor, href in link_map.items():
        if anchor in text and len(anchor) > 3:
            text = text.replace(anchor, f"[{anchor}]({href})", 1)
    return text


def _fix_obfuscated_emails(text):
    """Fix email obfuscation patterns like 'name\\n[at]\\nhost.edu' → 'name@host.edu'."""
    import re
    # Pattern: word \n [at] \n domain
    text = re.sub(r'(\w+)\s*\n\s*\[at\]\s*\n\s*(\w[\w.-]+)', r'\1@\2', text)
    # Inline pattern: word [at] domain
    text = re.sub(r'(\w+)\s*\[at\]\s*(\w[\w.-]+)', r'\1@\2', text)
    # Pattern with [dot]: registrar[at]ucumberlands[dot]edu
    text = re.sub(r'(\w+)\[at\](\w+)\[dot\](\w+)', r'\1@\2.\3', text)
    return text


def _is_list_item(line, lines, idx, heading_map):
    """Heuristic: short line, not a heading, not ending with period/colon,
    surrounded by similar short lines."""
    if len(line) > 100:
        return False
    if line.endswith(".") or line.endswith(":"):
        return False
    if line in heading_map:
        return False
    if line[0].islower():
        return False

    neighbors = 0
    for offset in [-1, 1, 2]:
        ni = idx + offset
        if 0 <= ni < len(lines):
            neighbor = lines[ni].strip()
            if (neighbor and len(neighbor) < 100
                    and not neighbor.endswith(":")
                    and neighbor not in heading_map):
                neighbors += 1
    return neighbors >= 2


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    json_files = list(SCRAPED_DIR.rglob("*.json"))
    print(f"Converting {len(json_files)} pages to markdown...")

    converted = 0
    skipped = 0

    for json_file in tqdm(json_files, desc="Converting"):
        with open(json_file) as f:
            data = json.load(f)

        md_content = convert_page_to_markdown(data)
        if not md_content.strip():
            skipped += 1
            continue

        # Mirror directory structure
        rel_path = json_file.relative_to(SCRAPED_DIR)
        md_path = OUTPUT_DIR / rel_path.with_suffix(".md")
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(md_content, encoding="utf-8")
        converted += 1

    print(f"\nDone: {converted} markdown files created, {skipped} skipped (empty)")
    print(f"Output: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
