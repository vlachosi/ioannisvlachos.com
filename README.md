# Ioannis Vlachos — personal website

My academic website, built with Quarto and published at <https://ioannisvlachos.com> through GitHub Pages.

See the [website management review](docs/REVIEW.md) for the changes made and remaining recommendations.

## Edit in the browser

[Pages CMS](https://app.pagescms.org) provides the forms defined in [.pages.yml](.pages.yml):

- **Writing:** create posts with a title, summary, date, topics, images, body, and draft switch.
- **Research and Projects:** manage records, statuses, links, homepage selection, and display order.
- **Profile and contact:** update the shared biography, role, affiliation, email, links, and optional section visibility.
- **CV:** upload a PDF, select the current version, and set its updated date.
- **Build preview:** render saved content with drafts into a downloadable Actions artifact.

Select **main** in Pages CMS and authorize its GitHub App for this repository. All development and content editing flow through main. Account connection is separate from this code.

**Saving to main can publish changes.** New posts default to draft, so you can save and preview them before clearing that switch to publish. A future date does not schedule publication. See [the editing guide](docs/EDITING.md) and [CMS configuration notes](docs/CMS-CONFIG.md).

## Preview and build locally

Install Quarto **1.9.38** and Python **3.12**, then:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
quarto preview --profile drafts
```

Quarto validates content and prepares profile/CV inputs automatically before rendering. Generated files are ignored; edit their source records.

```sh
quarto render --clean
python scripts/check-site.py _site
quarto render --profile drafts --output-dir _site-preview --clean
python scripts/check-site.py _site-preview --drafts
python -m unittest discover -s tests -v
```

Production excludes drafts/placeholders. Stop a live preview before building into its output directory.

## Where to edit

| Content | Source |
|---|---|
| Shared profile, bio, email, links, section visibility | [_data/profile.yml](_data/profile.yml) |
| Blog posts | writing/posts/date-slug/index.qmd |
| Papers | [research/papers.yml](research/papers.yml) |
| Projects | [projects/projects.yml](projects/projects.yml) |
| Talks / Teaching | talks/talks.yml / teaching/teaching.yml |
| Selected CV and updated date | [_data/cv.yml](_data/cv.yml) |
| Original uploaded PDFs | _cv-uploads/ |
| Images and attachments | assets/uploads/ |
| Page structure and theme | QMD pages, templates/, styles/ |
| Build/site configuration | [_quarto.yml](_quarto.yml) |

Research/projects use **featured** and **order** for homepage placement; lower order appears first. **draft** and **placeholder** records appear only in draft previews. Profile settings enable Talks/Teaching pages and their navigation together.

Only the selected CV is copied to **cv/vlachos-cv.pdf**. Do not edit that generated file. Clearing the selection restores the empty CV state. Historical uploads remain in Git history; this repository is not private document storage.

## Publication

Pushes to main validate content, run tests, and check both build modes. Each build saves a **site-preview** artifact. Only checked production output is deployed, and only from main.

The separate **Build preview** workflow never deploys. Once its workflow exists on the default branch, run it from Pages CMS or GitHub Actions. The artifact contains drafts and is a download, not a hosted review URL.

## Computational posts

Plain Markdown, mathematics, and displayed code require no R/Jupyter runtime. Executable R/Python articles need pinned language dependencies or appropriately refreshed frozen results. **freeze: auto** can execute changed source during a project render; committing _freeze/ alone does not guarantee code never runs. Establish a suitable CI execution policy before adding computational articles.

## Design and credits

The custom theme and figures remain in styles/ and assets/js/. Fonts are Petrona, Source Sans 3, and JetBrains Mono under the SIL Open Font License. Maths uses self-hosted KaTeX (MIT), and the CV viewer uses PDF.js (Apache-2.0); see the bundled licenses. Keep PDF.js main and worker versions together when updating them.
