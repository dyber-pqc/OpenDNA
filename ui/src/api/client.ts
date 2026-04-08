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
    pdb_string: string | null;
    structure_source: "alphafold" | null;
  }>("/v1/fetch_uniprot", { accession });

export const fetchAlphafold = (uniprot_id: string, with_meta = false) =>
  fetch(
    `${API_BASE}/v1/alphafold/${encodeURIComponent(uniprot_id)}?with_meta=${with_meta}`,
  ).then((r) => {
    if (!r.ok) throw new Error(`AlphaFold DB fetch failed: ${r.status}`);
    return r.json() as Promise<{
      uniprot_id: string;
      pdb: string;
      source: "alphafold-db";
      meta?: any;
    }>;
  });

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

// === v0.3 endpoints ===

export const conservation = (sequence: string) =>
  post<{
    scores: number[];
    most_conserved: number[];
    most_variable: number[];
    method: string;
    note: string;
  }>("/v1/conservation", { sequence });

export const constrainedDesign = (
  pdb_string: string,
  fixed_positions: number[],
  num_candidates = 10,
  temperature = 0.1
) =>
  post<{ job_id: string }>("/v1/constrained_design", {
    pdb_string,
    fixed_positions,
    num_candidates,
    temperature,
  });

export const multiObjectiveDesign = (
  sequence: string,
  objectives: string[],
  num_candidates = 20
) =>
  post<{ job_id: string }>("/v1/multi_objective_design", {
    sequence,
    objectives,
    num_candidates,
  });

export const pharmacophore = (pdb_string: string, pocket_residues?: number[]) =>
  post<any>("/v1/pharmacophore", { pdb_string, pocket_residues });

export const antibodyNumbering = (sequence: string, scheme = "kabat") =>
  post<{
    chain_type: string;
    scheme: string;
    cdrs: { name: string; start: number; end: number; sequence: string; length: number }[];
    n_cdrs: number;
    is_antibody: boolean;
  }>("/v1/antibody_numbering", { sequence, scheme });

export const predictPka = (pdb_string: string) =>
  post<any>("/v1/predict_pka", { pdb_string });

export const validateStructure = (pdb_string: string) =>
  post<{
    n_issues: number;
    issues: any[];
    ramachandran_favored_pct: number;
    ramachandran_outliers: number;
    clash_count: number;
    clash_score: number;
    molprobity_score: number;
    quality_grade: string;
  }>("/v1/validate_structure", { pdb_string });

export const mmgbsa = (pdb_string: string, ligand_smiles: string) =>
  post<any>("/v1/mmgbsa", { pdb_string, ligand_smiles });

export const qsar = (sequence: string) =>
  post<any>("/v1/qsar", { sequence });

export const runAgent = (goal: string, max_steps = 8) =>
  post<{
    goal: string;
    steps: any[];
    final_answer: string;
    success: boolean;
    provider: string;
  }>("/v1/agent", { goal, max_steps });

export const smartChat = (message: string, history?: any[]) =>
  post<{
    text: string;
    provider: string;
    model: string;
    tool_calls: any[];
    tool_results: any[];
  }>("/v1/smart_chat", { message, history });

export const llmProviders = () =>
  get<{
    providers: { name: string; available: boolean; model: string; supports_tools: boolean }[];
  }>("/v1/llm/providers");

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

// ========== Component Manager (Phase 2) ==========
export interface ComponentInfo {
  name: string;
  display_name: string;
  category: string;
  description: string;
  size_mb: number;
  version: string;
  install_kind: string;
  install_target: string;
  homepage?: string | null;
  license?: string | null;
  status: "installed" | "not_installed" | "unknown";
}

export interface ComponentJob {
  component: string;
  status: "running" | "completed" | "failed";
  progress: number;
  messages: string[];
  error?: string;
  result?: any;
}

export const listComponents = () =>
  get<{ components: ComponentInfo[] }>("/v1/components");

export const installComponent = (name: string) =>
  post<{ job_id: string; component: string }>(`/v1/components/${name}/install`, {});

export const uninstallComponent = (name: string) =>
  post<{ status: string; component: string }>(`/v1/components/${name}/uninstall`, {});

export const getComponentJob = (jobId: string) =>
  get<ComponentJob>(`/v1/components/jobs/${jobId}`);

// ========== Phase 3: real heavy-model backends ==========
export const getBackends = () =>
  get<{ backends: Record<string, boolean> }>("/v1/backends");

export const qmSinglePoint = (pdb_string: string, engine: "xtb" | "ani" = "xtb") =>
  post<{ engine: string; energy_hartree: number; energy_kj_mol: number; n_atoms: number }>(
    "/v1/qm/single_point",
    { pdb_string, engine },
  );

