"use client";

// R395: /run?id=X redirects into the workspace (?run=X) — the one
// experience. Old links keep working.

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";

function RedirectInner() {
  const id = useSearchParams().get("id") ?? "";
  const router = useRouter();
  useEffect(() => {
    router.replace(id ? `/?run=${encodeURIComponent(id)}` : "/");
  }, [id, router]);
  return <div className="loading">Opening the workspace…</div>;
}

export default function RunRedirect() {
  return (
    <Suspense fallback={<div className="loading">Loading…</div>}>
      <RedirectInner />
    </Suspense>
  );
}
