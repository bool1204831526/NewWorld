from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Set, Tuple

from app.schemas import LLMExtractionConfig, LoreEntry, Node, Relationship, Source, TimelineEvent
from app.storage import SQLiteStore

NODE_TYPES = {
    "人物": ["人物", "主角", "角色", "少年", "少女", "王", "女王", "骑士", "术士", "老师", "旅人"],
    "组织": ["组织", "议会", "协会", "军团", "学院", "家族", "王国", "帝国", "教会", "商会"],
    "地点": ["地点", "城市", "港", "城", "塔", "村", "大陆", "森林", "王城", "北境"],
    "物品": ["物品", "王印", "剑", "书", "钥匙", "戒指", "神器", "药剂"],
    "规则": ["规则", "禁令", "法律", "契约", "仪式", "能力", "魔法", "旧术"],
    "事件": ["事件", "战争", "失踪", "灾变", "叛乱", "审判", "远征"],
}

LORE_KEYWORDS = {
    "地理": ["地点", "城市", "大陆", "王城", "北境", "雾港"],
    "历史": ["历史", "纪年", "年前", "王历", "战争", "灾变"],
    "组织": ["组织", "议会", "协会", "教会", "家族", "军团"],
    "能力体系": ["能力", "魔法", "旧术", "术士", "禁术", "仪式"],
    "制度规则": ["规则", "禁令", "法律", "继承", "制度", "契约"],
    "物品资源": ["物品", "王印", "神器", "资源", "矿", "药剂"],
    "秘密伏笔": ["秘密", "隐藏", "传闻", "真相", "失踪", "背叛"],
}

RELATION_KEYWORDS = {
    "冲突": ["敌", "反对", "冲突", "追杀", "背叛", "阻止", "争夺"],
    "同盟": ["同盟", "帮助", "支持", "师徒", "朋友", "协助", "保护"],
    "追寻": ["寻找", "追寻", "调查", "追查", "试图获得"],
    "持有": ["持有", "拥有", "掌握", "携带", "继承"],
    "控制": ["统治", "隶属", "管理", "封锁", "支配", "管辖"],
    "秘密关联": ["秘密", "隐藏", "隐瞒", "真相", "传闻"],
    "规则约束": ["规定", "禁止", "不能", "必须", "契约", "禁令", "法律"],
}

TIME_PATTERN = re.compile(r"(第[一二三四五六七八九十百\d]+章|序章|终章|王历\s*\d+\s*年|\d+\s*年前|灾变前\s*\d+\s*年|灾变后\s*\d+\s*年)")
NAME_PATTERN = re.compile(r"([\u4e00-\u9fffA-Za-z0-9_·]{2,16})[：:]([^\n。！？.!?]{2,160})")

WEAK_ENTITY_NAMES = {
    "第一章", "第二章", "第三章", "第四章", "第五章", "第六章", "序章", "终章",
    "剧情", "资料", "设定", "世界观", "人物设定", "章节摘要", "内容", "故事",
}

def extract_world(
    project_id: str,
    store: SQLiteStore,
    source_ids: Optional[List[str]] = None,
    mode: str = "rules",
    llm_config: Optional[LLMExtractionConfig] = None,
) -> Tuple[int, int, int, int, int, int]:
    all_sources = store.list_sources(project_id)
    selected_source_ids = set(source_ids or [])
    candidate_sources = [source for source in all_sources if not selected_source_ids or source.id in selected_source_ids]
    pending_sources = [source for source in candidate_sources if source.extracted_at is None]
    skipped_sources = len(candidate_sources) - len(pending_sources)
    existing_nodes = {node.name: node for node in store.list_nodes(project_id)}
    existing_relationship_keys = {
        (relationship.source_node_id, relationship.target_node_id, relationship.type)
        for relationship in store.list_relationships(project_id)
    }
    existing_lore_keys = {
        (entry.type, entry.title, entry.content)
        for entry in store.list_lore_entries(project_id)
    }
    existing_event_keys = {
        (event.time_label, event.title, event.description)
        for event in store.list_timeline_events(project_id)
    }
    created_nodes: List[Node] = []
    created_relationships: List[Relationship] = []
    created_lore: List[LoreEntry] = []
    created_events: List[TimelineEvent] = []

    for source in pending_sources:
        if mode == "llm":
            if not llm_config:
                raise ValueError("LLM 抽取需要 API 配置")
            extracted = extract_source_with_llm(project_id, source, existing_nodes, llm_config)
            source_nodes = extracted["nodes"]
            source_lore = extracted["lore"]
            source_events = extracted["events"]
            source_relationships = extracted["relationships"]
        else:
            source_nodes = extract_nodes_from_source(project_id, source, set(existing_nodes))
            source_lore = extract_lore_from_source(project_id, source)
            source_events = extract_timeline_from_source(project_id, source, existing_nodes)
            source_relationships = []
        for node in source_nodes:
            saved = store.save_node(node)
            existing_nodes[saved.name] = saved
            created_nodes.append(saved)

        if mode != "llm":
            source_relationships = extract_relationships_from_source(project_id, source, existing_nodes)

        for entry in source_lore:
            key = (entry.type, entry.title, entry.content)
            if key not in existing_lore_keys:
                created_lore.append(store.save_lore_entry(entry))
                existing_lore_keys.add(key)

        for event in source_events:
            key = (event.time_label, event.title, event.description)
            if key not in existing_event_keys:
                created_events.append(store.save_timeline_event(event))
                existing_event_keys.add(key)

        for relationship in source_relationships:
            key = (relationship.source_node_id, relationship.target_node_id, relationship.type)
            if key not in existing_relationship_keys:
                created_relationships.append(store.save_relationship(relationship))
                existing_relationship_keys.add(key)

        source.extracted_at = datetime.utcnow()
        source.extraction_version = "llm-v1" if mode == "llm" else "rules-v2"
        store.mark_source_extracted(source)

    return (
        len(created_nodes),
        len(created_relationships),
        len(created_lore),
        len(created_events),
        len(pending_sources),
        skipped_sources,
    )


