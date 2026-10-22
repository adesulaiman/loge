"use client";

import { useTranslations } from "next-intl";
import Text from "@/refresh-components/texts/Text";

/** Owner of the application: company logo and name. */
export default function OwnerBadge() {
  const t = useTranslations("common");
  return (
    <div className="flex flex-col items-center gap-2 mt-8">
      {/* The logo has light text, so it sits on a dark tile in both themes. */}
      <div className="rounded-12 bg-black px-4 py-2">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/axon-logo.png"
          alt={t("owner.logo.alt")}
          className="h-10 w-auto"
        />
      </div>
      <Text as="p" secondaryBody text03>
        {t("owner.label")}
      </Text>
    </div>
  );
}
