/* Enhance Quarto's native listing controls without duplicating its index. */
document.addEventListener("DOMContentLoaded", () => {
  const container = document.getElementById("listing-posts");
  window["quarto-listings"] ||= {};
  const list = window["quarto-listings"]?.["listing-posts"];
  if (!container) return;

  const search = container.querySelector(".search");
  const sort = container.querySelector(".quarto-listing-sort select");
  const actions = container.querySelector(".listing-actions-group");
  const sidebar = document.getElementById("quarto-margin-sidebar");
  const categories = sidebar?.querySelector(".quarto-listing-category");
  const oldHeading = sidebar?.querySelector(".quarto-listing-category-title");
  const count = list?.items.length || 0;
  const pageKey = "listing-posts-page";
  let activeTopic = "";

  // List.js reads innerHTML by default. Index visible text so filtering never
  // matches button markup, and title sorting ignores inline formatting.
  for (const item of list?.items || []) {
    const values = {};
    for (const field of ["title", "description", "categories"]) {
      values[`listing-${field}`] = item.elm.querySelector(`.listing-${field}`)?.textContent.trim() || "";
    }
    item.values(values, true);
  }

  search.type = "search";
  search.setAttribute("aria-label", "Filter posts by title, summary or topic");
  search.setAttribute("aria-controls", "blog-post-list");
  container.querySelector(".entries").id = "blog-post-list";
  actions.querySelectorAll(".input-group-text").forEach(el => el.setAttribute("aria-hidden", "true"));

  // Use the existing date sort values, with one unambiguous default choice.
  for (const option of [...sort.options]) {
    if (!option.value || option.value === "index") option.remove();
    else if (option.value === "listing-title") option.textContent = "Title (A–Z)";
    else {
      const newest = option.dataset.direction === "desc";
      option.textContent = newest ? "Newest first" : "Oldest first";
      option.selected = newest;
    }
  }
  const newestOption = sort.querySelector('[data-direction="desc"]');
  if (newestOption) sort.prepend(newestOption);

  const summary = document.createElement("div");
  summary.className = "blog-results";
  const status = document.createElement("span");
  status.setAttribute("role", "status");
  status.setAttribute("aria-live", "polite");
  status.setAttribute("aria-atomic", "true");
  const reset = document.createElement("button");
  reset.type = "button";
  reset.className = "blog-reset";
  reset.textContent = "Clear filters";
  summary.append(status, reset);
  actions.after(summary);

  const panel = document.createElement("section");
  panel.className = "blog-topics";
  panel.setAttribute("aria-labelledby", "blog-topics-heading");
  const heading = document.createElement("h2");
  heading.id = "blog-topics-heading";
  heading.textContent = "Topics";
  panel.append(heading);
  oldHeading?.remove();

  const all = document.createElement("button");
  all.type = "button";
  all.className = "blog-all-topics";
  all.textContent = "All topics";
  all.setAttribute("aria-controls", "blog-post-list");
  panel.append(all);
  const topicButtons = [];
  const decode = value => decodeURIComponent(atob(value));

  if (categories) {
    // Native cloud entries are clickable divs. Buttons retain the generated
    // category data and sizing while adding keyboard activation and state.
    for (const entry of [...categories.querySelectorAll(".category")]) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = entry.className;
      button.dataset.category = entry.dataset.category;
      const label = document.createElement("span");
      label.className = entry.querySelector(".quarto-category-count")?.className || "";
      label.textContent = decode(entry.dataset.category);
      button.append(label);
      button.setAttribute("aria-controls", "blog-post-list");
      button.addEventListener("click", () => chooseTopic(decode(button.dataset.category)));
      entry.replaceWith(button);
      topicButtons.push(button);
    }
    panel.append(categories);
  }

  if (!topicButtons.length) {
    all.hidden = true;
    const empty = document.createElement("p");
    empty.className = "blog-topics-empty";
    empty.textContent = "Topics will appear as posts are published.";
    panel.append(empty);
  }

  function updateStatus() {
    const matching = list?.matchingItems.length || 0;
    status.textContent = matching === count
      ? `${count} ${count === 1 ? "post" : "posts"}`
      : `${matching} of ${count} posts`;
    reset.hidden = !search.value && !activeTopic;
    all.setAttribute("aria-pressed", String(!activeTopic));
    topicButtons.forEach(button => {
      const selected = decode(button.dataset.category) === activeTopic;
      button.classList.toggle("active", selected);
      button.setAttribute("aria-pressed", String(selected));
    });
  }

  function chooseTopic(topic, updateUrl = true) {
    if (!list) {
      updateStatus();
      return;
    }
    activeTopic = topic;
    if (topic) {
      // Read the original labels so topics containing commas remain intact.
      list.filter(item => [...item.elm.querySelectorAll("button[data-topic]")]
        .some(button => button.dataset.topic === topic));
    } else list.filter();
    if (updateUrl) {
      const url = new URL(location.href);
      // Quarto decodes its category hash twice. A separate key keeps percent
      // signs and other punctuation safe when opening a shared topic link.
      url.hash = topic ? `topic=${encodeURIComponent(topic)}` : "";
      history.pushState(null, "", url);
    }
    updateStatus();
  }

  all.addEventListener("click", () => chooseTopic(""));
  reset.addEventListener("click", () => {
    search.value = "";
    list.search();
    chooseTopic("");
    search.focus();
  });
  // Delegation also covers posts that List.js moves in from later pages.
  container.addEventListener("click", event => {
    const topic = event.target.closest("button[data-topic]");
    if (topic) {
      chooseTopic(topic.dataset.topic);
      // Filtering detaches post nodes. Keep keyboard focus on the selected
      // topic control, which remains available even if that post moves away.
      topicButtons.find(button => decode(button.dataset.category) === activeTopic)?.focus();
    }

    const page = event.target.closest(".listing-pagination .page-link[data-i]");
    if (!page || page.closest(".disabled")) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    const number = Number(page.dataset.i);
    list.show((number - 1) * list.page + 1, list.page);
    const url = new URL(location.href);
    const params = new URLSearchParams(url.hash.slice(1));
    params.set(pageKey, String(number));
    url.hash = params.toString();
    history.pushState(null, "", url);
    list.visibleItems[0]?.elm.querySelector(".listing-title")?.focus();
  }, true);

  function clearPageHash() {
    const url = new URL(location.href);
    const params = new URLSearchParams(url.hash.slice(1));
    params.delete(pageKey);
    url.hash = params.toString();
    history.replaceState(null, "", url);
  }

  list?.on("updated", updateStatus);
  search.addEventListener("input", () => {
    list?.search(search.value);
    clearPageHash();
  });
  sort.removeAttribute("onchange");
  sort.addEventListener("change", () => {
    const option = sort.selectedOptions[0];
    list.sort(option.value, { order: option.dataset.direction });
    list.show(1, list.page);
    clearPageHash();
  });

  const restoreLocation = () => {
    const params = new URLSearchParams(location.hash.slice(1));
    chooseTopic(params.get("topic") || "", false);
    const page = Number(params.get(pageKey));
    if (list && Number.isSafeInteger(page) && page > 0) {
      const last = Math.max(1, Math.ceil(list.matchingItems.length / list.page));
      list.show((Math.min(page, last) - 1) * list.page + 1, list.page);
    }
  };
  window.addEventListener("popstate", restoreLocation);
  window.addEventListener("hashchange", restoreLocation);

  // Keep one panel and one set of filter state as the layout changes.
  const compact = matchMedia("(max-width: 991.98px)");
  const placeTopics = () => {
    if (compact.matches || !sidebar) container.before(panel);
    else sidebar.append(panel);
  };
  compact.addEventListener("change", placeTopics);
  placeTopics();

  const noMatches = container.querySelector(".listing-no-matching");
  if (noMatches) noMatches.textContent = "No posts match these filters.";
  if (!count) {
    search.disabled = true;
    sort.disabled = true;
    // The authored empty state is clearer than a second no-match message.
    noMatches?.remove();
  }
  restoreLocation();
});
