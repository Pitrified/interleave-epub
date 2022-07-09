# Interleave epubs

A tool to interleave the paragraphs of two books in different languages.

Paragraphs in the language you are learning will be shown first,
followed by the translated paragraph in the language you know.

## TODOs

### Done

## IDEAs

* Global state should not be a boring dict,
  should be a fancy class with defaults inside,
  that knows how to get the assets
  and only calls the loading functions when a key is requested.

  Maybe defaults should be in the `html`?
  For example the fake file names for 

* We need an `active_sent_src_id`, that can be set by clicking src button,
  and will be matched to the `dst_id` when clicking dst button.

### App structure/flow

* Buttons to change chapter.
  Dropdown list in the sidebar.
* Buttons to change `lang_src` sentence.
* Button to save result.
  Should this be presented as a download popup?
  Also in the sidebar.

#### General flow:

1. Open on route `/` where you drop the two files.
1. Match the languages of the two files.
1. Parse the EPubs.
1. Go to `/align/ch_id`? Or stay on `/`? Probably go to `/align`.
1. Show similarity plot for fun.
1. Show alignment plot for fun.
1. Show table with mismatched sentences, `lang_src, lang_dst, button`.
   When the button is clicked update the sentence matches.

#### Handle requests:

1. There is a central method registered on `/` (or whatever page) that handles the requests.
1. Calls the right method to deal with the input.
1. That method will update the global (?) variables.
   And recompute `ooo` obvs.
1. Another method that prepares lists of sentences to show.
1. The central controller will call the render template.

#### Manually fix alignment

1. Find the first ooo
1. Find the best match for dst:
   need to interpolate neightbors, the actual match is wrong lmao
1. Show sents for both sides,
   with buttons to adjust `current_ooo` and `hopeful_match`
1. Also buttons to wildly change `current_ooo` and `hopeful_match`, `+-10`
1. Button to confirm and save

Use a getter to safely extract data from lists.

`[dst_id for dst_id in flattened_matches if dst_id != current_ooo_i]`

### Package structure

* Should we have more than one package? For EPubs, for matching... NO

### Misc

* Button with `form/POST` rather than link? YES
* Somehow save the aligned states.
  Maybe after every button click. YES
* Option in the sidebar to hide/show similarity/alignment plots.
* Drag and drop is cool but you can also use
  https://getbootstrap.com/docs/5.2/forms/form-control/#file-input
* Sample form
  https://getbootstrap.com/docs/5.2/forms/form-control/#readonly-plain-text
* A whole bunch of language tag wrangling to load the right models.
* As the app waits for user input on the first page,
  start loading the epubs assuming the lang tags are correct.
* Find a way to make `TranslationPipeline` accept batches of sentences.
* Chapter align as well,
  some buttons to begin with,
  maybe a slider?
  Then of course you could infer it with similarity `:D`.
* Global state should not be a boring dict,
  should be a fancy class with defaults inside,
  that knows how to get the assets
  and only calls the loading functions when a key is requested.
