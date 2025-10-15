(async function labelMyCards(domain, rows, name) {
  // Build the list of targets: either by provided rows/domain, or all .taskCard elements
  const targets = [];

  if (domain && Array.isArray(rows) && rows.length) {
    // Match specific rows for a domain
    for (const row of rows) {
      const matcher = new RegExp(`${domain}\\D{1,4}${row}`);
      const card = Array.from(document.querySelectorAll('.taskCard'))
        .find(c => matcher.test(c.textContent));
      if (!card) {
        console.warn(`No card found for ${domain}…${row}`);
        continue;
      }
      targets.push({ card, labelKey: `${domain}…${row}` });
    }
  } else {
    // Fallback: process every .taskCard on the page
    document.querySelectorAll('.taskCard').forEach(card => {
      const linkText = card.querySelector('a')?.textContent.trim();
      const labelKey = linkText || card.textContent.trim().slice(0, 30);
      targets.push({ card, labelKey });
    });
  }

  for (const { card, labelKey } of targets) {
    // Open the card
    card.click();

    // Wait for the label picker to appear
    const picker = await new Promise(resolve => {
      const obs = new MutationObserver((_, o) => {
        const el = document.querySelector('.labelPickerWrapper');
        if (el) {
          o.disconnect();
          resolve(el);
        }
      });
      obs.observe(document.body, { childList: true, subtree: true });
    });

    const input = picker.querySelector('input');
    if (!input) {
      console.warn(`No input found in label picker for ${labelKey}`);
      continue;
    }

    // Trigger suggestions
    await new Promise(r => setTimeout(r, 200));
    input.click();
    await new Promise(r => setTimeout(r, 200));

    const suggestionsContainer = document.querySelector('.labelPickerSuggestionsDropdown');
    if (!suggestionsContainer) {
      console.warn(`No suggestions container found for ${labelKey}`);
      continue;
    }

    const suggestions = Array.from(suggestionsContainer.querySelectorAll('.editableLabel'));
    const suggestion = suggestions.find(s => s.textContent?.toLowerCase().trim() === name);

    // Give UI time to render
    await new Promise(r => setTimeout(r, 200));
    if (suggestion) suggestion.click();
    await new Promise(r => setTimeout(r, 200));

    // Close the dialog
    document.querySelector('button.ms-Dialog-button--close')?.click();
    await new Promise(r => setTimeout(r, 200));

    // // User prompt to continue or quit
    // const userInput = prompt(
    //   `Added label "${name}" to ${labelKey}. Type 'quit' or 'q' to stop, or press OK to continue.`
    // );
    // if (userInput?.toLowerCase().match(/^q(u(it)?)?$/)) {
    //   console.log('User stopped the assignment process.');
    //   break;
    // }

    // Ensure any open popups are closed
    document.querySelector('.assignmentPicker .close')?.click();
  }
})(
  // Call signature: pass domain (string) and rows (array of numbers),
  // or omit/empty both to process all .taskCard elements.
  '',
  [],        // empty => fallback to every .taskCard
  'batch'    // label to apply
);