import { DragEvent, FormEvent, useEffect, useMemo, useState } from "react";
import { BookOpen, GitBranch, Layers3, Network, Play, Plus, ScrollText, Sparkles } from "lucide-react";
import { GraphResponse, LoreEntry, PredictionReport, Project, Source, TimelineBoard, TimelineEvent, TimelineFlowLayout as ApiTimelineFlowLayout, WikiEntry, api } from "./api";
import "./styles.css";

const emptyGraph: GraphResponse = { nodes: [], relationships: [] };
const emptyTimelineBoard: TimelineBoard = { project_id: "", lanes: [], placements: [], mode: "manual" };

const LLM_PROFILE_STORAGE_KEY = "newworld.llmProfiles";

interface TimelineFlowEdge {
  id: string;
  sourceEventId: string;
  targetEventId: string;
}

interface TimelineFlowLayout {
  positions: Record<string, { x: number; y: number }>;
  edges: TimelineFlowEdge[];
  hasLayout: boolean;
}

function normalizeTimelineFlowLayout(layout: ApiTimelineFlowLayout | null | undefined): TimelineFlowLayout {
  const positions: Record<string, { x: number; y: number }> = {};
  layout?.positions.forEach((position) => {
    positions[position.event_id] = { x: position.x, y: position.y };
  });
  const edges = layout?.edges.map((edge) => ({
    id: edge.id,
    sourceEventId: edge.source_event_id,
    targetEventId: edge.target_event_id,
  })) ?? [];
  return { positions, edges, hasLayout: Boolean(layout?.has_layout) };
}
interface LLMProfile {
  id: string;
  label: string;
  apiBase: string;
  model: string;
  apiKey: string;
  updatedAt: string;
}

