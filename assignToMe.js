// assignToMe.js
// This script assigns tasks to a user in a task management system by finding cards based on a specific domain and row number.
// It waits for the assignment popup to appear, inputs the user's name,
// and selects the first suggestion from the assignment picker.

const DEBUG = false // Set to false to disable debug logging

;(async function assignToMe(domain, rows, name) {
  const log = (...args) => DEBUG && console.log('[DEBUG]', ...args)

  const suggestionClick = (button) => {
    // log('CLICKING SUGGESTION BUTTON')
    button.click()
  }

  log(`Starting assignment process for ${rows.length} rows in domain ${domain}`)

  for (const row of rows) {
    log(`\n--- Processing ${domain}…${row} ---`)

    // find the card whose text matches "domain" + 1–4 non-digits + "row"
    const matcher = new RegExp(`${domain}\\D{1,4}${row}`)
    log(`Searching for card matching pattern: ${matcher}`)

    const card = Array.from(document.querySelectorAll('.taskCard')).find((c) =>
      matcher.test(c.textContent)
    )
    if (!card) {
      console.warn(`No card found for ${domain}…${row}`)
      continue
    }
    console.log(`Found card for ${domain}…${row}`)

    // open assignee popup
    const btn = card.querySelector('.plannerAssign')
    if (!btn) {
      console.warn(`No assign button in card ${domain}…${row}`)
      continue
    }
    log('Clicking assign button')
    await new Promise((r) => setTimeout(r, 500))

    btn.click()

    await new Promise((r) => setTimeout(r, 500))
    // wait for popup input to appear
    console.log('Waiting for assignment picker to appear...')
    const assignmentPicker = await new Promise((resolve) => {
      const observer = new MutationObserver((_, obs) => {
        const el = document.querySelector('.assignmentPicker')
        if (el) {
          obs.disconnect()
          resolve(el)
        }
      })
      observer.observe(document.body, { childList: true, subtree: true })
    })
    log('Assignment picker appeared')

    const input = assignmentPicker.querySelector('input')
    if (!input) {
      console.warn(`No input found in assignment picker for ${domain}…${row}`)
      continue
    }

    // set your name
    log(`Setting input value to: ${name}`)
    input.value = name
    input.dispatchEvent(new Event('input', { bubbles: true }))

    // wait a tick for suggestions to appear
    log('Waiting for suggestions to appear...')
    await new Promise((r) => setTimeout(r, 500))

    // click the first suggestion (class="user")
    const suggestion = assignmentPicker.querySelector('.user button')
    log('Waited 500ms for initial suggestion load')
    await new Promise((r) => setTimeout(r, 500))
    log('Waited additional 500ms')

    if (!suggestion) {
      console.warn(`No suggestion found for ${name} in ${domain}…${row}`)
      continue
    }
    log('Found suggestion button')

    // check if user is already assigned (personaActionButton class indicates they are)
    if (suggestion.classList.contains('personaActionButton')) {
      console.warn(`User is already assigned, skipping ${domain} - ${row}...`)
      log('Closing picker...')
      document.querySelector('.assignmentPicker .close')?.click()
      continue
    } else {
      log('User not already assigned, proceeding with click')
      suggestionClick(suggestion)
    }

    // pause with a prompt and continue unless the user enters 'quit' into the prompt
    // const userInput = prompt(
    //   `Assigned ${domain}…${row} to ${name}. Type 'quit' to stop or press OK to continue.`
    // )
    // if (
    //   (userInput && userInput.toLowerCase() === 'q') ||
    //   userInput.toLowerCase() === 'quit'
    // ) {
    //   console.log('User chose to stop the assignment process.')
    //   break
    // }

    //  END NEED TO COMMENT SECTION

    // optionally close the popup if needed
    log('Closing assignment picker...')
    document.querySelector('.assignmentPicker .close')?.click()
  }

  console.log('Assignment process completed'.toUpperCase())
})(
  'CON',
  [
    39, 48, 50, 71, 77, 114, 119
  ],
  'Rinder'
)
