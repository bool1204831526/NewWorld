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

  const activeProject = projects.find((project) => project.id === activeProjectId);
  const relationshipLabels = useMemo(() => {
    const byId = new Map(graph.nodes.map((node) => [node.id, node.name]));
    return graph.relationships.map((relationship) => ({
      ...relationship,
      sourceName: byId.get(relationship.source_node_id) ?? relationship.source_node_id,
      targetName: byId.get(relationship.target_node_id) ?? relationship.target_node_id,
    }));
  }, [graph]);

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


  function handleExtractWorld() {
    runAction(async () => {
      const projectId = requireProject();
      const result = await api.extractProject(projectId);
      await refreshProject(projectId);
      setReport(null);
      setStatus(`抽取完成：节点 ${result.created_nodes}，关系 ${result.created_relationships}，设定 ${result.created_lore_entries}，事件 ${result.created_timeline_events}`);
    }, "抽取完成");
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
            <div className="button-row"><button disabled={busy || !activeProjectId} type="submit">保存资料</button><button disabled={busy || !activeProjectId || sources.length === 0} onClick={handleExtractWorld} type="button">抽取世界</button></div>
          </form>
          <p className="status">{sources.length} 份来源资料</p>
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
            <div className="graph">
              {graph.nodes.length === 0 ? <p className="empty">先创建项目，再添加节点。</p> : graph.nodes.map((node, index) => (
                <article className={`node node-${(index % 4) + 1}`} key={node.id}><strong>{node.name}</strong><span>{node.type}</span></article>
              ))}
              {relationshipLabels.map((relationship) => <p className="relation" key={relationship.id}>{relationship.sourceName} <span>{relationship.type}</span> {relationship.targetName}</p>)}
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
            <ul className="lore-list">{loreEntries.length === 0 ? sources.map((source) => <li key={source.id}><strong>{source.title}</strong><span>{source.type}</span></li>) : loreEntries.map((entry) => <li key={entry.id}><strong>{entry.title}</strong><span>{entry.type}</span><p>{entry.content}</p></li>)}</ul>
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



