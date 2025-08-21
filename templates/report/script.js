document.addEventListener('keydown', function (e) {
  if (e.key === 'F1') {
    e.preventDefault();
    const metaBtn = document.getElementById('copy-meta-btn');
    if (metaBtn) {
      metaBtn.click();
      showToast('Meta description copied to clipboard!');
    }
  } else if (e.key === 'F2') {
    e.preventDefault();
    const proposedBtn = document.getElementById('copy-proposed-btn');
    if (proposedBtn) {
      proposedBtn.click();
      showToast('Proposed structure JS copied to clipboard!');
    }
  }
});

function showToast(message) {
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  document.body.appendChild(toast);

  // Animate in
  setTimeout(() => {
    toast.classList.add('show');
  }, 10);

  // Animate out and remove
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => {
      document.body.removeChild(toast);
    }, 500);
  }, 3000);
}

function copyToClipboard(e, text) {
  navigator.clipboard
    .writeText(text)
    .then(function () {
      e.target.closest('.copy-btn').style.background = 'mediumseagreen';

      setTimeout(() => {
        e.target.closest('.copy-btn').style.background = 'cornflowerblue';
      }, 1000);
    })
    .catch(function (err) {
      console.error('Could not copy text: ', err);
      alert('Copy failed. Text: ' + text);
    });
}

function copyAnchorToClipboard(e, copyValue, text, linkKind) {
  /*
  linkKind: "contact" | "pdf"
  */
  let anchorHtml = '';
  let bgColor = '';

  if (linkKind === 'contact') {
    anchorHtml = `<a href="${copyValue}">${text}</a>`;
    bgColor = 'mediumseagreen';
  } else if (linkKind === 'pdf') {
    anchorHtml = `<a href="${copyValue}" target="_blank" title="${text}. PDF format, opens in new window.">${text}</a>`;
    // set bg color to a deep, pale red
    bgColor = '#830202ff';
  }

  navigator.clipboard
    .writeText(anchorHtml)
    .then(function () {
      e.target.closest('.copy-anchor-btn').style.filter = 'brightness(1.2)';

      setTimeout(() => {
        e.target.closest('.copy-anchor-btn').style.filter = 'brightness(1)';
      }, 1000);
    })
    .catch(function (err) {
      console.error('Could not copy anchor HTML: ', err);
      alert('Copy failed. HTML: ' + anchorHtml);
    });
}

function copyMetaDescription(e) {
  const metaDescElement = document.getElementById('meta-desc-text');
  if (metaDescElement) {
    const metaDesc = metaDescElement.textContent;

    navigator.clipboard
      .writeText(metaDesc)
      .then(function () {
        const button = e.target;
        const originalText = button.textContent;
        button.textContent = '✅';
        button.style.background = 'mediumseagreen';

        setTimeout(() => {
          button.textContent = originalText;
          button.style.background = '';
        }, 1000);
      })
      .catch(function (err) {
        console.error('Could not copy meta description: ', err);
        alert('Copy failed. Text: ' + metaDesc);
      });
  }
}

function copyEmbedToClipboard(e, src, title) {
  const match = src.match(/player\.vimeo\.com\/video\/(\d+)/);
  const id = match ? match[1] : '';
  const snippet = `<iframe src="https://player.vimeo.com/video/${id}?badge=0&autopause=0&player_id=0&app_id=58479&texttrack=en" frameborder="0" allow="autoplay; fullscreen; picture-in-picture; clipboard-write; encrypted-media; web-share" style="position:absolute;top:0;left:0;width:100%;height:100%;" title="${title}"></iframe>`;
  navigator.clipboard
    .writeText(snippet)
    .then(function () {
      e.target.closest('.copy-btn').style.background = 'mediumseagreen';
      setTimeout(() => {
        e.target.closest('.copy-btn').style.background = 'cornflowerblue';
      }, 1000);
    })
    .catch(function (err) {
      console.error('Could not copy embed HTML: ', err);
      alert('Copy failed. HTML: ' + snippet);
    });
}
