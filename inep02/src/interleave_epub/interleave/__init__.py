"""Interleave the paragraphs of two epubs.

This is interactive, so all the things are loaded later,
when the user actually decides which to use.

This is basically the model in a model-view-something pattern.

There is some confusion because the Interleaver and the whole app_model
overlap almost completely. But I think that the interleaver should be
a separate thing, the app is another thing that uses the interleaver.

We might want to defer the translation of the paragraphs,
the language is the only thing that the app knows that the interleaver does not care about.
The interleaver only sees paragraphs, and knows that he should use the models.

The app loads the epub,
the epub automagically discover their original languages,
when the app sees that there are two epubs,
the translations are done,
the interleaver is setup.
"""
