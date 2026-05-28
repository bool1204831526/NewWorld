import { FormEvent, useEffect, useMemo, useState } from "react";
import { BookOpen, GitBranch, Layers3, Network, Play, Plus, ScrollText, Sparkles } from "lucide-react";
import { GraphResponse, LoreEntry, PredictionReport, Project, Source, TimelineEvent, api } from "./api";
import "./styles.css";

const emptyGraph: GraphResponse = { nodes: [], relationships: [] };

export default function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeProjectId, setActiveProjectId] = useState("");
  const [sources, setSources] = useState<Source[]>([]);
  const [graph, setGraph] = useState<GraphResponse>(emptyGraph);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [loreEntries, setLoreEntries] = useState<LoreEntry[]>([]);
  const [report, setReport] = useState<PredictionReport | null>(null);
  const [status, setStatus] = useState("准备就绪");
  const [busy, setBusy] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState("");
  const [selectedSourceIds, setSelectedSourceIds] = useState<string[]>([]);
  const [extractMode, setExtractMode] = useState<"rules" | "llm">("rules");
  const [llmApiBase, setLlmApiBase] = useState("https://api.openai.com/v1");
  const [llmModel, setLlmModel] = useState("gpt-4o-mini");
  const [llmApiKey, setLlmApiKey] = useState("");

  const activeProject = projects.find((project) => project.id === activeProjectId);
  const relationshipLabels = useMemo(() => {
    const byId = new Map(graph.nodes.map((node) => [node.id, node.name]));
    return graph.relationships.map((relationship) => ({
      ...relationship,
      sourceName: byId.get(relationship.source_node_id) ?? relationship.source_node_id,
      targetName: byId.get(relationship.target_node_id) ?? relationship.target_node_id,
    }));
  }, [graph]);

  const selectedNode = graph.nodes.find((node) => node.id === selectedNodeId) ?? graph.nodes[0];
  const selectedRelationships = useMemo(() => {
    if (!selectedNode) return [];
    return relationshipLabels.filter((relationship) =>
      relationship.source_node_id === selectedNode.id || relationship.target_node_id === selectedNode.id,
    );
  }, [relationshipLabels, selectedNode]);
  const graphLayout = useMemo(() => {
    const width = 900;
    const height = 520;
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
    const nodes = graph.nodes.map((node, index) => {
      const connected = degree.get(node.id) ?? 0;
      if (focusNode && node.id === focusNode.id) {
        return { ...node, connected, focusLevel: "selected", x: centerX, y: centerY };
      }
      if (focusNode && focusedRelationshipNodeIds.has(node.id)) {
        const position = placeOnRing(relatedOrder.get(node.id) ?? 0, relatedIds.length, 245, 155);
        return { ...node, connected, focusLevel: "related", ...position };
      }
      if (focusNode) {
        const position = placeOnRing(outerOrder.get(node.id) ?? 0, Math.max(outerIds.length, 1), 370, 225, -Math.PI / 3);
        return { ...node, connected, focusLevel: "outer", ...position };
      }
      const position = placeOnRing(index, graph.nodes.length, Math.max(190, Math.min(340, 96 + graph.nodes.length * 18)), Math.max(140, Math.min(210, 82 + graph.nodes.length * 10)));
      return { ...node, connected, focusLevel: "normal", ...position };
    });
    const byId = new Map(nodes.map((node) => [node.id, node]));
    const edges = relationshipLabels
      .map((relationship) => ({
        ...relationship,
        source: byId.get(relationship.source_node_id),
        target: byId.get(relationship.target_node_id),
      }))
      .filter((edge) => edge.source && edge.target);
    return { width, height, nodes, edges };
  }, [graph.nodes, graph.relationships, relationshipLabels, selectedNode, selectedRelationships]);

  async function refreshProject(projectId: string) {
    const [nextSources, nextGraph, nextEvents, nextLore] = await Promise.all([
      api.listSources(projectId),
      api.getGraph(projectId),
      api.getTimeline(projectId),
      api.getLore(projectId),
    ]);
    setSources(nextSources);
    setGraph(nextGraph);
    setEvents(nextEvents);
    setLoreEntries(nextLore);
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

  async function runAction(action: () => Promise<void>, doneMessage: string) {
    setBusy(true);
    setStatus("处理中...");
    try {
      await action();
      setStatus(doneMessage);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "操作失败");
    } finally {
      setBusy(false);
    }
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
  function handleAddNode(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const name = String(form.get("nodeName") ?? "").trim();
    const type = String(form.get("nodeType") ?? "人物").trim();
    const summary = String(form.get("nodeSummary") ?? "").trim();
    if (!name) return;
    runAction(async () => {
      const projectId = requireProject();
      await api.addNode(projectId, { name, type, summary });
      await refreshProject(projectId);
      formElement.reset();
    }, "节点已添加");
  }

  function handleAddRelationship(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const source_node_id = String(form.get("sourceNodeId") ?? "");
    const target_node_id = String(form.get("targetNodeId") ?? "");
    const type = String(form.get("relationshipType") ?? "关联").trim();
    const summary = String(form.get("relationshipSummary") ?? "").trim();
    if (!source_node_id || !target_node_id || source_node_id === target_node_id) return;
    runAction(async () => {
      const projectId = requireProject();
      await api.addRelationship(projectId, { source_node_id, target_node_id, type, summary });
      await refreshProject(projectId);
      formElement.reset();
    }, "关系已添加");
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
      await api.addTimelineEvent(projectId, {
        title,
        time_label,
        time_order,
        description,
        participant_node_ids: participant ? [participant] : [],
      });
      await refreshProject(projectId);
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
  function handleExtractWorld() {
    runAction(async () => {
      const projectId = requireProject();
      const llmPayload = extractMode === "llm" ? {
        api_base: String((document.querySelector("[name=llmApiBase]") as HTMLInputElement)?.value || "").trim(),
        api_key: String((document.querySelector("[name=llmApiKey]") as HTMLInputElement)?.value || "").trim(),
        model: String((document.querySelector("[name=llmModel]") as HTMLInputElement)?.value || "").trim(),
      } : null;
      if (extractMode === "llm" && (!llmPayload?.api_base || !llmPayload.api_key || !llmPayload.model)) {
        throw new Error("请填写 LLM API Base、API Key 和模型名");
      }
      const result = await api.extractProject(projectId, {
        source_ids: selectedSourceIds,
        mode: extractMode,
        llm: llmPayload,
      });
      await refreshProject(projectId);
      setReport(null);
      setStatus(`抽取完成：处理 ${result.processed_sources} 份，跳过 ${result.skipped_sources} 份；新增节点 ${result.created_nodes}，关系 ${result.created_relationships}，设定 ${result.created_lore_entries}，事件 ${result.created_timeline_events}`);
    }, "抽取完成");
  }

  function handleDeleteSelectedNode() {
    if (!selectedNode) return;
    const confirmed = window.confirm(`删除节点“${selectedNode.name}”？与它相连的关系也会一并删除。`);
    if (!confirmed) return;
    runAction(async () => {
      const projectId = requireProject();
      await api.deleteNode(projectId, selectedNode.id);
      setSelectedNodeId("");
      await refreshProject(projectId);
    }, "节点已删除");
  }
  function handlePrediction() {
    runAction(async () => {
      const projectId = requireProject();
      setReport(await api.createPrediction(projectId));
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
                <input name="llmModel" onChange={(event) => setLlmModel(event.target.value)} placeholder="模型名，例如：gpt-4o-mini" value={llmModel} />
                <input name="llmApiKey" onChange={(event) => setLlmApiKey(event.target.value)} placeholder="API Key，仅本次请求使用" type="password" value={llmApiKey} />
              </div>
            ) : null}
            <button disabled={busy || !activeProjectId || sources.length === 0} onClick={handleExtractWorld} type="button">抽取世界</button>
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
            <button className="active" type="button"><Network size={16} />地图</button>
            <button type="button"><GitBranch size={16} />时间线</button>
            <button type="button"><Layers3 size={16} />设定库</button>
            <button type="button"><ScrollText size={16} />报告</button>
          </nav>
          <button className="primary" disabled={busy || !activeProjectId} onClick={handlePrediction} type="button">
            <Play size={16} />推演剧情
          </button>
        </header>

        <div className="content-grid">
          <section className="panel form-panel">
            <div className="section-head"><h2>手动添加</h2><span>{status}</span></div>
            <div className="form-grid">
              <form className="stack" onSubmit={handleAddNode}>
                <strong>节点</strong>
                <input name="nodeName" placeholder="名称，例如：林曜" />
                <input name="nodeType" placeholder="类型，例如：人物 / 组织 / 物品" />
                <textarea name="nodeSummary" placeholder="节点简介" />
                <button disabled={busy || !activeProjectId} type="submit">添加节点</button>
              </form>

              <form className="stack" onSubmit={handleAddRelationship}>
                <strong>关系</strong>
                <select name="sourceNodeId"><option value="">起点节点</option>{graph.nodes.map((node) => <option key={node.id} value={node.id}>{node.name}</option>)}</select>
                <select name="targetNodeId"><option value="">终点节点</option>{graph.nodes.map((node) => <option key={node.id} value={node.id}>{node.name}</option>)}</select>
                <input name="relationshipType" placeholder="关系，例如：追寻 / 敌对 / 隐瞒" />
                <input name="relationshipSummary" placeholder="关系说明" />
                <button disabled={busy || graph.nodes.length < 2} type="submit">添加关系</button>
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
                      const selected = selectedNode && (edge.source_node_id === selectedNode.id || edge.target_node_id === selectedNode.id);
                      const midX = ((edge.source?.x ?? 0) + (edge.target?.x ?? 0)) / 2;
                      const midY = ((edge.source?.y ?? 0) + (edge.target?.y ?? 0)) / 2;
                      return (
                        <g className={selected ? "edge selected" : "edge"} key={edge.id}>
                          <line markerEnd="url(#arrow)" x1={edge.source?.x} x2={edge.target?.x} y1={edge.source?.y} y2={edge.target?.y} />
                          <text x={midX} y={midY}>{edge.type}</text>
                        </g>
                      );
                    })}
                    {graphLayout.nodes.map((node) => {
                      const selected = selectedNode?.id === node.id;
                      const related = node.focusLevel === "related";
                      return (
                        <g className={selected ? "graph-node selected" : related ? "graph-node related" : node.focusLevel === "outer" ? "graph-node outer" : "graph-node"} key={node.id} onClick={() => setSelectedNodeId(node.id)} role="button" tabIndex={0}>
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

          <section className="panel timeline-panel">
            <div className="section-head"><h2>时间发展线</h2><span>按作品内时间排序</span></div>
            <ol className="timeline">
              {events.map((event) => <li key={event.id}><time>{event.time_label}</time><strong>{event.title}</strong><p>{event.description || "暂无描述"}</p></li>)}
            </ol>
          </section>

          <section className="panel lore-panel">
            <div className="section-head"><h2>世界观设定</h2><span>{loreEntries.length} 条</span></div>
            <ul className="lore-list">{loreEntries.length === 0 ? sources.map((source) => <li key={source.id}><strong>{source.title}</strong><span>{source.type} · {source.extracted_at ? "已抽取" : "待抽取"}</span></li>) : loreEntries.map((entry) => <li key={entry.id}><strong>{entry.title}</strong><span>{entry.type}</span><p>{entry.content}</p></li>)}</ul>
          </section>

          <section className="panel report-panel">
            <div className="section-head"><h2>剧情推演</h2><span>{report ? report.latest_event : "等待推演"}</span></div>
            {report ? <div className="report"><p>{report.summary}</p><strong>可能分支</strong><ul>{report.branches.map((branch) => <li key={branch}>{branch}</li>)}</ul><strong>待确认问题</strong><ul>{report.open_questions.map((question) => <li key={question}>{question}</li>)}</ul></div> : <p>添加节点和时间线事件后，点击“推演剧情”生成第一版走向。</p>}
          </section>
        </div>
      </section>
    </main>
  );
}






