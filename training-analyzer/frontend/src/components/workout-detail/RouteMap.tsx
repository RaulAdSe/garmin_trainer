'use client';

import { useMemo, useEffect, useState } from 'react';
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

// Intensity colors for route
const ROUTE_COLOR = '#14b8a6'; // teal-500

interface RouteMapProps {
  gpsData: GPSCoordinate[];
  className?: string;
}

export function RouteMap({ gpsData, className = '' }: RouteMapProps) {
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

  // Start and end points
  const startPoint = gpsData[0];
  const endPoint = gpsData[gpsData.length - 1];

  if (!isClient) {
    return (
      <div className={`bg-gray-900 rounded-xl border border-gray-800 p-4 ${className}`}>
        <div className="flex items-center gap-2 mb-3">
          <svg className="w-5 h-5 text-teal-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
          </svg>
          <h3 className="text-sm font-medium text-gray-200">Route Map</h3>
        </div>
        <div className="h-64 sm:h-80 bg-gray-800 rounded-lg animate-pulse flex items-center justify-center">
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
        <div className="h-64 sm:h-80 bg-gray-800 rounded-lg flex items-center justify-center">
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
        </div>
      </div>
      <div className="h-64 sm:h-80 rounded-lg overflow-hidden">
        <MapContainer
          center={center}
          bounds={bounds || undefined}
          zoom={13}
          className="h-full w-full"
          style={{ background: '#1f2937' }}
          scrollWheelZoom={true}
          zoomControl={true}
        >
          {/* Dark theme map tiles */}
          <TileLayer
            attribution='&copy; <a href="https://carto.com/">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          />

          {/* Route polyline */}
          <Polyline
            positions={positions}
            color={ROUTE_COLOR}
            weight={3}
            opacity={0.9}
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
        </MapContainer>
      </div>
    </div>
  );
}

export default RouteMap;
