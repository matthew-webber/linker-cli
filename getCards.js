(function () {
  // 1) Collect headers only inside column containers
  const h3s = Array.from(document.querySelectorAll('.columnContent h3'));
  if (!h3s.length) {
    console.error('No <h3> elements found under .columnContent.');
    return;
  }

  // 2) Let user pick a lane
  const laneList = h3s.map((h, i) => `${i + 1}: ${h.textContent.trim() || '<empty heading>'}`).join('\n');
  const raw = prompt(`Select a swim lane by number (1..${h3s.length}):\n\n${laneList}`);
  if (raw === null) { console.log('Selection cancelled.'); return; }
  const idx = parseInt(raw.trim(), 10);
  if (!Number.isInteger(idx) || idx < 1 || idx > h3s.length) {
    alert('Invalid selection — please run again and enter a valid number.');
    return;
  }

  const selectedH3 = h3s[idx - 1];

  // 3) Climb to the common ancestor for that lane
  const column = selectedH3.closest('.columnContent');
  if (!column) {
    console.error('Could not find a .columnContent ancestor for the selected header.');
    return;
  }

  // 4) Find cards within THIS column only
  let cards = Array.from(column.querySelectorAll('.taskBoardCard'));

  // Optional: if your DOM virtualizes cards (some tools do), also sweep siblings after the header inside the column
  if (!cards.length) {
    let n = selectedH3.parentElement;
    while (n && n !== column) n = n.parentElement; // ensure we’re at the column level
    if (n) {
      let sib = selectedH3.parentElement.nextElementSibling;
      while (sib && sib !== null) {
        if (sib.closest('.columnContent') !== column) break; // don’t bleed into other columns
        cards.push(...sib.querySelectorAll('.taskBoardCard'));
        sib = sib.nextElementSibling;
      }
    }
    // Deduplicate just in case
    cards = Array.from(new Set(cards));
  }

  // 5) Extract the two values per card: Title + first line of notes (e.g., "COM - 1288")
  const rows = cards.map(card => {
    let id = card.id
    // Title
    let title = '';
    const tEl = card.querySelector('.title');
    if (tEl && tEl.textContent.trim()) title = tEl.textContent.trim();
    else if (card.getAttribute('aria-label')) title = card.getAttribute('aria-label').trim();
    else title = (card.innerText || '').split('\n').map(s=>s.trim()).find(Boolean) || '';

    // Notes first line
    let notesText = '';
    const notesEl = card.querySelector('.notesPreview') || card.querySelector('.preview');
    if (notesEl && notesEl.textContent) notesText = notesEl.textContent.trim();
    else {
      // fallback: scan for something that looks like the code line
      const lines = (card.innerText || '').split(/\r?\n/).map(s => s.trim()).filter(Boolean);
      // Heuristic: often line after the title is the code line
      notesText = lines.slice(1).find(Boolean) || '';
    }
    const firstLine = (notesText.split(/\r?\n/).map(s=>s.trim()).filter(Boolean)[0] || '');

    // return `\`${id}\t${title}\t${firstLine}`;
    return `${firstLine} | ${title}`;
  });

  // 6) Output + total + clipboard
  if (rows.length) {
    rows.forEach(r => console.log(r));
  } else {
    console.warn('No .taskBoardCard elements found within the selected column.');
  }
  console.log(`Total cards: ${rows.length}`);

  if (rows.length) {
    const text = rows.join('\n');
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(text).then(
        () => console.log('Copied to clipboard.'),
        () => { try { copy(text); console.log('Copied via copy() fallback.'); } catch (e) { console.warn('Copy failed:', e); } }
      );
    } else {
      try { copy(text); console.log('Copied via copy() fallback.'); } catch (e) { console.warn('Copy failed:', e); }
    }
  }
})();