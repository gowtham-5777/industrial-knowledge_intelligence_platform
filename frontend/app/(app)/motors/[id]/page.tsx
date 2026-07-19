import { PlaceholderPage } from "@/components/layout/placeholder-page";

type Props = {
  params: Promise<{ id: string }>;
};

export default async function Motor360Page({ params }: Props) {
  const { id } = await params;
  return (
    <PlaceholderPage
      title="Motor 360"
      description={`Flagship asset command center for motor ${id}.`}
      note="Timeline, documents, health, and recommendations panels arrive in Phase 3."
    />
  );
}
