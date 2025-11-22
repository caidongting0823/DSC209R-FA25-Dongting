// /index.js
import { fetchJSON, renderProjects } from './global.js';

const all = await fetchJSON('./projects/projects.json');
const top3 = all.slice(0, 3);

const container = document.querySelector('.projects');   // container on Home page
renderProjects(top3, container, 'h2');

// ---- GitHub Profile block (Lab 04 Step 3/4/5) ----
import { fetchGitHubData } from './global.js';

// 3) Parse response in index.js: fetch user data
const githubData = await fetchGitHubData('caidongting0823');

// 4) Target the HTML element
const profileStats = document.querySelector('#profile-stats');

// 5) Update the HTML
if (profileStats && githubData) {
  profileStats.innerHTML = `
    <h2>GitHub Profile</h2>
    <dl>
      <dt>Public Repos:</dt><dd>${githubData.public_repos}</dd>
      <dt>Public Gists:</dt><dd>${githubData.public_gists}</dd>
      <dt>Followers:</dt><dd>${githubData.followers}</dd>
      <dt>Following:</dt><dd>${githubData.following}</dd>
    </dl>
  `;
}