export const designDenovo = (length: number, num_designs = 1, contigs?: string) =>
  post<{ engine: string; designs: { index: number; pdb: string }[] }>(
    "/v1/design_denovo",
    { length, num_designs, contigs },
  );

// ========== Phase 4: PQC Auth ==========
let _authToken: string | null = localStorage.getItem("opendna.token");
export function setAuthToken(t: string | null) {
  _authToken = t;
  if (t) localStorage.setItem("opendna.token", t);
  else localStorage.removeItem("opendna.token");
}
export function getAuthToken(): string | null { return _authToken; }

export const authStatus = () =>
  get<{ pqc_available: boolean; auth_required: boolean; sig_algorithm: string; kem_algorithm: string }>("/v1/auth/status");

export const authRegister = (user_id: string, password?: string, scopes?: string[]) =>
  post<{ user_id: string; token: string; algorithm: string; pqc_available: boolean }>(
    "/v1/auth/register",
    { user_id, password, scopes },
  );

export const authLogin = (user_id: string, password: string) =>
  post<{ user_id: string; token: string; pqc: boolean }>("/v1/auth/login", { user_id, password });

export const authMe = () =>
  get<{ user_id?: string; scopes?: string[]; algorithm?: string; is_pqc?: boolean; auth_required?: boolean }>("/v1/auth/me");

export const authAuditTail = (limit = 100) =>
  get<{ chain: { ok: boolean; count?: number }; entries: any[] }>(`/v1/auth/audit?limit=${limit}`);

export const createApiKey = (name: string) =>
  post<{ api_key: string; user_id: string }>("/v1/auth/api_keys", { name });

// ========== Phase 5: workspaces ==========
export const openWorkspace = (user_id: string, password?: string, name = "default") =>
  post<{ user_id: string; name: string; encrypted: boolean; encryption_available: boolean; projects: any[] }>(
    "/v1/workspaces/open", { user_id, password, name },
  );

export const saveWorkspaceProject = (user_id: string, project_name: string, payload: any, password?: string, name = "default") =>
  post<{ path: string; encrypted: boolean }>("/v1/workspaces/save_project",
    { user_id, password, name, project_name, payload });

export const loadWorkspaceProject = (user_id: string, project_name: string, password?: string, name = "default") =>
  post<{ project: any }>("/v1/workspaces/load_project",
    { user_id, password, name, project_name });

// ========== Phase 6: queue + WS streaming ==========
export const queueStats = () =>
  get<{ queue: any; gpu: any }>("/v1/queue/stats");

export const enqueueJob = (kind: string, params: any, priority = 1, user_id?: string) =>
  post<{ job_id: string; priority: number }>("/v1/queue/enqueue",
    { kind, params, priority, user_id });

export const getQueueJob = (job_id: string) =>
  get<any>(`/v1/queue/jobs/${job_id}`);

export function streamJob(job_id: string, onEvent: (e: any) => void): WebSocket {
  const wsBase = API_BASE.replace(/^http/, "ws");
  const ws = new WebSocket(`${wsBase}/v1/ws/jobs/${job_id}`);
  ws.onmessage = (m) => {
    try { onEvent(JSON.parse(m.data)); } catch { /* swallow */ }
  };
  return ws;
}

export const gpuInfo = () => get<any>("/v1/gpu/info");

// ========== Phase 7: reliability ==========
export const healthCheck = () => get<Record<string, { ok: boolean; fix_count: number }>>("/v1/health");
export const listCrashes = (limit = 50) =>
  get<{ crashes: any[] }>(`/v1/crashes?limit=${limit}`);

// ========== Phase 8: provenance ==========
export interface ProvNode {
  id: string; ts: number; project_id: string; kind: string;
  inputs: any; outputs: any; score: number | null;
  parent_ids: string[]; actor: string | null; content_hash: string;
}
export const recordProvStep = (body: {
  project_id: string; kind: string; inputs: any; outputs: any;
  score?: number; parent_ids?: string[]; actor?: string;
}) => post<ProvNode>("/v1/provenance/record", body);

export const getProjectProvenance = (project_id: string) =>
  get<{ nodes: ProvNode[]; edges: { parent: string; child: string }[]; stats: any }>(
    `/v1/provenance/${project_id}`,
  );

export const getProvLineage = (node_id: string) =>
  get<{ lineage: ProvNode[] }>(`/v1/provenance/lineage/${node_id}`);

export const provDiff = (a: string, b: string) =>
  get<any>(`/v1/provenance/diff?a=${a}&b=${b}`);

export const provBlame = (project_id: string, residue: number) =>
  get<{ blame: any[] }>(`/v1/provenance/blame?project_id=${project_id}&residue=${residue}`);