def extract_source_with_llm(
    project_id: str,
    source: Source,
    existing_nodes: Dict[str, Node],
    config: LLMExtractionConfig,
) -> Dict[str, List]:
    payload = call_llm_extractor(source, config)
    nodes: List[Node] = []
    node_by_name = dict(existing_nodes)
    for item in payload.get("nodes", [])[:40]:
        name = normalize_name(str(item.get("name", "")))
        summary = normalize_description(str(item.get("summary", "")))
        if not is_describable_entity(name, summary) or name in node_by_name:
            continue
        node = Node.create(project_id=project_id, name=name, type=str(item.get("type") or infer_node_type(name, summary)), summary=summary)
        node.confidence = float(item.get("confidence") or 0.82)
        node.source_refs = [source.id]
        nodes.append(node)
        node_by_name[name] = node

    relationships: List[Relationship] = []
    for item in payload.get("relationships", [])[:80]:
        source_name = normalize_name(str(item.get("source") or item.get("source_name") or ""))
        target_name = normalize_name(str(item.get("target") or item.get("target_name") or ""))
        left = node_by_name.get(source_name)
        right = node_by_name.get(target_name)
        if not left or not right or left.id == right.id:
            continue
        relation = Relationship.create(
            project_id=project_id,
            source_node_id=left.id,
            target_node_id=right.id,
            type=str(item.get("type") or "关联"),
            summary=str(item.get("summary") or f"{left.name} 与 {right.name} 形成关联。"),
        )
        relation.confidence = float(item.get("confidence") or 0.72)
        relation.source_refs = [source.id]
        relationships.append(relation)

    lore: List[LoreEntry] = []
    for item in payload.get("lore", [])[:40]:
        title = normalize_description(str(item.get("title") or item.get("type") or "设定"))[:40]
        content = normalize_description(str(item.get("content") or ""))
        if not content:
            continue
        entry = LoreEntry.create(project_id=project_id, type=str(item.get("type") or "设定"), title=title, content=content)
        entry.confidence = float(item.get("confidence") or 0.72)
        entry.source_refs = [source.id]
        lore.append(entry)

    events: List[TimelineEvent] = []
    for index, item in enumerate(payload.get("timeline_events", []), start=1):
        title = normalize_description(str(item.get("title") or "时间线事件"))[:40]
        time_label = normalize_description(str(item.get("time_label") or "未标注"))[:30]
        description = normalize_description(str(item.get("description") or title))
        participant_ids = [node_by_name[name].id for name in node_by_name if name in description][:8]
        event = TimelineEvent.create(
            project_id=project_id,
            title=title,
            time_label=time_label,
            time_order=int(item.get("time_order") or index),
            description=description,
            participant_node_ids=participant_ids,
        )
        event.source_refs = [source.id]
        events.append(event)

    return {"nodes": nodes, "relationships": relationships, "lore": lore, "events": events}


