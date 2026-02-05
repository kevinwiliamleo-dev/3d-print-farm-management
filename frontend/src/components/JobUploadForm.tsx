import React, { useState } from 'react';
import { printFarmClient, JobResponse } from '../api/client';

interface JobUploadFormProps {
  onSuccess?: (job: JobResponse) => void;
}

export const JobUploadForm: React.FC<JobUploadFormProps> = ({ onSuccess }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loopCount, setLoopCount] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      const validExtensions = ['.3mf', '.stl'];
      const fileName = file.name.toLowerCase();
      const isValid = validExtensions.some(ext => fileName.endsWith(ext));

      if (isValid) {
        setSelectedFile(file);
        setError(null);
      } else {
        setError('Please select a .3mf or .stl file');
        setSelectedFile(null);
      }
    }
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setSuccessMessage(null);

    if (!selectedFile) {
      setError('Please select a file');
      return;
    }

    if (loopCount < 1) {
      setError('Loop count must be at least 1');
      return;
    }

    setIsLoading(true);
    try {
      const job = await printFarmClient.uploadJob(selectedFile, loopCount);
      setSuccessMessage(`✅ Job "${job.jobName}" uploaded successfully!`);
      setSelectedFile(null);
      setLoopCount(1);
      onSuccess?.(job);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to upload job');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow-md">
      <h2 className="text-2xl font-bold mb-4">Upload Print Job</h2>

      <div className="mb-4">
        <label className="block text-sm font-medium mb-2">Model File</label>
        <input
          type="file"
          accept=".3mf,.stl"
          onChange={handleFileChange}
          className="block w-full text-sm text-gray-600
            file:mr-4 file:py-2 file:px-4
            file:rounded-md file:border-0
            file:text-sm file:font-semibold
            file:bg-blue-50 file:text-blue-700
            hover:file:bg-blue-100"
        />
        {selectedFile && (
          <p className="text-sm text-green-600 mt-2">
            ✓ {selectedFile.name} selected
          </p>
        )}
      </div>

      <div className="mb-4">
        <label htmlFor="loopCount" className="block text-sm font-medium mb-2">
          🔄 Print Loops (berapa kali print)
        </label>
        <input
          id="loopCount"
          type="number"
          min="1"
          max="100"
          value={loopCount}
          onChange={(e) => setLoopCount(parseInt(e.target.value) || 1)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md
            focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="1"
        />
        <p className="text-xs text-gray-500 mt-1">
          File akan di-print sebanyak {loopCount}x secara otomatis
        </p>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
          {error}
        </div>
      )}

      {successMessage && (
        <div className="mb-4 p-3 bg-green-100 border border-green-400 text-green-700 rounded">
          {successMessage}
        </div>
      )}

      <button
        type="submit"
        disabled={isLoading || !selectedFile}
        className="w-full bg-blue-600 text-white py-2 px-4 rounded-md
          font-medium hover:bg-blue-700 disabled:bg-gray-400
          transition-colors"
      >
        {isLoading ? 'Uploading...' : 'Upload Job'}
      </button>
    </form>
  );
};