function loadLLMProfiles(): LLMProfile[] {
  try {
    const raw = window.localStorage.getItem(LLM_PROFILE_STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((item): item is LLMProfile =>
      typeof item?.id === "string" &&
      typeof item?.label === "string" &&
      typeof item?.apiBase === "string" &&
      typeof item?.model === "string" &&
      typeof item?.apiKey === "string" &&
      typeof item?.updatedAt === "string",
    );
  } catch {
    return [];
  }
}

function maskSecret(value: string) {
  if (!value) return "未保存 Key";
  if (value.length <= 8) return "已保存 Key";
  return `${value.slice(0, 4)}...${value.slice(-4)}`;
}

export default function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProjectId, setActiveProjectId] = useState("");
  const [sources, setSources] = useState<Source[]>([]);
  const [graph, setGraph] = useState<GraphResponse>(emptyGraph);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [editingEventId, setEditingEventId] = useState("");
  const [timelineFlowLayout, setTimelineFlowLayout] = useState<TimelineFlowLayout>({ positions: {}, edges: [], hasLayout: false });
  const [timelineBoard, setTimelineBoard] = useState<TimelineBoard>(emptyTimelineBoard);
  const [timelineMode, setTimelineMode] = useState<"llm" | "rules" | "manual">("manual");
  const [newLaneName, setNewLaneName] = useState("");
  const [draggingTimelineEventId, setDraggingTimelineEventId] = useState("");
  const [timelineEdgeSourceId, setTimelineEdgeSourceId] = useState("");
  const [timelineEdgeTargetId, setTimelineEdgeTargetId] = useState("");
  const [selectedTimelineEdgeId, setSelectedTimelineEdgeId] = useState("");
  const [loreEntries, setLoreEntries] = useState<LoreEntry[]>([]);
  const [report, setReport] = useState<PredictionReport | null>(null);
  const [wikiEntries, setWikiEntries] = useState<WikiEntry[]>([]);
  const [wikiSearchQuery, setWikiSearchQuery] = useState("");
  const [wikiKind, setWikiKind] = useState("");
  const [selectedWikiId, setSelectedWikiId] = useState("");
  const [predictionNodeId, setPredictionNodeId] = useState("");
  const [status, setStatus] = useState("准备就绪");
  const [busy, setBusy] = useState(false);
  const [activeView, setActiveView] = useState<"map" | "timeline" | "lore" | "wiki" | "report">("map");
  const [extracting, setExtracting] = useState(false);
  const [organizingTimeline, setOrganizingTimeline] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState("");
  const [editingNodeId, setEditingNodeId] = useState("");
  const [selectedRelationshipId, setSelectedRelationshipId] = useState("");
  const [editingRelationshipId, setEditingRelationshipId] = useState("");
  const [selectedSourceIds, setSelectedSourceIds] = useState<string[]>([]);
  const [manualNodeName, setManualNodeName] = useState("");
  const [manualNodeType, setManualNodeType] = useState("人物");
  const [manualNodeSummary, setManualNodeSummary] = useState("");
  const [extractMode, setExtractMode] = useState<"rules" | "llm">("rules");
  const [llmApiBase, setLlmApiBase] = useState("https://api.openai.com/v1");
  const [llmModel, setLlmModel] = useState("gpt-4o-mini");
  const [llmApiKey, setLlmApiKey] = useState("");
  const [relationshipSourceQuery, setRelationshipSourceQuery] = useState("");
  const [relationshipTargetQuery, setRelationshipTargetQuery] = useState("");
  const [graphNodeQuery, setGraphNodeQuery] = useState("");
  const [mergeNodeQuery, setMergeNodeQuery] = useState("");
  const [llmProfileLabel, setLlmProfileLabel] = useState("");
  const [llmProfiles, setLlmProfiles] = useState<LLMProfile[]>(() => loadLLMProfiles());
  const [loreSearchQuery, setLoreSearchQuery] = useState("");
  const [selectedLoreType, setSelectedLoreType] = useState("全部");
  const [selectedLoreId, setSelectedLoreId] = useState("");
  const [creatingLore, setCreatingLore] = useState(false);
  const [newLoreType, setNewLoreType] = useState("设定");
  const [newLoreTitle, setNewLoreTitle] = useState("");
  const [newLoreContent, setNewLoreContent] = useState("");

  const activeProject = projects.find((project) => project.id === activeProjectId);
  const relationshipLabels = useMemo(() => {
    const byId = new Map(graph.nodes.map((node) => [node.id, node.name]));
    return graph.relationships.map((relationship) => ({
      ...relationship,
      sourceName: byId.get(relationship.source_node_id) ?? relationship.source_node_id,
      targetName: byId.get(relationship.target_node_id) ?? relationship.target_node_id,
    }));
  }, [graph]);

  const nodeSearchOptions = useMemo(() => graph.nodes.map((node) => `${node.name} · ${node.type}`), [graph.nodes]);
  const selectedNode = graph.nodes.find((node) => node.id === selectedNodeId) ?? graph.nodes[0];
  const relationshipSourceNode = findNodeBySearchValue(relationshipSourceQuery);
  const relationshipTargetNode = findNodeBySearchValue(relationshipTargetQuery);
  const mergeCandidateNode = findNodeBySearchValue(mergeNodeQuery);
  const selectedRelationship = relationshipLabels.find((relationship) => relationship.id === selectedRelationshipId);
  const editingNode = graph.nodes.find((node) => node.id === editingNodeId);
  const editingRelationship = relationshipLabels.find((relationship) => relationship.id === editingRelationshipId);
  const selectedRelationshipGroup = selectedRelationship ? relationshipLabels.filter((relationship) => relationship.source_node_id === selectedRelationship.source_node_id && relationship.target_node_id === selectedRelationship.target_node_id) : [];
  const editingEvent = events.find((event) => event.id === editingEventId);
  const selectedRelationships = useMemo(() => {
    if (!selectedNode) return [];
    return relationshipLabels.filter((relationship) =>
      relationship.source_node_id === selectedNode.id || relationship.target_node_id === selectedNode.id,
    );
  }, [relationshipLabels, selectedNode]);
  const timelineFlow = useMemo(() => {
    const saved = timelineFlowLayout;
    const positions: Record<string, { x: number; y: number }> = {};
    if (!saved.hasLayout) return { positions, edges: [], hasLayout: false };
    events.forEach((event, index) => {
      positions[event.id] = saved.positions[event.id] ?? { x: 320, y: 70 + index * 180 };
    });
    const eventIds = new Set(events.map((event) => event.id));
    const defaultEdges: TimelineFlowEdge[] = [];
    const customEdges = saved.edges.filter((edge) => eventIds.has(edge.sourceEventId) && eventIds.has(edge.targetEventId));
    const edgeKeys = new Set<string>();
    const edges = [...defaultEdges, ...customEdges].filter((edge) => {
      const key = `${edge.sourceEventId}:${edge.targetEventId}`;
      if (edge.sourceEventId === edge.targetEventId || edgeKeys.has(key)) return false;
      edgeKeys.add(key);
      return true;
    });
    return { positions, edges, hasLayout: true };
  }, [events, timelineFlowLayout]);

  const timelineFlowEventById = useMemo(() => new Map(events.map((event) => [event.id, event])), [events]);

  const timelineEventById = useMemo(() => new Map(events.map((event) => [event.id, event])), [events]);
  const timelineBoardView = useMemo(() => {
    const placements = timelineBoard.placements.length > 0
      ? timelineBoard.placements
      : events.map((event, index) => ({ event_id: event.id, lane_id: "lane_main", sort_order: index, stage: event.time_label }));
    const lanes = timelineBoard.lanes.length > 0
      ? [...timelineBoard.lanes].sort((left, right) => left.order - right.order)
      : [{ id: "lane_main", name: "主线", type: "main", order: 0 }];
    const placementsByLane = new Map(lanes.map((lane) => [lane.id, [] as typeof placements]));
    placements.forEach((placement) => {
      if (!timelineEventById.has(placement.event_id)) return;
      const laneId = placementsByLane.has(placement.lane_id) ? placement.lane_id : lanes[0]?.id;
      if (!laneId) return;
      placementsByLane.get(laneId)?.push(placement);
    });
    placementsByLane.forEach((items) => items.sort((left, right) => left.sort_order - right.sort_order));
    return { lanes, placementsByLane };
  }, [events, timelineBoard, timelineEventById]);

  const loreTypes = useMemo(() => ["全部", ...Array.from(new Set(loreEntries.map((entry) => entry.type).filter(Boolean)))], [loreEntries]);
  const filteredLoreEntries = useMemo(() => {
    const keyword = loreSearchQuery.trim().toLowerCase();
    return loreEntries.filter((entry) => {
      const matchesType = selectedLoreType === "全部" || entry.type === selectedLoreType;
      const haystack = `${entry.title} ${entry.type} ${entry.content}`.toLowerCase();
      return matchesType && (!keyword || haystack.includes(keyword));
    });
  }, [loreEntries, loreSearchQuery, selectedLoreType]);
  const selectedLoreEntry = filteredLoreEntries.find((entry) => entry.id === selectedLoreId) ?? filteredLoreEntries[0] ?? null;
  const selectedWikiEntry = wikiEntries.find((entry) => entry.id === selectedWikiId) ?? wikiEntries[0] ?? null;




  async function saveTimelineFlowLayout(nextLayout: TimelineFlowLayout) {
    const projectId = requireProject();
    setTimelineFlowLayout(nextLayout);
    const payload: ApiTimelineFlowLayout = {
      project_id: projectId,
      has_layout: nextLayout.hasLayout,
      positions: Object.entries(nextLayout.positions).map(([event_id, position]) => ({
        event_id,
        x: position.x,
        y: position.y,
      })),
      edges: nextLayout.edges.map((edge) => ({
        id: edge.id,
        source_event_id: edge.sourceEventId,
        target_event_id: edge.targetEventId,
      })),
    };
    const saved = await api.saveTimelineFlow(projectId, payload);
    setTimelineFlowLayout(normalizeTimelineFlowLayout(saved));
  }

  function updateTimelineFlowLayout(updater: (layout: TimelineFlowLayout) => TimelineFlowLayout) {
    const nextLayout = updater(timelineFlowLayout);
    saveTimelineFlowLayout(nextLayout).catch((error) => {
      setStatus(error instanceof Error ? error.message : "流程图保存失败");
    });
  }

  function moveTimelineEvent(eventId: string, x: number, y: number) {
    updateTimelineFlowLayout((layout) => ({
      ...layout,
      hasLayout: true,
      positions: { ...layout.positions, [eventId]: { x: Math.max(30, x), y: Math.max(30, y) } },
    }));
  }

  function handleTimelineNodeDrag(eventId: string, event: DragEvent<HTMLButtonElement>) {
    const canvas = event.currentTarget.closest(".timeline-flow-canvas");
    if (!(canvas instanceof HTMLElement)) return;
    const bounds = canvas.getBoundingClientRect();
    moveTimelineEvent(eventId, event.clientX - bounds.left - 120, event.clientY - bounds.top - 60);
  }

  function handleAddTimelineEdge() {
    if (!timelineEdgeSourceId || !timelineEdgeTargetId || timelineEdgeSourceId === timelineEdgeTargetId) return;
    updateTimelineFlowLayout((layout) => {
      const exists = layout.edges.some((edge) => edge.sourceEventId === timelineEdgeSourceId && edge.targetEventId === timelineEdgeTargetId);
      if (exists) return layout;
      return {
        ...layout,
        hasLayout: true,
        edges: [...layout.edges, { id: `edge_${Date.now()}`, sourceEventId: timelineEdgeSourceId, targetEventId: timelineEdgeTargetId }],
      };
    });
  }
  function handleDeleteSelectedTimelineEdge() {
    if (!selectedTimelineEdgeId) return;
    updateTimelineFlowLayout((layout) => ({
      ...layout,
      edges: layout.edges.filter((edge) => edge.id !== selectedTimelineEdgeId),
    }));
    setSelectedTimelineEdgeId("");
  }

  function handleDeleteEditingTimelineEvent() {
    if (!editingEvent) return;
    const confirmed = window.confirm(`删除流程节点“${editingEvent.title}”？相关连线也会删除。`);
    if (!confirmed) return;
    runAction(async () => {
      const projectId = requireProject();
      await api.deleteTimelineEvent(projectId, editingEvent.id);
      await refreshProject(projectId);
      setEditingEventId("");
      setSelectedTimelineEdgeId("");
    }, "流程节点已删除");
  }

  function handleDeleteTimelineFlow() {
    runAction(async () => {
      const projectId = requireProject();
      const cleared = await api.deleteTimelineFlow(projectId);
      setTimelineFlowLayout(normalizeTimelineFlowLayout(cleared));
      setTimelineEdgeSourceId("");
      setTimelineEdgeTargetId("");
    }, "流程图布局已删除");
  }

  function handleResetTimelineFlow() {
    setOrganizingTimeline(true);
    setStatus("正在调用 LLM 整理时间线流程图，请稍等...");
    runAction(async () => {
      const projectId = requireProject();
      const layout = await api.organizeTimelineFlow(projectId, getLLMConfigPayload());
      setTimelineFlowLayout(normalizeTimelineFlowLayout(layout));
      setTimelineEdgeSourceId("");
      setTimelineEdgeTargetId("");
    }, "LLM 已重置时间线流程图", true).finally(() => setOrganizingTimeline(false));
  }

  function handleOrganizeTimelineBoard(mode: "llm" | "rules" | "manual") {
    setTimelineMode(mode);
    if (mode === "manual") {
      setStatus("已切换为手动整理");
      return;
    }
    setOrganizingTimeline(true);
    runAction(async () => {
      const projectId = requireProject();
      const board = await api.organizeTimelineBoard(projectId, {
        mode,
        llm: mode === "llm" ? getLLMConfigPayload() : null,
      });
      setTimelineBoard(board);
    }, mode === "llm" ? "LLM 已整理故事线" : "规则已整理故事线", true).finally(() => setOrganizingTimeline(false));
  }

  function saveTimelineBoard(nextBoard: TimelineBoard) {
    setTimelineBoard(nextBoard);
    api.saveTimelineBoard(requireProject(), nextBoard).catch((error) => setStatus(error instanceof Error ? error.message : "故事线保存失败"));
  }

  function handleAddTimelineLane() {
    const name = newLaneName.trim();
    if (!name) return;
    const lane = { id: "lane_" + Date.now(), name, type: "branch", order: timelineBoardView.lanes.length };
    saveTimelineBoard({ ...timelineBoard, project_id: requireProject(), mode: "manual", lanes: [...timelineBoardView.lanes, lane] });
    setNewLaneName("");
  }

  function handleDeleteTimelineLane(laneId: string) {
    if (laneId === "lane_main" || timelineBoardView.lanes.length <= 1) return;
    const fallbackLaneId = timelineBoardView.lanes.find((lane) => lane.id !== laneId)?.id ?? "lane_main";
    saveTimelineBoard({
      ...timelineBoard,
      project_id: requireProject(),
      mode: "manual",
      lanes: timelineBoardView.lanes.filter((lane) => lane.id !== laneId),
      placements: timelineBoard.placements.map((placement) => placement.lane_id === laneId ? { ...placement, lane_id: fallbackLaneId } : placement),
    });
  }

  function reorderTimelineEvent(eventId: string, laneId: string, beforeEventId = "") {
    const lanes = timelineBoardView.lanes;
    const placementsByLane = new Map(lanes.map((lane) => [lane.id, [...(timelineBoardView.placementsByLane.get(lane.id) ?? [])]]));
    const movingPlacement = Array.from(placementsByLane.values()).flat().find((placement) => placement.event_id === eventId) ?? {
      event_id: eventId,
      lane_id: laneId,
      sort_order: 0,
      stage: "",
    };

    placementsByLane.forEach((placements, currentLaneId) => {
      placementsByLane.set(currentLaneId, placements.filter((placement) => placement.event_id !== eventId));
    });

    const targetPlacements = placementsByLane.get(laneId) ?? [];
    const insertIndex = beforeEventId ? targetPlacements.findIndex((placement) => placement.event_id === beforeEventId) : targetPlacements.length;
    targetPlacements.splice(insertIndex >= 0 ? insertIndex : targetPlacements.length, 0, { ...movingPlacement, lane_id: laneId });
    placementsByLane.set(laneId, targetPlacements);

    const nextPlacements = lanes.flatMap((lane) => (placementsByLane.get(lane.id) ?? []).map((placement, index) => ({
      ...placement,
      lane_id: lane.id,
      sort_order: index,
      stage: placement.stage ?? "",
    })));

    saveTimelineBoard({ ...timelineBoard, project_id: requireProject(), mode: "manual", lanes, placements: nextPlacements });
  }

  function handleMoveEventToLane(eventId: string, laneId: string) {
    reorderTimelineEvent(eventId, laneId);
  }
  const graphLayout = useMemo(() => {
    const nodeCount = graph.nodes.length;
    const width = Math.max(980, Math.min(1380, 900 + nodeCount * 10));
    const height = Math.max(620, Math.min(860, 560 + nodeCount * 6));
    const centerX = width / 2;
    const centerY = height / 2;
    const focusNode = selectedNode;
    const focusedRelationshipNodeIds = new Set<string>();
    if (focusNode) {
      selectedRelationships.forEach((relationship) => {
        focusedRelationshipNodeIds.add(relationship.source_node_id);
        focusedRelationshipNodeIds.add(relationship.target_node_id);
      });
      focusedRelationshipNodeIds.delete(focusNode.id);
    }
    const relatedIds = Array.from(focusedRelationshipNodeIds);
    const outerIds = graph.nodes.map((node) => node.id).filter((id) => id !== focusNode?.id && !focusedRelationshipNodeIds.has(id));
    const relatedOrder = new Map(relatedIds.map((id, index) => [id, index]));
    const outerOrder = new Map(outerIds.map((id, index) => [id, index]));
    const degree = new Map(graph.nodes.map((node) => [node.id, 0]));
    graph.relationships.forEach((relationship) => {
      degree.set(relationship.source_node_id, (degree.get(relationship.source_node_id) ?? 0) + 1);
      degree.set(relationship.target_node_id, (degree.get(relationship.target_node_id) ?? 0) + 1);
    });

    const placeOnRing = (index: number, total: number, radiusX: number, radiusY: number, offset = -Math.PI / 2) => {
      const angle = total <= 1 ? offset : (Math.PI * 2 * index) / total + offset;
      return {
        x: centerX + Math.cos(angle) * radiusX,
        y: centerY + Math.sin(angle) * radiusY,
      };
    };

    const sortedNodes = [...graph.nodes].sort((left, right) => (degree.get(right.id) ?? 0) - (degree.get(left.id) ?? 0));
    const sortedOrder = new Map(sortedNodes.map((node, index) => [node.id, index]));
    const nodes = graph.nodes.map((node, index) => {
      const connected = degree.get(node.id) ?? 0;
      if (focusNode && node.id === focusNode.id) {
        return { ...node, connected, focusLevel: "selected", x: centerX, y: centerY };
      }
      if (focusNode && focusedRelationshipNodeIds.has(node.id)) {
        const position = placeOnRing(relatedOrder.get(node.id) ?? 0, relatedIds.length, 255, 165);
        return { ...node, connected, focusLevel: "related", ...position };
      }
      if (focusNode) {
        const position = placeOnRing(outerOrder.get(node.id) ?? 0, Math.max(outerIds.length, 1), 405, 245, -Math.PI / 3);
        return { ...node, connected, focusLevel: "outer", ...position };
      }
      const sortedIndex = sortedOrder.get(node.id) ?? index;
      const position = placeOnRing(sortedIndex, Math.max(nodeCount, 1), Math.max(250, Math.min(430, 140 + nodeCount * 12)), Math.max(170, Math.min(260, 110 + nodeCount * 7)));
      return { ...node, connected, focusLevel: "normal", ...position };
    });
    const byId = new Map(nodes.map((node) => [node.id, node]));
    const edgeGroups = new Map<string, typeof relationshipLabels>();
    relationshipLabels.forEach((relationship) => {
      const key = `${relationship.source_node_id}->${relationship.target_node_id}`;
      const group = edgeGroups.get(key) ?? [];
      group.push(relationship);
      edgeGroups.set(key, group);
    });
    const edges = Array.from(edgeGroups.values())
      .map((group) => {
        const primary = group[0];
        return {
          ...primary,
          source: byId.get(primary.source_node_id),
          target: byId.get(primary.target_node_id),
          relationshipIds: group.map((relationship) => relationship.id),
          relationshipCount: group.length,
          type: group.length > 1 ? `${primary.type} 等${group.length}条` : primary.type,
        };
      })
      .filter((edge) => edge.source && edge.target);
    return { width, height, nodes, edges };
  }, [graph.nodes, graph.relationships, relationshipLabels, selectedNode, selectedRelationships]);

  function buildRelationshipPath(edge: { source?: { x: number; y: number }; target?: { x: number; y: number } }) {
    const x1 = edge.source?.x ?? 0;
    const y1 = edge.source?.y ?? 0;
    const x2 = edge.target?.x ?? 0;
    const y2 = edge.target?.y ?? 0;
    return { path: `M ${x1} ${y1} L ${x2} ${y2}`, labelX: (x1 + x2) / 2, labelY: (y1 + y2) / 2 };
  }

  async function refreshProject(projectId: string) {
    const [nextSources, nextGraph, nextEvents, nextLore, nextTimelineFlow, nextTimelineBoard, nextWiki] = await Promise.all([
      api.listSources(projectId),
      api.getGraph(projectId),
      api.getTimeline(projectId),
      api.getLore(projectId),
      api.getTimelineFlow(projectId),
      api.getTimelineBoard(projectId),
      api.getWiki(projectId, wikiSearchQuery, wikiKind),
    ]);
    setSources(nextSources);
    setGraph(nextGraph);
    setEvents(nextEvents);
    setLoreEntries(nextLore);
    setTimelineFlowLayout(normalizeTimelineFlowLayout(nextTimelineFlow));
    setTimelineBoard(nextTimelineBoard);
    setWikiEntries(nextWiki.entries);
  }

  async function loadProjects() {
    const nextProjects = await api.listProjects();
    setProjects(nextProjects);
    const nextActiveId = activeProjectId || nextProjects[0]?.id || "";
    setActiveProjectId(nextActiveId);
    if (nextActiveId) await refreshProject(nextActiveId);
  }

  useEffect(() => {
    loadProjects().catch((error) => setStatus(error.message));
  }, []);

  useEffect(() => {
    setSelectedNodeId((current) => graph.nodes.some((node) => node.id === current) ? current : graph.nodes[0]?.id ?? "");
  }, [graph.nodes]);
  useEffect(() => {
    window.localStorage.setItem(LLM_PROFILE_STORAGE_KEY, JSON.stringify(llmProfiles));
  }, [llmProfiles]);

  async function runAction(action: () => Promise<void>, doneMessage: string, alertOnError = false) {
    setBusy(true);
    setStatus("处理中...");
    try {
      await action();
      setStatus(doneMessage);
    } catch (error) {
      const message = error instanceof Error ? error.message : "操作失败";
      setStatus(message);
      if (alertOnError) {
        window.alert(message);
      }
    } finally {
      setBusy(false);
    }
  }

  function findNodeBySearchValue(value: string) {
    const query = value.trim();
    if (!query) return undefined;
    const normalized = query.split(" · ")[0].trim();
    return graph.nodes.find((node) => node.id === query || node.name === normalized || node.name === query);
  }

  function focusNodeBySearchValue(value: string) {
    const node = findNodeBySearchValue(value);
    if (!node) {
      setStatus("没有找到匹配的节点");
      return;
    }
    setSelectedNodeId(node.id);
    setSelectedRelationshipId("");
    setGraphNodeQuery(`${node.name} · ${node.type}`);
    setStatus(`已定位节点：${node.name}`);
  }

  function requireProject() {
    if (!activeProjectId) throw new Error("请先创建项目");
    return activeProjectId;
  }

  function handleCreateProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const name = String(form.get("projectName") ?? "").trim();
    const description = String(form.get("projectDescription") ?? "").trim();
    if (!name) return;
    runAction(async () => {
      const project = await api.createProject({ name, description });
      setProjects((current) => [...current, project]);
      setActiveProjectId(project.id);
      setSources([]);
      setGraph(emptyGraph);
      setEvents([]);
      setTimelineFlowLayout({ positions: {}, edges: [], hasLayout: false });
      setTimelineBoard({ ...emptyTimelineBoard, project_id: project.id });
      setLoreEntries([]);
      setReport(null);
      setSelectedSourceIds([]);
      formElement.reset();
    }, "项目已创建");
  }

  function handleAddSource(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const title = String(form.get("sourceTitle") ?? "").trim();
    const type = String(form.get("sourceType") ?? "剧情资料");
    const content = String(form.get("sourceContent") ?? "").trim();
    if (!title || !content) return;
    runAction(async () => {
      const projectId = requireProject();
      await api.addSource(projectId, { title, type, content });
      await refreshProject(projectId);
      formElement.reset();
    }, "来源资料已保存");
  }

  function handleUploadSources(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const files = Array.from(form.getAll("sourceFiles")).filter((file): file is File => file instanceof File && file.size > 0);
    const type = String(form.get("uploadSourceType") ?? "剧情资料");
    if (files.length === 0) return;
    runAction(async () => {
      const projectId = requireProject();
      const uploaded = await api.uploadSources(projectId, files, type);
      await refreshProject(projectId);
      formElement.reset();
      setStatus(`已导入 ${uploaded.length} 份资料，等待抽取`);
    }, "资料文件已导入");
  }
  function handleAddNode() {
    const name = manualNodeName.trim();
    const type = manualNodeType.trim() || "人物";
    const summary = manualNodeSummary.trim();
    if (!name) {
      setStatus("请填写节点名称");
      window.alert("请填写节点名称");
      return;
    }
    runAction(async () => {
      const projectId = requireProject();
      const node = await api.addNode(projectId, { name, type, summary });
      await refreshProject(projectId);
      setSelectedNodeId(node.id);
      setSelectedRelationshipId("");
      setGraphNodeQuery(`${node.name} · ${node.type}`);
      setManualNodeName("");
      setManualNodeType("人物");
      setManualNodeSummary("");
      setStatus(`节点已添加：${node.name}`);
      window.alert(`节点已添加：${node.name}`);
    }, `节点已添加：${name}`, true);
  }


  function handleAddRelationship(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const sourceNode = findNodeBySearchValue(relationshipSourceQuery);
    const targetNode = findNodeBySearchValue(relationshipTargetQuery);
    const source_node_id = sourceNode?.id ?? "";
    const target_node_id = targetNode?.id ?? "";
    const type = String(form.get("relationshipType") ?? "关联").trim();
    const summary = String(form.get("relationshipSummary") ?? "").trim();
    if (!source_node_id || !target_node_id || source_node_id === target_node_id) return;
    runAction(async () => {
      const projectId = requireProject();
      await api.addRelationship(projectId, { source_node_id, target_node_id, type, summary });
      await refreshProject(projectId);
      setRelationshipSourceQuery("");
      setRelationshipTargetQuery("");
      formElement.reset();
    }, "关系已添加");
  }


  function handleUpdateNode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editingNode) return;
    const form = new FormData(event.currentTarget);
    const name = String(form.get("editNodeName") ?? "").trim();
    const type = String(form.get("editNodeType") ?? "").trim() || "人物";
    const summary = String(form.get("editNodeSummary") ?? "").trim();
    const current_state = String(form.get("editNodeState") ?? "").trim();
    if (!name) return;
    runAction(async () => {
      const projectId = requireProject();
      const node = await api.updateNode(projectId, editingNode.id, { name, type, summary, current_state });
      await refreshProject(projectId);
      setSelectedNodeId(node.id);
      setEditingNodeId("");
    }, "节点已更新");
  }

  function handleUpdateRelationship(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editingRelationship) return;
    const form = new FormData(event.currentTarget);
    const sourceNode = findNodeBySearchValue(String(form.get("editRelationshipSource") ?? ""));
    const targetNode = findNodeBySearchValue(String(form.get("editRelationshipTarget") ?? ""));
    const type = String(form.get("editRelationshipType") ?? "").trim() || "关联";
    const summary = String(form.get("editRelationshipSummary") ?? "").trim();
    if (!sourceNode || !targetNode || sourceNode.id === targetNode.id) return;
    runAction(async () => {
      const projectId = requireProject();
      const relationship = await api.updateRelationship(projectId, editingRelationship.id, {
        source_node_id: sourceNode.id,
        target_node_id: targetNode.id,
        type,
        summary,
      });
      await refreshProject(projectId);
      setSelectedRelationshipId(relationship.id);
      setSelectedNodeId(sourceNode.id);
      setEditingRelationshipId("");
    }, "关系已更新");
  }

  function handleAddEvent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const title = String(form.get("eventTitle") ?? "").trim();
    const time_label = String(form.get("timeLabel") ?? "").trim();
    const time_order = Number(form.get("timeOrder") ?? 0);
    const description = String(form.get("eventDescription") ?? "").trim();
    const participant = String(form.get("participantNodeId") ?? "");
    if (!title || !time_label) return;
    runAction(async () => {
      const projectId = requireProject();
      const created = await api.addTimelineEvent(projectId, {
        title,
        time_label,
        time_order,
        description,
        participant_node_ids: participant ? [participant] : [],
      });
      await refreshProject(projectId);
      await saveTimelineFlowLayout({
        ...timelineFlowLayout,
        hasLayout: true,
        positions: { ...timelineFlowLayout.positions, [created.id]: { x: 320, y: 70 + events.length * 180 } },
      });
      setEditingEventId(created.id);
      formElement.reset();
    }, "时间线事件已添加");
  }


  function toggleSourceSelection(sourceId: string) {
    setSelectedSourceIds((current) =>
      current.includes(sourceId) ? current.filter((id) => id !== sourceId) : [...current, sourceId],
    );
  }

  function handleDeleteSource(source: Source) {
    const confirmed = window.confirm(`删除来源资料“${source.title}”？已抽取出的节点和关系不会自动删除。`);
    if (!confirmed) return;
    runAction(async () => {
      const projectId = requireProject();
      await api.deleteSource(projectId, source.id);
      setSelectedSourceIds((current) => current.filter((id) => id !== source.id));
      await refreshProject(projectId);
    }, "来源资料已删除");
  }

  function handleSaveLLMProfile() {
    const apiBase = llmApiBase.trim();
    const model = llmModel.trim();
    const apiKey = llmApiKey.trim();
    if (!apiBase || !model || !apiKey) {
      setStatus("请先填写完整的 LLM API Base、模型名和 API Key");
      return;
    }
    const label = llmProfileLabel.trim() || `${model} · ${apiBase.replace(/^https?:\/\//, "")}`;
    const now = new Date().toISOString();
    setLlmProfiles((current) => {
      const existing = current.find((profile) => profile.label === label || (profile.apiBase === apiBase && profile.model === model));
      const profile: LLMProfile = {
        id: existing?.id ?? `llm_${Date.now()}`,
        label,
        apiBase,
        model,
        apiKey,
        updatedAt: now,
      };
      if (existing) {
        return current.map((item) => item.id === existing.id ? profile : item);
      }
      return [profile, ...current].slice(0, 12);
    });
    setLlmProfileLabel("");
    setStatus(`已保存 LLM 配置：${label}`);
  }

  function applyLLMProfile(profile: LLMProfile) {
    setLlmApiBase(profile.apiBase);
    setLlmModel(profile.model);
    setLlmApiKey(profile.apiKey);
    setLlmProfileLabel(profile.label);
    setExtractMode("llm");
    setStatus(`已套用 LLM 配置：${profile.label}`);
  }

  function deleteLLMProfile(profileId: string) {
    setLlmProfiles((current) => current.filter((profile) => profile.id !== profileId));
    setStatus("LLM 配置已删除");
  }

  function getLLMConfigPayload() {
    const payload = {
      api_base: llmApiBase.trim(),
      api_key: llmApiKey.trim(),
      model: llmModel.trim(),
    };
    if (!payload.api_base || !payload.api_key || !payload.model) {
      throw new Error("请填写 LLM API Base、API Key 和模型名");
    }
    return payload;
  }

  function handleExtractWorld() {
    setExtracting(true);
    setStatus(extractMode === "llm" ? "正在调用 LLM 抽取世界，请稍等..." : "正在抽取世界...");
    runAction(async () => {
      const projectId = requireProject();
      const llmPayload = extractMode === "llm" ? getLLMConfigPayload() : null;
      const result = await api.extractProject(projectId, {
        source_ids: selectedSourceIds,
        mode: extractMode,
        llm: llmPayload,
      });
      await refreshProject(projectId);
      setReport(null);
      setStatus(`抽取完成：处理 ${result.processed_sources} 份，跳过 ${result.skipped_sources} 份；新增节点 ${result.created_nodes}，关系 ${result.created_relationships}，设定 ${result.created_lore_entries}，事件 ${result.created_timeline_events}`);
    }, "抽取完成", true).finally(() => setExtracting(false));
  }


  function handleMergeSelectedNode() {
    if (!selectedNode || !mergeCandidateNode || selectedNode.id === mergeCandidateNode.id) return;
    const confirmed = window.confirm(`将“${mergeCandidateNode.name}”合并到“${selectedNode.name}”？被合并节点会删除，相关关系会转移。`);
    if (!confirmed) return;
    runAction(async () => {
      const projectId = requireProject();
      const merged = await api.mergeNode(projectId, selectedNode.id, mergeCandidateNode.id);
      await refreshProject(projectId);
      setSelectedNodeId(merged.id);
      setSelectedRelationshipId("");
      setGraphNodeQuery(`${merged.name} · ${merged.type}`);
      setMergeNodeQuery("");
    }, "节点已合并", true);
  }


  function handleDeleteSelectedNode() {
    if (!selectedNode) return;
    const confirmed = window.confirm(`删除节点“${selectedNode.name}”？与它相连的关系也会一并删除。`);
    if (!confirmed) return;
    runAction(async () => {
      const projectId = requireProject();
      await api.deleteNode(projectId, selectedNode.id);
      setSelectedNodeId("");
      setSelectedRelationshipId("");
      await refreshProject(projectId);
    }, "节点已删除");
  }
  function handleUpdateTimelineEvent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editingEvent) return;
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const title = String(form.get("editEventTitle") ?? "").trim();
    const time_label = String(form.get("editTimeLabel") ?? "").trim();
    const time_order = Number(form.get("editTimeOrder") ?? 0);
    const description = String(form.get("editEventDescription") ?? "").trim();
    if (!title || !time_label) return;
    runAction(async () => {
      const projectId = requireProject();
      await api.updateTimelineEvent(projectId, editingEvent.id, {
        title,
        time_label,
        time_order,
        description,
        participant_node_ids: editingEvent.participant_node_ids,
      });
      await refreshProject(projectId);
      setEditingEventId("");
    }, "时间线事件已更新");
  }


  function handleAddLoreEntry() {
    const type = newLoreType.trim();
    const title = newLoreTitle.trim();
    const content = newLoreContent.trim();
    if (!type || !title || !content) return;
    runAction(async () => {
      const projectId = requireProject();
      const entry = await api.addLoreEntry(projectId, { type, title, content });
      await refreshProject(projectId);
      setSelectedLoreId(entry.id);
      setCreatingLore(false);
      setNewLoreType("设定");
      setNewLoreTitle("");
      setNewLoreContent("");
    }, "设定条目已新增");
  }

  function handleUpdateLoreEntry(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedLoreEntry) return;
    const form = new FormData(event.currentTarget);
    const type = String(form.get("editLoreType") ?? "").trim();
    const title = String(form.get("editLoreTitle") ?? "").trim();
    const content = String(form.get("editLoreContent") ?? "").trim();
    if (!type || !title || !content) return;
    runAction(async () => {
      const projectId = requireProject();
      const entry = await api.updateLoreEntry(projectId, selectedLoreEntry.id, { type, title, content });
      await refreshProject(projectId);
      setSelectedLoreId(entry.id);
    }, "设定条目已更新");
  }

  function handleDeleteLoreEntry() {
    if (!selectedLoreEntry) return;
    const confirmed = window.confirm("删除设定《" + selectedLoreEntry.title + "》？");
    if (!confirmed) return;
    runAction(async () => {
      const projectId = requireProject();
      await api.deleteLoreEntry(projectId, selectedLoreEntry.id);
      setSelectedLoreId("");
      await refreshProject(projectId);
    }, "设定条目已删除");
  }

  function handleRefreshWiki() {
    runAction(async () => {
      const projectId = requireProject();
      const wiki = await api.getWiki(projectId, wikiSearchQuery, wikiKind);
      setWikiEntries(wiki.entries);
      setSelectedWikiId((current) => wiki.entries.some((entry) => entry.id === current) ? current : "");
    }, "Wiki 已更新");
  }

  function handleSelectWikiLink(entryId: string) {
    setSelectedWikiId(entryId);
    setActiveView("wiki");
  }

  function handlePrediction() {
    runAction(async () => {
      const projectId = requireProject();
      setReport(await api.createPrediction(projectId, { focus_node_id: predictionNodeId || null }));
    }, "推演完成");
  }

  return (
    <main className="workspace">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">NewWorld</p>
          <h1>叙事世界工作台</h1>
        </div>

        <section className="panel compact">
          <div className="panel-title"><BookOpen size={18} /><span>项目</span></div>
          <form className="stack" onSubmit={handleCreateProject}>
            <input name="projectName" placeholder="项目名，例如：雾港纪事" />
            <input name="projectDescription" placeholder="一句话描述" />
            <button disabled={busy} type="submit"><Plus size={16} />创建项目</button>
          </form>
          <select value={activeProjectId} onChange={(event) => {
            const projectId = event.target.value;
            setActiveProjectId(projectId);
            setReport(null);
            if (projectId) refreshProject(projectId).catch((error) => setStatus(error.message));
          }}>
            <option value="">选择项目</option>
            {projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}
          </select>
          <p className="status">{activeProject ? activeProject.description || activeProject.name : status}</p>
        </section>

        <section className="panel compact">
          <div className="panel-title"><Sparkles size={18} /><span>来源资料</span></div>
          <form className="stack" onSubmit={handleAddSource}>
            <input name="sourceTitle" placeholder="资料标题" />
            <select name="sourceType" defaultValue="剧情资料">
              <option>剧情资料</option><option>人物设定</option><option>世界观设定</option><option>章节摘要</option>
            </select>
            <textarea name="sourceContent" placeholder="粘贴小说剧情、人物设定、世界观设定或章节摘要。" />
            <button disabled={busy || !activeProjectId} type="submit">保存资料</button>
          </form>
          <form className="stack upload-box" onSubmit={handleUploadSources}>
            <select name="uploadSourceType" defaultValue="剧情资料">
              <option>剧情资料</option><option>人物设定</option><option>世界观设定</option><option>章节摘要</option>
            </select>
            <input accept=".txt,.md,.markdown,text/plain,text/markdown" multiple name="sourceFiles" type="file" />
            <button disabled={busy || !activeProjectId} type="submit">导入文件</button>
          </form>
          <div className="extract-settings">
            <div className="button-row">
              <button className={extractMode === "rules" ? "active" : ""} onClick={() => setExtractMode("rules")} type="button">规则抽取</button>
              <button className={extractMode === "llm" ? "active" : ""} onClick={() => setExtractMode("llm")} type="button">LLM 抽取</button>
            </div>
            {extractMode === "llm" ? (
              <div className="llm-settings">
                <input name="llmApiBase" onChange={(event) => setLlmApiBase(event.target.value)} placeholder="API Base，例如：https://api.openai.com/v1" value={llmApiBase} />
                <input name="llmModel" onChange={(event) => setLlmModel(event.target.value)} placeholder="模型名，例如：deepseek-v4-pro" value={llmModel} />
                <input name="llmApiKey" onChange={(event) => setLlmApiKey(event.target.value)} placeholder="API Key，可保存到本机浏览器" type="password" value={llmApiKey} />
                <div className="llm-save-row">
                  <input onChange={(event) => setLlmProfileLabel(event.target.value)} placeholder="配置名称，例如：DeepSeek Pro" value={llmProfileLabel} />
                  <button disabled={busy || !llmApiBase.trim() || !llmModel.trim() || !llmApiKey.trim()} onClick={handleSaveLLMProfile} type="button">保存配置</button>
                </div>
                <ul className="llm-profile-list">
                  {llmProfiles.length === 0 ? <li>暂无已保存 LLM 配置</li> : llmProfiles.map((profile) => (
                    <li key={profile.id}>
                      <button className="profile-main" onClick={() => applyLLMProfile(profile)} type="button">
                        <strong>{profile.label}</strong>
                        <span>{profile.model} · {profile.apiBase} · {maskSecret(profile.apiKey)}</span>
                      </button>
                      <button className="danger subtle" disabled={busy} onClick={() => deleteLLMProfile(profile.id)} type="button">删除</button>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
            <button disabled={busy || extracting || !activeProjectId || sources.length === 0} onClick={handleExtractWorld} type="button">{extracting ? "抽取中..." : "抽取世界"}</button>
            {extracting ? (
              <div className="extract-progress" role="status" aria-live="polite">
                <div className="extract-progress-bar"><span /></div>
                <p>{extractMode === "llm" ? "LLM 正在阅读资料并生成节点、关系、设定和时间线。" : "正在根据资料抽取节点、关系、设定和时间线。"}</p>
              </div>
            ) : null}
          </div>
          <p className="status">{sources.length} 份来源资料 · {sources.filter((source) => !source.extracted_at).length} 份待抽取 · 已选择 {selectedSourceIds.length || "全部待抽取"}</p>
          <ul className="source-list">
            {sources.length === 0 ? <li>暂无导入资料</li> : sources.map((source) => (
              <li key={source.id}>
                <label>
                  <input checked={selectedSourceIds.includes(source.id)} onChange={() => toggleSourceSelection(source.id)} type="checkbox" />
                  <span><strong>{source.title}</strong><small>{source.type} · {source.extracted_at ? "已抽取" : "待抽取"}</small></span>
                </label>
                <button className="danger subtle" disabled={busy} onClick={() => handleDeleteSource(source)} type="button">删除</button>
              </li>
            ))}
          </ul>
        </section>
      </aside>

      <section className="main-area">
        <header className="topbar">
          <nav>
            <button className={activeView === "map" ? "active" : ""} onClick={() => setActiveView("map")} type="button"><Network size={16} />地图</button>
            <button className={activeView === "timeline" ? "active" : ""} onClick={() => setActiveView("timeline")} type="button"><GitBranch size={16} />时间线</button>
            <button className={activeView === "lore" ? "active" : ""} onClick={() => setActiveView("lore")} type="button"><Layers3 size={16} />设定库</button>
            <button className={activeView === "wiki" ? "active" : ""} onClick={() => setActiveView("wiki")} type="button"><BookOpen size={16} />Wiki</button>
            <button className={activeView === "report" ? "active" : ""} onClick={() => setActiveView("report")} type="button"><ScrollText size={16} />报告</button>
          </nav>
          <button className="primary" disabled={busy || !activeProjectId} onClick={handlePrediction} type="button">
            <Play size={16} />推演剧情
          </button>
        </header>

        <div className="content-grid">
          {activeView === "map" ? (
          <>
          <section className="panel form-panel">
            <div className="section-head"><h2>手动添加</h2><span>{status}</span></div>
            <div className="form-grid">
              <div className="stack">
                <strong>节点</strong>
                <input onChange={(event) => setManualNodeName(event.target.value)} placeholder="名称，例如：林曜" value={manualNodeName} />
                <input onChange={(event) => setManualNodeType(event.target.value)} placeholder="类型，例如：人物 / 组织 / 物品" value={manualNodeType} />
                <textarea onChange={(event) => setManualNodeSummary(event.target.value)} placeholder="节点简介" value={manualNodeSummary} />
                <button disabled={busy || !activeProjectId} onClick={handleAddNode} title={!activeProjectId ? "请先选择或创建项目" : ""} type="button">添加节点</button>
              </div>

              <form className="stack" onSubmit={handleAddRelationship}>
                <strong>关系</strong>
                <input list="relationshipSourceNodes" onChange={(event) => setRelationshipSourceQuery(event.target.value)} placeholder="搜索起点节点" value={relationshipSourceQuery} />
                <datalist id="relationshipSourceNodes">{nodeSearchOptions.map((option) => <option key={option} value={option} />)}</datalist>
                <input list="relationshipTargetNodes" onChange={(event) => setRelationshipTargetQuery(event.target.value)} placeholder="搜索终点节点" value={relationshipTargetQuery} />
                <datalist id="relationshipTargetNodes">{nodeSearchOptions.map((option) => <option key={option} value={option} />)}</datalist>
                <input name="relationshipType" placeholder="关系，例如：追寻 / 敌对 / 隐瞒" />
                <input name="relationshipSummary" placeholder="关系说明" />
                <button disabled={busy || graph.nodes.length < 2 || !relationshipSourceNode || !relationshipTargetNode || relationshipSourceNode.id === relationshipTargetNode.id} type="submit">添加关系</button>
              </form>

              <form className="stack" onSubmit={handleAddEvent}>
                <strong>时间线事件</strong>
                <input name="eventTitle" placeholder="事件标题" />
                <input name="timeLabel" placeholder="时间，例如：第一章 / 王历142年" />
                <input name="timeOrder" type="number" placeholder="排序数字" />
                <select name="participantNodeId"><option value="">参与节点（可选）</option>{graph.nodes.map((node) => <option key={node.id} value={node.id}>{node.name}</option>)}</select>
                <textarea name="eventDescription" placeholder="事件描述" />
                <button disabled={busy || !activeProjectId} type="submit">添加事件</button>
              </form>
            </div>
          </section>

          <section className="panel graph-panel">
            <div className="section-head"><h2>重要节点地图</h2><span>{graph.nodes.length} 个节点 · {graph.relationships.length} 条关系</span></div>
            <div className="graph-search-row">
              <input list="graphNodeSearchOptions" onChange={(event) => setGraphNodeQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") focusNodeBySearchValue(graphNodeQuery); }} placeholder="搜索节点并定位" value={graphNodeQuery} />
              <datalist id="graphNodeSearchOptions">{nodeSearchOptions.map((option) => <option key={option} value={option} />)}</datalist>
              <button disabled={graph.nodes.length === 0} onClick={() => focusNodeBySearchValue(graphNodeQuery)} type="button">定位节点</button>
            </div>
            <div className="graph-workbench">
              <div className="graph-canvas" aria-label="节点关系网络">
                {graph.nodes.length === 0 ? <p className="empty">先创建项目，再添加节点。</p> : (
                  <svg viewBox={`0 0 ${graphLayout.width} ${graphLayout.height}`} role="img">
                    <defs>
                      <marker id="arrow" markerHeight="8" markerWidth="8" orient="auto" refX="7" refY="4">
                        <path d="M0,0 L8,4 L0,8 Z" />
                      </marker>
                    </defs>
                    {graphLayout.edges.map((edge) => {
                      const relatedToSelectedNode = selectedNode && (edge.source_node_id === selectedNode.id || edge.target_node_id === selectedNode.id);
                      const selected = selectedRelationshipId === edge.id;
                      const showRelationshipLabel = selected || relatedToSelectedNode;
                      const edgePath = buildRelationshipPath(edge);
                      return (
                        <g className={selected ? "edge selected" : relatedToSelectedNode ? "edge related" : "edge"} key={edge.id} onClick={() => setSelectedRelationshipId(edge.id)} onDoubleClick={() => { setSelectedRelationshipId(edge.id); setEditingRelationshipId(edge.id); }} role="button" tabIndex={0}>
                          <path d={edgePath.path} markerEnd="url(#arrow)" />
                          {showRelationshipLabel ? <text x={edgePath.labelX} y={edgePath.labelY}>{edge.relationshipCount > 1 ? `${edge.relationshipCount}条关系` : edge.type}</text> : null}
                        </g>
                      );
                    })}
                    {graphLayout.nodes.map((node) => {
                      const selected = selectedNode?.id === node.id;
                      const related = node.focusLevel === "related";
                      return (
                        <g className={[selected ? "graph-node selected" : related ? "graph-node related" : node.focusLevel === "outer" ? "graph-node outer" : "graph-node",].filter(Boolean).join(" ")} key={node.id} onClick={() => { setSelectedNodeId(node.id); setSelectedRelationshipId(""); }} onDoubleClick={() => { setSelectedNodeId(node.id); setEditingNodeId(node.id); }} role="button" tabIndex={0}>
                          <circle cx={node.x} cy={node.y} r={selected ? 48 : related ? Math.min(42, 29 + node.connected * 3) : Math.min(28, 18 + node.connected * 2)} />
                          <text x={node.x} y={node.y + 4}>{node.name}</text>
                          <text className="node-type" x={node.x} y={node.y + 24}>{node.type}</text>
                        </g>
                      );
                    })}
                  </svg>
                )}
              </div>
              <aside className="node-inspector">
                <div className="inspector-title">
                  <strong>节点详情</strong>
                  <span>{selectedRelationships.length} 条直接关系</span>
                </div>
                {selectedNode ? (
                  <>
                    <span>{selectedNode.type}</span>
                    <h3>{selectedNode.name}</h3>
                    <p>{selectedNode.summary || selectedNode.current_state || "暂无节点简介"}</p>
                    {selectedRelationship ? (
                      <div className="relationship-card">
                        <strong>选中节点连线</strong>
                        <div><b>{selectedRelationship.sourceName}</b><em>{selectedRelationshipGroup.length} 条关系</em><b>{selectedRelationship.targetName}</b></div>
                        <ul className="relationship-group-list">
                          {selectedRelationshipGroup.map((relationship) => (
                            <li key={relationship.id} onDoubleClick={() => setEditingRelationshipId(relationship.id)} title="双击修改这条关系">
                              <div><b>{relationship.sourceName}</b><em>{relationship.type}</em><b>{relationship.targetName}</b></div>
                              {relationship.summary ? <p>{relationship.summary}</p> : <p>暂无关系说明</p>}
                              <button className="subtle" onClick={() => setEditingRelationshipId(relationship.id)} type="button">修改</button>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                    <div className="merge-node-box">
                      <input list="mergeNodeOptions" onChange={(event) => setMergeNodeQuery(event.target.value)} placeholder="搜索要合并进来的重复节点" value={mergeNodeQuery} />
                      <datalist id="mergeNodeOptions">{nodeSearchOptions.filter((option) => !option.startsWith(`${selectedNode.name} ·`)).map((option) => <option key={option} value={option} />)}</datalist>
                      <button disabled={busy || !mergeCandidateNode || mergeCandidateNode.id === selectedNode.id} onClick={handleMergeSelectedNode} type="button">合并到当前节点</button>
                    </div>
                    <button className="danger" disabled={busy} onClick={handleDeleteSelectedNode} type="button">删除节点</button>
                    <strong>关联关系</strong>
                    <ul>
                      {selectedRelationships.length === 0 ? <li>暂无直接关系</li> : selectedRelationships.map((relationship) => (
                        <li key={relationship.id}>
                          <b>{relationship.sourceName}</b><em>{relationship.type}</em><b>{relationship.targetName}</b>
                          {relationship.summary ? <p>{relationship.summary}</p> : null}
                        </li>
                      ))}
                    </ul>
                  </>
                ) : <p>点击图谱中的节点查看信息。</p>}
              </aside>
            </div>
          </section>

          </>
          ) : null}
          {editingNode ? (
            <div className="timeline-editor-backdrop" onClick={() => setEditingNodeId("")}>
              <form className="timeline-editor graph-popup-editor" onClick={(event) => event.stopPropagation()} onSubmit={handleUpdateNode}>
                <strong>修改节点</strong>
                <input defaultValue={editingNode.name} name="editNodeName" placeholder="节点名称" />
                <input defaultValue={editingNode.type} name="editNodeType" placeholder="节点类型" />
                <textarea defaultValue={editingNode.summary} name="editNodeSummary" placeholder="节点简介" />
                <textarea defaultValue={editingNode.current_state} name="editNodeState" placeholder="当前状态" />
                <div className="button-row">
                  <button disabled={busy} type="submit">保存节点</button>
                  <button className="subtle" onClick={() => setEditingNodeId("")} type="button">取消</button>
                </div>
              </form>
            </div>
          ) : null}
          {editingRelationship ? (
            <div className="timeline-editor-backdrop" onClick={() => setEditingRelationshipId("")}>
              <form className="timeline-editor graph-popup-editor" onClick={(event) => event.stopPropagation()} onSubmit={handleUpdateRelationship}>
                <strong>修改关系</strong>
                <input defaultValue={`${editingRelationship.sourceName} · ${graph.nodes.find((node) => node.id === editingRelationship.source_node_id)?.type ?? "节点"}`} list="editRelationshipSourceNodes" name="editRelationshipSource" placeholder="搜索起点节点" />
                <datalist id="editRelationshipSourceNodes">{nodeSearchOptions.map((option) => <option key={option} value={option} />)}</datalist>
                <input defaultValue={`${editingRelationship.targetName} · ${graph.nodes.find((node) => node.id === editingRelationship.target_node_id)?.type ?? "节点"}`} list="editRelationshipTargetNodes" name="editRelationshipTarget" placeholder="搜索终点节点" />
                <datalist id="editRelationshipTargetNodes">{nodeSearchOptions.map((option) => <option key={option} value={option} />)}</datalist>
                <input defaultValue={editingRelationship.type} name="editRelationshipType" placeholder="关系类型" />
                <textarea defaultValue={editingRelationship.summary} name="editRelationshipSummary" placeholder="关系说明" />
                <div className="button-row">
                  <button disabled={busy} type="submit">保存关系</button>
                  <button className="subtle" onClick={() => setEditingRelationshipId("")} type="button">取消</button>
                </div>
              </form>
            </div>
          ) : null}
          {activeView === "timeline" ? (
          <section className="panel timeline-panel">
            <div className="section-head"><h2>时间发展线</h2><span>{events.length} 个事件 · {timelineBoardView.lanes.length} 条故事线</span></div>
            <div className="timeline-board-tools">
              <button className={timelineMode === "llm" ? "active" : ""} disabled={busy || organizingTimeline || events.length === 0} onClick={() => handleOrganizeTimelineBoard("llm")} type="button">{organizingTimeline && timelineMode === "llm" ? "整理中..." : "LLM 整理"}</button>
              <button className={timelineMode === "rules" ? "active" : ""} disabled={busy || organizingTimeline || events.length === 0} onClick={() => handleOrganizeTimelineBoard("rules")} type="button">规则整理</button>
              <button className={timelineMode === "manual" ? "active" : ""} disabled={busy || organizingTimeline} onClick={() => handleOrganizeTimelineBoard("manual")} type="button">手动整理</button>
              <input onChange={(event) => setNewLaneName(event.target.value)} placeholder="新增故事线，例如：王城线" value={newLaneName} />
              <button disabled={!newLaneName.trim()} onClick={handleAddTimelineLane} type="button">新增故事线</button>
            </div>
            {events.length === 0 ? <p className="empty">暂无时间线事件。导入资料并抽取后会自动生成。</p> : (
              <div className="timeline-board">
                {timelineBoardView.lanes.map((lane) => (
                  <section className="timeline-lane" key={lane.id} onDragOver={(dragEvent) => dragEvent.preventDefault()} onDrop={(dropEvent) => { dropEvent.preventDefault(); const draggedEventId = dropEvent.dataTransfer.getData("text/plain") || draggingTimelineEventId; if (draggedEventId) reorderTimelineEvent(draggedEventId, lane.id); setDraggingTimelineEventId(""); }}>
                    <div className="timeline-lane-head"><strong>{lane.name}</strong><span>{lane.type}</span>{lane.id !== "lane_main" ? <button className="danger subtle" onClick={() => handleDeleteTimelineLane(lane.id)} type="button">删除线</button> : null}</div>
                    <div className="timeline-lane-events">
                      {(timelineBoardView.placementsByLane.get(lane.id) ?? []).map((placement) => {
                        const event = timelineEventById.get(placement.event_id);
                        if (!event) return null;
                        return (
                          <article className={["timeline-card", editingEventId === event.id ? "active" : "", draggingTimelineEventId === event.id ? "dragging" : ""].filter(Boolean).join(" ")} draggable={!busy} key={event.id} onDragEnd={() => setDraggingTimelineEventId("")} onDragOver={(dragEvent) => dragEvent.preventDefault()} onDragStart={(dragEvent) => { setDraggingTimelineEventId(event.id); dragEvent.dataTransfer.effectAllowed = "move"; dragEvent.dataTransfer.setData("text/plain", event.id); }} onDrop={(dropEvent) => { dropEvent.preventDefault(); dropEvent.stopPropagation(); const draggedEventId = dropEvent.dataTransfer.getData("text/plain") || draggingTimelineEventId; if (draggedEventId && draggedEventId !== event.id) reorderTimelineEvent(draggedEventId, placement.lane_id, event.id); setDraggingTimelineEventId(""); }} onDoubleClick={() => setEditingEventId(event.id)} title="双击修改事件，拖拽调整顺序">
                            <time>{event.time_label}</time>
                            <strong>{event.title}</strong>
                            <p>{event.description || "暂无描述"}</p>
                            <select onClick={(selectEvent) => selectEvent.stopPropagation()} onChange={(changeEvent) => handleMoveEventToLane(event.id, changeEvent.target.value)} value={placement.lane_id}>
                              {timelineBoardView.lanes.map((option) => <option key={option.id} value={option.id}>{option.name}</option>)}
                            </select>
                          </article>
                        );
                      })}
                    </div>
                  </section>
                ))}
              </div>
            )}
            {editingEvent ? (
              <div className="timeline-editor-backdrop" onClick={() => setEditingEventId("")}><form className="timeline-editor" onClick={(event) => event.stopPropagation()} onSubmit={handleUpdateTimelineEvent}>
                <strong>修改事件</strong>
                <input name="editEventTitle" defaultValue={editingEvent.title} placeholder="事件标题" />
                <input name="editTimeLabel" defaultValue={editingEvent.time_label} placeholder="时间，例如：第一章" />
                <input name="editTimeOrder" defaultValue={editingEvent.time_order} type="number" placeholder="排序数字" />
                <textarea name="editEventDescription" defaultValue={editingEvent.description} placeholder="事件描述" />
                <div className="button-row">
                  <button disabled={busy} type="submit">保存修改</button>
                  <button disabled={busy} onClick={() => setEditingEventId("")} type="button">取消</button>
                  <button className="danger" disabled={busy} onClick={handleDeleteEditingTimelineEvent} type="button">删除事件</button>
                </div>
              </form></div>
            ) : null}
          </section>
          ) : null}
          {activeView === "lore" ? (
          <section className="panel lore-panel">
            <div className="section-head lore-head">
              <div><h2>设定库</h2><span>{loreEntries.length} 条设定 · {loreTypes.length - 1} 类</span></div>
              <button className="primary" disabled={busy} onClick={() => { setCreatingLore(true); setSelectedLoreId(""); }} type="button"><Plus size={16} />新增设定</button>
            </div>
            <div className="lore-workbench">
              <aside className="lore-index">
                <div className="lore-filter-row">
                  <input onChange={(event) => setLoreSearchQuery(event.target.value)} placeholder="搜索设定标题、类型或内容" value={loreSearchQuery} />
                  <select onChange={(event) => { setSelectedLoreType(event.target.value); setSelectedLoreId(""); setCreatingLore(false); }} value={selectedLoreType}>
                    {loreTypes.map((type) => <option key={type} value={type}>{type}</option>)}
                  </select>
                </div>
                <ul className="lore-list">
                  {filteredLoreEntries.length === 0 ? <li className="lore-empty-row">没有匹配的设定</li> : filteredLoreEntries.map((entry) => (
                    <li key={entry.id}>
                      <button className={!creatingLore && selectedLoreEntry?.id === entry.id ? "active" : ""} onClick={() => { setCreatingLore(false); setSelectedLoreId(entry.id); }} type="button">
                        <strong>{entry.title}</strong>
                        <span>{entry.type}</span>
                        <p>{entry.content}</p>
                      </button>
                    </li>
                  ))}
                </ul>
              </aside>
              <article className="lore-detail">
                {creatingLore ? (
                  <div className="lore-create-panel">
                    <span>新增设定</span>
                    <input onChange={(event) => setNewLoreType(event.target.value)} placeholder="类型，例如：势力 / 地点 / 规则" value={newLoreType} />
                    <input onChange={(event) => setNewLoreTitle(event.target.value)} placeholder="设定标题" value={newLoreTitle} />
                    <textarea onChange={(event) => setNewLoreContent(event.target.value)} placeholder="设定内容" value={newLoreContent} />
                    <div className="button-row">
                      <button disabled={busy || !newLoreType.trim() || !newLoreTitle.trim() || !newLoreContent.trim()} onClick={handleAddLoreEntry} type="button">保存设定</button>
                      <button disabled={busy} onClick={() => setCreatingLore(false)} type="button">取消</button>
                    </div>
                  </div>
                ) : selectedLoreEntry ? (
                  <form className="lore-edit-form" onSubmit={handleUpdateLoreEntry}>
                    <span>编辑设定</span>
                    <input key={selectedLoreEntry.id + "type"} defaultValue={selectedLoreEntry.type} name="editLoreType" placeholder="类型" />
                    <input key={selectedLoreEntry.id + "title"} defaultValue={selectedLoreEntry.title} name="editLoreTitle" placeholder="标题" />
                    <textarea key={selectedLoreEntry.id + "content"} defaultValue={selectedLoreEntry.content} name="editLoreContent" placeholder="内容" />
                    <div className="button-row">
                      <button disabled={busy} type="submit">保存修改</button>
                      <button className="danger" disabled={busy} onClick={handleDeleteLoreEntry} type="button">删除设定</button>
                    </div>
                  </form>
                ) : (
                  <div className="lore-empty-detail">
                    <strong>还没有可阅读的设定条目</strong>
                    <p>导入资料并抽取世界，或者点击右上角新增一条设定。</p>
                    <button disabled={busy} onClick={() => setCreatingLore(true)} type="button">新增设定</button>
                  </div>
                )}
              </article>
            </div>
          </section>

          ) : null}
          {activeView === "wiki" ? (
          <section className="panel wiki-panel">
            <div className="section-head"><h2>LLM Wiki</h2><span>{wikiEntries.length} 个条目</span></div>
            <div className="wiki-tools">
              <input onChange={(event) => setWikiSearchQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") handleRefreshWiki(); }} placeholder="搜索人物、地点、设定、事件" value={wikiSearchQuery} />
              <select onChange={(event) => setWikiKind(event.target.value)} value={wikiKind}>
                <option value="">全部类型</option>
                <option value="node">节点</option>
                <option value="event">事件</option>
                <option value="lore">设定</option>
              </select>
              <button disabled={busy || !activeProjectId} onClick={handleRefreshWiki} type="button">刷新 Wiki</button>
            </div>
            <div className="wiki-workbench">
              <aside className="wiki-index">
                {wikiEntries.length === 0 ? <p className="wiki-empty">暂无 Wiki 条目。</p> : wikiEntries.map((entry) => (
                  <button className={selectedWikiEntry?.id === entry.id ? "active" : ""} key={entry.id} onClick={() => setSelectedWikiId(entry.id)} type="button">
                    <strong>{entry.title}</strong>
                    <span>{entry.kind} · {entry.type || "未分类"}</span>
                    <p>{entry.summary || entry.content}</p>
                  </button>
                ))}
              </aside>
              <article className="wiki-detail">
                {selectedWikiEntry ? (
                  <>
                    <span>{selectedWikiEntry.kind} · {selectedWikiEntry.type || "未分类"}</span>
                    <h3>{selectedWikiEntry.title}</h3>
                    <p>{selectedWikiEntry.content || selectedWikiEntry.summary}</p>
                    <strong>关联链接</strong>
                    <ul>
                      {selectedWikiEntry.links.length === 0 ? <li>暂无关联</li> : selectedWikiEntry.links.map((link) => (
                        <li key={link.kind + link.id + link.relation}>
                          <button onClick={() => handleSelectWikiLink(link.id)} type="button"><b>{link.title}</b><em>{link.kind}</em><span>{link.relation}</span></button>
                        </li>
                      ))}
                    </ul>
                  </>
                ) : <p>选择一个 Wiki 条目查看内容和关联。</p>}
              </article>
            </div>
          </section>
          ) : null}
          {activeView === "report" ? (
          <section className="panel report-panel">
            <div className="section-head"><h2>剧情推演</h2><span>{report ? (report.focus_node_name || report.latest_event) : "等待推演"}</span></div>
            <div className="prediction-tools">
              <select onChange={(event) => setPredictionNodeId(event.target.value)} value={predictionNodeId}>
                <option value="">自动选择核心节点</option>
                {graph.nodes.map((node) => <option key={node.id} value={node.id}>{node.name} · {node.type}</option>)}
              </select>
              <button className="primary" disabled={busy || !activeProjectId || graph.nodes.length === 0} onClick={handlePrediction} type="button"><Play size={16} />推演剧情</button>
            </div>
            {report ? (
              <div className="report">
                <p>{report.summary}</p>
                <strong>可能分支</strong>
                <ul>{report.branches.map((branch) => <li key={branch}>{branch}</li>)}</ul>
                <strong>待确认问题</strong>
                <ul>{report.open_questions.map((question) => <li key={question}>{question}</li>)}</ul>
              </div>
            ) : <p>选择一个人物或重要节点，系统会根据它的关系网络、时间线和设定推演新的剧情走向。</p>}
          </section>
          ) : null}
        </div>
      </section>
    </main>
  );
}

