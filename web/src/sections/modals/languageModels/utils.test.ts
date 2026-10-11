import type { ModelConfiguration } from "@/lib/languageModels/types";
import { mergeFetchedModelConfigurations } from "./utils";

jest.mock("@/sections/model-selector/setting-controls", () => ({
  ALL_REASONING_STOPS: ["off", "low", "medium", "high", "xhigh"],
  maxReasoningStop: () => -1,
  minReasoningStop: () => 0,
}));

jest.mock("@/lib/languageModels/hooks", () => ({
  useWellKnownLLMProvider: () => ({ wellKnownLLMProvider: null }),
}));

function model(
  name: string,
  overrides: Partial<ModelConfiguration> = {}
): ModelConfiguration {
  return {
    name,
    is_visible: true,
    max_input_tokens: null,
    supports_image_input: false,
    supports_reasoning: false,
    ...overrides,
  };
}

describe("mergeFetchedModelConfigurations", () => {
  it("keeps prior visibility and marks new models hidden by default", () => {
    const existing = [model("a", { is_visible: true })];
    const fetched = [model("a"), model("b", { is_visible: true })];

    const merged = mergeFetchedModelConfigurations(fetched, existing);

    expect(merged.find((m) => m.name === "a")?.is_visible).toBe(true);
    expect(merged.find((m) => m.name === "b")?.is_visible).toBe(false);
  });

  it("marks newly discovered models visible when defaultNewVisible is true", () => {
    const existing = [model("z-ai/glm-5.3", { is_visible: true })];
    const fetched = [
      model("z-ai/glm-5.3"),
      model("deepseek/deepseek-v4-flash", { is_visible: true }),
    ];

    const merged = mergeFetchedModelConfigurations(fetched, existing, {
      defaultNewVisible: true,
    });

    expect(merged.find((m) => m.name === "z-ai/glm-5.3")?.is_visible).toBe(
      true
    );
    expect(
      merged.find((m) => m.name === "deepseek/deepseek-v4-flash")?.is_visible
    ).toBe(true);
  });

  it("preserves prior hidden state even when defaultNewVisible is true", () => {
    const existing = [
      model("deepseek/deepseek-v4-flash", { is_visible: false }),
    ];
    const fetched = [model("deepseek/deepseek-v4-flash", { is_visible: true })];

    const merged = mergeFetchedModelConfigurations(fetched, existing, {
      defaultNewVisible: true,
    });

    expect(merged[0]?.is_visible).toBe(false);
  });
});
