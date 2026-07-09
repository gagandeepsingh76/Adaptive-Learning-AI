import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <div className="space-y-6" aria-label="Loading page" aria-live="polite">
      <div className="space-y-3">
        <Skeleton className="h-8 w-44" />
        <Skeleton className="h-12 w-full max-w-2xl" />
      </div>
      <div className="metric-grid">
        <Skeleton className="h-28" />
        <Skeleton className="h-28" />
        <Skeleton className="h-28" />
      </div>
      <Skeleton className="h-80" />
    </div>
  );
}
