// OpenDNA API client

const API_BASE = "http://localhost:8765";

export interface ScoreData {
  overall: number;
  confidence: number;
  breakdown: Record<string, number>;
  summary: string;
  recommendations: string[];
}

export interface JobStatus {
  job_id: string;
  status: string;
  progress: number;
  result: any;
  error: string | null;
}

export interface ChatIntent {
  action: string;
  sequence: string | null;
  mutation: string | null;
  response: string;
}

export async function fold(sequence: string): Promise<{ job_id: string }> {
  const res = await fetch(`${API_BASE}/v1/fold`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sequence }),
  });
  return res.json();
}

export async function evaluate(sequence: string): Promise<ScoreData> {
  const res = await fetch(`${API_BASE}/v1/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sequence }),
  });
  return res.json();
}

export async function design(
  pdb_string: string,
  num_candidates = 10
): Promise<{ job_id: string }> {
  const res = await fetch(`${API_BASE}/v1/design`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pdb_string, num_candidates, temperature: 0.1 }),
  });
  return res.json();
}

export async function mutate(
  sequence: string,
  mutation: string
): Promise<{ original: string; mutated: string; mutation: string }> {
  const res = await fetch(`${API_BASE}/v1/mutate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sequence, mutation }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Mutation failed");
  }
  return res.json();
}

export async function chat(message: string): Promise<ChatIntent> {
  const res = await fetch(`${API_BASE}/v1/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  return res.json();
}

export async function getJob(jobId: string): Promise<JobStatus> {
  const res = await fetch(`${API_BASE}/v1/jobs/${jobId}`);
  return res.json();
}

export async function getHardware() {
  const res = await fetch(`${API_BASE}/v1/hardware`);
  return res.json();
}
