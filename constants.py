DOMAINS = [
    {
        "full_name": "Enterprise",
        "worksheet_name": "Enterprise",
        "sitecore_domain_name": "Enterprise",
        "url": "web.musc.edu",
        "worksheet_header_row": 3,
    },
    {
        "full_name": "Adult Health",
        "worksheet_name": "Adult Health",
        "sitecore_domain_name": "Health",
        "url": None,
        "worksheet_header_row": 2,
    },
    {
        "full_name": "Education",
        "worksheet_name": "Education",
        "sitecore_domain_name": "Education",
        "url": "education.musc.edu",
        "worksheet_header_row": 3,
    },
    {
        "full_name": "Research",
        "worksheet_name": "Research",
        "sitecore_domain_name": "Research",
        "url": "research.musc.edu",
        "worksheet_header_row": 3,
    },
    {
        "full_name": "Hollings Cancer",
        "worksheet_name": "Hollings Cancer",
        "sitecore_domain_name": "Hollings",
        "url": None,
        "worksheet_header_row": 3,
    },
    {
        "full_name": "Childrens Health",
        "worksheet_name": "Childrens Health",
        "sitecore_domain_name": "Kids",
        "url": None,
        "worksheet_header_row": 3,
    },
    {
        "full_name": "CDM",
        "worksheet_name": "CDM",
        "sitecore_domain_name": "Dental Medicine",
        "url": None,
        "worksheet_header_row": 3,
    },
    {
        "full_name": "MUSC Giving",
        "worksheet_name": "MUSC Giving",
        "sitecore_domain_name": "Giving",
        "url": "giving.musc.edu",
        "worksheet_header_row": 3,
    },
    {
        "full_name": "CGS",
        "worksheet_name": "CGS",
        "sitecore_domain_name": "Graduate Studies",
        "url": "gradstudies.musc.edu",
        "worksheet_header_row": 3,
    },
    {
        "full_name": "CHP",
        "worksheet_name": "CHP",
        "sitecore_domain_name": "Health Professions",
        "url": "chp.musc.edu",
        "worksheet_header_row": 3,
    },
    {
        "full_name": "COM",
        "worksheet_name": "COM",
        "sitecore_domain_name": "Medicine",
        "url": "medicine.musc.edu",
        "worksheet_header_row": 3,
    },
    {
        "full_name": "CON",
        "worksheet_name": "CON",
        "sitecore_domain_name": "Nursing",
        "url": "nursing.musc.edu",
        "worksheet_header_row": 3,
    },
    {
        "full_name": "COP",
        "worksheet_name": "COP",
        "sitecore_domain_name": "Pharmacy",
        "url": "pharmacy.musc.edu",
        "worksheet_header_row": 3,
    },
]

DOMAIN_MAPPING = {
    domain["url"]: domain["sitecore_domain_name"] for domain in DOMAINS if domain["url"]
}


def get_commands(state):
    """Dynamically load and return the COMMANDS dictionary."""
    from commands import (
        cmd_set,
        cmd_show,
        cmd_check,
        cmd_migrate,
        cmd_load,
        cmd_help,
        cmd_debug,
        cmd_clear,
        cmd_legacy,
        cmd_lookup,
        cmd_analyze_links,
    )

    return {
        "set": lambda args: cmd_set(args, state),
        "show": lambda args: cmd_show(args, state),
        "check": lambda args: cmd_check(args, state),
        "migrate": lambda args: cmd_migrate(args, state),
        "load": lambda args: cmd_load(args, state),
        "help": lambda args: cmd_help(args, state),
        "debug": lambda args: cmd_debug(args),
        "clear": lambda args: cmd_clear(args),
        "legacy": lambda args: cmd_legacy(args),
        "lookup": lambda args: cmd_lookup(args, state),
        "links": lambda args: cmd_analyze_links(args, state),
        # Aliases
        "vars": lambda args: cmd_show(["variables"], state),
        "ls": lambda args: cmd_show(["variables"], state),
        "exit": lambda args: exit(0),
        "quit": lambda args: exit(0),
        "q": lambda args: exit(0),
    }
