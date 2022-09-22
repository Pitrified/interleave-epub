# TODOs and IDEAs

## Better access to paragraphs

Should have `num_par`, `num_chap` as attributes of `Paragraph` and `Chapter`.

Use `Epub.get_par(ch_id, par_id, which_trad)` and `Chapter.get_par(par_id, which_trad)`
to access paragraph.

## Batched translations

Defer the translations inside `TradPipelineCache`
and only do them when a `get_par('trad')` is called.

## Chapters in the book

### Order of the chapters

An epub could have weird chapter file names,
where the number regex fails,
so the files would be unsorted.

`->`
Show the chapter names of the two books side by side,
and let the user pick the right one.

### Valid chapters

There could be cover/preface chapter at the beginning,
that match the number regex.

`->`
A pop up to set first and chap nums as a form in `/load`.

`->`
Show the chapter names and the first few paragraphs,
and let the user pick the first.

## Sentences

### Short sentences

The sentences found by spacy are too short sometimes.

`->`
Merge them.

`->`
Completely skip the alignment of that sentences,
and inherit the value of the previous long sentence.

```
Align at paragraph level!
Use the sentence greedy+rescaled for a best guess,
then present paragraph by paragraph for alignment.
```
