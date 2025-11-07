// /github.js
import { fetchJSON } from './global.js';

const GITHUB_USER = 'caidongting0823'; // <-- put YOUR GitHub username here
const ENDPOINT = `https://api.github.com/users/${GITHUB_USER}/repos?sort=updated&per_page=6`;

const grid = document.querySelector('.github-grid');
if (!grid) {
  console.warn('Missing .github-grid container on Home page');
}

function formatDate(iso) {
  try {
    return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(iso));
  } catch {
    return iso?.slice(0, 10) ?? '';
  }
}

function renderRepos(repos = []) {
  grid.innerHTML = '';
  if (repos.length === 0) {
    grid.innerHTML = '<p>No repositories found.</p>';
    return;
  }

  for (const r of repos) {
    const card = document.createElement('article');
    card.className = 'repo-card';
    const name = r?.name ?? 'untitled';
    const desc = r?.description ?? 'No description';
    const url  = r?.html_url ?? '#';
    const star = r?.stargazers_count ?? 0;
    const lang = r?.language ?? '';
    const upd  = formatDate(r?.updated_at);

    card.innerHTML = `
      <h3><a href="${url}" target="_blank" rel="noopener noreferrer">${name}</a></h3>
      <p>${desc || 'No description'}</p>
      <ul class="repo-meta">
        <li>${lang || '—'}</li>
        <li>★ ${star}</li>
        <li>Updated ${upd}</li>
      </ul>
    `;
    grid.appendChild(card);
  }
}

async function loadRepos() {
  try {
    // GitHub suggests this Accept header
    const res = await fetch(ENDPOINT, {
      headers: { Accept: 'application/vnd.github+json' },
    });

    if (!res.ok) {
      // 403 often = rate limited; 404 = bad username
      const msg = `GitHub API error: ${res.status} ${res.statusText}`;
      console.error(msg);
      grid.innerHTML = `<p class="error">${msg}. Check your username or try again later.</p>`;
      return;
    }

    let repos = await res.json();

    // Optional: filter out forks/archived to keep it clean
    repos = repos.filter(r => !r.fork && !r.archived);

    // Ensure sort by updated desc (API already does this, but just in case)
    repos.sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));

    // Take top 6
    renderRepos(repos.slice(0, 6));
  } catch (err) {
    console.error(err);
    grid.innerHTML = `<p class="error">Failed to load GitHub repos. ${String(err)}</p>`;
  }
}

if (grid) loadRepos();
