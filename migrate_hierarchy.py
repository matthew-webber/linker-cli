
from urllib.parse import urlparse

# Map web addresses to Sitecore domain names
DOMAIN_MAPPING = {
    "web.musc.edu": "Enterprise",
    "muschealth.org": "Health",
    "education.musc.edu": "Education",
    "research.musc.edu": "Research",
    "hollingscancercenter.musc.edu": "Hollings",
    "musckids.org": "Kids",
    "dentistry.musc.edu": "Dental Medicine",
    "giving.musc.edu": "Giving",
    "gradstudies.musc.edu": "Graduate Studies",
    "chp.musc.edu": "Health Professions",
    "medicine.musc.edu": "Medicine",
    "nursing.musc.edu": "Nursing",
    "pharmacy.musc.edu": "Pharmacy",
}

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
    print(f"{root} (Sites)")
    for seg in segments:
        print(f" > {seg}")


def print_proposed_hierarchy(existing_url: str, proposed_path: str):
    """
    Print the Sitecore hierarchy for a proposed URL path,
    using the department root inferred from existing URL.
    """
    root = get_sitecore_root(existing_url)
    segments = [seg for seg in proposed_path.strip("/").split("/") if seg]
    print("\nProposed directory hierarchy:")
    print(f"{root} (Sites)")
    for seg in segments:
        print(f" > {seg}")
