# Editing the website

## Connect

Commit the integration to a GitHub branch, sign in at [Pages CMS](https://app.pagescms.org), and authorize its GitHub App for vlachosi/vlachosi.github.io. Choose the repository and the branch containing .pages.yml. Account authorization happens in GitHub; no credentials belong in the source files.

Save writes a Git commit. Saving on main triggers live deployment after validation; use another branch and a pull request when you want review first. New posts default to draft, but saved profile, research, or CV changes on main can become live immediately after the build.

## Write a post

Choose Writing → New. Enter title, summary, publication date, and body. The date/title create its initial folder; later edits retain the URL. Add topics and an optional image with a description.

The body is Markdown/Quarto source, with no YAML editing required. Mathematical notation, code fences, raw HTML, and advanced article options are preserved. Use Quarto's visual editor as an optional companion for scientific writing.

Keep the draft switch on while working. Save before building a preview: builds use committed content. Clear the switch and save on main, or merge the content branch, when ready. A future date does not schedule publication.

## Preview

Use **Build preview** in Pages CMS or GitHub Actions → Build preview → Run workflow. The dedicated workflow validates and renders drafts without deploying.

After success, download **site-preview** from the run's Artifacts section. Extract it and serve that directory using an HTTP server to inspect it. Opening HTML directly from disk can prevent root-relative assets, PDF modules, and search from working. This is not a hosted preview URL.

The workflow must exist on the repository's default branch before GitHub permits dispatch. The button previews saved branch content; unsaved form edits are not included.

On first connection, create and reopen a draft on a working branch, add an image, edit research links, and select a CV. Inspect the resulting diff and preview before relying on the hosted integration. The supplied offline form screenshots illustrate configuration, not a connected account.

## Replace the CV

1. Open CV and upload a PDF through Current CV PDF.
2. Select the uploaded file; uploading alone does not select the active version.
3. Set its optional updated date and save.
4. Preview the actual document, text, links, and download.
5. Publish through your chosen branch workflow.

Duplicate uploads can receive numbered filenames. Explicit selection ensures the latest chosen version becomes active. The build copies it to cv/vlachos-cv.pdf, preserving the download URL. That download remains usable if the embedded viewer fails.

Use a PDF smaller than 25 MiB. The build checks its path, header, and end marker; the rendered preview confirms the actual document works. Unselected uploads are not copied into the public site, but remain in the source repository and Git history.

Clear the selection to remove the public download and return the page to its empty state. Select an earlier uploaded version to roll back.

## Research, projects, and profile

Choose a supported research status. Add a main title link and optional labelled links to code, papers, or slides. Use homepage selection and order to feature records; lower numbers appear first. Unpublished and placeholder records are excluded before homepage limits are applied.

Profile settings update shared identity, biography, contact links, navigation/footer, and page metadata. Leave optional email/links blank when unused. Talks and Teaching switches control both navigation and publication.

## Recover edits

Use GitHub file/commit history to restore previous content or revert a commit, then rebuild. Content stays in the repository, so local editing remains available if the hosted dashboard is unavailable.
