'use client';

import { useEffect } from 'react';
import { useMap } from 'react-leaflet';

interface FitBoundsProps {
  bounds: [[number, number], [number, number]];
  padding?: [number, number];
}

export function FitBounds({ bounds, padding = [20, 20] }: FitBoundsProps) {
  const map = useMap();

  useEffect(() => {
    if (bounds) {
      // Fit the map to the route bounds with some padding
      map.fitBounds(bounds, {
        padding,
        maxZoom: 16, // Don't zoom in too much
        animate: false, // Instant fit on load
      });
    }
  }, [map, bounds, padding]);

  return null;
}

export default FitBounds;
