# Week 7.6 — RAG Failure Scenarios

The central question: **"What should the AI do when it doesn't know?"**
Expected answer: **it should not invent an answer.**

This file maps every scenario from the checklist to exactly how this
project handles it, and how to test it yourself.

---

### 1. Question not in documents
**Handling:** `document_store.get_relevant_context()` drops any chunk
scoring below `RAG_MIN_SCORE` (default 0.2 cosine similarity) before
it ever reaches the prompt. If nothing survives the filter, the
context block sent to the model literally says *"No relevant excerpts
were found..."*, and `prompts.DOCUMENT_QA_INSTRUCTIONS` instructs the
model to say it doesn't have enough information in that case.
**Test:** Load a document about password resets, ask *"What's the
capital of France?"*. Expect: an "I don't have enough information"
answer, no citations shown (the UI shows the "No excerpt scored as
relevant" note instead of source pills).

### 2. Incorrect question (false premise)
**Handling:** No special code path — relies on the prompt instruction
"never invent... use ONLY the context" plus retrieval naturally
finding nothing relevant to a premise the documents don't support.
**Test:** *"Why did you remove the refund policy last month?"*
(when no such removal is documented). Expect the model to not play
along with the false premise, and either say it has no information
about that, or answer only the part it can verify.

### 3. Ambiguous question
**Handling:** Not resolved automatically — this is a genuine RAG
limitation worth demonstrating, not hiding. Retrieval returns
whatever's closest by embedding similarity, which may not match what
the user actually meant.
**Test:** Load two documents, one about "account settings" and one
about "billing settings". Ask *"How do I change my settings?"*.
Expect: retrieval pulls from one or both; a good answer distinguishes
them or asks for clarification. Worth noting in your write-up: adding
a clarifying-question step is a natural next improvement here.

### 4. Very long question
**Handling:** No truncation — it's passed through normally.
`config.MAX_COMPLETION_TOKENS` bounds only the *output*; the input is
naturally bounded by the model's context window and tracked by the
token-usage bar in the UI.
**Test:** Paste several paragraphs as a question. Expect: it still
works, `token_usage.turn_prompt_tokens` in the response reflects the
larger input.

### 5. Multiple relevant documents
**Handling:** This is *why* the document store supports more than one
document at once (Week 7's biggest structural change from earlier
weeks). `get_relevant_context()` searches across all loaded documents
by default; retrieved chunks from different `doc_id`s all appear in
the same CONTEXT block, each separately labeled.
**Test:** Load "Password Reset Guide" and "Account Recovery Guide".
Ask *"I'm locked out, what are my options?"*. Expect: both sources
cited if both are genuinely relevant.

### 6. Conflicting documents
**Handling:** The prompt explicitly instructs: *"If different sources
in the context disagree with each other, point out the disagreement
rather than silently picking one."* Both conflicting chunks are
retrieved and shown to the model side by side (it isn't deduplicated
by document, unlike the Week 6 mini project's search results).
**Test:** Upload two small `.txt` files with contradictory info, e.g.
`policy_v1.txt`: "Refunds are available within 14 days." and
`policy_v2.txt`: "Refunds are available within 30 days." Ask *"How
many days do I have for a refund?"*. Expect: the model flags the
conflict rather than confidently stating one number. If it doesn't,
that's a real finding worth writing up — cite the exact question and
answer as your evidence.

### 7. Empty document
**Handling:** `document_store.load_document()` raises `ValueError`
before anything is indexed if `parse_document()` returns no segments
at all — caught in `routes/chat_routes.py` and returned as a 400 with
a clear message.
**Test:** Upload a 0-byte `.txt` file. Expect: an error response,
nothing added to the document library, `tests/test_document_store.py
::test_empty_document_is_rejected` covers this directly.

### 8. Duplicate document
**Handling:** Deliberately **not blocked** — `load_document()` hashes
the extracted text (SHA-256) and, if it matches an already-loaded
document, still indexes it but sets `duplicate_of` to the earlier
doc's id. The UI shows a "Duplicate content" badge. This was a design
choice: silently rejecting duplicates would hide a real signal (the
user re-uploaded something on purpose, maybe under a new filename);
silently double-indexing without saying anything would double the
weight that content gets in retrieval without the user knowing.
**Test:** `tests/test_document_store.py::test_uploading_identical_
content_is_flagged_as_duplicate` covers this exactly.

### 9. Poorly formatted PDF
**Handling:** `rag/parsers.py::parse_pdf()` wraps each page's
`extract_text()` call in its own `try/except` — one unreadable/
corrupted page returns an empty string and is skipped, rather than
crashing extraction for the whole document. `rag/text_cleaning.py`
also specifically handles the artifacts poorly-formatted PDFs produce:
hyphenated line-break words re-joined, stray page-number-only lines
stripped, hard-wrapped lines re-flowed into paragraphs.
**Test:** Try a scanned (image-only) PDF — expect a clean "No readable
text was found" error (same path as scenario 7), not a crash. Try a
PDF with a few pages of garbled/corrupted text mixed with clean pages
— expect the clean pages are still indexed.

---

## Summary for a quick verbal answer

*"When the AI doesn't know, it should say so — not guess."* This
project enforces that at two levels: **retrieval** (a similarity
threshold keeps irrelevant chunks out of the prompt in the first
place) and **the prompt itself** (explicit instructions to admit
uncertainty, flag conflicts, and never fabricate a source). The
citations shown in the UI come from the actual retrieved chunks, not
from parsing the model's text — so even if the model's own "Sources:"
line were wrong, the UI's citation pills would still be honest.