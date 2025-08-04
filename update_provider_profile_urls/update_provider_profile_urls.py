#!/usr/bin/env python3
import re
from pathlib import Path
from bs4 import BeautifulSoup


def extract_first_last(name_text: str):
    # Strip off credentials after comma, e.g. "W. Scott Russell, M.D." -> "W. Scott Russell"
    name_part = name_text.split(",", 1)[0].strip()
    if not name_part:
        return None, None
    tokens = name_part.split()
    if len(tokens) == 1:
        return tokens[0].strip("., "), tokens[0].strip("., ")
    last_name = tokens[-1].strip("., ")
    # Pick first non-initial as first name; fallback to last token before last
    tokens_before = tokens[:-1]
    first_name_candidate = None
    for tok in tokens_before:
        if not re.match(
            r"^[A-Za-z]\.?$", tok
        ):  # skip single-letter initials like "W." or "M."
            first_name_candidate = tok
            break
    if first_name_candidate is None:
        first_name_candidate = tokens_before[-1]
    first_name = first_name_candidate.strip("., ").replace(".", "")
    return first_name, last_name


def build_new_url(first_name: str, last_name: str):
    # lower-case, keep hyphens in last name
    return f"https://education.musc.edu/MUSCApps/FacultyDirectory/{last_name.lower()}-{first_name.lower()}"


def main(input_file="before.html", output_file="after.html"):
    in_path = Path(input_file)
    out_path = Path(output_file)
    if not in_path.exists():
        raise FileNotFoundError(f"{input_file} not found")

    with open(in_path, encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")

    for a in soup.find_all("a"):
        display_text = a.get_text(separator=" ", strip=True)
        first_name, last_name = extract_first_last(display_text)
        if not first_name or not last_name:
            continue  # unable to parse; leave as-is
        new_href = build_new_url(first_name, last_name)

        # Determine title: keep existing, otherwise add
        if a.has_attr("title"):
            title_value = a["title"]
        else:
            title_value = f"Profile of Dr. {last_name}"

        # Reset attributes except href and title
        a.attrs = {}
        a["href"] = new_href
        a["title"] = title_value

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(str(soup))


if __name__ == "__main__":
    main()
