# Setup and maintenance

For everyday changes, use the [editing guide](EDITING.md).

## Local setup

Install **Quarto 1.9.38** and **Python 3.12**, then run from the repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m playwright install --with-deps chromium --only-shell
python scripts/prepare-site.py
quarto preview --profile drafts
```

Run preparation before the first Quarto command: it creates includes Quarto needs while scanning a fresh checkout. The pre-render hook refreshes them afterward. Edit source records, not ignored `_generated/` files or `cv/vlachos-cv.pdf`.

Playwright 1.62.0 and its matching Chromium headless shell generate the site's social thumbnail. Install the browser after installing Python dependencies, and repeat that step when updating Playwright. On Linux, `--with-deps` installs the required system libraries and may need administrator access. Keep the virtual environment active so Quarto's `python3` hook uses the installed packages.

To check changes locally:

```sh
python -m unittest discover -s tests -v
quarto render --clean
python scripts/check-site.py _site
quarto render --profile drafts --output-dir _site-preview --clean
python scripts/check-site.py _site-preview --drafts
```

Stop a live preview before building into its output directory. The [publication workflow](../.github/workflows/publish.yml) runs these checks and deploys only production from main. The separate [preview workflow](../.github/workflows/preview.yml) creates a draft artifact without deploying.

## Configuration to preserve

| Area | Source / requirement |
| --- | --- |
| Browser forms | [.pages.yml](../.pages.yml) |
| Shared profile / CV selection | [_data/profile.yml](../_data/profile.yml) / [_data/cv.yml](../_data/cv.yml) |
| Page structure / appearance | QMD pages, [templates/](../templates/), [styles/](../styles/), and [assets/js/](../assets/js/) |
| Site and build settings | [_quarto.yml](../_quarto.yml) and [scripts/](../scripts/) |

`settings.content.merge: true` preserves post options outside the forms, such as custom scripts. **Pages CMS does not merge top-level YAML lists.** Keep all Research, Code, Talks, and Teaching fields in their form schemas; omitted fields can be lost on save. Formatting and comments may also be rewritten. Keep post renaming disabled to preserve article URLs. Talks and Teaching use the shared **Keep as draft** switch too; preserve those fields so editing a record cannot remove its unpublished state.

Every Code entry requires a **Section**: Packages, Replication code, or Templates. Keep these choices aligned with the renderer. Entries use **Display order** within their section; production hides sections without published entries. The form and public page retain the existing `projects/` source paths and URLs.

Code records retain optional `year`, `authors`, `venue`, and `version` fields at the top level. Replication entries use the paper title and bibliographic details, with **Paper** and **Code** links. Package entries use the package name, purpose, version, and tags, with **Docs** and **Source** links. Additional links remain optional.

The Profile links object is required, while each URL inside it, including ResearchGate, is optional. Blank URLs omit their buttons from Home and Research; About omits all empty profile, social, and email entries. Preserve the required object: an optional object with every field cleared is treated as absent, which lets content merging restore the old URLs instead of removing them.

The shared `bio` uses two Markdown paragraphs separated by a blank line on Home and About. Preserve that paragraph break; `about_extra` remains additional text shown only on About.

The preparation hook generates a 1200×630 PNG social thumbnail from the profile's `name`, `role`, and `affiliation`, the site domain, bundled fonts, and an abstract contour graphic. Its template is [templates/social-card.html](../templates/social-card.html), rendered by [scripts/social_image.py](../scripts/social_image.py). The default image URL is `/assets/generated/social-preview.png?v=<PNG digest>`; the query changes when the image bytes change. The generator also refreshes `/assets/og.png` for older share URLs. Both PNG files are generated: edit the CMS profile or template rather than the images. The build uses local assets and a browser renderer; it needs no AI service or API key. Article-specific social images continue to override the site default. Sharing services may retain an older preview until they fetch the page metadata again.

**About → Page visibility → Publish blog page** writes the boolean `sections.blog` in `_data/profile.yml`. Both the CMS field and renderer default to `true` when it is absent. Preserve an explicit `false`: it excludes `writing/` from production and draft builds, removes Blog navigation, homepage listings, search and sitemap entries, and removes the Blog Subscribe option and RSS discovery link. The 404 page also omits its Blog link. Source posts, topics, listing settings, and the CMS collection remain available for editing and are restored when the switch is enabled.

After changing page visibility, use a full clean render for each output being checked; the commands above and both CI workflows already do this. Stop live preview first. Partial or non-clean renders may retain old HTML or indexes, and `check-site.py` rejects stale Blog pages or references while the Blog is disabled. Homepage listing metadata is generated conditionally as well as its body markup: keeping a hidden Blog listing in YAML would let Quarto recreate its container.

The preview button dispatches `preview.yml` on main with a string `payload` input. Keep that contract if changing the workflow; the payload is not executed as shell commands.

Plain prose, equations, and displayed code need no R/Jupyter runtime. Before adding executable R/Python posts, pin their dependencies or establish a frozen-output policy. **`freeze: auto` can execute changed source**; committing `_freeze/` alone does not guarantee code never runs.

Bundled fonts, KaTeX, and PDF.js retain their licenses under [assets/fonts/](../assets/fonts/) and [assets/vendor/](../assets/vendor/). Keep PDF.js main and worker versions together when updating them.

## RSS subscriptions

The footer RSS icon links to `subscribe.html`. Preserve these feed URLs:

| Feed | URL |
| --- | --- |
| All updates | `/index.xml` |
| Blog | `/writing/index.xml` |
| Research | `/research/index.xml` |
| Code | `/projects/index.xml` |

When the Blog is enabled, Quarto generates its feed. The post-render hook runs `scripts/build-feeds.py` to create the other feeds from source records and the native Blog feed. When disabled, the hook replaces `/writing/index.xml` with a valid empty feed at the same stable address and omits Blog posts from All updates, including in draft previews. Reenabling the Blog resumes its feed without changing subscription URLs. These custom feeds exclude drafts and placeholders even in preview builds.

Research and Code records may include `feed: {id: stable-lowercase-slug, date: YYYY-MM-DD}`. Omit the optional object or clear both fields to leave the entry off RSS without changing page visibility. A populated object requires both fields; IDs must be unique within each collection and remain stable when content is edited. The date is an announcement date, separate from a paper's bibliographic year. Eligibility uses the **Australia/Melbourne** calendar date at build time; later dates are excluded until a qualifying build. Publication runs on pushes to main or manual workflow dispatch, with no scheduled run; the date alone cannot trigger publication.

Keep the RSS announcement date as a `YYYY-MM-DD` text field. Pages CMS 2.1.8's native date writer fails on undefined values inside an unused optional object; upstream serialization checks reproduce that failure and pass with the text field. CMS validation checks ID and date format; the build checks real calendar dates and ID uniqueness.

## Connection status

CMS configuration was checked against [Pages CMS 2.1.8 source](https://github.com/pages-cms/pages-cms/tree/6f4e860a35d934406580287e7042e5e111e207a1), including schema and serialization behavior. This does not establish successful hosted authentication or saves; complete the first-use check in the editing guide. See the official [configuration documentation](https://pagescms.org/docs/configuration/) when changing forms.

The repository is [vlachosi/ioannisvlachos.com](https://github.com/vlachosi/ioannisvlachos.com), and the public site is [ioannisvlachos.com](https://ioannisvlachos.com). Select this repository when connecting Pages CMS and ensure its GitHub App has access. The rename is complete; hosted CMS authentication and the save/reopen/upload flow still need verification.

When published, the **Blog** keeps its existing `writing/` URLs, including article links and the RSS feed. Article URLs are unavailable while the Blog is disabled and return when it is enabled again; the empty RSS feed remains available throughout.
