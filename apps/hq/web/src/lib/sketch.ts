export const MAX_SKETCH_TEXT = 4000;
const words = new Intl.Segmenter(undefined, { granularity: 'sentence' });

/** Extract the leading points verbatim. The caller displays the result only as text. */
export function sketchPoints(source: string): string[] {
  return source.slice(0, MAX_SKETCH_TEXT).split(/\r?\n/).flatMap((line) => {
    const cleaned = line.replace(/^\s*(?:(?:[-*•]|#{1,6}|\d+[.)])\s+)?/, '').trim();
    return Array.from(words.segment(cleaned), ({ segment }) => segment.trim()).filter(Boolean);
  }).slice(0, 5);
}
