"use client";

// R395: /showcase?slot=X redirects into the workspace (?invention=X)
// — the one experience. Old links keep working.

import { Suspense, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";

function RedirectInner() {
  const slot = useSearchParams().get("slot") ?? "";
  const router = useRouter();
  useEffect(() => {
    router.replace(slot ? `/?invention=${encodeURIComponent(slot)}` : "/");
  }, [slot, router]);
  return <div className="loading">Opening the workspace…</div>;
}

export default function ShowcaseRedirect() {
  return (
    <Suspense fallback={<div className="loading">Loading…</div>}>
      <RedirectInner />
    </Suspense>
  );
}
