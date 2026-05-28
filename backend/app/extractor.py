from __future__ import annotations

import re
from datetime import datetime
from typing import Dict, Iterable, List, Set, Tuple

from app.schemas import LoreEntry, Node, Relationship, Source, TimelineEvent
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

def extract_world(project_id: str, store: SQLiteStore) -> Tuple[int, int, int, int, int, int]:
    all_sources = store.list_sources(project_id)
    pending_sources = [source for source in all_sources if source.extracted_at is None]
    skipped_sources = len(all_sources) - len(pending_sources)
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
        source_nodes = extract_nodes_from_source(project_id, source, set(existing_nodes))
        for node in source_nodes:
            saved = store.save_node(node)
            existing_nodes[saved.name] = saved
            created_nodes.append(saved)

        for entry in extract_lore_from_source(project_id, source):
            key = (entry.type, entry.title, entry.content)
            if key not in existing_lore_keys:
                created_lore.append(store.save_lore_entry(entry))
                existing_lore_keys.add(key)

        for event in extract_timeline_from_source(project_id, source, existing_nodes):
            key = (event.time_label, event.title, event.description)
            if key not in existing_event_keys:
                created_events.append(store.save_timeline_event(event))
                existing_event_keys.add(key)

        for relationship in extract_relationships_from_source(project_id, source, existing_nodes):
            key = (relationship.source_node_id, relationship.target_node_id, relationship.type)
            if key not in existing_relationship_keys:
                created_relationships.append(store.save_relationship(relationship))
                existing_relationship_keys.add(key)

        source.extracted_at = datetime.utcnow()
        source.extraction_version = "rules-v2"
        store.mark_source_extracted(source)

    return (
        len(created_nodes),
        len(created_relationships),
        len(created_lore),
        len(created_events),
        len(pending_sources),
        skipped_sources,
    )

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

