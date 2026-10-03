/*
 * CV viewer. Draws the PDF named in [data-cv-viewer] into the page with
 * PDF.js: one canvas per page, a transparent text layer on top so the text can
 * be selected and searched, and clickable areas for the PDF's links. The
 * build supplies a working download link independently of this preview.
 */
const viewer = document.querySelector("[data-cv-viewer]");
const status = document.querySelector("[data-cv-status]");

function showError(error) {
  if (viewer) viewer.setAttribute("aria-busy", "false");
  if (!status) return;
  const missing = error?.name === "MissingPDFException" || error?.status === 404;
  status.textContent = missing
    ? "The CV PDF could not be found. Please try again later."
    : "The embedded preview is unavailable. You can still download the PDF above.";
  status.hidden = false;
}

async function drawPage(pdfjsLib, page, width) {
  const scale = width / page.getViewport({ scale: 1 }).width;
  const viewport = page.getViewport({ scale });
  const ratio = Math.min(window.devicePixelRatio || 1, 3);

  const wrap = document.createElement("div");
  wrap.className = "cv-page";
  wrap.style.aspectRatio = `${viewport.width} / ${viewport.height}`;
  wrap.style.setProperty("--scale-factor", scale);
  wrap.style.setProperty("--total-scale-factor", scale);
  wrap.style.setProperty("--scale-round-x", "1px");
  wrap.style.setProperty("--scale-round-y", "1px");

  const canvas = document.createElement("canvas");
  canvas.width = Math.floor(viewport.width * ratio);
  canvas.height = Math.floor(viewport.height * ratio);
  canvas.setAttribute("aria-hidden", "true");
  wrap.appendChild(canvas);

  const text = document.createElement("div");
  text.className = "textLayer";
  wrap.appendChild(text);

  const links = document.createElement("div");
  links.className = "cv-links";
  wrap.appendChild(links);

  await page.render({
    canvasContext: canvas.getContext("2d"),
    viewport,
    transform: ratio === 1 ? null : [ratio, 0, 0, ratio, 0, 0],
  }).promise;

  await new pdfjsLib.TextLayer({
    textContentSource: page.streamTextContent(),
    container: text,
    viewport,
  }).render();

  for (const annotation of await page.getAnnotations()) {
    if (annotation.subtype !== "Link" || !annotation.url) continue;
    const [x1, y1] = viewport.convertToViewportPoint(annotation.rect[0], annotation.rect[1]);
    const [x2, y2] = viewport.convertToViewportPoint(annotation.rect[2], annotation.rect[3]);
    const link = document.createElement("a");
    link.className = "cv-link";
    link.href = annotation.url;
    link.setAttribute("aria-label", annotation.url.replace(/^mailto:/, ""));
    Object.assign(link.style, {
      left: `${Math.min(x1, x2)}px`,
      top: `${Math.min(y1, y2)}px`,
      width: `${Math.abs(x2 - x1)}px`,
      height: `${Math.abs(y2 - y1)}px`,
    });
    links.appendChild(link);
  }

  return wrap;
}

async function main() {
  if (!viewer) return;
  viewer.setAttribute("aria-busy", "true");
  if (status) {
    status.hidden = false;
    status.textContent = "Loading CV preview…";
  }
  const src = new URL(viewer.dataset.cvViewer, window.location.href).href;

  // A dynamic import lets the page recover when the renderer itself is blocked
  // or unsupported. The direct download link never depends on JavaScript.
  const pdfjsLib = await import("/assets/vendor/pdfjs/pdf.min.mjs");
  pdfjsLib.GlobalWorkerOptions.workerSrc = "/assets/vendor/pdfjs/pdf.worker.min.mjs";
  const pdf = await pdfjsLib.getDocument({ url: src }).promise;

  const pages = [];
  for (let n = 1; n <= pdf.numPages; n++) pages.push(await pdf.getPage(n));

  // Redraw at the container's width, and again whenever that width changes.
  let drawnWidth = 0;
  let drawVersion = 0;
  const draw = async () => {
    const width = Math.floor(viewer.clientWidth);
    if (!width || width === drawnWidth) return;
    drawnWidth = width;
    const version = ++drawVersion;
    const drawn = [];
    for (const page of pages) {
      drawn.push(await drawPage(pdfjsLib, page, width));
      if (version !== drawVersion) return;
    }
    viewer.replaceChildren(...drawn);
    viewer.dataset.ready = "true";
    viewer.setAttribute("aria-busy", "false");
    if (status) status.hidden = true;
  };
  await draw();

  let timer = 0;
  new ResizeObserver(() => {
    clearTimeout(timer);
    timer = setTimeout(() => draw().catch(showError), 150);
  }).observe(viewer);
}

main().catch(showError);
