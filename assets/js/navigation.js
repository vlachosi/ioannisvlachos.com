/* Arrange Quarto's existing controls without replacing their event handlers. */
(function () {
  "use strict";

  const navbar = document.querySelector(".navbar-container");
  if (!navbar) return;
  const brand = navbar.querySelector(".navbar-brand-container");
  const menu = navbar.querySelector(".navbar-toggler");
  const navigation = navbar.querySelector(".navbar-collapse");
  const search = navbar.querySelector("#quarto-search");
  const tools = navbar.querySelector(".quarto-navbar-tools");
  const appearance = tools?.querySelector(".quarto-color-scheme-toggle");
  const compact = window.matchMedia("(max-width: 991.98px)");
  if (!brand || !menu || !navigation || !search || !tools || !appearance) return;

  // Keep the native theme link, including Quarto's saved preference and icon.
  const label = document.createElement("span");
  label.className = "navigation-appearance-label";
  label.textContent = "Appearance";
  const state = document.createElement("span");
  state.className = "navigation-appearance-state";
  appearance.append(label, state);
  appearance.setAttribute("role", "button");
  appearance.setAttribute("aria-label", "Dark mode");
  appearance.querySelector("i")?.setAttribute("aria-hidden", "true");
  appearance.addEventListener("keydown", (event) => {
    if (event.key === " ") {
      event.preventDefault();
      appearance.click();
    }
  });

  const updateAppearance = () => {
    const dark = document.body.classList.contains("quarto-dark");
    appearance.setAttribute("aria-pressed", String(dark));
    appearance.title = dark ? "Switch to light mode" : "Switch to dark mode";
    state.textContent = dark ? "Dark" : "Light";
  };
  updateAppearance();
  new MutationObserver(updateAppearance).observe(document.body, {
    attributes: true,
    attributeFilter: ["class"],
  });

  const arrange = () => {
    // DOM order follows the visual order, including keyboard navigation.
    if (compact.matches) {
      navbar.prepend(menu, brand, search);
      navigation.append(tools);
    } else {
      navbar.prepend(brand, tools, navigation, search, menu);
    }
  };
  arrange();
  compact.addEventListener("change", arrange);

  // Quarto creates its search button after page scripts have loaded. Add only
  // a label; the native button continues to own search and keyboard shortcuts.
  const labelSearch = () => {
    const button = search.querySelector(".aa-DetachedSearchButton");
    if (!button) return;
    button.setAttribute("aria-label", "Search website");
    if (!button.querySelector(".navigation-search-label")) {
      const text = document.createElement("span");
      text.className = "navigation-search-label";
      text.textContent = "Search";
      button.append(text);
    }
  };
  labelSearch();
  new MutationObserver(labelSearch).observe(search, { childList: true, subtree: true });
})();
