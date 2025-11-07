// /projects/projects.js — consolidated Steps 1–5

import { fetchJSON, renderProjects } from '../global.js';
import * as d3 from 'https://cdn.jsdelivr.net/npm/d3@7.9.0/+esm';

// --- Load data + render cards (Lab 04 carryover)
const projects = await fetchJSON('./projects.json');          // same folder
const container = document.querySelector('.projects');
renderProjects(projects, container, 'h2');

const titleEl = document.querySelector('.projects-title');
if (titleEl) titleEl.textContent = `Projects (${projects.length})`;

// --- D3 scaffolding (pie + legend roots)
const svg = d3.select('#projects-pie-plot');
const legend = d3.select('.legend');

const colors = d3.scaleOrdinal(d3.schemeTableau10);
const arcGenerator = d3.arc().innerRadius(0).outerRadius(50);
const sliceGenerator = d3.pie().value(d => d.value);

// --- State for Step 5
let query = '';
let selectedYear = null;  // string or null
let hoverYear = null;

const searchInput = document.querySelector('.searchBar');
const hintEl = document.querySelector('.search-hint');

// Helpers for filtering/search
function applyFilters() {
  const q = (query || '').toLowerCase();
  let list = projects.filter(p =>
    Object.values(p).join('\n').toLowerCase().includes(q)
  );
  if (selectedYear) list = list.filter(p => String(p.year) === selectedYear);
  return list;
}
function updateHint(list) {
  if (selectedYear && query) {
    hintEl.textContent = `Showing ${list.length} project(s) in ${selectedYear} matching “${query}”`;
  } else if (selectedYear) {
    hintEl.textContent = `Showing ${list.length} project(s) in ${selectedYear}`;
  } else if (query) {
    hintEl.textContent = `Showing ${list.length} matching project(s)`;
  } else {
    hintEl.textContent = '';
  }
}
function toggleYear(label) {
  selectedYear = (selectedYear === label ? null : label);
  renderFromState();
}
function updateHover() {
  const haveHover = !!hoverYear;
  svg.selectAll('path.slice')
    .classed('hover', d => haveHover && d.data.label === hoverYear)
    .classed('muted', d => haveHover && d.data.label !== hoverYear);
  legend.selectAll('li')
    .classed('hover', d => haveHover && d.label === hoverYear)
    .classed('muted', d => haveHover && d.label !== hoverYear);
}

// --- Single draw function (interactive)
function drawPieFrom(projectsArr) {
  const rolled = d3.rollups(projectsArr, v => v.length, d => d.year)
                   .sort((a, b) => d3.ascending(+a[0], +b[0]));
  const data = rolled.map(([year, count]) => ({ label: String(year), value: count }));
  const arcs = sliceGenerator(data);

  // slices
  svg.selectAll('path.slice')
    .data(arcs, d => d.data.label)
    .join(
      enter => enter.append('path')
        .attr('class', 'slice')
        .attr('d', arcGenerator)
        .attr('fill', (d, i) => colors(i))
        .on('mouseenter', (_, d) => { hoverYear = d.data.label; updateHover(); })
        .on('mouseleave', () => { hoverYear = null; updateHover(); })
        .on('click', (_, d) => toggleYear(d.data.label)),
      update => update,
      exit => exit.remove()
    )
    .attr('fill', (d, i) => colors(i))
    .attr('d', arcGenerator)
    .classed('active', d => d.data.label === selectedYear);

  // legend
  legend.selectAll('li')
    .data(data, d => d.label)
    .join(
      enter => enter.append('li')
        .attr('style', (_, i) => `--color:${colors(i)}`)
        .attr('tabindex', '0')
        .attr('role', 'button')
        .html(d => `<span class="swatch"></span> ${d.label} <em>(${d.value})</em>`)
        .on('mouseenter', (_, d) => { hoverYear = d.label; updateHover(); })
        .on('mouseleave', () => { hoverYear = null; updateHover(); })
        .on('click', (_, d) => toggleYear(d.label))
        .on('keydown', (e, d) => {
          if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleYear(d.label); }
        }),
      update => update.html(d => `<span class="swatch"></span> ${d.label} <em>(${d.value})</em>`),
      exit => exit.remove()
    )
    .classed('active', d => d.label === selectedYear);

  updateHover();
}

// Central render
function renderFromState() {
  const list = applyFilters();
  renderProjects(list, container, 'h2');
  drawPieFrom(list);
  updateHint(list);
}

// Search wiring
if (searchInput) {
  searchInput.addEventListener('input', (e) => {
    query = (e.target.value || '').trim();
    renderFromState();
  });
}

// Initial render
renderFromState();
