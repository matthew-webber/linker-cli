DOMAINS = [
    {
        "full_name": "Enterprise",
        "worksheet_name": "Enterprise",
        "sitecore_domain_name": "Enterprise",
        "url": "web.musc.edu",
        "worksheet_header_row": 4,
    },
    {
        "full_name": "Adult Health",
        "worksheet_name": "Adult Health",
        "sitecore_domain_name": "Adult Health",
        "url": None,
        "worksheet_header_row": 3,
    },
    {
        "full_name": "Education",
        "worksheet_name": "Education",
        "sitecore_domain_name": "Education",
        "url": "education.musc.edu",
        "worksheet_header_row": 4,
    },
    {
        "full_name": "Research",
        "worksheet_name": "Research",
        "sitecore_domain_name": "Research",
        "url": "research.musc.edu",
        "worksheet_header_row": 4,
    },
    {
        "full_name": "Hollings Cancer",
        "worksheet_name": "Hollings Cancer",
        "sitecore_domain_name": "Hollings Cancer",
        "url": None,
        "worksheet_header_row": 4,
    },
    {
        "full_name": "Childrens Health",
        "worksheet_name": "Childrens Health",
        "sitecore_domain_name": "Childrens Health",
        "url": None,
        "worksheet_header_row": 4,
    },
    {
        "full_name": "CDM",
        "worksheet_name": "CDM",
        "sitecore_domain_name": "CDM",
        "url": None,
        "worksheet_header_row": 4,
    },
    {
        "full_name": "MUSC Giving",
        "worksheet_name": "MUSC Giving",
        "sitecore_domain_name": "MUSC Giving",
        "url": "giving.musc.edu",
        "worksheet_header_row": 4,
    },
    {
        "full_name": "CGS",
        "worksheet_name": "CGS",
        "sitecore_domain_name": "CGS",
        "url": "gradstudies.musc.edu",
        "worksheet_header_row": 4,
    },
    {
        "full_name": "CHP",
        "worksheet_name": "CHP",
        "sitecore_domain_name": "CHP",
        "url": "chp.musc.edu",
        "worksheet_header_row": 4,
    },
    {
        "full_name": "COM",
        "worksheet_name": "COM",
        "sitecore_domain_name": "COM",
        "url": "medicine.musc.edu",
        "worksheet_header_row": 4,
    },
    {
        "full_name": "CON",
        "worksheet_name": "CON",
        "sitecore_domain_name": "CON",
        "url": "nursing.musc.edu",
        "worksheet_header_row": 4,
    },
    {
        "full_name": "COP",
        "worksheet_name": "COP",
        "sitecore_domain_name": "COP",
        "url": "pharmacy.musc.edu",
        "worksheet_header_row": 4,
    },
]

DOMAIN_MAPPING = {
    domain["url"]: domain["sitecore_domain_name"] for domain in DOMAINS if domain["url"]
}
