console.log("IT’S ALIVE!");

// Where is this site’s root
const BASE = new URL(".", import.meta.url).pathname;

// Treat "", "index.html", and trailing slash as the same route
function normalize(pathname) {
  let p = pathname;
  if (p.endsWith("/index.html")) p = p.slice(0, -"/index.html".length);
  if (p === "") p = "/";
  if (!p.endsWith("/")) p += "/";
  return p;
}

// Build hrefs relative to BASE
function hrefFrom(path) {
  if (/^https?:\/\//i.test(path)) return path;
  return BASE + path; // path must NOT start with "/"
}

// ---- Site map ----
const PAGES = [
  { url: "",          title: "Home" },
  { url: "projects/", title: "Projects" },
  { url: "contact/",  title: "Contact" },
  { url: "resume/",   title: "Resume" },
];

// ---- Build and inject <nav> ----
(function buildNav() {
  if (document.querySelector('nav[aria-label="Main"]')) return;

  const nav = document.createElement("nav");
  nav.setAttribute("aria-label", "Main");
  document.body.prepend(nav);

  const frag = document.createDocumentFragment();
  for (const { url, title } of PAGES) {
    const a = document.createElement("a");
    a.href = hrefFrom(url);
    a.textContent = title;

    if (new URL(a.href).host !== location.host) {
      a.target = "_blank";
      a.rel = "noopener noreferrer";
    }
    frag.append(a);
  }
  nav.append(frag);

  // Highlight current page
  const here = normalize(location.pathname);
  for (const a of nav.querySelectorAll("a")) {
    const aPath = normalize(new URL(a.href).pathname);
    if (new URL(a.href).host === location.host && aPath === here) {
      a.classList.add("current");
      a.setAttribute("aria-current", "page");
    }
  }
})();

// ---- Theme switcher (Automatic / Light / Dark) ----
;(function themeSwitcher() {
  document.body.insertAdjacentHTML(
    "afterbegin",
    `
      <label class="color-scheme" style="position:absolute;top:1rem;right:1rem;font-size:80%;">
        Theme:
        <select>
          <option value="light dark">Automatic</option>
          <option value="light">Light</option>
          <option value="dark">Dark</option>
        </select>
      </label>
    `
  );

  const select = document.querySelector(".color-scheme select");

  function setColorScheme(val) {
    document.documentElement.style.setProperty("color-scheme", val);
    select.value = val;
  }

  if ("colorScheme" in localStorage) setColorScheme(localStorage.colorScheme);

  select.addEventListener("input", (e) => {
    const val = e.target.value;
    setColorScheme(val);
    localStorage.colorScheme = val;
  });
})();

// ---- Contact form mailto encoding  ----
;(function enhanceMailto() {
  const form = document.querySelector("form[action^='mailto:']");
  if (!form) return;

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const data = new FormData(form);
    const to = form.getAttribute("action"); // "mailto:..."
    const qs = [...data]
      .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
      .join("&");
    location.href = `${to}?${qs}`;
  });
})();

// /global.js
export async function fetchJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} for ${url}`);
  return res.json();
}

export function renderProjects(projects, container, headingLevel = 'h2') {
  if (!container) return;
  container.innerHTML = '';
  const safeHeading = /^(h[1-6])$/.test(headingLevel) ? headingLevel : 'h2';
  for (const p of projects ?? []) {
    const a = document.createElement('article');
    const title = p?.title ?? 'Untitled';
    const img   = p?.image ?? '';
    const desc  = p?.description ?? '';
    a.innerHTML = `
      <${safeHeading}>${title}</${safeHeading}>
      <img src="${img}" alt="${title}">
      <p>${desc}</p>`;
    container.appendChild(a);
  }
  if (!projects || projects.length === 0) {
    container.innerHTML = '<p>No projects to display.</p>';
  }
}

/*
# Legacy Code for Step 2

import { $$ } from "./global.js"; // if you split files later; otherwise ignore

const navLinks = $$("nav a"); // Step 2.1
let currentLink = navLinks.find(a =>
  a.host === location.host && a.pathname === location.pathname
); // Step 2.2

currentLink?.classList.add("current"); // Step 2.3 (safe if not found)
*/

