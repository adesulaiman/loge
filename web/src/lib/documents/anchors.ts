/** Find a comment's quoted text again in the current document text. */

export interface QuoteMatch {
  start: number;
  end: number;
}

const CONTEXT_CHARS = 40;

function commonSuffixLength(a: string, b: string): number {
  let n = 0;
  while (
    n < a.length &&
    n < b.length &&
    a[a.length - 1 - n] === b[b.length - 1 - n]
  ) {
    n += 1;
  }
  return n;
}

function commonPrefixLength(a: string, b: string): number {
  let n = 0;
  while (n < a.length && n < b.length && a[n] === b[n]) n += 1;
  return n;
}

/**
 * Locate quote in text. When it occurs more than once, pick the occurrence whose
 * surrounding text best matches prefix and suffix. Returns null if it is gone.
 */
export function locateQuote(
  text: string,
  quote: string,
  prefix: string,
  suffix: string
): QuoteMatch | null {
  if (!quote) return null;
  const starts: number[] = [];
  let from = 0;
  for (;;) {
    const at = text.indexOf(quote, from);
    if (at === -1) break;
    starts.push(at);
    from = at + 1;
  }
  if (starts.length === 0) return null;

  let best = starts[0] ?? 0;
  let bestScore = -1;
  for (const at of starts) {
    const before = text.slice(Math.max(0, at - CONTEXT_CHARS), at);
    const after = text.slice(
      at + quote.length,
      at + quote.length + CONTEXT_CHARS
    );
    const score =
      commonSuffixLength(before, prefix) + commonPrefixLength(after, suffix);
    if (score > bestScore) {
      best = at;
      bestScore = score;
    }
  }
  return { start: best, end: best + quote.length };
}

/** Text just before and after a selection, for anchoring. */
export function anchorContext(
  fullText: string,
  start: number,
  end: number
): { prefix: string; suffix: string } {
  return {
    prefix: fullText.slice(Math.max(0, start - CONTEXT_CHARS), start),
    suffix: fullText.slice(end, end + CONTEXT_CHARS),
  };
}
