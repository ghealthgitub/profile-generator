"""
🫚 Ginger Universe v3 — Prompt Builder
Assembles the final Claude prompt from:
  1. Admin-editable prompt template (from DB)
  2. Scraped doctor data (from URLs)
  3. Treatment dictionary (from DB specialties + treatments)
"""


def build_prompt(prompt_template, scraped_data, treatment_dict):
    """
    Fills the prompt template with actual data.

    Template placeholders:
        {scraped_data}          — Combined text from all scraped URLs
        {treatment_dictionary}  — Formatted list of specialties + treatments from DB
    """

    # Format treatment dictionary for prompt injection
    treatments_text = format_treatment_dictionary(treatment_dict)

    # Format scraped data
    scraped_text = format_scraped_data(scraped_data)

    # Fill template
    final_prompt = prompt_template
    final_prompt = final_prompt.replace('{scraped_data}', scraped_text)
    final_prompt = final_prompt.replace('{treatment_dictionary}', treatments_text)

    return final_prompt


def format_treatment_dictionary(treatments):
    """
    Formats the treatment dictionary into a structured reference
    grouped by specialty for easy reading by Claude.
    """
    if not treatments:
        return "(No treatments loaded from database)"

    # Group by specialty
    by_specialty = {}
    for t in treatments:
        spec = t.get('specialty') or 'Uncategorized'
        if spec not in by_specialty:
            by_specialty[spec] = []
        by_specialty[spec].append(t.get('name', ''))

    lines = []
    for specialty in sorted(by_specialty.keys()):
        procs = by_specialty[specialty]
        lines.append(f"\n[{specialty}]")
        for proc in sorted(procs):
            lines.append(f"  • {proc}")

    lines.append(f"\nTotal: {len(treatments)} treatments across {len(by_specialty)} specialties")
    return '\n'.join(lines)


def format_scraped_data(scraped_data):
    """Formats the scraped data for the prompt"""
    if not scraped_data:
        return "(No data scraped)"

    parts = []

    urls = scraped_data.get('urls', [])
    if urls:
        parts.append(f"Source URLs: {', '.join(urls)}")

    titles = scraped_data.get('titles', [])
    if titles:
        parts.append(f"Page titles: {', '.join(titles)}")

    text = scraped_data.get('combined_text', '')
    if text:
        parts.append(f"\n--- Extracted Content ---\n{text}")

    return '\n'.join(parts) if parts else "(No data available)"
