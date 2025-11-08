// meta/index.js
import * as d3 from 'https://cdn.jsdelivr.net/npm/d3@7.9.0/+esm';

// ---- Step 1.1: Read & type-convert the CSV (lab spec) ----
async function loadData() {
  const data = await d3.csv('./loc.csv', (row) => ({
    ...row,
    line:   +row.line,
    depth:  +row.depth,
    length: +row.length,
    date:     new Date(row.date + 'T00:00' + row.timezone),
    datetime: new Date(row.datetime),
  }));
  return data;
}

// ---- Step 1.2: Compute commit-level data (group by commit) ----
function processCommits(data) {
  return d3.groups(data, d => d.commit).map(([commit, lines]) => {
    const first = lines[0];
    const { author, date, time, timezone, datetime } = first;

    const ret = {
      id: commit,
      // TODO: replace with your GitHub repo path if you want clickable links
      url: 'https://github.com/USER/REPO/commit/' + commit,
      author, date, time, timezone, datetime,
      hourFrac: datetime.getHours() + datetime.getMinutes() / 60,
      totalLines: lines.length,
    };

    // keep raw lines but don't clutter console prints
    Object.defineProperty(ret, 'lines', {
      value: lines,
      enumerable: false,
      writable: false,
      configurable: false,
    });

    return ret;
  });
}

// ---- Step 1.3: Render <dl class="stats"> with several stats ----
function renderCommitInfo(data, commits) {
  const dl = d3.select('#stats').append('dl').attr('class', 'stats');

  // Small helpers for nice formatting + class for numeric values
  const fmtInt = d3.format(',');
  const fmt1   = d3.format('.1f');
  const add = (label, value, isNumber = false) => {
    dl.append('dt').html(label);
    dl.append('dd')
      .attr('class', isNumber ? 'num' : null)
      .text(value);
  };

  // --- required ---
  add('Total <abbr title="Lines of code">LOC</abbr>', fmtInt(data.length), true);
  add('Total commits', fmtInt(commits.length), true);

  // --- pick any 3–4 more ---
  const fileCount = d3.groups(data, d => d.file).length;
  add('Distinct files', fmtInt(fileCount), true);

  const maxDepth = d3.max(data, d => d.depth) ?? 0;
  add('Max depth', fmtInt(maxDepth), true);

  const avgLen = d3.mean(data, d => d.length) ?? 0;
  add('Avg line length', fmt1(avgLen), true);

  const workByPeriod = d3.rollups(
    data,
    v => v.length,
    d => new Date(d.datetime).toLocaleString('en', { dayPeriod: 'long' }) // “in the morning”, etc.
  );
  const maxPeriod = d3.greatest(workByPeriod, d => d[1])?.[0] ?? '—';
  add('Peak time of day', maxPeriod, false);
}


