"use client";

import { Suspense } from "react";
import CopilotPageInner from "./copilot-inner";

export default function CopilotPage() {
  return (
    <Suspense
      fallback={
        <main className="flex flex-1 items-center justify-center p-6 text-sm text-muted-foreground">
          Loading Industrial Copilot…
        </main>
      }
    >
      <CopilotPageInner />
    </Suspense>
  );
}
