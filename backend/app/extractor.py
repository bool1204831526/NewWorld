from __future__ import annotations

import re
from collections import Counter
from typing import Dict, Iterable, List, Set, Tuple

from app.schemas import LoreEntry, Node, Relationship, Source, TimelineEvent
from app.storage import SQLiteStore

NODE_TYPES = {
    "人物": ["人物", "主角", "角色", "少年", "少女", "王", "女王", "骑士", "术士", "老师"],
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

TIME_PATTERN = re.compile(r"(第[一二三四五六七八九十百\d]+章|序章|终章|王历\s*\d+\s*年|\d+\s*年前|灾变前\s*\d+\s*年|灾变后\s*\d+\s*年)")
NAME_PATTERN = re.compile(r"([\u4e00-\u9fffA-Za-z0-9_·]{2,16})[：:]([^\n。！？.!?]{2,120})")


def extract_world(project_id: str, store: SQLiteStore) -> Tuple[int, int, int, int]:
    sources = store.list_sources(project_id)
    existing_nodes = {node.name: node for node in store.list_nodes(project_id)}
    created_nodes: List[Node] = []
    created_relationships: List[Relationship] = []
    created_lore: List[LoreEntry] = []
    created_events: List[TimelineEvent] = []

    for source in sources:
        source_nodes = extract_nodes_from_source(project_id, source, set(existing_nodes))
        for node in source_nodes:
            saved = store.save_node(node)
            existing_nodes[saved.name] = saved
            created_nodes.append(saved)

        for entry in extract_lore_from_source(project_id, source):
            created_lore.append(store.save_lore_entry(entry))

        for event in extract_timeline_from_source(project_id, source, existing_nodes):
            created_events.append(store.save_timeline_event(event))

    existing_relationship_keys = {
        (relationship.source_node_id, relationship.target_node_id, relationship.type)
        for relationship in store.list_relationships(project_id)
    }
    for source in sources:
        for relationship in extract_relationships_from_source(project_id, source, existing_nodes):
            key = (relationship.source_node_id, relationship.target_node_id, relationship.type)
            if key not in existing_relationship_keys:
                created_relationships.append(store.save_relationship(relationship))
                existing_relationship_keys.add(key)

    return len(created_nodes), len(created_relationships), len(created_lore), len(created_events)


def extract_nodes_from_source(project_id: str, source: Source, existing_names: Set[str]) -> List[Node]:
    candidates: Dict[str, str] = {}
    for name, description in NAME_PATTERN.findall(source.content):
        clean_name = normalize_name(name)
        if is_valid_name(clean_name):
            candidates[clean_name] = description.strip()

    for token, count in frequent_terms(source.content):
        if count >= 2 and token not in candidates:
            candidates[token] = "从资料中多次出现，自动识别为重要节点。"

    nodes: List[Node] = []
    for name, summary in candidates.items():
        if name in existing_names:
            continue
        node = Node.create(project_id=project_id, name=name, type=infer_node_type(name, summary), summary=summary)
        node.confidence = 0.72
        node.source_refs = [source.id]
        nodes.append(node)
    return nodes[:24]


def extract_relationships_from_source(project_id: str, source: Source, nodes_by_name: Dict[str, Node]) -> List[Relationship]:
    relationships: List[Relationship] = []
    sentences = split_sentences(source.content)
    for sentence in sentences:
        present = [node for name, node in nodes_by_name.items() if name in sentence]
        if len(present) < 2:
            continue
        for index, left in enumerate(present):
            for right in present[index + 1 :]:
                relation = Relationship.create(
                    project_id=project_id,
                    source_node_id=left.id,
                    target_node_id=right.id,
                    type=infer_relationship_type(sentence),
                    summary=sentence[:120],
                )
                relation.confidence = 0.58
                relation.source_refs = [source.id]
                relationships.append(relation)
    return relationships[:40]


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
    return "重要节点"


def infer_lore_type(sentence: str) -> str:
    for lore_type, keywords in LORE_KEYWORDS.items():
        if any(keyword in sentence for keyword in keywords):
            return lore_type
    return ""


def infer_relationship_type(sentence: str) -> str:
    if any(word in sentence for word in ["敌", "反对", "冲突", "追杀", "背叛"]):
        return "冲突"
    if any(word in sentence for word in ["同盟", "帮助", "支持", "师徒", "朋友"]):
        return "同盟"
    if any(word in sentence for word in ["寻找", "追寻", "持有", "拥有", "掌握"]):
        return "追寻/持有"
    if any(word in sentence for word in ["统治", "隶属", "管理", "封锁"]):
        return "控制"
    if any(word in sentence for word in ["秘密", "隐藏", "隐瞒", "真相"]):
        return "秘密关联"
    return "关联"


def frequent_terms(text: str) -> Iterable[Tuple[str, int]]:
    tokens = re.findall(r"[\u4e00-\u9fff]{2,8}", text)
    stopwords = {"一个", "他们", "因为", "但是", "后来", "这个", "以及", "资料", "设定", "剧情"}
    counter = Counter(token for token in tokens if token not in stopwords and is_valid_name(token))
    return counter.most_common(20)


def split_sentences(text: str) -> List[str]:
    return [part.strip() for part in re.split(r"(?<=[。！？!?])\s*|\n+", text) if part.strip()]


def normalize_name(name: str) -> str:
    return name.strip(" #*-，。,.；;\t\r\n")


def is_valid_name(name: str) -> bool:
    if len(name) < 2 or len(name) > 16:
        return False
    if re.search(r"[的是了和与及在为有被把到中上下一二三四五六七八九十]$", name) and len(name) > 4:
        return False
    return True

