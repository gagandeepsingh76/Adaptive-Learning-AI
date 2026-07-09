"use client";

import { useCallback, useEffect, useState } from "react";
import { getStoredRoadmap, storeRoadmap } from "@/lib/storage";
import type { RoadmapResponse } from "@/types/api";

export function useLatestRoadmap() {
  const [roadmap, setRoadmap] = useState<RoadmapResponse | null>(null);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    setRoadmap(getStoredRoadmap());
    setIsReady(true);
  }, []);

  const saveRoadmap = useCallback((nextRoadmap: RoadmapResponse) => {
    storeRoadmap(nextRoadmap);
    setRoadmap(nextRoadmap);
  }, []);

  return {
    roadmap,
    roadmapId: roadmap?.roadmap_id ?? "",
    isReady,
    saveRoadmap
  };
}
