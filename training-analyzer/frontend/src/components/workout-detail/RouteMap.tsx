'use client';

import { useMemo, useEffect, useState, useCallback, useRef } from 'react';
import dynamic from 'next/dynamic';
import type { GPSCoordinate } from '@/types/workout-detail';

// Dynamic import to avoid SSR issues with Leaflet
const MapContainer = dynamic(
  () => import('react-leaflet').then((mod) => mod.MapContainer),
  { ssr: false }
);
const TileLayer = dynamic(
  () => import('react-leaflet').then((mod) => mod.TileLayer),
  { ssr: false }
);
const Polyline = dynamic(
  () => import('react-leaflet').then((mod) => mod.Polyline),
  { ssr: false }
);
const CircleMarker = dynamic(
  () => import('react-leaflet').then((mod) => mod.CircleMarker),
  { ssr: false }
);

// FitBounds component to auto-fit map to route bounds
const FitBounds = dynamic(
  () => import('./FitBounds').then((mod) => mod.FitBounds),
  { ssr: false }
);

// Throttle interval for map hover (ms)
const HOVER_THROTTLE_MS = 50;

// Route colors
const ROUTE_COLOR = '#14b8a6'; // teal-500
const ACTIVE_MARKER_COLOR = '#fbbf24'; // amber-400

interface RouteMapProps {
  gpsData: GPSCoordinate[];
  className?: string;
  activeIndex?: number | null;
  chartDataLength?: number; // Length of chart data for index mapping
  onHoverIndex?: (index: number | null) => void;
}

