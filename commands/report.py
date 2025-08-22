import re
import sys
import shutil
import json
from html import escape
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


def _capture_output(func, *args, **kwargs):
    """Capture stdout from a function call and return it as a string."""
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()
    try:
        func(*args, **kwargs)
        return captured_output.getvalue()
    finally:
        sys.stdout = old_stdout


def _build_sitecore_nav_js(path: list[str]) -> str:
    """Builds the JS to navigate sitecore from a path list."""
    if not path:
        return ""

    json_path_array = json.dumps(path)
    return SITECORE_NAV_JS_TEMPLATE.format(path_array=json_path_array)


def _extract_sitecore_paths(state):
    """Return root names, path segments and navigation JS for current and proposed structures."""
    url = state.get_variable("URL")
    proposed_path = state.get_variable("PROPOSED_PATH")

    try:
        from utils.sitecore import (
            get_current_sitecore_root,
            get_proposed_sitecore_root,
        )
        from html import escape
        from urllib.parse import urlparse

        current_root = get_current_sitecore_root(url)
        proposed_root = get_proposed_sitecore_root(url)

        parsed = urlparse(url) if url else None
        existing_segments = (
            [seg for seg in parsed.path.strip("/").split("/") if seg] if parsed else []
        )

        if proposed_path:
            proposed_segments = [
                seg for seg in proposed_path.strip("/").split("/") if seg
            ]
            if (
                len(proposed_segments) >= 3
                and proposed_segments[0] == "sitecore"
                and proposed_segments[1] == "content"
                and proposed_segments[2] == "Content Hub"
            ):
                proposed_segments = proposed_segments[3:]
        else:
            proposed_segments = []

        current_path_for_js = ["Sites", current_root] + existing_segments
        current_js = _build_sitecore_nav_js(current_path_for_js)
        escaped_current_js = escape(current_js, quote=True)

        proposed_path_for_js = ["Redesign Sites", proposed_root] + proposed_segments
        if proposed_root == "Content Hub":
            proposed_path_for_js.pop(0)
        proposed_js = _build_sitecore_nav_js(proposed_path_for_js)
        escaped_proposed_js = escape(proposed_js, quote=True)

    except Exception:
        current_root = "Sites"
        proposed_root = "Sites"
        existing_segments = []
        proposed_segments = []
        escaped_current_js = ""
        escaped_proposed_js = ""

    return (
        current_root,
        existing_segments,
        escaped_current_js,
        proposed_root,
        proposed_segments,
        escaped_proposed_js,
    )


def _build_source_info_html(urls, domain, row, page_data):
    """Build the source information section."""
    meta_description = page_data.get("meta_description", "")
    meta_robots = page_data.get("meta_robots", "")

    url_links = "<br>".join(
        f"<a href=\"{u}\" onclick=\"window.open(this.href, '_blank', 'noopener,noreferrer,width=1200,height=1200'); return false;\">{u}</a>"
        for u in urls
    )

    url_label = "URLs" if len(urls) > 1 else "URL"

    html = f"""
        <div class="source-info">
            <h3>📍 Source Information</h3>
            <p><strong>{url_label}:</strong> {url_links}</p>
            <p><strong>DSM Location:</strong> {domain} {row}</p>
    """

    if meta_description:
        from html import escape

        escaped_meta = escape(meta_description)
        if len(escaped_meta) > 200:
            escaped_meta = escaped_meta[:200] + "..."
        html += f"""
            <p><strong>Meta Description:</strong>
                <button id="copy-meta-btn" onclick="copyMetaDescription(event)" class="copy-btn" style="display: inline-flex;" title="Copy meta description (F1)">📋</button>
                <span id="meta-desc-text">{escaped_meta}</span>
            </p>"""
    else:
        html += """
            <p><strong>Meta Description:</strong> <em>Not available</em></p>"""

    robots_content = meta_robots.lower()
    noindex_style = (
        "color: red; font-weight: bold;" if "noindex" in robots_content else ""
    )
    nofollow_style = (
        "color: red; font-weight: bold;" if "nofollow" in robots_content else ""
    )
    html += f"""
            <p><span style="{noindex_style}">noindex</span>, <span style="{nofollow_style}">nofollow</span></p>
        </div>
    """

    return html


