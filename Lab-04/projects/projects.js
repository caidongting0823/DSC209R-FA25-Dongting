// /projects/projects.js
import { fetchJSON, renderProjects } from '../global.js';

const projects = await fetchJSON('./projects.json');  // same folder as this file
const container = document.querySelector('.projects');

renderProjects(projects, container, 'h2');

// Bonus for Step 1.6: update count in the page title if present
const titleEl = document.querySelector('.projects-title');
if (titleEl) titleEl.textContent = `Projects (${projects.length})`;
