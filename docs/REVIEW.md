# Website management review

Keep Quarto and the static website. The main difficulty was the editing workflow: everyday updates required knowing filenames, YAML, template behavior, and Git. A browser content manager addresses that without replacing the site's design or adding a database/server to maintain.

The implemented approach uses [Pages CMS](https://app.pagescms.org) forms over the existing repository. Development and content editing both use **main**. Saving commits content; the checked production build can then publish it. Draft switches protect unfinished articles, while profile and selected-CV updates take effect after a successful build.

| Original friction | Implemented change |
| --- | --- |
| Adding a post required creating a folder and writing front matter correctly. | [Writing forms](../.pages.yml) create the initial date/title folder, default new posts to draft, and preserve their URLs on later edits. The article editor retains Quarto/Markdown source, equations, code, and custom HTML. |
| CV updates required replacing a specific repository file; the download depended on the viewer, and a wildcard could publish other PDFs in the same directory. | The CV form uploads and selects a document. Only that selection is copied to the stable `cv/vlachos-cv.pdf` address, with an optional updated date. The download works independently of the embedded viewer. |
| Biography, identity, and social links were duplicated across pages and configuration. Enabling Talks/Teaching required multiple edits. | [_data/profile.yml](../_data/profile.yml) supplies the shared profile and metadata; visibility switches control each optional page and its navigation together. |
| A typo in a paper's status could hide it silently. Placeholder records reached production, and homepage placement depended on list position. | Forms and build validation check supported fields. Production filters drafts/placeholders before homepage limits; explicit **featured** and **order** fields control selection. Empty states and venue rendering were corrected. |
| A successful render gave little assurance that links, metadata, draft exclusion, or the selected CV worked. | The build validates content, runs regression tests, renders both modes, and checks the resulting site before deploying production from main. The default sharing-image path was corrected for nested pages. |
| Previewing saved edits required local tools. | A separate **Build preview** action creates a downloadable draft-site artifact without deploying it. Normal publication runs also save this artifact. It is not a hosted preview URL. |

Both full production and draft renders, including the resulting-site checks, passed in the cloud environment. Pages CMS configuration was checked against its official implementation; its live account connection and authenticated save/upload flow still require the first-use check below. Supplied CMS screenshots are **offline form illustrations**, not evidence of a connected dashboard.

The remaining work, in priority order:

1. **Connect Pages CMS and complete one real editing cycle.** Authorize its GitHub App for this repository and select main. Create and reopen a draft, upload an image, save, and run Build preview. Then select the actual CV and inspect its pages, links, text selection, and download. The preview workflow must already exist on main before its button can run. Follow [Editing the website](EDITING.md); [CMS configuration notes](CMS-CONFIG.md) explain compatibility and publication behavior.

2. **Complete the requested repository rename manually.** The attempted rename to `ioannisvlachos.com` was blocked by GitHub integration permissions (HTTP 403). A repository owner can perform it in GitHub settings. Then update repository links and CMS access/selection, and verify Pages deployment, the existing `CNAME`, DNS, and HTTPS. The public site address is already `https://ioannisvlachos.com`; renaming the repository is a separate operation.

3. **Replace sample content with authentic material.** Research, Talks, and Teaching currently contain examples; no actual CV is selected, and contact email remains blank. Production now hides placeholder entries. Add real records and the intended PDF/email when ready, then deliberately clear the relevant placeholder/draft switches. A future post date does not schedule publication.

4. **Add a hosted draft preview only if artifact downloads remain inconvenient.** A separate preview target for saved main content would make the browser workflow smoother. Keep it separate from production publication; the current downloadable artifact is functional but requires serving the extracted site over HTTP.

5. **Define execution dependencies before publishing computational articles.** Ordinary prose, equations, and displayed code work with the current build. Executable R/Python posts need pinned dependencies or a deliberate frozen-output policy: `freeze: auto` may execute changed source, so committing `_freeze/` alone does not guarantee a runtime-free build.

Content remains in Git, with file history and local Quarto editing available for recovery. Draft source and uploaded documents in this public repository are public even when excluded from the built website. Keep the CMS schemas aligned with future content fields, especially the YAML lists whose unknown fields Pages CMS does not preserve automatically.
