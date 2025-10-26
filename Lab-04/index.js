// /index.js
import { fetchJSON, renderProjects } from './global.js';

const all = await fetchJSON('./projects/projects.json');
const top3 = all.slice(0, 3);

const container = document.querySelector('.projects');   // container on Home page
renderProjects(top3, container, 'h2');
