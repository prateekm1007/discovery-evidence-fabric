export const metadata = {
  title: "Toscanini",
  description:
    "Describe an engineering or scientific problem. Toscanini runs a real discovery-and-invention engine and returns a credible technology package with an inspectable 3D design.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <header className="topbar">
            <div className="brand">
              Toscanini<em>.</em>
            </div>
            <div className="meta">
              discovery · invention · evidence · 3D design
            </div>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}
