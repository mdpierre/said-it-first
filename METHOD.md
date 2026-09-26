# Method

How this pipeline was designed, and what broke the first time it ran on a
real archive. The scripts encode the fixes; this file explains why they exist.

The reference run: one person's ChatGPT export, **4,164 conversations over
nearly four years**, 1,628 of them substantial. Over about two weeks of
review, 126 shortlisted conversations were read and dispositioned and the
owner's idea-notes went from 73 to 120. All numbers below come from that run.

---

## The problem

If you think out loud in ChatGPT (voice mode on a walk, long reflections at
night), your chat history is your real journal. It is also unusable as one:
thousands of threads, most of them logistics, homework, code, or pasted
articles, with the reflective ones mixed in and half of every thread written
by the model.

The goal is two things from the same archive:

1. **A record of your thinking**: one note per idea, with how and why it
   changed over time.
2. **A small, current AI-context file**: who you are *now*, so your agents
   can be useful without being told everything each session.

These want opposite things. Old positions you've abandoned are the most
valuable material for (1) and actively harmful in (2). Volume helps (1) and
degrades (2). The pipeline routes one conversation two ways rather than
letting either goal filter the other.

## Design principles

**The idea must be yours; the sentence need not be.** Requiring handwritten
notes means the job never finishes. Letting the model write freely means the
notes fill with ideas the model had. The line: model-drafted prose is fine
when it renders thinking you actually did, and provenance is always
queryable (verbatim quotes are verbatim; paraphrase is labeled).

**Record deltas, not snapshots.** "In 2023 I thought X" is filler. The value
is *Was / Now / Because*: what moved, and what moved it.

**Strip the assistant before any model reads the corpus.** The assistant's
turns were 83% of the archive's volume and are exactly the words that must not
end up attributed to you. Removing them took the corpus from ~6.5M tokens to
~1M: small enough for one long-context read, and more correct at the same time.

**Scripts triage, models read, the human decides.** Each layer does what it's
good at. Nothing enters your notes without your explicit approval of that
content.

**Manual export batches, not a scraper.** Scraping your own account with
session cookies is against the provider's terms, breaks on every auth change,
and risks the account that is your capture layer. Export once or twice a year.

**Pull, not push.** No daily digest. You run it when you want it.

---

## What broke, and the fix in the code

### 1. A third of "your" words weren't yours

Of 701,883 words in user turns, **234,739 (33%) were not authored by the
user**: pasted articles and transcripts, answers picked from quiz menus, and
ChatGPT's suggested follow-up chips, clicked rather than typed.

A scorer that counts user words ranks homework and pasted reading at the top.
In the first ranking, a class-assignment thread was #4 overall.

**Fix:** `parse.classify_turn` labels every user turn `authored`,
`own_voice`, `pasted`, `quiz`, or `suggestion`, and every score runs on
authored words only.

### 2. Length penalties are a trap

The obvious fix for pastes is to penalize very long turns. That would have
deleted the most valuable material in the archive: **dictated voice memos**,
where the owner pasted a transcript of themselves thinking out loud. A memo
and a pasted article look identical to a word counter.

**Fix:** decide by *voice*, never length.
- An explicit preamble ("here's my voice memo") marks own-voice, and those
  turns are weighted **up**.
- With no preamble, a long turn is credited only if its first-person and
  spoken-filler density look like a person talking about themselves. On the
  reference corpus the populations separated cleanly: own dictation ran 10-15
  first-person words per 100 and 10-18 filler; pasted documents ran 0-1 and
  0-1. `synth stats` shows you where your own archive falls.

### 3. The agent's report said everything was fine. It wasn't.

This was the failure that mattered, and it was not the one anticipated. The
expected risk was old positions being asserted as current. What actually
happened was **authorship errors, in both directions**:

- The delta pass put paraphrase inside quotation marks twice, and quoted as
  the owner's a line ChatGPT had coined and the owner had echoed back.
- The ranking pass read the owner's own pasted voice memos as material they
  were consuming, and rejected the densest first-person document in the archive.

**Neither showed up in the agent's own summary.** Both were caught only by
checking claims against the source.

**Fix:** `synth verify` checks every quote of 40+ characters three ways:
verbatim in your turns, said by the assistant first and echoed back, or
silently cleaned up. It runs on every batch before review and on notes
before they are final. It exits non-zero on any failure.

### 4. A silent bug dropped a quarter of the corpus

Frontmatter was stripped with `body.split("\n---\n", 2)[-1]`. Any conversation
containing a markdown horizontal rule lost everything before it. **926 of
1,628 conversations were truncated; 24% of the owner's words silently
disappeared**, and two model passes had already run on the damaged corpus.

**Fix:** a proper frontmatter regex, a regression test, and a word-count
reconciliation in the voice stage that warns if output is short of input.
The general lesson: **count input and output at every stage.** `synth parse`
now accounts for every conversation it reads.

### 5. Returning to a thread isn't returning to a thought

"Days touched" was the heaviest signal: a conversation revisited over many
days seemed like one you kept thinking about. The top of the list filled with
standing-instruction threads, like a daily check-in touched on 16 days with 373
words total.

**Fix:** `content_days` counts only days with 80+ authored words. On the
reference corpus, 263 conversations were touched on 2+ days; only 53 had real
content on 2+ days.

### 6. Titles lie; bodies route

Topic routing on titles missed about three quarters of the top 60. Titles are
auto-generated from whatever line opened the thread. Routing on a frequency
bag of the owner's own words, requiring two distinct matching terms, raised
coverage from 25% to 34%.

**And that's roughly the ceiling for regex.** People reflect in feeling words
and function words, not topic nouns. The best material often gets no topic at
all. That's why a model reads the shortlist (stage 4) instead of trusting it.

### 7. The archive is a trailing indicator

The export ends on its export date. During review, the archive supported
recording one direction as abandoned; the owner had restarted it in the
five weeks since. **Never let archive silence stand in for a current
decision.** The agents are told to ask.

### 8. Scope by feel was wrong

The plan was to import three to six months. The export covered four years,
and most of the important transitions were older than the planned cutoff. A
six-month window would have caught the conclusions and none of the changes
that led to them.

---

## Yield, honestly

Voice memos and personal reflection produced the most notes per word read.
Sections dominated by the logistics of directions the owner had since dropped
produced very few, which was correct: the machinery of an abandoned plan is
not thinking. Low yield from a section is a result, not a failure.

## Known limits

- Authorship classification is triage. It will not catch every paste shape.
  The honest upgrade is a cheap per-turn model classification.
- Thresholds were calibrated on one English-speaking person's archive. Run
  `synth stats` on yours first.
- Topic routing needs a model or embedding pass to go much past a third of
  conversations.
- ChatGPT exports only, for now. The pipeline is shaped for other sources
  (a sibling adapter for a Discord export was built on the same pattern); a
  new source needs only its own `parse`.
