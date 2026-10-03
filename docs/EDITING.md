# Editing the website

## Connect

Sign in at [Pages CMS](https://app.pagescms.org), authorize its GitHub App for vlachosi/vlachosi.github.io, and choose **main**. Account authorization happens in GitHub; no credentials belong in the source files.

All development and editing happen on main. Save writes a Git commit and triggers the checked production build. New posts default to draft, but saved profile, published research, or CV changes can become live immediately after the build.

## Write a post

Choose Writing → New. Enter title, summary, publication date, and body. The date/title create its initial folder; later edits retain the URL. Add topics and an optional image with a description.

The body is Markdown/Quarto source, with no YAML editing required. Mathematical notation, code fences, raw HTML, and advanced article options are preserved. Use Quarto's visual editor as an optional companion for scientific writing.

Keep the draft switch on while working. Save before building a preview: builds use committed content on main. Clear the switch and save when ready to publish. A future date does not schedule publication.

## Preview

Use **Build preview** in Pages CMS or GitHub Actions → Build preview → Run workflow. The dedicated workflow validates and renders drafts without deploying.

After success, download **site-preview** from the run's Artifacts section. Extract it and serve that directory using an HTTP server to inspect it. Opening HTML directly from disk can prevent root-relative assets, PDF modules, and search from working. This is not a hosted preview URL.

The workflow must exist on main before GitHub permits dispatch. The button always previews saved main content; unsaved form edits are not included.

On first connection, create and reopen a draft on main, add an image, and build its preview. Keep sample research/project entries marked as drafts until ready. Selecting and saving a CV updates its public version after the build. The supplied offline form screenshots illustrate configuration, not a connected account.

## Replace the CV

1. Open CV and upload a PDF through Current CV PDF.
2. Select the uploaded file; uploading alone does not select the active version.
3. Set its optional updated date and save.
4. Preview the actual document, text, links, and download.
5. Check the successful main build and the public CV page.

Duplicate uploads can receive numbered filenames. Explicit selection ensures the latest chosen version becomes active. The build copies it to cv/vlachos-cv.pdf, preserving the download URL. That download remains usable if the embedded viewer fails.

Use a PDF smaller than 25 MiB. The build checks its path, header, and end marker; the rendered preview confirms the actual document works. Unselected uploads are not copied into the public site, but remain in the source repository and Git history.

Clear the selection to remove the public download and return the page to its empty state. Select an earlier uploaded version to roll back.

## Research, projects, and profile

Choose a supported research status. Add a main title link and optional labelled links to code, papers, or slides. Use homepage selection and order to feature records; lower numbers appear first. Unpublished and placeholder records are excluded before homepage limits are applied.

Profile settings update shared identity, biography, contact links, navigation/footer, and page metadata. Leave optional email/links blank when unused. Talks and Teaching switches control both navigation and publication.

## Recover edits

Use GitHub file/commit history to restore previous content or revert a commit, then rebuild. Content stays in the repository, so local editing remains available if the hosted dashboard is unavailable.
