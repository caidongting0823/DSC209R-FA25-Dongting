// meta/index.js
import * as d3 from 'https://cdn.jsdelivr.net/npm/d3@7.9.0/+esm';
import scrollama from 'https://cdn.jsdelivr.net/npm/scrollama@3.2.0/+esm';

let xScale, yScale; // so isCommitSelected() can access them

// Slider / evolution state (Lab 8 Step 1)
let commitProgress = 100;      // 0–100 slider value
let commitMaxTime = null;      // Date object for current slider position
let timeScale = null;          // maps datetime -> [0,100] and back
let filteredCommits = null;    // subset of commits up to commitMaxTime

// keep references so handlers outside init() can use them
let allData = null;
let allCommits = null;

// Lab 8 Step 2 – color by technology
const lineColorScale = d3.scaleOrdinal(d3.schemeTableau10);

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
  xScale = d3.scaleTime()
    .domain(d3.extent(commits, d => d.datetime))
    .range([0, width])
    .nice();

  yScale = d3.scaleLinear()
    .domain([0, 24])
    .range([height, 0]);

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
    .data(sortedCommits, d => d.id)
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

  // ---- Brush: set up & wire events
  function brushed(event){
    const selection = event.selection;

  // Flag selected dots
    d3.selectAll('.dots circle').classed('selected', d => isCommitSelected(selection, d));

  // Update panels
    renderSelectionCount(selection, commits);
    renderLanguageBreakdown(selection, commits);
  }

  // Brush confined to the chart area
    const brush = d3.brush()
      .extent([[usable.left, usable.top], [usable.right, usable.bottom]])
      .on('start brush end', brushed);

    const brushG = svg.append('g')
      .attr('class', 'brush')
      .call(brush);

// Keep dots hoverable after the overlay is inserted
svg.selectAll('.dots, .overlay ~ *').raise();

}

