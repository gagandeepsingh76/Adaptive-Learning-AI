import * as React from "react";
import { cn } from "@/lib/utils";

interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: number;
}

const Progress = React.forwardRef<HTMLDivElement, ProgressProps>(({ className, value = 0, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("relative h-3 w-full overflow-hidden rounded-full bg-secondary", className)}
    role="progressbar"
    aria-valuemin={0}
    aria-valuemax={100}
    aria-valuenow={Math.round(value)}
    {...props}
  >
    <div
      className="h-full w-full flex-1 bg-primary transition-transform"
      style={{ transform: `translateX(-${100 - Math.min(100, Math.max(0, value))}%)` }}
    />
  </div>
));
Progress.displayName = "Progress";

export { Progress };
