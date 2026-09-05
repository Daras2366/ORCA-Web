import { Compass } from "lucide-react";

export function ComingSoon({ title, description }: { title: string; description: string }) {
  return (
    <div className="panel flex min-h-[50vh] flex-col items-center justify-center px-6 py-12 text-center">
      <Compass className="size-8 text-accent" />
      <h2 className="mt-4 text-lg font-semibold text-shell">{title}</h2>
      <p className="mt-2 max-w-md text-sm text-muted-foreground">{description}</p>
      <p className="mt-4 rounded-full border border-border px-3 py-1 text-xs text-blush">
        Coming soon
      </p>
    </div>
  );
}
