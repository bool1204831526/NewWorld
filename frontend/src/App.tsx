import {
  BookOpen,
  GitBranch,
  Layers3,
  Network,
  Play,
  Plus,
  ScrollText,
  Sparkles,
} from "lucide-react";
import "./styles.css";

const nodes = [
  { name: "林曜", type: "人物", state: "寻找失踪的北境王印" },
  { name: "北境王印", type: "物品", state: "下落不明，牵动继承权" },
  { name: "雾港议会", type: "组织", state: "表面中立，暗中封锁港口" },
  { name: "灰塔禁令", type: "规则", state: "限制旧术使用" },
];

const relationships = [
  ["林曜", "北境王印", "追寻"],
  ["雾港议会", "北境王印", "隐瞒"],
  ["灰塔禁令", "林曜", "限制"],
];

const events = [
  { time: "序章前十年", title: "灰塔禁令颁布", detail: "旧术被列为禁忌，术士家族开始分裂。" },
  { time: "第一章", title: "北境王印失踪", detail: "继承权悬空，雾港开始封锁出入记录。" },
  { time: "第二章后", title: "林曜进入雾港", detail: "主角线与议会线交汇，隐藏冲突浮出水面。" },
];

const lore = [
  "灰塔禁令：旧术不能在王城范围内公开使用。",
  "北境继承制：王印比血统更能证明统治合法性。",
  "雾港议会：掌握航道、档案和走私审判权。",
];

export default function App() {
  return (
    <main className="workspace">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">NewWorld</p>
          <h1>叙事世界工作台</h1>
        </div>

        <section className="panel compact">
          <div className="panel-title">
            <BookOpen size={18} />
            <span>来源资料</span>
          </div>
          <textarea
            defaultValue="粘贴小说剧情、人物设定、世界观设定或章节摘要。下一步会接入抽取接口，把资料变成节点、关系、设定和时间线。"
          />
          <button type="button">
            <Sparkles size={16} />
            抽取世界
          </button>
        </section>

        <section className="panel compact">
          <div className="panel-title">
            <Plus size={18} />
            <span>手动添加</span>
          </div>
          <div className="quick-grid">
            <button type="button">节点</button>
            <button type="button">关系</button>
            <button type="button">事件</button>
            <button type="button">设定</button>
          </div>
        </section>
      </aside>

      <section className="main-area">
        <header className="topbar">
          <nav>
            <button className="active" type="button">
              <Network size={16} />
              地图
            </button>
            <button type="button">
              <GitBranch size={16} />
              时间线
            </button>
            <button type="button">
              <Layers3 size={16} />
              设定库
            </button>
            <button type="button">
              <ScrollText size={16} />
              报告
            </button>
          </nav>
          <button className="primary" type="button">
            <Play size={16} />
            推演剧情
          </button>
        </header>

        <div className="content-grid">
          <section className="panel graph-panel">
            <div className="section-head">
              <h2>重要节点地图</h2>
              <span>{nodes.length} 个节点 · {relationships.length} 条关系</span>
            </div>
            <div className="graph">
              {nodes.map((node, index) => (
                <article className={`node node-${index + 1}`} key={node.name}>
                  <strong>{node.name}</strong>
                  <span>{node.type}</span>
                </article>
              ))}
              {relationships.map((relationship) => (
                <p className="relation" key={relationship.join("-")}>
                  {relationship[0]} <span>{relationship[2]}</span> {relationship[1]}
                </p>
              ))}
            </div>
          </section>

          <section className="panel timeline-panel">
            <div className="section-head">
              <h2>时间发展线</h2>
              <span>按作品内时间排序</span>
            </div>
            <ol className="timeline">
              {events.map((event) => (
                <li key={event.title}>
                  <time>{event.time}</time>
                  <strong>{event.title}</strong>
                  <p>{event.detail}</p>
                </li>
              ))}
            </ol>
          </section>

          <section className="panel lore-panel">
            <div className="section-head">
              <h2>世界观设定</h2>
              <span>{lore.length} 条</span>
            </div>
            <ul className="lore-list">
              {lore.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>

          <section className="panel report-panel">
            <div className="section-head">
              <h2>剧情推演</h2>
              <span>草案</span>
            </div>
            <p>
              当前最强推动力来自“王印失踪”和“禁令限制”的叠加。下一步剧情可以让林曜获得一条与雾港议会有关的证据，
              迫使议会从暗中阻拦转为公开行动。
            </p>
          </section>
        </div>
      </section>
    </main>
  );
}
