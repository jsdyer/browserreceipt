import {normalizeConnection} from '../model.mjs';

const button = document.querySelector('#check');
const status = document.querySelector('#status');
const results = document.querySelector('#result');
button.addEventListener('click', async () => {
  button.disabled = true;
  results.replaceChildren();
  results.hidden = true;
  status.textContent = 'Checking this connection…';
  try {
    const response = await fetch('https://coolcode-visitor-api.jeffdyer.workers.dev/api/browserreceipt/connection', {
      credentials: 'omit', cache: 'no-store', referrerPolicy: 'no-referrer', signal: AbortSignal.timeout(10000)
    });
    if (!response.ok) throw new Error('The connection check is unavailable. Try again shortly.');
    const fields = normalizeConnection(await response.json());
    for (const [label, value] of Object.entries(fields)) {
      const name = document.createElement('dt'), detail = document.createElement('dd');
      name.textContent = label.replace('Connection · ', '');
      detail.textContent = value ?? 'Unavailable';
      results.append(name,detail);
    }
    results.hidden = false;
    status.textContent = 'Checked at ' + new Date().toLocaleTimeString() + '.';
  } catch (error) {
    status.textContent = error.name === 'TimeoutError' ? 'The connection check timed out. Try again.' : error.message;
  } finally { button.disabled = false; }
});
