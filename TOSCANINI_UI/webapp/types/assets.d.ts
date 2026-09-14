// Ambient module declarations for assets TypeScript does not type.
// The KaTeX stylesheet is imported lazily inside lib/MathText.tsx —
// Next.js bundles it with that dynamic chunk; tsc only needs to know
// the import is intentional.
declare module "katex/dist/katex.min.css";
