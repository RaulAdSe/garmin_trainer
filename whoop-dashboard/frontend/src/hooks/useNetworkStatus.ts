/**
 * Network status hook for monitoring connectivity.
 * Uses @capacitor/network to monitor network status changes.
 *
 * Part of Phase 3 (UX Polish) - Task 3.1 from the deployment plan.
 */

import { Network, ConnectionStatus, ConnectionType } from '@capacitor/network';
import { useState, useEffect } from 'react';

/**
 * Network status information returned by the hook.
 */
export interface NetworkStatus {
  /** Whether the device is currently online */
  isOnline: boolean;
  /** The type of network connection (wifi, cellular, none, unknown) */
  connectionType: ConnectionType;
  /** Whether the initial network status check is still loading */
  isLoading: boolean;
}

/**
 * Hook to monitor network connectivity status.
 *
 * @returns NetworkStatus object with isOnline, connectionType, and isLoading states
 *
 * @example
 * ```typescript
 * function MyComponent() {
 *   const { isOnline, connectionType, isLoading } = useNetworkStatus();
 *
 *   if (isLoading) {
 *     return <LoadingSpinner />;
 *   }
 *
 *   return (
 *     <div>
 *       {!isOnline && <OfflineBanner />}
 *       <p>Connection: {connectionType}</p>
 *     </div>
 *   );
 * }
 * ```
 */
export function useNetworkStatus(): NetworkStatus {
  const [isOnline, setIsOnline] = useState<boolean>(true);
  const [connectionType, setConnectionType] = useState<ConnectionType>('unknown');
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    // Get initial network status
    const getInitialStatus = async () => {
      try {
        const status: ConnectionStatus = await Network.getStatus();
        setIsOnline(status.connected);
        setConnectionType(status.connectionType);
      } catch (error) {
        // If we can't determine network status, assume online
        console.warn('Failed to get initial network status:', error);
        setIsOnline(true);
        setConnectionType('unknown');
      } finally {
        setIsLoading(false);
      }
    };

    getInitialStatus();

    // Listen for network status changes
    const listener = Network.addListener('networkStatusChange', (status: ConnectionStatus) => {
      setIsOnline(status.connected);
      setConnectionType(status.connectionType);
    });

    // Cleanup listener on unmount
    return () => {
      listener.then(handle => handle.remove());
    };
  }, []);

  return { isOnline, connectionType, isLoading };
}

// Default export for convenience
export default useNetworkStatus;
