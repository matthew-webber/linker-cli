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

function copyAnchorToClipboard(e, copyValue, text) {
  // Create the anchor HTML
  const anchorHtml = `<a href="${copyValue}">${text}</a>`;
  navigator.clipboard
    .writeText(anchorHtml)
    .then(function () {
      e.target.closest('.copy-anchor-btn').style.background = 'mediumseagreen';

      setTimeout(() => {
        e.target.closest('.copy-anchor-btn').style.background = '#e67e22';
      }, 1000);
    })
    .catch(function (err) {
      console.error('Could not copy anchor HTML: ', err);
      alert('Copy failed. HTML: ' + anchorHtml);
    });
}
