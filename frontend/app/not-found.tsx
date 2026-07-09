import { ArrowLeft, Map, Search } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function NotFound() {
  return (
    <Card className="mx-auto max-w-xl">
      <CardHeader>
        <div className="mb-2 flex h-11 w-11 items-center justify-center rounded-lg bg-secondary">
          <Search className="h-5 w-5" aria-hidden="true" />
        </div>
        <Badge variant="secondary" className="mb-2 w-fit">
          404
        </Badge>
        <CardTitle>Page not found</CardTitle>
        <CardDescription>
          This route does not exist in the learning workspace. Head back to the product flow and
          continue from a generated roadmap.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3 sm:flex-row">
        <Button asChild>
          <Link href="/">
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Back home
          </Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/roadmap">
            <Map className="h-4 w-4" aria-hidden="true" />
            Create roadmap
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}
