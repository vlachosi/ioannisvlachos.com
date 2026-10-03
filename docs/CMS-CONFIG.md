# CMS configuration notes

[`.pages.yml`](../.pages.yml) defines the forms for the hosted [Pages CMS](https://app.pagescms.org). The public website remains a Quarto site on GitHub Pages; the CMS edits its source files through GitHub.

## Connect and publish

Sign in to Pages CMS with GitHub, install its GitHub App for this repository, then open the repository and the intended branch. Configuration must exist on that branch before its forms appear. No application secrets belong in this repository.

**Saving commits to the selected branch.** Saving on `main` triggers the normal build and, if successful, publication. Saving on a working branch does not publish the website; open a pull request and merge it after reviewing the rendered result. This configuration does not add dashboard-native pull request creation, approval, or a Publish button.

New writing defaults to `draft: true`. Clear **Keep as draft** when the article is ready for a production build. A future post date does not schedule publication. Drafts and unused uploads are not confidential: their source files are visible in this public repository.

The **Build preview** action starts the dedicated [preview workflow](https://github.com/vlachosi/vlachosi.github.io/actions/workflows/preview.yml) for the branch selected in Pages CMS. Save your edits first: unsaved form changes are not included. The workflow renders the site with drafts and creates a `site-preview` artifact; it never deploys the public website, including when started on `main`. Saving edits on `main` still triggers the separate publication workflow described above.

Follow the run's progress in GitHub Actions, then download `site-preview` from its Artifacts section after it succeeds. The artifact is a rendered site bundle, not a hosted preview URL. Serve its extracted directory over HTTP to inspect it; opening `index.html` directly does not reliably resolve the site's root-relative assets. The normal CI workflow also produces a draft preview artifact for its runs. Use the site's local preview workflow for an immediately browsable version.

The Pages CMS button requires GitHub Actions access and the preview workflow to have been added to the default branch. Its dispatch contract is `workflow_dispatch` with a string `payload` input; Pages CMS sends the selected branch and action context there. No preview workflow consumes the payload as shell commands. The button and hosted authentication have not been exercised against the live repository. A screenshot of an offline form preview demonstrates the fields only, not a live authenticated CMS session.

## Form contracts

| Form | Stored content | Behavior |
| --- | --- | --- |
| Writing | `writing/posts/<date>-<title>/index.qmd` | The initial post date and title generate the folder. Later edits retain its URL. Renaming through the CMS is disabled. |
| Research, Projects | Existing YAML lists | Every supported field is modelled, including links, placeholder/draft status, homepage selection, and display order. |
| Profile and contact | `_data/profile.yml` | Shared homepage/About identity, contact links, and optional Talks/Teaching visibility. |
| CV | `_data/cv.yml` | Selects a PDF from `_cv-uploads/`; the build prepares the stable `cv/vlachos-cv.pdf` download. |
| Talks, Teaching | Existing YAML lists | Edit content here; enable the page in Profile and contact. |

Writing and biography use a **Markdown source editor**. Equations, Quarto attributes, executable cells, and raw HTML are not passed through a generic rich-text editor. Use Quarto's own visual editor when a visual writing interface is needed. Executable articles still require their dependencies and valid frozen output; uploading source in the CMS does not execute it.

The **Images and attachments** media library uploads to `assets/uploads/`. For an inline image, upload it there and use its public path in Markdown, for example `![Description](/assets/uploads/figure.png)`. The **Listing image** field selects an image from the same library.

For CV updates, upload the PDF in the CV form, select it as **Current CV PDF**, optionally update its date, and save the form. Uploading alone does not select a version. Duplicate filenames may gain a numeric suffix; this is why the form selects a source file instead of relying on replacement of an existing filename. Clearing the selection restores the site's CV placeholder. Only the selected PDF is copied to the public CV path; uploads still exist in Git history and the public source repository.

## Preservation and validation

`settings.content.merge: true` retains post metadata that is outside the forms, including the sample article's `include-after-body` script. The current Pages CMS implementation does **not** merge top-level array files. Keep the complete Research, Projects, Talks, and Teaching schemas in sync when adding fields, or form saves can remove unknown fields. YAML formatting and comments may be rewritten by the CMS serializer.

The configuration was checked against the official Pages CMS source at commit [`6f4e860`](https://github.com/pages-cms/pages-cms/tree/6f4e860a35d934406580287e7042e5e111e207a1), version 2.1.8: its configuration schema, normalization, nested filename generation, and YAML/frontmatter serialization. This verifies source compatibility, not a completed authenticated save in the hosted application. Before first use on `main`, create and reopen a draft, add an image, edit a list item, and select a CV on a working branch; inspect the diff and rendered result before merging.

Official references: [configuration fields](https://pagescms.org/docs/configuration/content/fields/), [whole-file lists](https://pagescms.org/docs/configuration/content/list/), [filename templates](https://pagescms.org/docs/configuration/content/filename/), [media](https://pagescms.org/docs/configuration/media/), [settings](https://pagescms.org/docs/configuration/settings/), [custom Actions](https://pagescms.org/docs/configuration/actions/), and [GitHub connection](https://pagescms.org/docs/quick-start/).
