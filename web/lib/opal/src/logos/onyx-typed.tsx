import type { IconProps } from "@opal/types";

/** Loge wordmark. Red sun for the O. Kept as SvgOnyxTyped for import compatibility. */
const SvgOnyxTyped = ({ size, ...props }: IconProps) => (
  <svg
    height={size}
    viewBox="0 0 148 40"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    {...props}
  >
    <text
      x="0"
      y="30"
      fill="var(--theme-primary-05)"
      style={{
        fontFamily:
          'var(--font-loge-brand), "Dela Gothic One", "Zen Kaku Gothic New", sans-serif',
        fontSize: "32px",
        letterSpacing: "0.06em",
      }}
    >
      L
    </text>
    <circle cx="52" cy="22" r="11" fill="var(--theme-red-05, #D7301F)" />
    <text
      x="68"
      y="30"
      fill="var(--theme-primary-05)"
      style={{
        fontFamily:
          'var(--font-loge-brand), "Dela Gothic One", "Zen Kaku Gothic New", sans-serif',
        fontSize: "32px",
        letterSpacing: "0.06em",
      }}
    >
      GE
    </text>
  </svg>
);
export default SvgOnyxTyped;
