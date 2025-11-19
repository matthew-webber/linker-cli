// assignToMe.js
// This script assigns tasks to a user in a task management system by finding cards based on a specific domain and row number.
// It waits for the assignment popup to appear, inputs the user's name,
// and selects the first suggestion from the assignment picker.

(async function assignToMe(domain, rows, name) {
  for (const row of rows) {
    // find the card whose text matches “domain” + 1–4 non-digits + “row”
    const matcher = new RegExp(`${domain}\\D{1,4}${row}`);
    const card = Array.from(document.querySelectorAll('.taskCard')).find((c) =>
      matcher.test(c.textContent)
    );
    if (!card) {
      console.warn(`No card found for ${domain}…${row}`);
      continue;
    }

    // open assignee popup
    const btn = card.querySelector('.plannerAssign');
    if (!btn) {
      console.warn(`No assign button in card ${domain}…${row}`);
      continue;
    }
    btn.click();

    // wait for popup input to appear
    const assignmentPicker = await new Promise((resolve) => {
      const observer = new MutationObserver((_, obs) => {
        const el = document.querySelector('.assignmentPicker');
        if (el) {
          obs.disconnect();
          resolve(el);
        }
      });
      observer.observe(document.body, { childList: true, subtree: true });
    });

    const input = assignmentPicker.querySelector('input');
    // set your name
    input.value = name;
    input.dispatchEvent(new Event('input', { bubbles: true }));

    // wait a tick for suggestions to appear
    await new Promise((r) => setTimeout(r, 500));
    // click the first suggestion (class="user")
    const suggestion = assignmentPicker.querySelector('.user button');
    await new Promise((r) => setTimeout(r, 500));
    if (!suggestion) {
      console.warn(`No suggestion found for ${name} in ${domain}…${row}`);
      continue;
    }
    suggestion.click();

    // pause with a prompt and continue unless the user enters 'quit' into the prompt
    const userInput = prompt(
      `Assigned ${domain}…${row} to ${name}. Type 'quit' to stop or press OK to continue.`
    );
    if (
      (userInput && userInput.toLowerCase() === 'q') ||
      userInput.toLowerCase() === 'quit'
    ) {
      console.log('User chose to stop the assignment process.');
      break;
    }

    // optionally close the popup if needed
    document.querySelector('.assignmentPicker .close')?.click();
  }
})(
  'CGS',
  [
115, 32, 59, 8, 114, 20, 21, 22, 30
    
  ],
  'matt'
);

