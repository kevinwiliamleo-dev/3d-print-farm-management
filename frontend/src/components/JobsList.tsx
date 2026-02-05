import React, { useEffect, useState } from 'react';
import { printFarmClient, JobResponse } from '../api/client';
import { PrintPreviewModal } from './PrintPreviewModal';

export const JobsList: React.FC = () => {
  const [jobs, setJobs] = useState<JobResponse[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewJobId, setPreviewJobId] = useState<number | null>(null);

  useEffect(() => {
    loadJobs();
    // Poll jobs every 10 seconds to reduce API load
    const interval = setInterval(loadJobs, 10000);
    return () => clearInterval(interval);
  }, []);

  const loadJobs = async () => {
    setIsLoading(true);
    try {
      const jobList = await printFarmClient.getAllJobs();
      setJobs(jobList);
      setError(null);
    } catch (err: any) {
      setError('Failed to load jobs');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteJob = async (jobId: number) => {
    if (!window.confirm('Are you sure you want to delete this job?')) return;

    try {
      await printFarmClient.deleteJob(jobId);
      await loadJobs();
    } catch (err: any) {
      setError('Failed to delete job');
    }
  };

  const getStatusBadgeColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'printing':
        return 'bg-blue-100 text-blue-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold">All Jobs</h2>
        <button
          onClick={loadJobs}
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

      {jobs.length === 0 ? (
        <p className="text-gray-500">No jobs yet. Upload one to get started!</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-100 border-b">
              <tr>
                <th className="text-left px-4 py-2">Job Name</th>
                <th className="text-left px-4 py-2">File</th>
                <th className="text-left px-4 py-2">Loops</th>
                <th className="text-left px-4 py-2">Status</th>
                <th className="text-left px-4 py-2">Created</th>
                <th className="text-left px-4 py-2">Action</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.jobId} className="border-b hover:bg-gray-50">
                  <td className="px-4 py-2 font-semibold">{job.jobName}</td>
                  <td className="px-4 py-2 text-gray-600 text-xs font-mono">
                    {job.filename}
                  </td>
                  <td className="px-4 py-2">
                    <span className="font-mono">
                      {job.currentLoop}/{job.loopCount}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium ${getStatusBadgeColor(job.status)}`}
                    >
                      {job.status}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-gray-600 text-xs">
                    {new Date(job.createdAt).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex gap-2">
                      <button
                        onClick={() => setPreviewJobId(job.jobId)}
                        className="text-blue-600 hover:text-blue-800 font-medium text-xs"
                        title="Preview print steps"
                      >
                        📋 Preview
                      </button>
                      <button
                        onClick={() => handleDeleteJob(job.jobId)}
                        className="text-red-600 hover:text-red-800 font-medium text-xs"
                      >
                        🗑️ Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Print Preview Modal */}
      <PrintPreviewModal
        jobId={previewJobId}
        isOpen={previewJobId !== null}
        onClose={() => setPreviewJobId(null)}
      />
    </div>
  );
};
