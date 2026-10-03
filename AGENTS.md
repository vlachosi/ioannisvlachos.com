# Working on this website

- Work directly on `main`. The owner wants code and content changes to flow through main; do not create task branches unless they explicitly change this preference.
- Use the existing checkout. Cloud tasks already run in an isolated environment; do not create a Git worktree unless requested.
- Show intermediate desktop/mobile screenshots for visual changes. Distinguish actual website screenshots from offline CMS form previews.
- Preserve the custom domain `ioannisvlachos.com`, existing article URLs, and the stable `cv/vlachos-cv.pdf` download.
- Content is edited through `.pages.yml` forms. Keep the full root-list schemas in sync with the YAML fields; their CMS saves do not merge omitted fields.
- Edit `_data/profile.yml` and `_data/cv.yml`, not ignored generated profile/CV files.

## Validation

Use Quarto 1.9.38 and Python 3.12 with `requirements.txt`. Run relevant tests, then verify both outputs when changing content/build behavior:

```sh
python scripts/prepare-site.py
python -m unittest discover -s tests -v
quarto render --clean
python scripts/check-site.py _site
quarto render --profile drafts --output-dir _site-preview --clean
python scripts/check-site.py _site-preview --drafts
```

Stop live preview processes before rendering into the same output directory. Only production `_site` output belongs in the Pages deployment; draft previews use `_site-preview` and a separate artifact.
