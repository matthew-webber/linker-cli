import re
import sys
import shutil
from pathlib import Path
from io import StringIO
from datetime import datetime

from commands.common import print_help_for_command
from utils.core import debug_print
from commands.core import _open_file_in_default_app

from commands.load import cmd_load
from utils.core import display_page_data
from utils.core import output_internal_links_analysis_detail
from utils.sitecore import print_hierarchy, print_proposed_hierarchy


def _capture_migrate_page_mapping_output(state):
    """Capture the output from migrate page mapping functionality."""
    url = state.get_variable("URL")
    if not url:
        return "❌ No URL set for page mapping."

    output = StringIO()
    old_stdout = sys.stdout
    sys.stdout = output

    try:
        print_hierarchy(url)
        proposed = state.get_variable("PROPOSED_PATH")
        if proposed:
            print_proposed_hierarchy(url, proposed)
        else:
            print("No proposed path set. Use 'set PROPOSED_PATH <path>' to set it.")
    finally:
        sys.stdout = old_stdout

    return output.getvalue()


def _capture_output(func, *args, **kwargs):
    """Capture stdout from a function call and return it as a string."""
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()
    try:
        func(*args, **kwargs)
        return captured_output.getvalue()
    finally:
        sys.stdout = old_stdout


def _generate_consolidated_section(state):
    """Generate the consolidated section with enhanced link display."""
    url = state.get_variable("URL")
    domain = state.get_variable("DOMAIN")
    row = state.get_variable("ROW")
    proposed_path = state.get_variable("PROPOSED_PATH")

    if not state.current_page_data:
        return "<p>No page data available.</p>"

    try:
        from utils.sitecore import get_sitecore_root

        root = get_sitecore_root(url)
        if url:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            existing_segments = [
                seg for seg in parsed.path.strip("/").split("/") if seg
            ]
        else:
            existing_segments = []

        if proposed_path:
            proposed_segments = [
                seg for seg in proposed_path.strip("/").split("/") if seg
            ]
        else:
            proposed_segments = []
    except Exception:
        root = "Sites"
        existing_segments = []
        proposed_segments = []

    html = f"""
    <div class="consolidated-section">
        <div class="source-info">
            <h3>📍 Source Information</h3>
            <p><strong>URL:</strong> <a href="{url}" onclick="window.open(this.href, '_blank', 'noopener,noreferrer,width=1200,height=1200'); return false;">{url}</a></p>
            <p><strong>DSM Location:</strong> {domain} {row}</p>"""

    # Add meta description if available
    meta_description = state.current_page_data.get("meta_description", "")
    if meta_description:
        # Escape HTML characters and truncate if too long
        from html import escape

        escaped_meta = escape(meta_description)
        if len(escaped_meta) > 200:
            escaped_meta = escaped_meta[:200] + "..."

        html += f"""
            <p><strong>Meta Description:</strong> 
                <button onclick="copyMetaDescription()" class="copy-btn" title="Copy meta description">📋</button>
                <span id="meta-desc-text">{escaped_meta}</span>
            </p>"""
    else:
        html += """
            <p><strong>Meta Description:</strong> <em>Not available</em></p>"""

    html += """
        </div>

        <div class="hierarchy-info">
            <h3>🏗️ Directory Structure</h3>
            <div class="hierarchy-comparison">
                <div class="existing-hierarchy">
                    <h4>Current Structure</h4>
                    <div class="hierarchy-tree">
                        🏠 {root}<br>
    """

    for i, segment in enumerate(existing_segments):
        indent = "   " * (i + 1)
        html += f"{indent}|-- {segment}<br>"

    html += """
                    </div>
                </div>
                <div class="proposed-hierarchy">
                    <h4>Proposed Structure</h4>
                    <div class="hierarchy-tree">
    """

    if proposed_segments:
        html += f"                        🏠 {root}<br>"
        for i, segment in enumerate(proposed_segments):
            indent = "   " * (i + 1)
            html += f"{indent}|-- {segment}<br>"
    else:
        html += "                        <em>No proposed path set</em><br>"

    html += """
                    </div>
                </div>
            </div>
        </div>

        <div class="links-summary">
            <h3>🔗 Found Links & Resources</h3>
    """

    all_items = []
    for link in state.current_page_data.get("links", []):
        all_items.append(("link", link))
    for link in state.current_page_data.get("sidebar_links", []):
        all_items.append(("sidebar_link", link))
    for pdf in state.current_page_data.get("pdfs", []):
        all_items.append(("pdf", pdf))
    for pdf in state.current_page_data.get("sidebar_pdfs", []):
        all_items.append(("sidebar_pdf", pdf))
    for embed in state.current_page_data.get("embeds", []):
        all_items.append(("embed", embed))
    for embed in state.current_page_data.get("sidebar_embeds", []):
        all_items.append(("sidebar_embed", embed))

    if not all_items:
        html += "<p><em>No links or resources found.</em></p>"
    else:
        html += '<div class="links-list">'

        for item_type, item in all_items:
            text, href, status = item
            debug_print(
                f"Processing item: {item_type} - {text} ({href}) with status {status}"
            )
            try:
                status = int(status)
            except (ValueError, TypeError):
                debug_print(
                    f"Invalid status code for {href}: {status} <-- status rec'd"
                )
                status = 0

            if status == 200:
                circle = "🟢"
            elif status == 404:
                circle = "🔴"
            elif status == 0:
                circle = "⚪"
            else:
                circle = f"🟡 [{status}]"

            copy_value = _get_copy_value(href)

            from urllib.parse import urlparse
            from constants import DOMAIN_MAPPING

            parsed = urlparse(href)
            href_hostname = parsed.hostname
            internal_domains = set(DOMAIN_MAPPING.keys())
            is_internal = not href_hostname or href_hostname in internal_domains
            internal_hierarchy = ""
            if is_internal:
                try:
                    from data.dsm import lookup_link_in_dsm

                    lookup_result = lookup_link_in_dsm(href, state.excel_data, state)
                    hierarchy = (
                        lookup_result.get("proposed_hierarchy", {})
                        if lookup_result
                        else {}
                    )
                    segments = hierarchy.get("segments", [])
                    root_name = hierarchy.get("root", "Sites")
                    internal_hierarchy = (
                        f"<div class='internal-hierarchy'>   → {root_name}"
                    )
                    for segment in segments:
                        internal_hierarchy += f" / {segment}"
                    internal_hierarchy += "</div>"
                except Exception:
                    internal_hierarchy = (
                        "<div class='internal-hierarchy'>   → Sites</div>"
                    )

            is_contact_link = href.startswith(("tel:", "mailto:"))
            is_pdf_link = href.lower().endswith(".pdf")
            anchor_copy_button = ""
            link_kind = "contact" if is_contact_link else "pdf"
            if is_contact_link or is_pdf_link:
                anchor_copy_button = f"""
                        <button class="copy-anchor-btn" onclick="copyAnchorToClipboard(event, '{copy_value}', '{text}', '{link_kind}')" title="Copy as HTML anchor">
                            &lt;/&gt;
                        </button>"""

            html += f"""
                <div class="link-item">
                    <div class="link-main">
                        {circle} <a href="{href}" target="_blank">{text}</a>
                        <button class="copy-btn" onclick="copyToClipboard(event, '{copy_value}')" title="Copy URL">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/>
                            </svg>
                        </button>{anchor_copy_button}
                        <span class="item-type">[{item_type.replace('_', ' ').title()}]</span>
                    </div>
                    {internal_hierarchy}
                </div>
            """

        html += "</div>"

    html += """
        </div>
    </div>
    """

    return html


