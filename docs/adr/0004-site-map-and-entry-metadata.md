# Separate site-map data from learning-entry content

The migration needs two kinds of source information. The home page and category pages need stable navigation facts and short direction-level copy, while project, knowledge, and research entries need Markdown bodies, front matter, and clean URLs. We will keep the former in one site-level data source and keep the latter in Markdown entries. Category templates discover entries by their validated `kind` and `order`; a category with no entries renders a shared empty state.

This keeps the content model precise: a learning direction or site page is not itself a learning entry, and an entry card is only a presentation of entry metadata. It also lets the generator render all five site-level routes without turning navigation shells into fake content entries or duplicating HString's description in hand-written HTML.

The alternatives were to keep each page as hand-written HTML or to make every site shell a special Markdown content type. Hand-written HTML would preserve the migration problem, while a page content type would mix navigation pages with the three stable learning-entry types and add routing rules that do not describe actual learning content. A small site-map source has the narrower responsibility.