export const provBisect = (project_id: string, threshold = 0.0) =>
  get<{ result: any }>(`/v1/provenance/bisect?project_id=${project_id}&threshold=${threshold}`);

// ========== Phase 9: workflow editor ==========
export const listWorkflowNodeTypes = () =>
  get<{ node_types: any[] }>("/v1/workflow/node_types");

export const runWorkflowGraph = (workflow: any, project_id?: string, actor?: string) =>
  post<{ job_id: string }>("/v1/workflow/run_graph", { workflow, project_id, actor });

// ========== Phase 10: external APIs ==========
export interface UniprotHit {
  accession: string;
  id: string;
  name: string;
  gene: string;
  organism: string;
  length: number;
  sequence: string;
  annotation_score?: number;
  function?: string;
}
export const uniprotSearch = (query: string, size = 25, reviewed_only = true, organism?: string) => {
  const params = new URLSearchParams({ query, size: String(size), reviewed_only: String(reviewed_only) });
  if (organism) params.set("organism", organism);
  return get<{ query: string; total: number; hits: UniprotHit[] }>(`/v1/uniprot/search?${params}`);
};
export const uniprotFetch = (accession: string) =>
  get<{ accession: string; sequence: string; length: number; header: string }>(`/v1/uniprot/${accession}`);

export const ncbiSearch = (db: string, term: string, retmax = 20) =>
  get<any>(`/v1/ncbi/search?db=${db}&term=${encodeURIComponent(term)}&retmax=${retmax}`);

export const ncbiFetch = (db: string, id: string, rettype = "fasta") =>
  get<any>(`/v1/ncbi/fetch?db=${db}&id=${id}&rettype=${rettype}`);

export const pubmedSearch = (query: string, retmax = 20) =>
  get<any>(`/v1/pubmed/search?query=${encodeURIComponent(query)}&retmax=${retmax}`);

export const pubmedSummarize = (pmid: string) =>
  get<any>(`/v1/pubmed/summarize?pmid=${pmid}`);

export const listVendors = () => get<{ vendors: any[] }>("/v1/vendors");

export const quoteSynthesis = (sequence: string, kind = "dna_gene", vendor?: string) =>
  post<any>("/v1/vendors/quote", { sequence, kind, vendor });

export const placeOrder = (sequence: string, vendor: string, product: string, customer_email = "", notes = "") =>
  post<any>("/v1/vendors/order", { sequence, vendor, product, customer_email, notes });

export const sendNotification = (channel: "slack" | "teams" | "discord", text: string, webhook_url?: string) =>
  post<{ sent: boolean }>("/v1/notify", { channel, text, webhook_url });

export const registerWebhook = (url: string, event = "*", secret?: string) =>
  post<{ id: string }>("/v1/webhooks", { url, event, secret });

export const listUserWebhooks = () => get<{ webhooks: any[] }>("/v1/webhooks");

export const deleteUserWebhook = (id: string) =>
  fetch(`${API_BASE}/v1/webhooks/${id}`, { method: "DELETE" }).then(r => r.json());

// ========== Phase 12: notebook + zenodo + export ==========
export const addNotebookEntry = (body: { project_id: string; title: string; body_md: string; tags?: string[]; prov_node_ids?: string[]; author?: string }) =>
  post<any>("/v1/notebook/entries", body);
export const listNotebookEntries = (project_id: string) =>
  get<{ entries: any[] }>(`/v1/notebook/${project_id}/entries`);
export const mintDoiZenodo = (body: { title: string; description: string; creators: string[]; files?: string[]; keywords?: string[]; upload_type?: string }) =>
  post<any>("/v1/zenodo/mint", body);
export const exportFigure = (data: any, format: "svg" | "png" = "svg", title = "") =>
  post<any>("/v1/export/figure", { data, title, format });
export const exportPdb3D = (pdb_string: string, format: "gltf" | "obj" = "gltf") =>
  post<any>("/v1/export/3d", { pdb_string, format });

// ========== Phase 14: Academy ==========
export const academyLevels = () => get<{ levels: any[] }>("/v1/academy/levels");
export const academyLevel = (id: number) => get<any>(`/v1/academy/levels/${id}`);
export const academyBadges = () => get<{ badges: any[] }>("/v1/academy/badges");
export const academyGlossary = () => get<{ glossary: Record<string, string> }>("/v1/academy/glossary");
export const academyDaily = () => get<any>("/v1/academy/daily");
export const academyAnswer = (user_id: string, sequence: string) =>
  post<any>("/v1/academy/daily/answer", { user_id, sequence });
export const academyLeaderboard = (limit = 20) =>
  get<{ leaderboard: any[] }>(`/v1/academy/leaderboard?limit=${limit}`);