def _get_copy_value(href):
    if href.startswith("tel:"):
        phone = href.replace("tel:", "").strip()
        digits_only = re.sub(r"[^\d]", "", phone)
        if len(digits_only) == 10:
            return f"tel:+1{digits_only}"
        elif len(digits_only) == 11 and digits_only.startswith("1"):
            return f"tel:+{digits_only}"
        else:
            return href
    elif href.lower().endswith(".pdf") or "/pdf/" in href.lower():
        from urllib.parse import urlparse

        parsed = urlparse(href)
        return parsed.path
    else:
        return href


def _get_report_template_dir():
    template_dir = Path("templates/report")
    template_dir.mkdir(exist_ok=True)
    return template_dir


def _generate_html_report(
    domain,
    row,
    show_page_output,
    migrate_output,
    links_output,
    consolidated_output,
    kanban_id=None,
):
    template_dir = _get_report_template_dir()
    template_path = template_dir / "template.html"
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()
    except Exception as e:
        print(f"⛔️ ERROR: Failed to read template:\n'{e}'")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    kanban_html = ""
    if kanban_id and kanban_id.strip():
        kanban_url = f"https://planner.cloud.microsoft/webui/v1/plan/aF9AETwLXEi oMF3ADqLdpWQADWIy/view/board/task/{kanban_id.strip()}"
        kanban_html = f'<div class="kanban-link"><a href="{kanban_url}" onclick="window.open(this.href, \'_blank\', \'noopener,noreferrer,width=800,height=1200\'); return false;" class="kanban-button">📋 Kanban card</a></div>'
        debug_print(f"Generated Kanban link: {kanban_html}")
    else:
        debug_print("No Kanban ID provided.")

    return template.format(
        domain=domain,
        row=row,
        kanban_url=kanban_html,
        consolidated_output=consolidated_output,
        show_page_output=show_page_output.replace("<", "&lt;").replace(">", "&gt;"),
        migrate_output=migrate_output.replace("<", "&lt;").replace(">", "&gt;"),
        links_output=links_output.replace("<", "&lt;").replace(">", "&gt;"),
        timestamp=timestamp,
    )


# check.py
def _sync_report_static_assets(reports_dir):
    template_dir = _get_report_template_dir()
    for file in template_dir.glob("*"):
        if file.suffix in {".css", ".js"}:
            dest = reports_dir / file.name
            shutil.copy(file, dest)