def _build_taxonomy_html(taxonomy):
    """Build the taxonomy section if data is available."""
    if not taxonomy:
        return ""

    return f"""
        <div class=\"taxonomy\">
            <h3>🔬 Taxonomy</h3>
            <ul>
                {''.join(f'<li>{escape(t.strip())}</li>' for t in taxonomy.split(','))}
            </ul>
        </div>
    """


def _build_hierarchy_html(
    current_root,
    existing_segments,
    escaped_current_js,
    proposed_root,
    proposed_segments,
    escaped_proposed_js,
):
    """Build the HTML for current and proposed hierarchy sections."""
    html = f"""
        <div class="hierarchy-info">
            <h3>🏗️ Directory Structure</h3>
            <div class="hierarchy-comparison">
                <div class="existing-hierarchy">
                    <h4>
                        Current Structure
                        <button class="copy-btn" onclick="copyToClipboard(event, `{escaped_current_js}`)" title="Copy Sitecore navigation JS">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg>
                        </button>
                    </h4>
                    <div class="hierarchy-tree">
                        🏠 {current_root}<br>
    """

    for i, segment in enumerate(existing_segments):
        indent = "   " * (i + 1)
        html += f"{indent}|-- {segment}<br>"

    html += f"""
                    </div>
                </div>
                <div class="proposed-hierarchy">
                    <h4>
                        Proposed Structure
                        <button id="copy-proposed-btn" class="copy-btn" onclick="copyToClipboard(event, `{escaped_proposed_js}`)" title="Copy Sitecore navigation JS (F2)">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg>
                        </button>
                    </h4>
                    <div class="hierarchy-tree">
    """

    if proposed_segments:
        html += f"                        🏠 {proposed_root}<br>"
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
    """

    return html


def _collect_page_items(page_data):
    """Collect all links, PDFs and embeds from page data."""
    items = []
    for link in page_data.get("links", []):
        items.append(("link", link))
    for link in page_data.get("sidebar_links", []):
        items.append(("sidebar_link", link))
    for pdf in page_data.get("pdfs", []):
        items.append(("pdf", pdf))
    for pdf in page_data.get("sidebar_pdfs", []):
        items.append(("sidebar_pdf", pdf))
    for embed in page_data.get("embeds", []):
        items.append(("embed", embed))
    for embed in page_data.get("sidebar_embeds", []):
        items.append(("sidebar_embed", embed))
    return items


def _truncate_url_display(url: str, max_length: int = 80) -> str:
    """Return a shortened representation of a URL for display."""
    if len(url) <= max_length:
        return escape(url)

    half = (max_length - 3) // 2
    return escape(url[:half] + "..." + url[-half:])


def _build_link_item_html(item_type, item, state):
    """Build the HTML for a single link/resource entry."""
    if item_type in {"embed", "sidebar_embed"}:
        title, src = item
        debug_print(f"Processing embed: {title} ({src})")
        escaped_title = escape(title)
        escaped_src = escape(src, quote=True)
        attr_safe_src = escape(src, quote=True).replace("'", "&#39;")
        attr_safe_title = escape(title, quote=True).replace("'", "&#39;")
        url_display = _truncate_url_display(src)
        return f"""
                <div class="link-item">
                    <div class="link-main">
                        🎬 <a href="{escaped_src}" target="_blank">{escaped_title}</a>
                        <button class="copy-btn" onclick="copyEmbedToClipboard(event, '{attr_safe_src}', '{attr_safe_title}')" title="Copy embed HTML">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/>
                            </svg>
                        </button>
                        <span class="item-type type-{item_type.replace('_', ' ')}">[{item_type.replace('_', ' ')}]</span>
                    </div>
                    <div class="link-url">{url_display}</div>
                </div>
            """

    text, href, status = item
    debug_print(f"Processing item: {item_type} - {text} ({href}) with status {status}")
    try:
        status = int(status)
    except (ValueError, TypeError):
        debug_print(f"Invalid status code for {href}: {status} <-- status rec'd")
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

    is_contact_link = href.startswith(("tel:", "mailto:"))
    is_pdf_link = href.lower().endswith(".pdf")

    from urllib.parse import urlparse
    from constants import DOMAIN_MAPPING

    parsed = urlparse(href)
    href_hostname = parsed.hostname
    scheme = parsed.scheme
    internal_domains = set(DOMAIN_MAPPING.keys())
    is_internal_page = (
        not is_contact_link
        and not is_pdf_link
        and (scheme in ("http", "https") or not scheme)
        and (not href_hostname or href_hostname in internal_domains)
    )
    internal_hierarchy = ""
    if is_internal_page:
        try:
            from data.dsm import lookup_link_in_dsm

            lookup_result = lookup_link_in_dsm(href, state.excel_data, state)
            hierarchy = (
                lookup_result.get("proposed_hierarchy", {}) if lookup_result else {}
            )
            segments = hierarchy.get("segments", [])
            root_name = hierarchy.get("root", "Sites")
            internal_hierarchy = f"<div class='internal-hierarchy'>   → {root_name}"
            for segment in segments:
                internal_hierarchy += f" / {segment}"
            internal_hierarchy += "</div>"
        except Exception:
            internal_hierarchy = "<div class='internal-hierarchy'>   → Sites</div>"

    anchor_copy_button = ""
    link_kind = "contact" if is_contact_link else "pdf"
    if is_contact_link or is_pdf_link:
        anchor_copy_button = f"""
                        <button class="copy-anchor-btn {link_kind}" onclick="copyAnchorToClipboard(event, '{copy_value}', '{text}', '{link_kind}')" title="Copy as HTML anchor">
                            &lt;/&gt;
                        </button>"""

    url_display = _truncate_url_display(href)
    return f"""
                <div class="link-item">
                    <div class="link-main">
                        {circle} <a href="{href}" target="_blank">{text}</a>
                        <button class="copy-btn" onclick="copyToClipboard(event, '{copy_value}')" title="Copy URL">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/>
                            </svg>
                        </button>{anchor_copy_button}
                        <span class="item-type type-{item_type.replace('_', ' ')}">[{item_type.replace('_', ' ')}]</span>
                    </div>
                    {internal_hierarchy}
                    <div class="link-url">{url_display}</div>
                </div>
            """


def _build_links_summary_html(items, state):
    """Build the links/resources summary section."""
    html = '<div class="links-summary"><h3>🔗 Found Links & Resources</h3>'
    if not items:
        html += "<p><em>No links or resources found.</em></p></div>"
        return html

    html += '<div class="links-list">'
    for item_type, item in items:
        html += _build_link_item_html(item_type, item, state)
    html += "</div></div>"
    return html


def _generate_consolidated_section(state):
    """Generate the consolidated section with enhanced link display."""
    urls = state.get_variable("EXISTING_URLS") or []
    url = urls[0] if urls else state.get_variable("URL")
    domain = state.get_variable("DOMAIN")
    row = state.get_variable("ROW")

    if not state.current_page_data:
        return "<p>No page data available.</p>"

    (
        current_root,
        existing_segments,
        escaped_current_js,
        proposed_root,
        proposed_segments,
        escaped_proposed_js,
    ) = _extract_sitecore_paths(state)

    source_html = _build_source_info_html(
        urls or [url], domain, row, state.current_page_data
    )
    taxonomy = state.get_variable("TAXONOMY")
    taxonomy_html = _build_taxonomy_html(taxonomy)
    hierarchy_html = _build_hierarchy_html(
        current_root,
        existing_segments,
        escaped_current_js,
        proposed_root,
        proposed_segments,
        escaped_proposed_js,
    )
    items = _collect_page_items(state.current_page_data)
    links_html = _build_links_summary_html(items, state)

    html = f"""
    <div class="consolidated-section">
        <div style="display: flex; gap: 20px;">
            {source_html}
            {taxonomy_html}
        </div>
        {hierarchy_html}
        {links_html}
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


