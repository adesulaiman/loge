"use client";

import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { cn } from "@opal/utils";

export interface LogeSkyBackgroundProps {
  className?: string;
}

/**
 * Anime night-city / dawn sky from design-loge/loge-design.
 * Sits behind chat chrome; pointer-events none.
 */
export default function LogeSkyBackground({ className }: LogeSkyBackgroundProps) {
  const { resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    setMounted(true);
  }, []);

  const isDark = mounted && resolvedTheme === "dark";

  return (
    <div
      aria-hidden
      className={cn(
        "pointer-events-none absolute inset-0 overflow-hidden z-0",
        className
      )}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={isDark ? "/loge/sky-dark.svg" : "/loge/sky-light.svg"}
        alt=""
        className="absolute inset-0 h-full w-full object-cover object-bottom"
      />
      <div className="absolute inset-0 bg-linear-to-b from-transparent via-transparent to-background-neutral-00/80" />
    </div>
  );
}
