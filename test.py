#!/usr/bin/env python3
"""
add_cumulative_columns.py

Reads a wiki HTML table from 'table_input.html' and writes a new table
with two cumulative columns inserted after "Exp. needed" and "A-Q Chip cost".

It handles multi-line <tr> and <td> blocks and preserves attributes (like rowspan).
"""

import re
from pathlib import Path

INPUT_FILE = Path("table_input.html")
OUTPUT_FILE = Path("table_with_cumsum.html")

# Read entire file
text = INPUT_FILE.read_text(encoding="utf-8")

# Find the first <table ...>...</table> block (greedy to include everything inside)
table_match = re.search(
    r"(<table\b[^>]*>.*?</table>)", text, flags=re.DOTALL | re.IGNORECASE
)
if not table_match:
    raise SystemExit("No <table>...</table> block found in table_input.html")

table_html = table_match.group(1)

# Split into head (before table), table, tail (after table) so we can replace later
head = text[: table_match.start(1)]
tail = text[table_match.end(1) :]


# 1) Add header columns: replace the header row line containing the two THs
# We'll try to find the header row which contains "Exp. needed" and "A-Q Chip cost"
def add_header_columns(table_html):
    # Replace <th>Exp. needed</th> with two ths
    table_html_new = table_html
    table_html_new = re.sub(
        r"(<th[^>]*>\s*Exp\. needed\s*</th>)",
        r"\1\n    <th>Total Exp.</th>",
        table_html_new,
        flags=re.IGNORECASE,
        count=1,
    )
    table_html_new = re.sub(
        r"(<th[^>]*>\s*A-Q Chip cost\s*</th>)",
        r"\1\n    <th>Total Chips</th>",
        table_html_new,
        flags=re.IGNORECASE,
        count=1,
    )
    return table_html_new


table_html = add_header_columns(table_html)

# 2) Find all <tr>...</tr> blocks
tr_pattern = re.compile(r"(<tr\b[^>]*>.*?</tr>)", flags=re.DOTALL | re.IGNORECASE)
trs = tr_pattern.findall(table_html)

exp_total = 0
chip_total = 0

processed_trs = []

# Pattern to grab full <td ...>...</td> including newlines
td_pattern = re.compile(r"(<td\b[^>]*?>.*?</td>)", flags=re.DOTALL | re.IGNORECASE)


# Helper to extract numeric value from a td (first integer found), returns None if not found
def extract_first_int_from_td(td_html):
    # Remove HTML tags inside cell for easier search
    inner = re.sub(r"<[^>]+>", " ", td_html)
    m = re.search(r"(-?\d[\d,]*)", inner)
    if not m:
        return None
    s = m.group(1).replace(",", "")
    try:
        return int(s)
    except ValueError:
        return None


for tr in trs:
    # If this tr is a header (contains <th>), leave as-is (we already added header ths)
    if re.search(r"<th\b", tr, flags=re.IGNORECASE):
        processed_trs.append(tr)
        continue

    # Extract all td blocks in this row (preserve order and original text)
    tds = td_pattern.findall(tr)

    # If there are less than 3 td cells, it's unexpected for data rows; just pass through
    if len(tds) < 3:
        processed_trs.append(tr)
        continue

    # Parse lvl, exp, chip from the first three tds
    lvl_val = extract_first_int_from_td(tds[0])
    exp_val = extract_first_int_from_td(tds[1])
    chip_val = extract_first_int_from_td(tds[2])

    # If exp_val or chip_val is None, treat as 0 (so we keep running totals stable)
    if exp_val is None:
        exp_val = 0
    if chip_val is None:
        chip_val = 0

    exp_total += exp_val
    chip_total += chip_val

    # Build new td list: insert cumulative tds after index 1 (exp) and after index 3 (chip + inserted total)
    new_tds = []
    for i, td in enumerate(tds):
        new_tds.append(td)
        # After the Exp cell (index 1) insert the Total Exp td
        if i == 1:
            new_tds.append(f"<td>{exp_total}</td>")
        # After the Chip cell (original index 2) insert the Total Chips td.
        # Note: since we've appended an extra td already after index 1, the chip original index is still 2 here.
        if i == 2:
            new_tds.append(f"<td>{chip_total}</td>")

    # Reconstruct the <tr> preserving any attributes on <tr> tag if present
    tr_open_match = re.match(r"(<tr\b[^>]*>)", tr, flags=re.IGNORECASE)
    tr_open = tr_open_match.group(1) if tr_open_match else "<tr>"
    tr_close = "</tr>"

    # Join tds with a newline and two spaces for readability
    new_tr = tr_open + "\n  " + "\n  ".join(new_tds) + "\n" + tr_close

    processed_trs.append(new_tr)

# Rebuild the table_html by replacing the old tr blocks in order.
# We'll replace the sequence of trs in the original table_html with processed_trs.
# To be robust, iterate matches and build new table string.
out_parts = []
last_end = 0
for m, new_tr in zip(tr_pattern.finditer(table_html), processed_trs):
    out_parts.append(table_html[last_end : m.start(1)])
    out_parts.append(new_tr)
    last_end = m.end(1)
out_parts.append(table_html[last_end:])

new_table_html = "".join(out_parts)

# Replace the old table in the original document with the new one
new_text = head + new_table_html + tail

# Write to output file
OUTPUT_FILE.write_text(new_text, encoding="utf-8")
print(f"Wrote updated table with cumulative columns to: {OUTPUT_FILE.resolve()}")