function renderScatterPlot(data, commits) {
  const width = 1000, height = 600;
  const svg = d3.select('#chart')
    .append('svg')
    .attr('viewBox', `0 0 ${width} ${height}`)
    .style('overflow', 'visible');

  // Scales
  const xScale = d3.scaleTime()
    .domain(d3.extent(commits, d => d.datetime))
    .range([0, width])
    .nice();
  const yScale = d3.scaleLinear().domain([0, 24]).range([height, 0]);

  // Margins
  const margin = { top: 10, right: 10, bottom: 30, left: 36 };
  const usable = {
    left: margin.left,
    top: margin.top,
    right: width - margin.right,
    bottom: height - margin.bottom,
    width: width - margin.left - margin.right,
    height: height - margin.top - margin.bottom,
  };
  xScale.range([usable.left, usable.right]);
  yScale.range([usable.bottom, usable.top]);

  // Gridlines (behind everything)
  svg.append('g')
    .attr('class', 'gridlines')
    .attr('transform', `translate(${usable.left},0)`)
    .call(d3.axisLeft(yScale).tickFormat('').tickSize(-usable.width));

  // ✅ Re-add the dots layer
  const dots = svg.append('g').attr('class', 'dots');

  // Radius scale (area ∝ lines)
  const [minLines, maxLines] = d3.extent(commits, d => d.totalLines || 0);
  const rScale = d3.scaleSqrt()
    .domain([minLines ?? 0, Math.max(1, maxLines ?? 1)])
    .range([3, 22]);

  // Sort so small dots are drawn last (on top)
  const sortedCommits = d3.sort(
    commits,
    (a, b) => d3.descending(a.totalLines, b.totalLines)
  );

  // Dots
  dots.selectAll('circle')
    .data(sortedCommits)
    .join('circle')
    .attr('cx', d => xScale(d.datetime))
    .attr('cy', d => yScale(d.hourFrac))
    .attr('r',  d => rScale(d.totalLines))
    .attr('fill', 'steelblue')
    .style('fill-opacity', 0.7)
    .on('mouseenter', (event, commit) => {
      d3.select(event.currentTarget).style('fill-opacity', 1);
      renderTooltipContent(commit);
      updateTooltipVisibility(true);
      updateTooltipPosition(event);
    })
    .on('mousemove', (event) => updateTooltipPosition(event))
    .on('mouseleave', (event) => {
      d3.select(event.currentTarget).style('fill-opacity', 0.7);
      updateTooltipVisibility(false);
    });

  // Axes
  const xAxis = d3.axisBottom(xScale);
  const yAxis = d3.axisLeft(yScale)
    .tickFormat(d => String(d % 24).padStart(2, '0') + ':00');

  svg.append('g')
    .attr('class', 'x-axis')
    .attr('transform', `translate(0,${usable.bottom})`)
    .call(xAxis);

  svg.append('g')
    .attr('class', 'y-axis')
    .attr('transform', `translate(${usable.left},0)`)
    .call(yAxis);
}

function renderTooltipContent(commit){
  const link  = document.getElementById('commit-link');
  const date  = document.getElementById('commit-date');
  const time  = document.getElementById('commit-time');
  const author= document.getElementById('commit-author');
  const lines = document.getElementById('commit-lines');

  if(!commit || !commit.datetime) return;

  link.href = commit.url || '#';
  link.textContent = (commit.id || '').slice(0, 7);

  date.textContent = commit.datetime.toLocaleDateString('en', { dateStyle:'full' });
  time.textContent = commit.datetime.toLocaleTimeString('en', { hour:'2-digit', minute:'2-digit' });
  author.textContent = commit.author ?? '—';
  lines.textContent  = commit.totalLines ?? (commit.lines ? commit.lines.length : 0);
}

function updateTooltipVisibility(isVisible){
  const tt = document.getElementById('commit-tooltip');
  tt.hidden = !isVisible;
}

function updateTooltipPosition(event){
  const tt = document.getElementById('commit-tooltip');
  const pad = 12; // offset from cursor
  tt.style.left = `${event.clientX + pad}px`;
  tt.style.top  = `${event.clientY + pad}px`;
}


// ---- Init wrapper (avoids top-level await) ----
async function init() {
  try {
    const data = await loadData();                 // Step 1.1 :contentReference[oaicite:2]{index=2}
    const commits = processCommits(data);          // Step 1.2 :contentReference[oaicite:3]{index=3}
    renderCommitInfo(data, commits);               // Step 1.3 :contentReference[oaicite:4]{index=4}
    renderScatterPlot(data, commits);              // Step 2     :contentReference[oaicite:5]{index=5}

    // expose for quick debugging in console
    window.metaDebug = { data, commits };
  } catch (err) {
    console.error(err);
    const box = document.getElementById('stats');
    box.innerHTML = `<p style="color:#c00">Failed to load meta/loc.csv. Check the path and see console for details.</p>`;
  }
}

// make sure DOM exists, then run
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init, { once: true });
} else {
  init();
}
