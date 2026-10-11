import type { IconProps } from "@opal/types";

/** Loge mark (red sun + L arch). Kept as SvgOnyxLogo for import compatibility. */
const SvgOnyxLogo = ({ size, ...props }: IconProps) => (
  <svg
    height={size}
    viewBox="0 0 48 48"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    {...props}
  >
    <defs>
      <linearGradient
        id="logePlate"
        x1="6"
        y1="2"
        x2="42"
        y2="46"
        gradientUnits="userSpaceOnUse"
      >
        <stop offset="0" stopColor="#1A2742" />
        <stop offset="1" stopColor="#0A1120" />
      </linearGradient>
      <linearGradient
        id="logeArch"
        x1="15"
        y1="12"
        x2="33"
        y2="36"
        gradientUnits="userSpaceOnUse"
      >
        <stop offset="0" stopColor="#9DBBFF" />
        <stop offset="1" stopColor="#E9EEF8" />
      </linearGradient>
    </defs>
    <rect
      x="2.5"
      y="2.5"
      width="43"
      height="43"
      rx="12"
      fill="url(#logePlate)"
      stroke="#3E4E72"
      strokeWidth="1"
    />
    <rect
      x="5.5"
      y="5.5"
      width="37"
      height="37"
      rx="9.5"
      stroke="#FFFFFF"
      strokeOpacity=".12"
      strokeWidth=".75"
    />
    <path
      d="M15.5 21.5a8.5 8.5 0 0 1 17 0V35.5"
      stroke="url(#logeArch)"
      strokeWidth="1.1"
      strokeLinecap="round"
      strokeOpacity=".75"
    />
    <circle cx="24" cy="29.5" r="4.25" fill="#E23A26" />
    <path d="M18.5 32.6h11" stroke="#0A1120" strokeWidth="1" />
    <path
      d="M15.5 12.5V35.5H35.5"
      stroke="#F4F6FA"
      strokeWidth="2.2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M36.5 10.2l.7 2.1 2.1.7-2.1.7-.7 2.1-.7-2.1-2.1-.7 2.1-.7z"
      fill="#9DBBFF"
    />
  </svg>
);
export default SvgOnyxLogo;