export function RouteMap({
  gpsData,
  className = '',
  activeIndex = null,
  chartDataLength,
  onHoverIndex,
}: RouteMapProps) {
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
  }, []);

  // Calculate map bounds
  const bounds = useMemo(() => {
    if (gpsData.length === 0) return null;

    const lats = gpsData.map(p => p.lat);
    const lons = gpsData.map(p => p.lon);

    return [
      [Math.min(...lats), Math.min(...lons)],
      [Math.max(...lats), Math.max(...lons)],
    ] as [[number, number], [number, number]];
  }, [gpsData]);

  // Calculate center
  const center = useMemo(() => {
    if (gpsData.length === 0) return [41.3851, 2.1734] as [number, number]; // Default to Barcelona

    const avgLat = gpsData.reduce((sum, p) => sum + p.lat, 0) / gpsData.length;
    const avgLon = gpsData.reduce((sum, p) => sum + p.lon, 0) / gpsData.length;

    return [avgLat, avgLon] as [number, number];
  }, [gpsData]);

  // Create polyline positions
  const positions = useMemo(() => {
    return gpsData.map(p => [p.lat, p.lon] as [number, number]);
  }, [gpsData]);

  // Map chart index to GPS index (they may have different lengths)
  const getGPSIndex = useCallback((chartIdx: number | null): number | null => {
    if (chartIdx === null || gpsData.length === 0) return null;

    const dataLen = chartDataLength || 400; // Default downsampled chart length
    const ratio = gpsData.length / dataLen;
    const gpsIdx = Math.round(chartIdx * ratio);

    return Math.min(gpsIdx, gpsData.length - 1);
  }, [gpsData.length, chartDataLength]);

  // Map GPS index to chart index
  const getChartIndex = useCallback((gpsIdx: number): number => {
    const dataLen = chartDataLength || 400;
    const ratio = dataLen / gpsData.length;
    return Math.round(gpsIdx * ratio);
  }, [gpsData.length, chartDataLength]);

  // Find nearest GPS point to a lat/lon
  const findNearestGPSIndex = useCallback((lat: number, lon: number): number => {
    let minDistance = Infinity;
    let nearestIndex = 0;

    gpsData.forEach((point, index) => {
      const distance = Math.sqrt(
        Math.pow(lat - point.lat, 2) +
        Math.pow(lon - point.lon, 2)
      );
      if (distance < minDistance) {
        minDistance = distance;
        nearestIndex = index;
      }
    });

    return nearestIndex;
  }, [gpsData]);

  // Get active GPS point
  const activeGPSIndex = getGPSIndex(activeIndex);
  const activePoint = activeGPSIndex !== null ? gpsData[activeGPSIndex] : null;

  // Start and end points
  const startPoint = gpsData[0];
  const endPoint = gpsData[gpsData.length - 1];

  // Throttling refs for smooth map hover
  const lastHoverTimeRef = useRef<number>(0);
  const lastChartIndexRef = useRef<number | null>(null);
  const pendingHoverRef = useRef<{ lat: number; lng: number } | null>(null);
  const throttleTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (throttleTimeoutRef.current !== null) {
        clearTimeout(throttleTimeoutRef.current);
      }
    };
  }, []);

  // Process hover update
  const processHover = useCallback((lat: number, lng: number) => {
    const gpsIdx = findNearestGPSIndex(lat, lng);
    const chartIdx = getChartIndex(gpsIdx);

    // Only update if the index actually changed
    if (chartIdx !== lastChartIndexRef.current) {
      lastChartIndexRef.current = chartIdx;
      onHoverIndex?.(chartIdx);
    }
  }, [findNearestGPSIndex, getChartIndex, onHoverIndex]);

  // Handle polyline hover/move - time-based throttling
  // Must be defined before early returns to satisfy Rules of Hooks
  const handlePolylineHover = useCallback((e: { latlng: { lat: number; lng: number } }) => {
    if (!onHoverIndex) return;

    const now = Date.now();
    const lat = e.latlng.lat;
    const lng = e.latlng.lng;

    // Store the latest position
    pendingHoverRef.current = { lat, lng };

    // If enough time has passed, process immediately
    if (now - lastHoverTimeRef.current >= HOVER_THROTTLE_MS) {
      lastHoverTimeRef.current = now;
      processHover(lat, lng);
      pendingHoverRef.current = null;

      // Clear any pending timeout
      if (throttleTimeoutRef.current !== null) {
        clearTimeout(throttleTimeoutRef.current);
        throttleTimeoutRef.current = null;
      }
    } else if (throttleTimeoutRef.current === null) {
      // Schedule a trailing update
      const remaining = HOVER_THROTTLE_MS - (now - lastHoverTimeRef.current);
      throttleTimeoutRef.current = setTimeout(() => {
        throttleTimeoutRef.current = null;
        if (pendingHoverRef.current) {
          lastHoverTimeRef.current = Date.now();
          processHover(pendingHoverRef.current.lat, pendingHoverRef.current.lng);
          pendingHoverRef.current = null;
        }
      }, remaining);
    }
  }, [onHoverIndex, processHover]);

  // Handle mouse leave
  const handlePolylineLeave = useCallback(() => {
    // Clear any pending timeout
    if (throttleTimeoutRef.current !== null) {
      clearTimeout(throttleTimeoutRef.current);
      throttleTimeoutRef.current = null;
    }
    pendingHoverRef.current = null;
    lastChartIndexRef.current = null;
    onHoverIndex?.(null);
  }, [onHoverIndex]);

  // Map height classes - taller as requested
  const heightClass = "h-96 sm:h-[500px]";

  if (!isClient) {
    return (
      <div className={`bg-gray-900 rounded-xl border border-gray-800 p-4 ${className}`}>
        <div className="flex items-center gap-2 mb-3">
          <svg className="w-5 h-5 text-teal-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
          </svg>
          <h3 className="text-sm font-medium text-gray-200">Route Map</h3>
        </div>
        <div className={`${heightClass} bg-gray-800 rounded-lg animate-pulse flex items-center justify-center`}>
          <svg className="w-8 h-8 text-gray-600 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        </div>
      </div>
    );
  }

  if (gpsData.length === 0) {
    return (
      <div className={`bg-gray-900 rounded-xl border border-gray-800 p-4 ${className}`}>
        <div className="flex items-center gap-2 mb-3">
          <svg className="w-5 h-5 text-teal-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
          </svg>
          <h3 className="text-sm font-medium text-gray-200">Route Map</h3>
        </div>
        <div className={`${heightClass} bg-gray-800 rounded-lg flex items-center justify-center`}>
          <div className="text-center">
            <svg className="w-10 h-10 text-gray-600 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <p className="text-sm text-gray-500">No GPS data available</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-gray-900 rounded-xl border border-gray-800 p-4 ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 text-teal-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
          </svg>
          <h3 className="text-sm font-medium text-gray-200">Route Map</h3>
        </div>
        <div className="flex items-center gap-3 text-xs text-gray-400">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-green-500"></span>
            Start
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-red-500"></span>
            Finish
          </span>
          {activePoint && (
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
              Position
            </span>
          )}
        </div>
      </div>
      <div className={`${heightClass} rounded-lg overflow-hidden`}>
        <MapContainer
          center={center}
          zoom={13}
          className="h-full w-full"
          style={{ background: '#1f2937' }}
          scrollWheelZoom={true}
          zoomControl={true}
        >
          {/* Auto-fit to route bounds on load */}
          {bounds && <FitBounds bounds={bounds} />}

          {/* Terrain map tiles - Esri World Topo (good terrain colors, not too intense) */}
          <TileLayer
            attribution='&copy; <a href="https://www.esri.com/">Esri</a> &mdash; Sources: Esri, HERE, Garmin, USGS, NGA'
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}"
            maxZoom={18}
          />

          {/* Invisible wider polyline for easier hover detection */}
          <Polyline
            positions={positions}
            color="transparent"
            weight={20}
            opacity={0}
            eventHandlers={{
              mouseover: handlePolylineHover,
              mousemove: handlePolylineHover,
              mouseout: handlePolylineLeave,
            }}
          />

          {/* Visible route polyline */}
          <Polyline
            positions={positions}
            color={ROUTE_COLOR}
            weight={4}
            opacity={0.9}
            interactive={false}
          />

          {/* Start marker */}
          {startPoint && (
            <CircleMarker
              center={[startPoint.lat, startPoint.lon]}
              radius={8}
              fillColor="#22c55e"
              fillOpacity={1}
              color="#fff"
              weight={2}
            />
          )}

          {/* End marker */}
          {endPoint && startPoint !== endPoint && (
            <CircleMarker
              center={[endPoint.lat, endPoint.lon]}
              radius={8}
              fillColor="#ef4444"
              fillOpacity={1}
              color="#fff"
              weight={2}
            />
          )}

          {/* Active position marker - shows when hovering charts or map */}
          {activePoint && (
            <CircleMarker
              center={[activePoint.lat, activePoint.lon]}
              radius={10}
              fillColor={ACTIVE_MARKER_COLOR}
              fillOpacity={0.9}
              color="#fff"
              weight={3}
              interactive={false}
            />
          )}
        </MapContainer>
      </div>
    </div>
  );
}

export default RouteMap;