def call_llm_extractor(source: Source, config: LLMExtractionConfig) -> Dict:
    api_base = validate_llm_api_base(config.api_base)
    api_key = validate_llm_api_key(config.api_key)
    model = config.model.strip()
    if not model:
        raise ValueError("LLM 模型名不能为空")
    url = f"{api_base}/chat/completions"
    prompt = (
        "你是小说资料结构化抽取器。请只返回 JSON，不要解释。"
        "JSON 字段：nodes, relationships, lore, timeline_events。"
        "nodes: [{name,type,summary,confidence}]，只保留可描述的重要实体。"
        "relationships: [{source,target,type,summary,confidence}]，summary 必须是总结，不要照抄原文。"
        "lore: [{type,title,content,confidence}]。"
        "timeline_events: [{title,time_label,time_order,description}]。"
    )
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"资料标题：{source.title}\n资料类型：{source.type}\n资料内容：\n{source.content}"},
        ],
        "temperature": 0.2,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "NewWorld/0.1 OpenAI-Compatible-Client",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            response_text = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="ignore")
        raise ValueError(f"LLM 接口返回 HTTP {error.code}：{extract_llm_error_message(error_body, error.code)}")
    except urllib.error.URLError as error:
        raise ValueError(f"无法连接 LLM 接口：{error.reason}")
    except TimeoutError:
        raise ValueError("LLM 请求超时，请检查网络或稍后重试")

    try:
        response_data = json.loads(response_text)
        content = response_data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
        raise ValueError(f"LLM 接口返回格式不符合 OpenAI Chat Completions：{error}")

    try:
        parsed = json.loads(strip_json_code_fence(content))
    except json.JSONDecodeError as error:
        preview = content[:300].replace("\n", " ")
        raise ValueError(f"LLM 未返回合法 JSON：{error.msg}。返回片段：{preview}")
    if not isinstance(parsed, dict):
        raise ValueError("LLM 返回内容不是 JSON 对象")
    return parsed


def validate_llm_api_base(api_base: str) -> str:
    value = api_base.strip().rstrip("/")
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("LLM API Base 必须是 http 或 https 接口地址")
    try:
        value.encode("ascii")
    except UnicodeEncodeError:
        raise ValueError("LLM API Base 不能包含中文或全角字符，请填写接口地址")
    return value


def validate_llm_api_key(api_key: str) -> str:
    value = api_key.strip()
    if not value:
        raise ValueError("LLM API Key 不能为空")
    try:
        value.encode("latin-1")
    except UnicodeEncodeError:
        raise ValueError("LLM API Key 包含无法用于 HTTP 请求头的字符，请检查是否误粘贴了中文、全角字符或说明文字")
    return value

def extract_llm_error_message(error_body: str, status_code: Optional[int] = None) -> str:
    if not error_body:
        return "无响应内容"
    raw_message = error_body[:500]
    try:
        data = json.loads(error_body)
        if isinstance(data, dict):
            error = data.get("error")
            if isinstance(error, dict):
                raw_message = str(error.get("message") or error)
            else:
                raw_message = str(data.get("message") or data)
    except json.JSONDecodeError:
        pass
    if status_code == 403 and "1010" in raw_message:
        return (
            f"{raw_message}。这通常表示 API 网关拒绝了当前运行环境的请求。"
            "如果 API Base 已确认无误，请重点检查 API Key 权限、当前 IP、代理/VPN、服务商白名单，"
            "或该服务商是否拦截 Python/本地客户端请求。"
        )
    return raw_message


def strip_json_code_fence(content: str) -> str:
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()
def extract_nodes_from_source(project_id: str, source: Source, existing_names: Set[str]) -> List[Node]:
    candidates: Dict[str, str] = {}
    for name, description in NAME_PATTERN.findall(source.content):
        clean_name = normalize_name(name)
        clean_description = normalize_description(description)
        if is_describable_entity(clean_name, clean_description):
            candidates[clean_name] = clean_description

    nodes: List[Node] = []
    for name, summary in candidates.items():
        if name in existing_names:
            continue
        node = Node.create(project_id=project_id, name=name, type=infer_node_type(name, summary), summary=summary)
        node.confidence = 0.78
        node.source_refs = [source.id]
        nodes.append(node)
    return nodes[:32]

def extract_relationships_from_source(project_id: str, source: Source, nodes_by_name: Dict[str, Node]) -> List[Relationship]:
    relationships: List[Relationship] = []
    sentences = split_sentences(source.content)
    for sentence in sentences:
        present = [node for name, node in nodes_by_name.items() if name in sentence]
        if len(present) < 2:
            continue
        relation_types = infer_relationship_types(sentence)
        for relation_type in relation_types:
            for index, left in enumerate(present):
                for right in present[index + 1:]:
                    relation = Relationship.create(
                        project_id=project_id,
                        source_node_id=left.id,
                        target_node_id=right.id,
                        type=relation_type,
                        summary=summarize_relationship(left.name, right.name, relation_type, sentence),
                    )
                    relation.confidence = 0.62
                    relation.source_refs = [source.id]
                    relationships.append(relation)
    return relationships[:60]

