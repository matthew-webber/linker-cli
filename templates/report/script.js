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
