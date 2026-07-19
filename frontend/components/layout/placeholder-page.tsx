import { AppHeader } from "@/components/layout/app-header";

type PlaceholderPageProps = {
  title: string;
  description: string;
  note?: string;
};

/** Shell placeholder — no fake business data (Milestone 1.8.5). */
export function PlaceholderPage({
  title,
  description,
  note = "This screen is wired in the enterprise shell. Domain content arrives in later milestones.",
}: PlaceholderPageProps) {
  return (
    <>
      <AppHeader title={title} description={description} />
      <main className="flex-1 overflow-y-auto p-5">
        <div className="mx-auto max-w-3xl rounded-lg border border-border bg-card p-6 shadow-sm">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
            Placeholder
          </p>
          <h2 className="mt-2 text-xl font-semibold tracking-tight">{title}</h2>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            {description}
          </p>
          <p className="mt-4 border-t border-border pt-4 text-sm text-muted-foreground">
            {note}
          </p>
        </div>
      </main>
    </>
  );
}
