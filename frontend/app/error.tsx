"use client";

import { AlertTriangle, RotateCcw, Settings } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function Error({
  reset
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <Card className="mx-auto max-w-xl" role="alert">
      <CardHeader>
        <div className="mb-2 flex h-11 w-11 items-center justify-center rounded-lg bg-destructive/10 text-destructive">
          <AlertTriangle className="h-5 w-5" aria-hidden="true" />
        </div>
        <Badge variant="secondary" className="mb-2 w-fit">
          Route recovery
        </Badge>
        <CardTitle>Something broke while loading this view</CardTitle>
        <CardDescription>
          The app is still running. Retry the route, or check the backend URL in Settings if API
          calls were involved.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3 sm:flex-row">
        <Button type="button" onClick={reset}>
          <RotateCcw className="h-4 w-4" aria-hidden="true" />
          Retry
        </Button>
        <Button asChild variant="outline">
          <Link href="/settings">
            <Settings className="h-4 w-4" aria-hidden="true" />
            Open settings
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}