function updateScatterPlot(data, commits) {
  const width = 1000, height = 600;
  const margin = { top: 10, right: 10, bottom: 30, left: 36 };
  const usable = {
    left: margin.left,
    top: margin.top,
    right: width - margin.right,
    bottom: height - margin.bottom,
    width: width - margin.left - margin.right,
    height: height - margin.top - margin.bottom,
  };

  // reuse existing SVG and scales
  const svg = d3.select('#chart').select('svg');

  // update x domain to only show commits up to commitMaxTime
  xScale.domain(d3.extent(commits, d => d.datetime));

  // new radius scale for the current subset
  const [minLines, maxLines] = d3.extent(commits, d => d.totalLines || 0);
  const rScale = d3.scaleSqrt()
    .domain([minLines ?? 0, Math.max(1, maxLines ?? 1)])
    .range([3, 22]);

  // update x-axis in place
  const xAxis = d3.axisBottom(xScale);
  svg.select('g.x-axis').call(xAxis);

  // re-bind dots to the filtered commits
  const dots = svg.select('g.dots');

  const sortedCommits = d3.sort(
    commits,
    (a, b) => d3.descending(a.totalLines, b.totalLines)
  );

  dots.selectAll('circle')
    .data(sortedCommits, d => d.id)              // key by commit id (1.3)
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

function isCommitSelected(selection, commit){
  if (!selection) return false;
  const [[x0,y0],[x1,y1]] = selection;
  const minX = Math.min(x0,x1), maxX = Math.max(x0,x1);
  const minY = Math.min(y0,y1), maxY = Math.max(y0,y1);

  // Commit position in pixels
  const cx = xScale(commit.datetime);
  const cy = yScale(commit.hourFrac);

  return cx >= minX && cx <= maxX && cy >= minY && cy <= maxY;
}

function renderSelectionCount(selection, commits){
  const selected = selection
    ? commits.filter(d => isCommitSelected(selection, d))
    : [];

  const el = document.querySelector('#selection-count');
  const panel = document.querySelector('#selection-panel');

  if (!el) return selected;

  if (selected.length === 0) {
    el.textContent = 'Select commits in the chart above to view details.';
    if (panel) panel.classList.add('empty');
  } else {
    const n = selected.length;
    el.textContent = `${n} commit${n === 1 ? '' : 's'} selected`;
    if (panel) panel.classList.remove('empty');
  }

  return selected;
}


function renderLanguageBreakdown(selection, commits){
  const selected = selection
    ? commits.filter(d => isCommitSelected(selection, d))
    : [];

  const container = document.getElementById('language-breakdown');

  // Clear when nothing is selected
  if (selected.length === 0){
    container.innerHTML = '';
    return;
  }

  // Flatten the 'lines' from the selected commits
  const lines = selected.flatMap(d => d.lines);

  // Count lines by language/type
  const breakdown = d3.rollup(
    lines,
    v => v.length,
    d => d.type
  );

  // Render DL rows
  container.innerHTML = '';
  for (const [language, count] of breakdown){
    const pct = d3.format('.1~%')(count / lines.length);
    container.innerHTML += `<dt>${language}</dt><dd>${count} lines (${pct})</dd>`;
  }
}


function updateFileDisplay(filteredCommits) {
  // If #files does not exist, bail out gracefully
  const filesRoot = d3.select('#files');
  if (filesRoot.empty()) return;

  // No commits? Clear everything.
  if (!filteredCommits || filteredCommits.length === 0) {
    filesRoot.html('');
    return;
  }

  // 1) Gather all lines from the filtered commits
  const lines = filteredCommits.flatMap(d => d.lines);

  // 2) Group by file and sort by number of lines (desc)
  let files = d3
    .groups(lines, d => d.file)
    .map(([name, lines]) => ({ name, lines }))
    .sort((a, b) => b.lines.length - a.lines.length);

  // 3) Bind one <div> per file inside #files
  const filesContainer = filesRoot
    .selectAll('div')
    .data(files, d => d.name)
    .join(
      // Runs only when a new file block is created
      enter =>
        enter.append('div').call(div => {
          // <dt> with <code> and <small> for counts
          div.append('dt').html('<code></code><small></small>');
          // <dd> will hold our unit dots
          div.append('dd');
        })
    );

  // 4) Update filename + line counts
  filesContainer.select('dt > code').text(d => d.name);
  filesContainer
    .select('dt > small')
    .text(d => `${d.lines.length} lines`);

  // 5) For each file, create one dot per line → unit visualization
  const lineDots = filesContainer
    .select('dd')
    .selectAll('div')
    .data(d => d.lines)
    .join('div')
    .attr('class', 'loc')
    .style('--color', d => lineColorScale(d.type ?? 'other'));
}

function renderCommitStory(commits) {
  const story = d3.select('#scatter-story');

  const fmtDate = new Intl.DateTimeFormat('en', { dateStyle: 'medium' });
  const fmtTime = new Intl.DateTimeFormat('en', { timeStyle: 'short' });

  const steps = story
    .selectAll('.step')
    .data(commits, d => d.id)
    .join('div')
    .attr('class', 'step');

  steps.html((d, i) => {
    // For this commit, count lines by file
    const fileRollups = d3.rollups(
      d.lines,
      v => v.length,
      l => l.file
    ).sort((a, b) => d3.descending(a[1], b[1]));

    const fileCount = fileRollups.length;

    // Top 1–2 files to mention in the narrative
    const top = fileRollups.slice(0, 2);
    const topFilesMarkup = top
      .map(([name, count]) =>
        `<span class="step-file">
           <code>${name}</code>
           <span class="step-file-lines">${count} line${count === 1 ? '' : 's'}</span>
         </span>`
      )
      .join(', ');

    return `
      <p class="step-meta">
        <span class="step-index">Commit ${i + 1} of ${commits.length}</span>
        <span class="step-datetime">
          ${fmtDate.format(d.datetime)} · ${fmtTime.format(d.datetime)}
        </span>
      </p>

      <p class="step-title">
        <a href="${d.url}" target="_blank" rel="noopener">
          ${d.id.slice(0, 7)}
        </a>
      </p>

      <p class="step-body">
        Updated <strong>${d.totalLines}</strong> lines across
        <strong>${fileCount}</strong> file${fileCount === 1 ? '' : 's'}.
        ${topFilesMarkup ? `Key files: ${topFilesMarkup}.` : ''}
      </p>
    `;
  });
}


function onTimeSliderChange() {
  if (!allData || !allCommits || !timeScale) return;

  const slider = document.querySelector('#commit-progress');
  const timeEl = document.querySelector('#commit-progress-time');
  if (!slider || !timeEl) return;

  // 1) read slider & update progress
  commitProgress = Number(slider.value);

  // 2) convert 0–100 value back to a Date
  commitMaxTime = timeScale.invert(commitProgress);

  // 3) update the label text
  timeEl.textContent = commitMaxTime.toLocaleString('en', {
    dateStyle: 'long',
    timeStyle: 'short',
  });

  // 4) filter commits up to commitMaxTime
  filteredCommits = allCommits.filter(d => d.datetime <= commitMaxTime);

  // 5) update the existing scatter plot
  updateScatterPlot(allData, filteredCommits);

  // 6) update the files unit visualization
  updateFileDisplay(filteredCommits);
}

function highlightFilesForCommit(commit) {
  const filesRoot = d3.select('#files');
  if (filesRoot.empty() || !commit || !commit.lines) return;

  // Find the top 1–2 files for this commit
  const topFiles = d3.rollups(
    commit.lines,
    v => v.length,
    l => l.file
  )
    .sort((a, b) => d3.descending(a[1], b[1]))
    .slice(0, 2)
    .map(d => d[0]); // just the file names

  // Mark the matching file blocks as active
  filesRoot
    .selectAll('div')
    .classed('is-active', d => topFiles.includes(d.name));
}


let scroller; // Scrollama instance

function onStepEnter(response) {
  // The DOM element for this step has the commit data bound to it
  const commit = response.element.__data__;
  if (!commit || !timeScale) return;

  const slider = document.querySelector('#commit-progress');
  if (!slider) return;

  // 1) Visually mark the active step
  d3.selectAll('#scatter-story .step').classed('is-active', false);
  d3.select(response.element).classed('is-active', true);

  // 2) Move the slider to this commit's datetime
  const progress = timeScale(commit.datetime);
  commitProgress = progress;
  slider.value = progress;

  // 3) Reuse slider logic to update plot + file dots
  onTimeSliderChange();

  // 4) Link story step to the file view
  highlightFilesForCommit(commit);
}


function setupScrolly() {
  scroller = scrollama();

  scroller
    .setup({
      container: '#scrolly-1',
      step: '#scrolly-1 .step',
      offset: 0.6, // trigger when step is ~60% down the viewport
    })
    .onStepEnter(onStepEnter);
}

// keep Scrollama responsive
window.addEventListener('resize', () => {
  if (scroller) scroller.resize();
});


// ---- Init wrapper (avoids top-level await) ----
async function init() {
  try {
    const data = await loadData();
    const commits = processCommits(data);
    renderCommitInfo(data, commits);
    renderScatterPlot(data, commits);

    // --- Lab 8 Step 1: set up evolution slider state ---
    allData = data;
    allCommits = commits;

    timeScale = d3.scaleTime()
      .domain([
        d3.min(allCommits, d => d.datetime),
        d3.max(allCommits, d => d.datetime),
      ])
      .range([0, 100]);

    // initial max time = 100% (latest commit)
    commitMaxTime = timeScale.invert(commitProgress);
    filteredCommits = allCommits.filter(d => d.datetime <= commitMaxTime);

    // wire up slider
    const slider = document.querySelector('#commit-progress');
    if (slider) {
      slider.addEventListener('input', onTimeSliderChange);
      onTimeSliderChange(); // initialize label + plots
    }

    // Lab 8 Step 3.2 – generate narrative steps
    renderCommitStory(commits);

    // Lab 8 Step 3.3 – set up Scrollama
    setupScrolly();

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
