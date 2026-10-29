(async () => {
  "use strict";
  const $ = id => document.getElementById(id);
  const shell = $("timeline-shell"), timeline = $("timeline"), rail = $("timeline-rail"), dots = $("rail-dots"), axis = $("rail-axis"), svg = $("connections");
  const filters = $("type-filters"), year = $("year"), search = $("search"), count = $("result-count"), empty = $("empty");
  const state = { type: "all", year: "all", query: "", active: null, selected: null, previewType: null, openId: null };
  const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const dateLabel = value => new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" }).format(new Date(`${value}T12:00:00Z`));
  const typeClass = value => value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  let data, shown = [], frame = 0;
  try {
    const response = await fetch("data/news.json");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    data = await response.json();
    if (!Array.isArray(data.posts)) throw new Error("Invalid news data");
  } catch (error) { count.textContent = `Stories are unavailable: ${error.message}`; return; }
  const posts = [...data.posts].sort((a, b) => b.published_date.localeCompare(a.published_date) || Number(b.id) - Number(a.id));
  const byId = new Map(posts.map(post => [String(post.id), post]));
  const normalizedUrl = raw => { try { const url = new URL(raw); return url.origin + url.pathname.replace(/\/+$/, ""); } catch { return ""; } };
  const byUrl = new Map(posts.map(post => [normalizedUrl(post.url), String(post.id)]));
  const years = [...new Set(posts.map(p => p.published_date.slice(0, 4)))].sort().reverse();
  year.innerHTML = '<option value="all">All years</option>' + years.map(y => `<option value="${y}">${y}</option>`).join("");

  function safeArticleHtml(post) {
    const allowed = new Set(["p", "h2", "h3", "h4", "h5", "ul", "ol", "li", "blockquote", "strong", "b", "em", "i", "br", "hr", "a", "img", "figure", "figcaption", "table", "thead", "tbody", "tr", "th", "td", "sup", "sub"]);
    const blocked = new Set(["script", "style", "iframe", "object", "embed", "form", "input", "button", "svg", "math", "video", "audio", "template"]);
    const savedImages = new Set(post.inline_images || []);
    const source = new DOMParser().parseFromString(post.content_html || "", "text/html");
    function copy(node) {
      if (node.nodeType === Node.TEXT_NODE) return document.createTextNode(node.textContent);
      if (node.nodeType !== Node.ELEMENT_NODE) return null;
      const tag = node.tagName.toLowerCase();
      if (blocked.has(tag)) return null;
      if (tag === "img") {
        const path = (node.getAttribute("src") || "").replace(/^images\//, "assets/images/");
        if (!savedImages.has(path)) return null;
        const image = document.createElement("img");
        image.src = path;
        image.alt = node.getAttribute("alt") || "";
        image.loading = "lazy";
        return image;
      }
      const element = allowed.has(tag) ? document.createElement(tag) : document.createDocumentFragment();
      if (tag === "a") {
        try {
          const url = new URL(node.getAttribute("href") || "", post.url);
          if (["https:", "http:"].includes(url.protocol)) {
            const targetId = byUrl.get(normalizedUrl(url.href));
            if (targetId) { element.href = `?story=${targetId}`; element.dataset.localStory = targetId; }
            else { element.href = url.href; element.target = "_blank"; element.rel = "noopener noreferrer"; }
          }
        } catch { /* Keep the link text without an unsafe URL. */ }
      }
      for (const child of node.childNodes) {
        const clean = copy(child);
        if (clean) element.append(clean);
      }
      return element;
    }
    const output = document.createElement("div");
    for (const child of source.body.childNodes) {
      const clean = copy(child);
      if (clean) output.append(clean);
    }
    return output.innerHTML || `<p>${esc(post.full_text)}</p>`;
  }

  function renderFilters() {
    filters.innerHTML = [{ label: "All stories", value: "all" }, ...data.story_types.map(label => ({ label, value: label }))]
      .map(({ label, value }) => `<button type="button" class="filter-chip${value === "all" ? "" : ` type-${typeClass(value)}`}${state.type === value ? " active" : ""}" data-type="${esc(value)}" aria-pressed="${state.type === value}">${esc(label)}</button>`).join("");
  }
  function visiblePosts() {
    return posts.filter(p => (state.type === "all" || p.story_type === state.type) &&
      (state.year === "all" || p.published_date.startsWith(state.year)) &&
      (!state.query || `${p.title} ${p.excerpt} ${p.full_text}`.toLocaleLowerCase().includes(state.query)));
  }
  function render() {
    shown = visiblePosts();
    state.active = null;
    state.selected = null;
    state.previewType = null;
    state.openId = null;
    count.textContent = shown.length === posts.length ? "Browse the news archive" : `${shown.length} matching ${shown.length === 1 ? "story" : "stories"}`;
    empty.hidden = !!shown.length;
    shell.hidden = !shown.length;
    timeline.innerHTML = shown.map(p => {
      const image = p.image ? `<figure class="story-image"><img src="${esc(p.image.path)}" alt="${esc(p.image.alt)}" loading="lazy" decoding="async"><figcaption>${esc(p.image.credit || p.image.caption)}</figcaption></figure>` : "";
      return `<article class="story type-${typeClass(p.story_type)}" id="post-${esc(p.id)}" data-id="${esc(p.id)}"><div class="story-card">${image}<div class="story-body"><div class="story-top"><time datetime="${esc(p.published_date)}">${dateLabel(p.published_date)}</time><span class="type-label">${esc(p.story_type)}</span></div><h2>${esc(p.title)}</h2><p class="excerpt">${esc(p.excerpt)}</p><button class="read-link" type="button" data-open-story="${esc(p.id)}" aria-expanded="false" aria-controls="story-full-${esc(p.id)}">Read full story</button></div><div class="story-full" id="story-full-${esc(p.id)}" hidden></div></div></article>`;
    }).join("");
    timeline.scrollTop = 0;
    requestLayout();
  }
  function updateStoryUrl(id, replace = false) {
    const url = new URL(location.href);
    if (id) url.searchParams.set("story", id);
    else url.searchParams.delete("story");
    history[replace ? "replaceState" : "pushState"]({}, "", url);
  }
  function closeStory(updateUrl = true) {
    if (!state.openId) return;
    const story = $("post-" + state.openId);
    if (story) {
      const full = story.querySelector(".story-full");
      full.hidden = true;
      full.replaceChildren();
      story.classList.remove("expanded");
      const button = story.querySelector("[data-open-story]");
      button.textContent = "Read full story";
      button.setAttribute("aria-expanded", "false");
    }
    state.openId = null;
    if (updateUrl) updateStoryUrl(null, true);
    highlight(state.selected);
    requestLayout();
  }
  function openStory(id, updateUrl = true) {
    const post = byId.get(String(id));
    if (!post) return;
    if (state.openId === String(id)) return;
    if (state.openId) closeStory(false);
    let story = $("post-" + id);
    if (!story) {
      state.type = "all"; state.year = "all"; state.query = "";
      year.value = "all"; search.value = "";
      renderFilters(); render();
      story = $("post-" + id);
    }
    if (!story) return;
    const full = story.querySelector(".story-full");
    full.innerHTML = `<div class="article-content">${safeArticleHtml(post)}</div>`;
    full.hidden = false;
    story.classList.add("expanded");
    const button = story.querySelector("[data-open-story]");
    button.textContent = "Close full story";
    button.setAttribute("aria-expanded", "true");
    state.openId = String(id);
    state.selected = String(id);
    if (updateUrl) updateStoryUrl(String(id));
    highlight(String(id));
    requestLayout();
    requestAnimationFrame(() => {
      if (matchMedia("(max-width: 760px)").matches) story.scrollIntoView({ block: "start", behavior: "instant" });
      else timeline.scrollTo({ top: story.offsetTop - timeline.offsetTop - 12, behavior: "instant" });
    });
  }
  function requestLayout() { cancelAnimationFrame(frame); frame = requestAnimationFrame(layout); }
  function layout() {
    if (!shown.length || matchMedia("(max-width: 760px), print").matches) return;
    const top = 90, bottom = Math.max(top + 30, rail.clientHeight - 42);
    const dates = shown.map(p => Date.parse(`${p.published_date}T12:00:00Z`));
    const max = Math.max(...dates), min = Math.min(...dates), span = max - min || 1, center = rail.clientWidth * .46;
    const placed = [];
    const positions = dates.map(date => {
      const target = top + (max - date) / span * (bottom - top);
      let best = { x: center, y: target, score: Infinity };
      for (let ring = 0; ring < 13; ring++) for (const side of (ring ? [-1, 1] : [0])) {
        const x = center + side * ring * 12;
        if (x < 16 || x > rail.clientWidth - 16) continue;
        for (let offset = 0; offset < 20; offset++) {
          const y = target + (offset % 2 ? -1 : 1) * Math.ceil(offset / 2) * 11;
          if (y < 72 || y > rail.clientHeight - 15) continue;
          if (placed.some(p => Math.hypot(p.x - x, p.y - y) < 11)) continue;
          const score = Math.abs(y - target) * 3 + Math.abs(x - center);
          if (score < best.score) best = { x, y, score };
          break;
        }
      }
      placed.push(best);
      return best;
    });
    axis.innerHTML = years.filter(y => shown.some(p => p.published_date.startsWith(y))).map(y => {
      const date = Date.parse(`${y}-07-01T12:00:00Z`);
      const at = Math.max(top, Math.min(bottom, top + (max - date) / span * (bottom - top)));
      return `<span class="year-mark" style="top:${at}px">${y}</span>`;
    }).join("");
    dots.innerHTML = shown.map((p, i) => `<button type="button" class="rail-dot type-${typeClass(p.story_type)}" data-id="${esc(p.id)}" style="left:${positions[i].x}px;top:${positions[i].y}px" title="${esc(`${dateLabel(p.published_date)}: ${p.title}`)}" aria-label="${esc(`${dateLabel(p.published_date)}: ${p.title}`)}"></button>`).join("");
    highlight(state.active || state.selected);
  }
  function drawConnections() {
    if (!shown.length || matchMedia("(max-width: 760px), print").matches) return;
    const box = shell.getBoundingClientRect(), stories = new Map([...timeline.querySelectorAll(".story")].map(n => [n.dataset.id, n]));
    const paths = [];
    for (const dot of dots.children) {
      const story = stories.get(dot.dataset.id);
      if (!story) continue;
      const card = story.getBoundingClientRect();
      if (card.bottom < box.top || card.top > box.bottom) continue;
      const point = dot.getBoundingClientRect();
      const x1 = point.left + point.width / 2 - box.left, y1 = point.top + point.height / 2 - box.top;
      const x2 = card.left - box.left, y2 = card.top + Math.min(48, card.height / 3) - box.top, bend = x1 + (x2 - x1) * .55;
      paths.push(`<path class="connector${state.active === dot.dataset.id ? " active" : ""}${dot.classList.contains("type-preview") ? " type-preview" : ""} ${[...dot.classList].find(name => name.startsWith("type-") && name !== "type-preview") || ""}" d="M ${x1} ${y1} C ${bend} ${y1}, ${bend} ${y2}, ${x2} ${y2}"/>`);
    }
    svg.setAttribute("viewBox", `0 0 ${shell.clientWidth} ${shell.clientHeight}`);
    svg.classList.toggle("previewing", !!state.previewType);
    svg.innerHTML = paths.join("");
  }
  function highlight(id) {
    state.active = id;
    dots.querySelectorAll(".rail-dot").forEach(n => { n.classList.toggle("active", n.dataset.id === id); n.setAttribute("aria-pressed", String(n.dataset.id === state.selected)); });
    timeline.querySelectorAll(".story").forEach(n => n.classList.toggle("active", n.dataset.id === id));
    drawConnections();
  }
  function previewType(type) {
    state.previewType = type && type !== "all" ? type : null;
    dots.classList.toggle("previewing", !!state.previewType);
    const match = state.previewType ? `type-${typeClass(state.previewType)}` : "";
    dots.querySelectorAll(".rail-dot").forEach(dot => dot.classList.toggle("type-preview", !!match && dot.classList.contains(match)));
    drawConnections();
  }
  filters.addEventListener("click", e => { const b = e.target.closest("button[data-type]"); if (b) { closeStory(); state.type = b.dataset.type; renderFilters(); render(); } });
  filters.addEventListener("pointerover", e => { const b = e.target.closest("button[data-type]"); if (b) previewType(b.dataset.type); });
  filters.addEventListener("pointerleave", () => previewType(null));
  filters.addEventListener("focusin", e => { const b = e.target.closest("button[data-type]"); if (b) previewType(b.dataset.type); });
  filters.addEventListener("focusout", e => { if (!filters.contains(e.relatedTarget)) previewType(null); });
  year.addEventListener("change", () => { closeStory(); state.year = year.value; render(); });
  search.addEventListener("input", () => { closeStory(); state.query = search.value.trim().toLocaleLowerCase(); render(); });
  timeline.addEventListener("click", e => {
    const local = e.target.closest("a[data-local-story]");
    if (local) { e.preventDefault(); openStory(local.dataset.localStory); return; }
    const button = e.target.closest("button[data-open-story]");
    if (button) { state.openId === button.dataset.openStory ? closeStory() : openStory(button.dataset.openStory); return; }
    if (e.target.closest("a, button")) return;
    const story = e.target.closest(".story");
    if (story && !story.classList.contains("expanded")) openStory(story.dataset.id);
  });
  dots.addEventListener("click", e => { const d = e.target.closest(".rail-dot"); if (d) { state.selected = d.dataset.id; const story = $("post-" + d.dataset.id); if (story) timeline.scrollTo({ top: story.offsetTop - timeline.offsetTop - timeline.clientHeight / 2 + story.clientHeight / 2, behavior: "instant" }); highlight(d.dataset.id); requestAnimationFrame(drawConnections); } });
  dots.addEventListener("pointerover", e => { const d = e.target.closest(".rail-dot"); if (d) highlight(d.dataset.id); });
  dots.addEventListener("pointerout", e => { if (e.target.closest(".rail-dot") && !e.relatedTarget?.closest?.(".rail-dot")) highlight(state.selected); });
  timeline.addEventListener("pointerover", e => { const s = e.target.closest(".story"); if (s) highlight(s.dataset.id); });
  timeline.addEventListener("pointerout", e => { const from = e.target.closest(".story"), to = e.relatedTarget?.closest?.(".story"); if (from && from !== to) highlight(state.selected); });
  shell.addEventListener("pointerleave", () => highlight(state.selected));
  shell.addEventListener("wheel", e => {
    if (e.ctrlKey || timeline.contains(e.target) || matchMedia("(max-width: 760px), print").matches) return;
    e.preventDefault();
    timeline.scrollBy({ top: e.deltaY, behavior: "instant" });
  }, { passive: false });
  timeline.addEventListener("scroll", () => requestAnimationFrame(drawConnections), { passive: true });
  window.addEventListener("resize", requestLayout);
  window.addEventListener("popstate", () => {
    const id = new URL(location.href).searchParams.get("story");
    if (id && byId.has(id)) openStory(id, false);
    else closeStory(false);
  });
  $("print").addEventListener("click", () => window.print());
  renderFilters(); render();
  const initialStory = new URL(location.href).searchParams.get("story");
  if (initialStory && byId.has(initialStory)) openStory(initialStory, false);
})();
