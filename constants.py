from commands.check import cmd_check


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
        "url": "muschealth.org",
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
        "url": "hollingscancercenter.musc.edu",
        "worksheet_header_row": 3,
    },
    {
        "full_name": "Childrens Health",
        "worksheet_name": "Childrens Health",
        "sitecore_domain_name": "Kids",
        "url": "musckids.org",
        "worksheet_header_row": 3,
    },
    {
        "full_name": "CDM",
        "worksheet_name": "CDM",
        "sitecore_domain_name": "Dental Medicine",
        "url": "dentistry.musc.edu",
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
    from commands.core import (
        cmd_links,
        cmd_open,
        cmd_set,
        cmd_show,
    )
    from commands.sidebar import cmd_sidebar
    from commands.load import cmd_load
    from commands.report import cmd_report
    from commands.clear import cmd_clear
    from commands.common import cmd_help, cmd_debug
    from commands.bulk import cmd_bulk_check

    return {
        "bulk_check": lambda args: cmd_bulk_check(args, state),
        "bulk": lambda args: cmd_bulk_check(args, state),  # Alias for bulk
        "check": lambda args: cmd_check(args, state),
        "clear": lambda args: cmd_clear(args),
        "debug": lambda args: cmd_debug(args, state),
        "help": lambda args: cmd_help(args, state),
        "links": lambda args: cmd_links(args, state),
        "load": lambda args: cmd_load(args, state),
        "open": lambda args: cmd_open(args, state),
        "report": lambda args: cmd_report(args, state),
        "set": lambda args: cmd_set(args, state),
        "sidebar": lambda args: cmd_sidebar(args, state),
        "show": lambda args: cmd_show(args, state),
        # Aliases
        "vars": lambda args: cmd_show(["variables"], state),
        "ls": lambda args: cmd_show(["variables"], state),
        "exit": lambda args: exit(0),
        "quit": lambda args: exit(0),
        "q": lambda args: exit(0),
    }
