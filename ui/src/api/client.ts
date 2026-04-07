// OpenDNA API client v0.2

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

export interface SequenceProperties {
  length: number;
  molecular_weight: number;
  isoelectric_point: number;
  gravy: number;
  aromaticity: number;
  instability_index: number;
  extinction_coefficient_reduced: number;
  extinction_coefficient_oxidized: number;
  aliphatic_index: number;
  charge_at_ph7: number;
  composition: Record<string, number>;
  composition_pct: Record<string, number>;
  half_life_mammalian: string;
  classification: string;
}

export interface LipinskiResult {
  molecular_weight: number;
  h_bond_donors: number;
  h_bond_acceptors: number;
  logp_estimate: number;
  rotatable_bonds: number;
  passes_ro5: boolean;
  violations: string[];
}

export interface AnalysisResult {
  properties: SequenceProperties;
  lipinski: LipinskiResult;
  hydropathy_profile: number[];
  disorder: {
    scores: number[];
    regions: { start: number; end: number; length: number }[];
    disorder_percent: number;
    is_mostly_disordered: boolean;
  };
  transmembrane: {
    scores: number[];
    regions: { start: number; end: number; length: number }[];
    n_helices: number;
    is_membrane_protein: boolean;
  };
  signal_peptide: {
    has_signal: boolean;
    score: number;
    cleavage_site: number | null;
    mature_sequence: string | null;
  };
  aggregation: {
    scores: number[];
    aggregation_prone_regions: any[];
    n_apr: number;
    overall_aggregation_score: number;
    risk_level: string;
  };
  phosphorylation: {
    sites: any[];
    count: number;
  };
  glycosylation: {
    n_glycosylation_sites: any[];
    o_glycosylation_sites: any[];
    n_count: number;
    o_count: number;
  };
  structure?: {
    secondary_structure: string;
    helix_pct: number;
    strand_pct: number;
    coil_pct: number;
    ramachandran: { phi: number | null; psi: number | null }[];
    radius_of_gyration: number;
    sasa_estimate: number;
    pockets: any[];
    num_atoms: number;
    bonds: {
      h_bonds: any[];
      h_bond_count: number;
      salt_bridges: any[];
      salt_bridge_count: number;
      disulfides: any[];
      disulfide_count: number;
    };
  } | null;
}

async function post<T>(path: string, body: any): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `${path} failed: ${res.status}`);
  }
  return res.json();
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return res.json();
}

export const fold = (sequence: string) =>
  post<{ job_id: string }>("/v1/fold", { sequence });

export const evaluate = (sequence: string) =>
  post<ScoreData>("/v1/evaluate", { sequence });

export const design = (pdb_string: string, num_candidates = 10) =>
  post<{ job_id: string }>("/v1/design", {
    pdb_string,
    num_candidates,
    temperature: 0.1,
  });

export const iterativeDesign = (
  sequence: string,
  n_rounds = 5,
  candidates_per_round = 5
) =>
  post<{ job_id: string }>("/v1/iterative_design", {
    sequence,
    n_rounds,
    candidates_per_round,
  });

export const mutate = (sequence: string, mutation: string) =>
  post<{ original: string; mutated: string; mutation: string }>("/v1/mutate", {
    sequence,
    mutation,
  });

export const chat = (message: string) =>
  post<ChatIntent>("/v1/chat", { message });

export const analyze = (sequence: string, pdb_string?: string) =>
  post<AnalysisResult>("/v1/analyze", { sequence, pdb_string });

export const explain = (sequence: string, pdb_string?: string) =>
  post<{ explanation: string }>("/v1/explain", { sequence, pdb_string });

export const fetchUniprot = (accession: string) =>
  post<{
    accession: string;
    name: string;
    sequence: string;
    organism: string;
    length: number;
    description: string;
  }>("/v1/fetch_uniprot", { accession });

export const fetchPdb = (pdb_id: string) =>
  post<{ pdb_id: string; pdb_string: string }>("/v1/fetch_pdb", { pdb_id });

export const compareStructures = (pdb_a: string, pdb_b: string) =>
  post<{
    rmsd: number;
    length_1: number;
    length_2: number;
    aligned_residues: number;
    ss_identity: number;
    rg_1: number;
    rg_2: number;
  }>("/v1/compare", { pdb_a, pdb_b });

export const dock = (pdb_string: string, ligand_smiles: string) =>
  post<any>("/v1/dock", { pdb_string, ligand_smiles });

export const screen = (pdb_string: string, ligands: string[]) =>
  post<{ results: any[] }>("/v1/screen", { pdb_string, ligands });

export const md = (pdb_string: string, duration_ps = 100) =>
  post<{ job_id: string }>("/v1/md", { pdb_string, duration_ps });

export const align = (seq1: string, seq2: string) =>
  post<{
    score: number;
    identity_pct: number;
    similarity_pct: number;
    aligned_length: number;
    alignment_1: string;
    alignment_2: string;
    comparison: string;
    matches: number;
  }>("/v1/align", { seq1, seq2 });

export const predictDdg = (sequence: string, mutation: string) =>
  post<{
    mutation: string;
    ddg_kcal_mol: number;
    classification: string;
    interpretation: string;
  }>("/v1/predict_ddg", { sequence, mutation });

export const cost = (sequence: string) =>
  post<{
    synthesis: any;
    compute_carbon_cpu: any;
    compute_carbon_gpu: any;
  }>("/v1/cost", { sequence });

export const saveProject = (name: string, data: any) =>
  post<{ name: string; path: string }>("/v1/projects/save", { name, data });

export const loadProject = (name: string) =>
  post<any>("/v1/projects/load", { name });

export const listProjects = () =>
  get<{ projects: any[] }>("/v1/projects");

export const famousProteins = () =>
  get<Record<string, string>>("/v1/famous_proteins");

export const getJob = (jobId: string) =>
  get<JobStatus>(`/v1/jobs/${jobId}`);

export const listJobs = () => get<{ jobs: any[] }>("/v1/jobs");

export const getHardware = () => get<any>("/v1/hardware");

export const mutate_ = mutate;
