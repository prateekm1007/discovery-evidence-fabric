// R393 (deployment-defect fix): the design system MUST be imported here.
// The webapp shipped since R389 with globals.css present but imported by
// NOTHING — the static export therefore contained zero CSS and the public
// deployment rendered as browser-default HTML (measured on the deployed
// host: no <link rel="stylesheet"> in any exported page, no
// _next/static/css/ directory in out/). One import; no other change.
import "./globals.css";

export const metadata = {
  title: "Toscanini",
  description:
    "Give Toscanini a real problem. It will investigate the evidence, challenge its own ideas, and develop the strongest invention it can defend — a technology package with an inspectable 3D design.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
