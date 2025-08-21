from utils.cache import _cache_page_data, _is_cache_valid_for_context
from utils.scraping import retrieve_page_data
from ui.spinner import Spinner
from utils.core import debug_print


def _generate_summary_report(include_sidebar, data):
    links_count = len(data.get("links", []))
    pdfs_count = len(data.get("pdfs", []))
    embeds_count = len(data.get("embeds", []))

    sidebar_links_count = len(data.get("sidebar_links", []))
    sidebar_pdfs_count = len(data.get("sidebar_pdfs", []))
    sidebar_embeds_count = len(data.get("sidebar_embeds", []))

    total_links = links_count + sidebar_links_count
    total_pdfs = pdfs_count + sidebar_pdfs_count
    total_embeds = embeds_count + sidebar_embeds_count

    if include_sidebar and (
        sidebar_links_count > 0 or sidebar_pdfs_count > 0 or sidebar_embeds_count > 0
    ):
        print(
            f"📊 Main content: {links_count} links, {pdfs_count} PDFs, {embeds_count} embeds"
        )
        print(
            f"📊 Sidebar content: {sidebar_links_count} links, {sidebar_pdfs_count} PDFs, {sidebar_embeds_count} embeds"
        )
        print(
            f"📊 Total: {total_links} links, {total_pdfs} PDFs, {total_embeds} embeds"
        )
    else:
        print(
            f"📊 Summary: {total_links} links, {total_pdfs} PDFs, {total_embeds} embeds found"
        )


def _merge_page_data(base, new):
    for key in [
        "links",
        "pdfs",
        "embeds",
        "sidebar_links",
        "sidebar_pdfs",
        "sidebar_embeds",
    ]:
        base.setdefault(key, []).extend(new.get(key, []))

    for key in ["meta_description", "meta_robots"]:
        if key not in base or not base.get(key):
            base[key] = new.get(key, "")
    return base


def cmd_check(args, state):
    # TODO add ability to run check with args like --url, --selector, --include-sidebar
    urls = state.get_variable("EXISTING_URLS") or []
    url = state.get_variable("URL")
    if not urls and url:
        urls = [url]
    selector = state.get_variable("SELECTOR")
    include_sidebar = state.get_variable("INCLUDE_SIDEBAR")

    # Validate required variables
    required_vars = ["URL", "SELECTOR"]
    missing_vars, invalid_vars = state.validate_required_vars(required_vars)

    if missing_vars or invalid_vars:
        return

    if len(urls) > 1:
        print(f"🔍 Checking primary page: {url} (plus {len(urls)-1} additional URLs)")
    else:
        print(f"🔍 Checking page: {url}")
    print(f"🎯 Using selector: {selector}")
    if include_sidebar:
        print("🔲 Including sidebar content")

    debug_print("🔄 state.current_page_data", state.current_page_data)

    # Check if we have cached data that matches the current context
    if state.current_page_data and len(urls) == 1:
        # Verify the cached data is for the current URL/context
        cache_file = state.get_variable("CACHE_FILE")
        is_valid, reason = _is_cache_valid_for_context(state, cache_file)

        if is_valid:
            print("📋 Using cached data")
            data = state.current_page_data

            _generate_summary_report(include_sidebar, data)
            print("💡 Use 'show page' to see detailed results")
            return
        else:
            debug_print(f"Cache validation failed: {reason}")

    spinner = Spinner(f"🔄 Please wait...")
    spinner.start()

    combined = {}
    try:
        for u in urls:
            data = retrieve_page_data(u, selector, include_sidebar)
            if "error" in data:
                print(f"❌ Failed to extract data for {u}: {data['error']}")
                continue
            combined = _merge_page_data(combined, data)
    except Exception as e:
        print(f"❌ Error during page check: {e}")
        debug_print(f"Full error: {e}")
        return
    finally:
        spinner.stop()

    state.current_page_data = combined

    if urls:
        _cache_page_data(state, urls[0], combined)

    _generate_summary_report(include_sidebar, combined)
    print("💡 Use 'show page' to see detailed results")
