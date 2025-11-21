const DOMAINS = [
  {
    full_name: "Enterprise",
    sitecore_domain_name: "Enterprise",
  },
  {
    full_name: "Adult Health",
    sitecore_domain_name: "Health",
  },
  {
    full_name: "Education",
    sitecore_domain_name: "Education",
  },
  {
    full_name: "Research",
    sitecore_domain_name: "Research",
  },
  {
    full_name: "Hollings Cancer",
    sitecore_domain_name: "Hollings",
  },
  {
    full_name: "Childrens Health",
    sitecore_domain_name: "Kids",
  },
  {
    full_name: "CDM",
    sitecore_domain_name: "Dental Medicine",
  },
  {
    full_name: "MUSC Giving",
    sitecore_domain_name: "Giving",
  },
  {
    full_name: "CGS",
    sitecore_domain_name: "Graduate Studies",
  },
  {
    full_name: "CHP",
    sitecore_domain_name: "Health Professions",
  },
  {
    full_name: "COM",
    sitecore_domain_name: "Medicine",
  },
  {
    full_name: "CON",
    sitecore_domain_name: "Nursing",
  },
  {
    full_name: "COP",
    sitecore_domain_name: "Pharmacy",
  },
  {
    full_name: "News Releases",
    sitecore_domain_name: "Content Hub",
    root_for_new_sitecore: "Content Hub",
  },
  {
    full_name: "Progress Notes",
    sitecore_domain_name: "Content Hub",
    root_for_new_sitecore: "Content Hub",
  },
];

const SITECORE_NAV_JS_TEMPLATE = `(async () => {
  myDebug = 3;
  myDebugLevels = {
    DEBUG: 1,
    INFO: 2,
    WARN: 3,
  };
  const path = __PATH_ARRAY__;
  if (path.length === 0) {
    console.error('empty path');
    return;
  }
  const sanitizeName = (name) =>
    name.toLowerCase().replace(/[-_]/g, ' ').trim();
  if (path.some((name) => !name || typeof name !== 'string')) {
    console.error('invalid path', path);
    return;
  }
  const finalName = path[path.length - 1];
  const expandNames = path.slice(0, -1);
  const findNode = (name, searchRoot = document) =>
    Array.from(searchRoot.querySelectorAll('.scContentTreeNode')).find(
      (node) => {
        const target = sanitizeName(name);
        const span = node.querySelector('span');
        if (!span) {
          console.warn('no span for', name);
          return false;
        }
        if (myDebug < myDebugLevels.INFO) {
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
        }
        return span && sanitizeName(span.textContent) === target;
      }
    );
  function waitForMatch(name, searchRoot = document, timeout = 5000) {
    return new Promise((resolve, reject) => {
      const start = Date.now();
      (function check() {
        const m = findNode(name, searchRoot);
        if (m) return resolve(m);
        if (Date.now() - start > timeout)
          return reject(new Error('Timeout waiting for ' + name));
        setTimeout(check, 1000);
      })();
    });
  }
  async function expand(name, searchRoot = document) {
    const node = await waitForMatch(name, searchRoot);
    const arrow = node.querySelector('img');
    if (!arrow) {
      console.warn('no expand arrow for', name);
      return node; // Return the node even if no arrow
    }
    if (myDebug < myDebugLevels.WARN) {
      console.log('expanding', name, 'found node:', node, 'with arrow:', arrow);
    }
    if (node.lastElementChild.tagName === 'DIV') {
      // If the last child is a DIV, it means it's already expanded
      console.log('already expanded', name);
      return node;
    }
    arrow.click();
    await new Promise((r) => setTimeout(r, 200));
    return node;
  }
  async function clickNode(name, searchRoot = document) {
    const node = await waitForMatch(name, searchRoot);
    const span = node.querySelector('span');
    if (span) {
      span.click();
    } else {
      console.warn('no span to click for final node', name);
    }
  }
  try {
    let currentSearchRoot = document;
    for (const name of expandNames) {
      const expandedNode = await expand(name, currentSearchRoot);
      // Update the search root to be the expanded node's subtree
      currentSearchRoot = expandedNode;
    }
    await clickNode(finalName, currentSearchRoot);
  } catch (e) {
    console.error(e);
  }
})();`;

