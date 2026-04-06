import "./JobMonitor.css";

interface Job {
  id: string;
  type: string;
  status: string;
  progress: number;
}

interface JobMonitorProps {
  jobs: Job[];
}

function JobMonitor({ jobs }: JobMonitorProps) {
  const activeJobs = jobs.filter((j) => j.status === "running");
  const completedJobs = jobs.filter((j) => j.status === "completed");

  if (jobs.length === 0) return null;

  return (
    <div className="job-monitor">
      {activeJobs.map((job) => (
        <div key={job.id} className="job-item running">
          <span className="job-spinner" />
          <span className="job-label">
            {job.type}: {job.id}
          </span>
          <div className="job-progress-bar">
            <div
              className="job-progress-fill"
              style={{ width: `${job.progress * 100}%` }}
            />
          </div>
          <span className="job-percent">{Math.round(job.progress * 100)}%</span>
        </div>
      ))}
      {completedJobs.length > 0 && activeJobs.length === 0 && (
        <div className="job-item completed">
          <span className="job-check">&#x2713;</span>
          <span className="job-label">
            {completedJobs.length} job{completedJobs.length > 1 ? "s" : ""}{" "}
            completed
          </span>
        </div>
      )}
    </div>
  );
}

export default JobMonitor;
