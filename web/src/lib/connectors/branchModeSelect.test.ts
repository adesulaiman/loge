import { ValidSources } from "@/lib/connectors/types/source";

import { createConnectorInitialValues } from "./utils";

describe("branch_mode select defaults", () => {
  it.each([ValidSources.GitHub, ValidSources.GitLab] as const)(
    "defaults %s branch_mode to the API token, not the label",
    (source) => {
      expect(createConnectorInitialValues(source)).toMatchObject({
        branch_mode: "single",
      });
    }
  );
});