def _generate_report(state, prompt_open=True, force_regenerate=False):
    from utils.cache import _is_cache_valid_for_context

    need_to_check = False
    if not state.current_page_data:
        need_to_check = True
        reason = "No page data available"
    else:
        cache_file = state.get_variable("CACHE_FILE")
        is_valid, validation_reason = _is_cache_valid_for_context(state, cache_file)
        if not is_valid:
            need_to_check = True
            reason = validation_reason

    if need_to_check:
        print(f"🔄 Running 'check' to gather page data... ({reason})")
        from commands.check import cmd_check

        cmd_check([], state)
        if not state.current_page_data:
            print("❌ Failed to gather page data. Cannot generate report.")
            return None
    else:
        print("📋 Using existing cached page data for report")

    domain = state.get_variable("DOMAIN") or "unknown"
    row = state.get_variable("ROW") or "unknown"

    reports_dir = Path("./reports")
    reports_dir.mkdir(exist_ok=True)

    clean_domain = re.sub(r"[^a-zA-Z0-9]", "_", domain.lower())
    filename = f"./reports/{clean_domain}_{row}.html"

    report_path = Path(filename)

    if report_path.exists() and not force_regenerate:
        cache_file = state.get_variable("CACHE_FILE")

        if cache_file:
            try:
                report_mtime = report_path.stat().st_mtime
                cache_path = Path(cache_file)

                if cache_path.exists():
                    cache_mtime = cache_path.stat().st_mtime

                    if report_mtime >= cache_mtime:
                        print(f"📋 Report already exists and is up-to-date: {filename}")
                        if prompt_open:
                            prompt_to_open_report(report_path)
                        return str(filename)
                    else:
                        print(
                            f"📊 Regenerating report (cache is newer than existing report): {filename}"
                        )
                else:
                    print(f"📊 Regenerating report (cache file not found): {filename}")
            except Exception as e:
                debug_print(f"Error checking report currency: {e}")
                print(f"📊 Regenerating report (error checking timestamps): {filename}")
        else:
            print(f"📊 Regenerating report (no cache file available): {filename}")
    elif force_regenerate:
        print(f"📊 Force regenerating report: {filename}")
    else:
        print(f"📊 Generating report: {filename}")

    print("  ▶ Capturing page data...")
    if state.current_page_data:
        show_page_output = _capture_output(display_page_data, state.current_page_data)
    else:
        show_page_output = "❌ No page data available. Run 'check' first."

    print("  ▶ Capturing migration mapping...")
    migrate_output = _capture_migrate_page_mapping_output(state)

    print("  ▶ Capturing links analysis...")
    links_output = _capture_output(output_internal_links_analysis_detail, state)

    print("  ▶ Generating consolidated summary...")
    consolidated_output = _generate_consolidated_section(state)

    print("  ▶ Generating HTML...")
    kanban_id = state.get_variable("KANBAN_ID")
    html_content = _generate_html_report(
        domain,
        row,
        show_page_output,
        migrate_output,
        links_output,
        consolidated_output,
        kanban_id,
    )

    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"✅ Report saved to: {filename}")
        print(f"💡 Open the file in your browser to view the report")
    except Exception as e:
        print(f"❌ Failed to save report: {e}")

    _sync_report_static_assets(reports_dir)

    if prompt_open:
        open_report_now = (
            input("Do you want to open the report in your browser now? [Y/n]: ")
            .strip()
            .lower()
        )
        if open_report_now in ["", "y", "yes"]:
            try:
                from commands.core import cmd_open

                cmd_open(["report"], state)
            except Exception as e:
                print(f"❌ Failed to open report: {e}")
                debug_print(f"Full error: {e}")

    return filename


def prompt_to_open_report(report_path):
    open_report_now = (
        input("Do you want to open the existing report in your browser now? [Y/n]: ")
        .strip()
        .lower()
    )
    if open_report_now in ["", "y", "yes"]:
        try:
            _open_file_in_default_app(report_path)
        except Exception as e:
            print(f"❌ Failed to open report: {e}")
            debug_print(f"Full error: {e}")


def cmd_report(args, state):
    force_regenerate = False
    if args and args[0] in ["--force", "-f"]:
        force_regenerate = True
        args = args[1:]

    if args:
        first_row_idx = next((i for i, a in enumerate(args) if a.isdigit()), None)
        if first_row_idx is None:
            return print_help_for_command("report", state)

        domain = " ".join(args[:first_row_idx])
        rows = args[first_row_idx:]
        report_files = []

        for row in rows:
            cmd_load([domain, row], state)
            report_file = _generate_report(
                state, prompt_open=False, force_regenerate=force_regenerate
            )
            if report_file:
                report_files.append(report_file)

        if report_files:
            open_now = (
                input(
                    f"Open {len(report_files)} report{'s' if len(report_files)>1 else ''} in your browser now? [Y/n]: "
                )
                .strip()
                .lower()
            )
            if open_now in ["", "y", "yes"]:
                for rf in report_files:
                    try:
                        _open_file_in_default_app(rf)
                    except Exception as e:
                        print(f"❌ Failed to open report {rf}: {e}")
        return

    _generate_report(state, prompt_open=True, force_regenerate=force_regenerate)
