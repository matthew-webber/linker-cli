from urllib.parse import urlparse

from constants import DOMAIN_MAPPING


def format_hierarchy(root: str, segments: list) -> str:
    """Format the Sitecore hierarchy as a multi-line string."""
    lines = [f"{root} (Sites)"]
    for seg in segments:
        lines.append(f" > {seg}")
    return "\n".join(lines)


def get_sitecore_root(existing_url: str) -> str:
    """
    Infer the Sitecore root folder name from the existing URL's hostname.
    """
    parsed = urlparse(existing_url)
    hostname = parsed.hostname or ""
    return DOMAIN_MAPPING.get(hostname, hostname.split(".")[0])


def print_hierarchy(existing_url: str):
    """
    Print the Sitecore hierarchy for the given page's existing URL.
    """
    root = get_sitecore_root(existing_url)
    # split existing path
    segments = [seg for seg in urlparse(existing_url).path.strip("/").split("/") if seg]
    print("\nExisting directory hierarchy:")
    print(format_hierarchy(root, segments))


def print_proposed_hierarchy(existing_url: str, proposed_path: str):
    """
    Print the Sitecore hierarchy for a proposed URL path,
    using the department root inferred from existing URL.
    """
    root = get_sitecore_root(existing_url)
    segments = [seg for seg in proposed_path.strip("/").split("/") if seg]
    print("\nProposed directory hierarchy:")
    print(format_hierarchy(root, segments))
