(() => {
  "use strict";
  for (const button of document.querySelectorAll("[data-copy-feed]")) {
    const address = document.getElementById(button.dataset.copyFeed);
    const label = button.querySelector("[data-copy-label]");
    if (!address || !label) continue;
    const status = document.createElement("p");
    status.className = "subscription-status sr-only";
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    status.setAttribute("aria-atomic", "true");
    button.closest(".subscription-option").append(status);
    const accessibleLabel = button.getAttribute("aria-label");
    let reset;
    button.hidden = false;
    button.addEventListener("click", async () => {
      clearTimeout(reset);
      label.textContent = "Copy link";
      button.setAttribute("aria-label", accessibleLabel);
      status.textContent = "";
      status.classList.add("sr-only");
      try {
        await navigator.clipboard.writeText(address.textContent.trim());
        label.textContent = "Copied";
        button.setAttribute("aria-label", `Copied: ${button.dataset.feedLabel} feed link`);
        status.textContent = `${button.dataset.feedLabel} feed address copied.`;
        reset = setTimeout(() => {
          label.textContent = "Copy link";
          button.setAttribute("aria-label", accessibleLabel);
        }, 2500);
      } catch {
        address.focus();
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(address);
        selection.removeAllRanges();
        selection.addRange(range);
        status.classList.remove("sr-only");
        status.textContent = "Select Copy from your device’s menu, or press Ctrl+C / Command+C to copy the selected address.";
      }
    });
  }
})();
