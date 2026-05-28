const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000/api";

export interface Project {
  id: string;
  name: string;
  description: string;
}

export interface Source {
  id: string;
  project_id: string;
  title: string;
  type: string;
  content: string;
}

export interface NodeItem {
  id: string;
  project_id: string;
  name: string;
  type: string;
  summary: string;
  current_state: string;
}

export interface Relationship {
  id: string;
  project_id: string;
  source_node_id: string;
  target_node_id: string;
  type: string;
  summary: string;
}

export interface LoreEntry {
  id: string;
  project_id: string;
  type: string;
  title: string;
  content: string;
}

export interface ExtractionResult {
  project_id: string;
  created_nodes: number;
  created_relationships: number;
  created_lore_entries: number;
  created_timeline_events: number;
}

export interface TimelineEvent {
  id: string;
  project_id: string;
  title: string;
  time_label: string;
  time_order: number;
  description: string;
  participant_node_ids: string[];
}

export interface GraphResponse {
  nodes: NodeItem[];
  relationships: Relationship[];
}

export interface PredictionReport {
  project_id: string;
  summary: string;
  branches: string[];
  latest_event: string;
  open_questions: string[];
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    ...init,
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(data?.detail ?? "请求失败");
  }
  return data as T;
}

export const api = {
  listProjects: () => request<Project[]>("/projects"),
  createProject: (payload: { name: string; description?: string }) =>
    request<Project>("/projects", { method: "POST", body: JSON.stringify(payload) }),
  listSources: (projectId: string) => request<Source[]>(`/projects/${projectId}/sources`),
  addSource: (projectId: string, payload: { title: string; type: string; content: string }) =>
    request<Source>(`/projects/${projectId}/sources`, { method: "POST", body: JSON.stringify(payload) }),
  getGraph: (projectId: string) => request<GraphResponse>(`/projects/${projectId}/graph`),
  getLore: (projectId: string) => request<LoreEntry[]>(`/projects/${projectId}/lore`),
  extractProject: (projectId: string) =>
    request<ExtractionResult>(`/projects/${projectId}/extract`, { method: "POST" }),
  addNode: (projectId: string, payload: { name: string; type: string; summary: string }) =>
    request<NodeItem>(`/projects/${projectId}/nodes`, { method: "POST", body: JSON.stringify(payload) }),
  addRelationship: (
    projectId: string,
    payload: { source_node_id: string; target_node_id: string; type: string; summary: string },
  ) => request<Relationship>(`/projects/${projectId}/relationships`, { method: "POST", body: JSON.stringify(payload) }),
  getTimeline: (projectId: string) => request<TimelineEvent[]>(`/projects/${projectId}/timeline`),
  addTimelineEvent: (
    projectId: string,
    payload: { title: string; time_label: string; time_order: number; description: string; participant_node_ids: string[] },
  ) => request<TimelineEvent>(`/projects/${projectId}/timeline-events`, { method: "POST", body: JSON.stringify(payload) }),
  createPrediction: (projectId: string) =>
    request<PredictionReport>(`/projects/${projectId}/predictions`, { method: "POST" }),
};
