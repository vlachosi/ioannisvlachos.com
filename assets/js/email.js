/*
 * Populate public contact links from the generated profile record.
 * An empty email keeps the existing placeholders visible.
 */
(function () {
  "use strict";

  const contact = document.getElementById("site-contact");
  if (!contact) return;
  let address;
  try {
    address = JSON.parse(contact.textContent).email;
  } catch (_) {
    return;
  }
  if (typeof address !== "string" || !address.trim()) return;
  address = address.trim();

  document.querySelectorAll("[data-email-slot]").forEach((slot) => {
    const link = document.createElement("a");
    link.href = "mailto:" + address;
    if (slot.closest(".id-links")) {
      link.setAttribute("aria-label", "Email");
      link.title = address;
      link.innerHTML = '<i class="bi bi-envelope" aria-hidden="true"></i>';
    } else {
      link.textContent = address;
    }
    slot.replaceChildren(link);
  });
})();
