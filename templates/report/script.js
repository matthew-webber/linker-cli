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
