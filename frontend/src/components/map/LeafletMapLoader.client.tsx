import { lazy } from "react";

// Re-export LeafletMap as a lazy-loaded component.
// This file is intentionally named *.client.tsx so TanStack Start's
// import-protection allows it to import other *.client.* files.
const LeafletMap = lazy(() => import("./LeafletMap.client"));

export default LeafletMap;
