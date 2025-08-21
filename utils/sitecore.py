from urllib.parse import urlparse

from constants import DOMAIN_MAPPING, DOMAINS


def format_hierarchy(root: str, segments: list) -> str:
    """Format the Sitecore hierarchy as a multi-line filesystem-style tree."""
    lines = [f"🏠 {root}"]
    for idx, seg in enumerate(segments):
        indent = "|   " * idx
        lines.append(f"{indent}|-- {seg}")
    return "\n".join(lines)


def get_sitecore_root(existing_url: str) -> str:
    """
    Infer the Sitecore root folder name from the existing URL's hostname.
    """
    parsed = urlparse(existing_url)
    hostname = parsed.hostname or ""
    return DOMAIN_MAPPING.get(hostname, hostname.split(".")[0])


def get_current_sitecore_root(existing_url: str) -> str:
    """
    Get the current Sitecore root folder name based on the existing URL.
    """
    return get_sitecore_root(existing_url)


def get_proposed_sitecore_root(existing_url: str) -> str:
    """Determine the Sitecore root folder for the redesigned site.

    The function checks the domain of ``existing_url`` against entries in
    :data:`DOMAINS` and returns the ``root_for_new_sitecore`` value when
    defined. If no mapping exists the current root is returned instead.
    """
    from utils.core import debug_print

    proposed_root = next(
        (
            domain["root_for_new_sitecore"]
            for domain in DOMAINS
            if domain.get("url") in existing_url and domain.get("root_for_new_sitecore")
        ),
        None,
    )

    debug_print(f"Proposed root for {existing_url}: {proposed_root}")
    return proposed_root or get_sitecore_root(existing_url)


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
