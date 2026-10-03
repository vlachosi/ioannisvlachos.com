# Editing the website

## Connect once

Sign in to [Pages CMS](https://app.pagescms.org), authorize its GitHub App for **[vlachosi/ioannisvlachos.com](https://github.com/vlachosi/ioannisvlachos.com)**, and select **main**. All editing happens on main.

The content tabs follow **About → Research → Code → Teaching → Talks → Blog → CV**. Teaching, Talks, and Blog remain editable in Pages CMS while their public pages are disabled. The website omits disabled sections from navigation.

**Save creates a commit and starts the production build.** Draft articles stay off the live site; saved profile, CV, and published-record changes can go live after the build succeeds. Draft source and uploaded files remain visible in this public repository.

The live sign-in/save/upload flow has not yet been verified. Start by creating and reopening a draft, adding an image, and building a preview. Any supplied offline CMS screenshots illustrate forms, not a connected account.

## Write and publish a blog post

1. Choose **Blog → New**. Enter the title, summary, date, and article; add topics and an optional social preview image with a description.
2. Leave **Keep as draft** on, save, and preview the result.
3. When ready, clear the draft switch and save. Check the successful GitHub Actions build and the live article.

The article editor uses Markdown/Quarto source without requiring YAML editing. Equations, code fences, and custom HTML are preserved. The initial title/date set the URL; later edits retain it. A future date does **not** schedule publication.

When enabled, the Blog lists newest posts first. Readers can sort by date or title, search titles, summaries and topics, and combine the search with a topic filter. The Topics panel is built automatically from each post's **Topics** field; reuse topic names consistently. Draft topics appear only in draft previews. Topic links can be bookmarked or shared.

For an inline image, upload through **Images and attachments**, then insert its public path, for example `![Description](/assets/uploads/figure.png)`.

## Show or hide the Blog

Open **About → Page visibility → Publish blog page**. This switch is on by default. Turn it off and save to remove the Blog index and articles, navigation link, homepage section, search and sitemap entries, and Blog subscription option from the built website. The same switch applies to draft previews.

Posts, topics, Blog settings, and the CMS editor stay intact. Turn the switch back on to restore the Blog and its sorting, search, topic filters, and subscriptions; each post retains its own draft setting and URL. While disabled, `/writing/index.xml` remains a valid empty RSS feed for existing subscribers, and All updates contains no Blog posts. Previously downloaded feed items may remain in a reader.

The publication and preview workflows use clean builds. If working locally, stop any live preview and run a full `quarto render --clean` after changing the switch; use `quarto render --profile drafts --output-dir _site-preview --clean` for draft previews. A partial render can leave old pages behind.

## Preview saved edits

Choose **Build preview** in Pages CMS, or GitHub Actions → Build preview → Run workflow. The workflow must exist on main, and your account needs Actions access. It includes saved drafts on enabled pages and never deploys; unsaved form changes are not included. A disabled Blog stays absent even in this preview.

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

## Maintain Code entries

Open **Code** and choose a **Section**: Packages, Replication code, or Templates.

| Section | What to enter |
| --- | --- |
| Packages | Use the package name as the title and describe its purpose. Add an optional version and tags for languages or relevant topics. Use **Docs** and **Source** labels for documentation and repository links. |
| Replication code | Use the paper title as the entry title. Add the year, authors, and publication venue when available, followed by a short description of the replication code. Use **Paper** and **Code** labels for the paper and code links. |
| Templates | Give the template a descriptive title, explain its purpose, and add relevant tags and links. |

Year, authors, venue, and version are optional. Add extra links only when useful. Select **Feature on homepage** when appropriate and set **Display order**; lower numbers appear first within each section. On the live Code page, sections with no published entries are hidden.

## Announce Research and Code updates

The footer's RSS icon opens [Subscribe](https://ioannisvlachos.com/subscribe.html), where readers can choose All updates, Research, Code, and Blog when enabled, and add the feed to an RSS reader. Subscriptions use RSS; there is no email signup.

To announce a Research or Code entry, fill in its optional **RSS announcement** group:

1. Set an ID such as `market-news-study`, using lowercase words separated by hyphens. The ID must be unique within Research or Code; keep it unchanged when editing the entry's title or description.
2. Set the announcement date in `YYYY-MM-DD` format. Use the date of the announcement, not the paper's bibliographic year. Both ID and date are required when using this group.
3. Save and check the successful production build. The item appears in its section's feed and All updates when its announcement date is no later than the build date in **Australia/Melbourne**.

Leave the group empty to display a published entry without announcing it. A future announcement date affects RSS only; it does not hide the entry from its page. The site has no scheduled daily build, so a future announcement needs a successful build on or after that Melbourne calendar date, triggered by a push to main or a manual **Publish site** workflow run.

Drafts and placeholders are excluded from the All updates, Research, and Code feeds, including in preview builds. When the Blog is enabled, its posts use the existing feed at `/writing/index.xml`. Disabling the Blog leaves that feed empty at the same address so existing subscriptions can resume when it is enabled again.

## Other updates

| Form | What to do |
| --- | --- |
| Research | Choose a research status and add paper links. Use **Feature on homepage** and **Display order**; lower numbers appear first. |
| About | Update identity, biography, email, and profile URLs, including ResearchGate. **More about me** adds text only to About. |
| Talks / Teaching | Edit the records, then enable the page under About; its switch controls navigation and publication together. |

The shared biography appears on the homepage and About page as two paragraphs; keep the blank line between them. Blank profile URLs are omitted from homepage and Research buttons. About also omits any empty profile, social, or email entry. Add a URL or contact email to show its link, or clear it to hide the link again.

The website's social thumbnail updates automatically after a successful build when you change **Name**, **Role**, or **Affiliation** in About. It uses abstract contours and the site fonts, with your name on one line and no biography text. You do not need to edit or upload a thumbnail manually. Individual Blog posts can still use their own social preview image. Sharing services may cache an older preview until they refresh the page.

Keep unfinished entries as drafts. Drafts and placeholders appear only in draft previews.

Use GitHub file/commit history to restore content or revert a mistaken change. Local editing remains available if the dashboard is unavailable.
