import { anchorContext, locateQuote } from "@/lib/documents/anchors";

describe("locateQuote", () => {
  it("finds a unique quote", () => {
    expect(locateQuote("alpha beta gamma", "beta", "", "")).toEqual({
      start: 6,
      end: 10,
    });
  });

  it("returns null when the quote is gone or empty", () => {
    expect(locateQuote("alpha beta", "delta", "", "")).toBeNull();
    expect(locateQuote("alpha beta", "", "", "")).toBeNull();
  });

  it("uses the surrounding text to pick between repeats", () => {
    const text = "one item. two item. three item.";
    const second = text.indexOf("item", 5);
    const { prefix, suffix } = anchorContext(text, second, second + 4);
    expect(locateQuote(text, "item", prefix, suffix)?.start).toBe(second);
  });
});
