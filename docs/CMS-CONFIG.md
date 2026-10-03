# Setup and maintenance

For everyday changes, use the [editing guide](EDITING.md).

## Local setup

Install **Quarto 1.9.38** and **Python 3.12**, then run from the repository root:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/prepare-site.py
quarto preview --profile drafts
```

Run preparation before the first Quarto command: it creates includes Quarto needs while scanning a fresh checkout. The pre-render hook refreshes them afterward. Edit source records, not ignored `_generated/` files or `cv/vlachos-cv.pdf`.

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

`settings.content.merge: true` preserves post options outside the forms, such as custom scripts. **Pages CMS does not merge top-level YAML lists.** Keep all Research, Projects, Talks, and Teaching fields in their form schemas; omitted fields can be lost on save. Formatting and comments may also be rewritten. Keep post renaming disabled to preserve article URLs.

The preview button dispatches `preview.yml` on main with a string `payload` input. Keep that contract if changing the workflow; the payload is not executed as shell commands.

Plain prose, equations, and displayed code need no R/Jupyter runtime. Before adding executable R/Python posts, pin their dependencies or establish a frozen-output policy. **`freeze: auto` can execute changed source**; committing `_freeze/` alone does not guarantee code never runs.

Bundled fonts, KaTeX, and PDF.js retain their licenses under [assets/fonts/](../assets/fonts/) and [assets/vendor/](../assets/vendor/). Keep PDF.js main and worker versions together when updating them.

## Connection status

CMS configuration was checked against [Pages CMS 2.1.8 source](https://github.com/pages-cms/pages-cms/tree/6f4e860a35d934406580287e7042e5e111e207a1), including schema and serialization behavior. This does not establish successful hosted authentication or saves; complete the first-use check in the editing guide. See the official [configuration documentation](https://pagescms.org/docs/configuration/) when changing forms.

The requested repository rename to `ioannisvlachos.com` remains incomplete: GitHub integration permissions blocked it with HTTP 403. An owner can rename it in GitHub settings, then update repository links/CMS access and verify Pages, DNS, and HTTPS. The public site address is already `https://ioannisvlachos.com`.
