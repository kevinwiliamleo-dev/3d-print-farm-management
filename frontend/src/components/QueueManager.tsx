import React, { useEffect, useState } from 'react';
import { printFarmClient, QueueItemResponse } from '../api/client';

interface QueueManagerProps {
  printerId: string;
}

export const QueueManager: React.FC<QueueManagerProps> = ({ printerId }) => {
  const [queueItems, setQueueItems] = useState<QueueItemResponse[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadQueue();
    const interval = setInterval(loadQueue, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, [printerId]);

  const loadQueue = async () => {
    setIsLoading(true);
    try {
      const items = await printFarmClient.getQueueForPrinter(printerId);
      setQueueItems(items);
      setError(null);
    } catch (err: any) {
      setError('Failed to load queue');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRemoveJob = async (queueId: number) => {
    try {
      await printFarmClient.removeFromQueue(queueId);
      await loadQueue();
    } catch (err: any) {
      setError('Failed to remove job from queue');
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold">Print Queue</h2>
        <button
          onClick={loadQueue}
          disabled={isLoading}
          className="px-3 py-1 bg-blue-600 text-white rounded text-sm
            hover:bg-blue-700 disabled:bg-gray-400"
        >
          🔄 Refresh
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
          {error}
        </div>
      )}

      {queueItems.length === 0 ? (
        <p className="text-gray-500">Queue is empty</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-100 border-b">
              <tr>
                <th className="text-left px-4 py-2">Position</th>
                <th className="text-left px-4 py-2">Job ID</th>
                <th className="text-left px-4 py-2">Loop</th>
                <th className="text-left px-4 py-2">Status</th>
                <th className="text-left px-4 py-2">Action</th>
              </tr>
            </thead>
            <tbody>
              {queueItems.map((item) => (
                <tr key={item.queueId} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-2">
                    {item.positionInQueue === 1 ? (
                      <span className="text-lg">▶️</span>
                    ) : (
                      item.positionInQueue
                    )}
                  </td>
                  <td className="px-4 py-2 font-mono">{item.jobId}</td>
                  <td className="px-4 py-2">{item.currentLoop}/{item.loopCount || 1}</td>
                  <td className="px-4 py-2">
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium ${
                        item.queueStatus === 'printing'
                          ? 'bg-green-100 text-green-800'
                          : item.queueStatus === 'queued'
                          ? 'bg-blue-100 text-blue-800'
                          : 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {item.queueStatus}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    {item.queueStatus !== 'printing' && (
                      <button
                        onClick={() => handleRemoveJob(item.queueId)}
                        className="text-red-600 hover:text-red-800 font-medium text-xs"
                      >
                        Remove
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