def _format_display_url(url: str, max_length: int = 60) -> str:
    """Format a URL for display, truncating the middle if it is too long."""
    from html import escape

    escaped = escape(url)
    if len(escaped) <= max_length:
        return escaped
    half = (max_length - 3) // 2
    return f"{escaped[:half]}...{escaped[-half:]}"


def _get_report_template_dir():
    template_dir = Path("templates/report")
    template_dir.mkdir(exist_ok=True)
    return template_dir


def _generate_html_report(
    domain,
    row,
    show_page_output,
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


SITECORE_NAV_JS_TEMPLATE = """(async () => {{
  myDebug = 3;
  myDebugLevels = {{
    DEBUG: 1,
    INFO: 2,
    WARN: 3,
  }};
  const path = {path_array};
  if (path.length === 0) {{
    console.error('empty path');
    return;
  }}
  const sanitizeName = (name) =>
    name.toLowerCase().replace(/[-_]/g, ' ').trim();
  if (path.some((name) => !name || typeof name !== 'string')) {{
    console.error('invalid path', path);
    return;
  }}
  const finalName = path[path.length - 1];
  const expandNames = path.slice(0, -1);
  const findNode = (name, searchRoot = document) =>
    Array.from(searchRoot.querySelectorAll('.scContentTreeNode')).find(
      (node) => {{
        const target = sanitizeName(name);
        const span = node.querySelector('span');
        if (!span) {{
          console.warn('no span for', name);
          return false;
        }}
        if (myDebug < myDebugLevels.INFO) {{
          console.log('span', span, 'textContent', span.textContent);
          console.log(
            'SANITIZED span.textContent:',
            sanitizeName(span.textContent),
            'target:',
            target
          );
          console.log(
            'checking "sanitizeName(span.textContent) === target":',
            sanitizeName(span.textContent),
            '===',
            target
          );
        }}
        return span && sanitizeName(span.textContent) === target;
      }}
    );
  function waitForMatch(name, searchRoot = document, timeout = 5000) {{
    return new Promise((resolve, reject) => {{
      const start = Date.now();
      (function check() {{
        const m = findNode(name, searchRoot);
        if (m) return resolve(m);
        if (Date.now() - start > timeout)
          return reject(new Error('Timeout waiting for ' + name));
        setTimeout(check, 1000);
      }})();
    }});
  }}
  async function expand(name, searchRoot = document) {{
    const node = await waitForMatch(name, searchRoot);
    const arrow = node.querySelector('img');
    if (!arrow) {{
      console.warn('no expand arrow for', name);
      return node; // Return the node even if no arrow
    }}
    if (myDebug < myDebugLevels.WARN) {{
      console.log('expanding', name, 'found node:', node, 'with arrow:', arrow);
    }}
    if (node.lastElementChild.tagName === 'DIV') {{
      // If the last child is a DIV, it means it's already expanded
      console.log('already expanded', name);
      return node;
    }}
    arrow.click();
    await new Promise((r) => setTimeout(r, 200));
    return node;
  }}
  async function clickNode(name, searchRoot = document) {{
    const node = await waitForMatch(name, searchRoot);
    const span = node.querySelector('span');
    if (span) {{
      span.click();
    }} else {{
      console.warn('no span to click for final node', name);
    }}
  }}
  try {{
    let currentSearchRoot = document;
    for (const name of expandNames) {{
      const expandedNode = await expand(name, currentSearchRoot);
      // Update the search root to be the expanded node's subtree
      currentSearchRoot = expandedNode;
    }}
    await clickNode(finalName, currentSearchRoot);
  }} catch (e) {{
    console.error(e);
  }}
}})();"""
