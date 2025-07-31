import sys
import re
import json
import subprocess
from typing import List

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE,
)


def strip_emojis(s: str) -> str:
    return EMOJI_PATTERN.sub("", s)


def parse_tree_outline(tree_str: str) -> List[str]:
    lines = [l.rstrip("\n") for l in tree_str.strip().splitlines() if l.strip()]
    if not lines:
        raise ValueError("empty outline")
    path = []
    header = lines[0].strip()
    if "proposed structure" in header.lower():
        path.append("Redesign Sites")
    else:
        path.append(strip_emojis(header).strip())
    for line in lines[1:]:
        cleaned = re.sub(r'^[\|\-\s]*', "", line)
        cleaned = strip_emojis(cleaned).strip()
        if cleaned:
            path.append(cleaned)
    return path


def build_js(path: List[str]) -> str:
    if not path:
        raise ValueError("path is empty")
    expands = path[:-1]
    final = path[-1]
    js_array = "[" + ", ".join(json.dumps(p) for p in path) + "]"
    return f"""(async () => {{
  myDebug = 5;
  myDebugLevels = {{
    DEBUG: 1,
    INFO: 2,
    WARN: 3,
  }};
  const path = {js_array}
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
          console.log('\\nspan', span, '\\ntextContent', span.textContent);
          console.log(
            '\\nSANITIZED span.textContent:',
            sanitizeName(span.textContent),
            '\\ntarget:',
            target
          );
          console.log(
            '\\nchecking "sanitizeName(span.textContent) === target":',
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
        setTimeout(check, 100);
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
    if (arrow.getAttribute('aria-expanded') === 'true') {{
      console.log('already expanded', name);
      return node;
    }}
    arrow.click();
    await new Promise((r) => setTimeout(r, 2000));
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


def copy_to_clipboard(text: str):
    platform = sys.platform
    try:
        if platform == "darwin":
            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            p.communicate(text.encode("utf-8"))
        elif platform.startswith("win"):
            p = subprocess.Popen("clip", stdin=subprocess.PIPE, shell=True)
            p.communicate(text.encode("utf-8"))
        else:
            try:
                p = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
                p.communicate(text.encode("utf-8"))
            except FileNotFoundError:
                try:
                    p = subprocess.Popen(["xsel", "--clipboard", "--input"], stdin=subprocess.PIPE)
                    p.communicate(text.encode("utf-8"))
                except FileNotFoundError:
                    raise RuntimeError("no clipboard utility found (install xclip/xsel)")
        print("JS code copied to clipboard.")
    except Exception as e:
        print(f"failed to copy to clipboard: {e}")
        print("---- fallback output below ----")
        print(text)

def read_outline() -> str:
    if not sys.stdin.isatty():
        return sys.stdin.read()
    print("Paste the outline. End with a line containing only 'EOF'.")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "EOF":
            break
        lines.append(line)
    return "\n".join(lines)


def main():
    raw = read_outline()
    if not raw.strip():
        print("no input received", file=sys.stderr)
        sys.exit(1)
    try:
        path = parse_tree_outline(raw)
    except Exception as e:
        print(f"error parsing outline: {e}", file=sys.stderr)
        sys.exit(1)
    js = build_js(path)
    copy_to_clipboard(js)