def extract_lore_from_source(project_id: str, source: Source) -> List[LoreEntry]:
    entries: List[LoreEntry] = []
    for sentence in split_sentences(source.content):
        lore_type = infer_lore_type(sentence)
        if not lore_type:
            continue
        title = sentence[:24].strip(" ，。,.；;") or lore_type
        entry = LoreEntry.create(project_id=project_id, type=lore_type, title=title, content=sentence)
        entry.confidence = 0.62
        entry.source_refs = [source.id]
        entries.append(entry)
    return entries[:30]

def extract_timeline_from_source(project_id: str, source: Source, nodes_by_name: Dict[str, Node]) -> List[TimelineEvent]:
    events: List[TimelineEvent] = []
    for index, sentence in enumerate(split_sentences(source.content), start=1):
        match = TIME_PATTERN.search(sentence)
        if not match:
            continue
        participants = [node.id for name, node in nodes_by_name.items() if name in sentence]
        title = sentence.replace(match.group(1), "").strip(" ，。,.；;")[:32] or "时间线事件"
        event = TimelineEvent.create(
            project_id=project_id,
            title=title,
            time_label=match.group(1).replace(" ", ""),
            time_order=index,
            description=sentence,
            participant_node_ids=participants[:8],
        )
        event.source_refs = [source.id]
        events.append(event)
    return events[:30]

def infer_node_type(name: str, summary: str) -> str:
    text = f"{name} {summary}"
    for node_type, keywords in NODE_TYPES.items():
        if any(keyword in text for keyword in keywords):
            return node_type
    return "重要实体"

def infer_lore_type(sentence: str) -> str:
    for lore_type, keywords in LORE_KEYWORDS.items():
        if any(keyword in sentence for keyword in keywords):
            return lore_type
    return ""

def infer_relationship_types(sentence: str) -> List[str]:
    relation_types = [
        relation_type
        for relation_type, keywords in RELATION_KEYWORDS.items()
        if any(keyword in sentence for keyword in keywords)
    ]
    return relation_types or ["关联"]

def summarize_relationship(left_name: str, right_name: str, relation_type: str, sentence: str) -> str:
    reason = infer_relationship_reason(relation_type, sentence)
    if reason:
        return f"{left_name} 与 {right_name} 存在{relation_type}关系，核心原因是{reason}。"
    return f"{left_name} 与 {right_name} 在当前资料中形成{relation_type}关系。"

def infer_relationship_reason(relation_type: str, sentence: str) -> str:
    if relation_type == "冲突":
        return "双方目标、立场或利益发生对抗"
    if relation_type == "同盟":
        return "双方存在协助、支持或共同目标"
    if relation_type == "追寻":
        return "一方正在寻找、调查或接近另一方"
    if relation_type == "持有":
        return "资料暗示存在拥有、掌握或继承关系"
    if relation_type == "控制":
        return "资料暗示存在管理、统治或约束关系"
    if relation_type == "秘密关联":
        return "双方之间存在隐藏信息、传闻或未公开真相"
    if relation_type == "规则约束":
        return "相关规则、禁令或制度影响双方行动"
    return ""

def split_sentences(text: str) -> List[str]:
    return [part.strip() for part in re.split(r"(?<=[。！？!?])\s*|\n+", text) if part.strip()]

def normalize_name(name: str) -> str:
    return name.strip(" #*-，。,.；;\t\r\n")

def normalize_description(description: str) -> str:
    return description.strip(" #*-，。,.；;\t\r\n")

def is_describable_entity(name: str, description: str) -> bool:
    if not is_valid_name(name):
        return False
    if len(description) < 4 or description in WEAK_ENTITY_NAMES:
        return False
    if not re.search(r"[\u4e00-\u9fffA-Za-z]", description):
        return False
    weak_description_patterns = ["暂无", "待定", "无", "未知"]
    if description in weak_description_patterns:
        return False
    return True

def is_valid_name(name: str) -> bool:
    if len(name) < 2 or len(name) > 16:
        return False
    if name in WEAK_ENTITY_NAMES:
        return False
    if re.search(r"第[一二三四五六七八九十百\d]+章", name):
        return False
    if re.search(r"[的是了和与及在为有被把到中上下一二三四五六七八九十]$", name) and len(name) > 4:
        return False
    return True