const tldPattern = /\.(org|edu|com|gov|net)/i;

const parsePathSegments = (rawInput) => {
  if (!rawInput) return [];
  let candidate = rawInput.trim();
  if (!candidate) return [];

  if (tldPattern.test(candidate)) {
    const urlToParse = candidate.startsWith("http")
      ? candidate
      : `https://${candidate}`;
    try {
      candidate = new URL(urlToParse).pathname;
    } catch {
      // Fall through if URL parsing fails
    }
  }

  let segments = candidate
    .split("/")
    .map((seg) => seg.trim())
    .filter(Boolean);

  if (
    segments.length >= 3 &&
    segments[0].toLowerCase() === "sitecore" &&
    segments[1].toLowerCase() === "content" &&
    segments[2].toLowerCase() === "content hub"
  ) {
    segments = segments.slice(3);
  }

  return segments;
};

const buildSitecorePath = (domain, segments) => {
  const isContentHub = domain.root_for_new_sitecore === "Content Hub";
  const root = isContentHub
    ? ["Content Hub"]
    : ["Redesign Sites", domain.sitecore_domain_name];
  return [...root, ...segments];
};

const buildSitecoreNavJs = (path) =>
  SITECORE_NAV_JS_TEMPLATE.replace("__PATH_ARRAY__", JSON.stringify(path));

const renderDomains = () => {
  const container = document.getElementById("domainList");
  const toast = document.getElementById("toast");
  let firstInput = null;
  let toastTimeout = null;

  const showToast = (message) => {
    toast.textContent = message;
    toast.classList.add("show");
    clearTimeout(toastTimeout);
    toastTimeout = setTimeout(() => {
      toast.classList.remove("show");
    }, 1800);
  };

  DOMAINS.forEach((domain, index) => {
    const row = document.createElement("div");
    row.className = "domain-row";

    const header = document.createElement("div");
    header.className = "domain-header";

    const title = document.createElement("div");
    title.className = "domain-title";
    title.textContent = domain.full_name;

    const subtitle = document.createElement("div");
    subtitle.className = "domain-subtitle";
    const subtitleBits = [`Sitecore: ${domain.sitecore_domain_name}`];
    if (domain.root_for_new_sitecore === "Content Hub") {
      subtitleBits.unshift("Content Hub root");
    }
    subtitle.textContent = subtitleBits.join(" | ");

    header.appendChild(title);
    header.appendChild(subtitle);

    const inputRow = document.createElement("div");
    inputRow.className = "input-row";

    const input = document.createElement("input");
    input.type = "text";
    input.placeholder = "Paste proposed path or URL, e.g. /about/leadership";
    input.autocomplete = "off";
    input.spellcheck = false;

    const button = document.createElement("button");
    button.type = "button";
    button.textContent = "Copy";

    const status = document.createElement("div");
    status.className = "status";

    const handleStatus = (message, variant = "neutral") => {
      status.textContent = message;
      status.classList.remove("success", "error");
      if (variant === "success") status.classList.add("success");
      if (variant === "error") status.classList.add("error");
    };

    const handleCopy = async () => {
      const segments = parsePathSegments(input.value);
      const path = buildSitecorePath(domain, segments);
      const navJs = buildSitecoreNavJs(path);

      if (!navigator.clipboard) {
        handleStatus("Clipboard unavailable", "error");
        return;
      }

      try {
        await navigator.clipboard.writeText(navJs);
        const humanPath = path.join(" > ");
        handleStatus(`Copied - ${humanPath}`, "success");
        showToast(`Copied JS for ${domain.full_name}`);
      } catch (err) {
        console.error(err);
        handleStatus("Copy failed", "error");
      }
    };

    button.addEventListener("click", handleCopy);
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        handleCopy();
      }
    });

    inputRow.appendChild(input);
    inputRow.appendChild(button);

    row.appendChild(header);
    row.appendChild(inputRow);
    row.appendChild(status);

    container.appendChild(row);

    if (index === 0) {
      firstInput = input;
    }
  });

  if (firstInput) {
    setTimeout(() => firstInput.focus(), 50);
  }
};

document.addEventListener("DOMContentLoaded", renderDomains);
