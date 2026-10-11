import { fetchStandardSettingsSS } from "@/lib/settings/svcSS";
import FeatureRedirect from "@/loge/app/FeatureRedirect";

export default async function PaidFeatureLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Gate paid features on the runtime license status.
  try {
    const settings = await fetchStandardSettingsSS();
    if (settings) {
      if (settings.ee_features_enabled === false) {
        // When the app is in GATED_ACCESS, defer to the root layout's
        // GatedContentWrapper which handles path-based exemptions (e.g.
        // allowing /admin/billing for license management).
        if (settings.application_status === "gated_access") {
          return children;
        }

        return <FeatureRedirect />;
      }
    }
  } catch (error) {
    // If settings fetch fails, allow access (fail open for better UX)
    console.error("Failed to fetch settings for paid feature check:", error);
  }

  return children;
}
