# Editing the website

## Connect once

Sign in to [Pages CMS](https://app.pagescms.org), authorize its GitHub App for **vlachosi/vlachosi.github.io**, and select **main**. All editing happens on main.

**Save creates a commit and starts the production build.** Draft articles stay off the live site; saved profile, CV, and published-record changes can go live after the build succeeds. Draft source and uploaded files remain visible in this public repository.

The live sign-in/save/upload flow has not yet been verified. Start by creating and reopening a draft, adding an image, and building a preview. Any supplied offline CMS screenshots illustrate forms, not a connected account.

## Write and publish

1. Choose **Writing → New**. Enter the title, summary, date, and article; add topics and an optional social preview image with a description.
2. Leave **Keep as draft** on, save, and preview the result.
3. When ready, clear the draft switch and save. Check the successful GitHub Actions build and the live article.

The article editor uses Markdown/Quarto source without requiring YAML editing. Equations, code fences, and custom HTML are preserved. The initial title/date set the URL; later edits retain it. A future date does **not** schedule publication.

For an inline image, upload through **Images and attachments**, then insert its public path, for example `![Description](/assets/uploads/figure.png)`.

## Preview saved edits

Choose **Build preview** in Pages CMS, or GitHub Actions → Build preview → Run workflow. The workflow must exist on main, and your account needs Actions access. It includes saved drafts and never deploys; unsaved form changes are not included.

After success, download **site-preview** from the run's Artifacts section. This is a site bundle, **not a hosted preview URL**. On your computer, extract it, open a terminal in that folder, and run:

```sh
python3 -m http.server 8000 --bind 127.0.0.1
```

Open `localhost:8000` in your browser. Opening the HTML files directly can break assets, search, and the PDF viewer. For local authoring, use the [Quarto preview commands](CMS-CONFIG.md#local-setup).

## Replace the CV

1. Open **CV → Current CV PDF**. Upload a PDF smaller than 25 MiB and **select it**; uploading alone does not make it current.
2. Set the optional updated date and save.
3. After the build, inspect the CV page, text, links, and download.

Only the selected document is published at the stable `cv/vlachos-cv.pdf` address. Duplicate uploads may get numbered filenames; selection determines the active version. The download remains usable if the viewer fails. Select an earlier upload to roll back, or clear the field to remove the public CV. Old uploads remain in repository history.

## Other updates

| Form | What to do |
| --- | --- |
| Research / Projects | Choose a research status, add links, and use **Feature on homepage** and **Display order**; lower numbers appear first. Keep unfinished entries as drafts. Placeholder entries also stay off production. |
| Profile and contact | Update shared identity, biography, email, and links. **More about me** adds text only to About. Optional fields can be blank. |
| Talks / Teaching | Edit the records, then enable the page under Profile and contact; its switch controls navigation and publication together. |

Use GitHub file/commit history to restore content or revert a mistaken change. Local editing remains available if the dashboard is unavailable.
