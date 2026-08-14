#!/usr/bin/env python3

import datetime
from pathlib import Path

from sqlalchemy import func

from webserver.models import LibraryBookCategory, LibraryCategory, ReadingState, ShelfCategory, ShelfCategoryBook


MAX_CATEGORY_DEPTH = 12
MAX_CATEGORY_NAME_LENGTH = 100
PARENT_UNCHANGED = object()


class CategoryError(ValueError):
    pass


def normalize_name(name):
    name = " ".join(str(name or "").strip().split())
    if not name:
        raise CategoryError("分类名称不能为空")
    if len(name) > MAX_CATEGORY_NAME_LENGTH:
        raise CategoryError("分类名称不能超过100个字符")
    if name in {".", ".."} or "/" in name or "\\" in name:
        raise CategoryError("分类名称不能包含路径分隔符")
    return name


def category_path_from_file(scan_root, file_path):
    root = Path(scan_root).resolve()
    path = Path(file_path).resolve()
    try:
        relative = path.relative_to(root)
    except ValueError as error:
        raise CategoryError("扫描文件不在导入根目录中") from error
    parts = [normalize_name(part) for part in relative.parent.parts if not part.startswith(".")]
    if len(parts) > MAX_CATEGORY_DEPTH:
        raise CategoryError("目录分类不能超过12层")
    return parts


def _scope_filter(query, model, reader_id):
    return query.filter(model.reader_id == reader_id) if model is ShelfCategory else query


def find_child(session, model, parent_id, name, reader_id=None):
    query = session.query(model).filter(model.parent_id == parent_id, model.name == name)
    return _scope_filter(query, model, reader_id).first()


def ensure_path(session, model, names, reader_id=None):
    if len(names) > MAX_CATEGORY_DEPTH:
        raise CategoryError("分类层级不能超过12层")
    parent_id = None
    node = None
    for raw_name in names:
        name = normalize_name(raw_name)
        node = find_child(session, model, parent_id, name, reader_id)
        if node is None:
            node = model(name=name, parent_id=parent_id)
            if model is ShelfCategory:
                node.reader_id = reader_id
            session.add(node)
            session.flush()
        parent_id = node.id
    return node


def node_path(session, node):
    path = []
    seen = set()
    while node is not None:
        if node.id in seen:
            raise CategoryError("分类树存在循环")
        seen.add(node.id)
        path.append(node.name)
        node = session.get(type(node), node.parent_id) if node.parent_id else None
    return list(reversed(path))


def assign_library_path(session, book_id, names):
    if not names:
        return None
    existing = session.get(LibraryBookCategory, book_id)
    if existing is not None:
        return existing.category
    category = ensure_path(session, LibraryCategory, names)
    session.add(LibraryBookCategory(book_id=book_id, category_id=category.id))
    session.commit()
    return category


def inherit_library_path(session, reader_id, book_id):
    link = session.get(LibraryBookCategory, book_id)
    if link is None:
        return None
    names = node_path(session, link.category)
    category = ensure_path(session, ShelfCategory, names, reader_id)
    existing = session.get(ShelfCategoryBook, (reader_id, category.id, book_id))
    if existing is None:
        session.add(ShelfCategoryBook(reader_id=reader_id, category_id=category.id, book_id=book_id))
        session.commit()
    return category


def remove_book_from_shelf_categories(session, reader_id, book_id):
    session.query(ShelfCategoryBook).filter(
        ShelfCategoryBook.reader_id == reader_id, ShelfCategoryBook.book_id == book_id
    ).delete(synchronize_session=False)
    session.commit()


def descendants(nodes, category_id):
    children = {}
    for node in nodes:
        children.setdefault(node.parent_id, []).append(node.id)
    result = set()
    pending = [category_id]
    while pending:
        current = pending.pop()
        if current in result:
            continue
        result.add(current)
        pending.extend(children.get(current, []))
    return result


def build_tree(session, model, reader_id=None, visible_book_ids=None):
    query = _scope_filter(session.query(model), model, reader_id)
    nodes = query.order_by(model.sort_order.asc(), model.name.asc()).all()
    if model is LibraryCategory:
        count_query = session.query(LibraryBookCategory.category_id, func.count(LibraryBookCategory.book_id))
        if visible_book_ids is not None:
            count_query = count_query.filter(LibraryBookCategory.book_id.in_(visible_book_ids))
        direct_counts = dict(count_query.group_by(LibraryBookCategory.category_id).all())
    else:
        direct_counts = dict(
            session.query(ShelfCategoryBook.category_id, func.count(ShelfCategoryBook.book_id))
            .filter(ShelfCategoryBook.reader_id == reader_id)
            .group_by(ShelfCategoryBook.category_id)
            .all()
        )
    by_parent = {}
    for node in nodes:
        by_parent.setdefault(node.parent_id, []).append(node)

    def serialize(node, depth=1):
        children = [serialize(child, depth + 1) for child in by_parent.get(node.id, [])]
        direct = direct_counts.get(node.id, 0)
        return {
            "id": node.id,
            "name": node.name,
            "parent_id": node.parent_id,
            "depth": depth,
            "direct_count": direct,
            "count": direct + sum(child["count"] for child in children),
            "children": children,
        }

    return [serialize(node) for node in by_parent.get(None, [])]


def create_category(session, model, name, parent_id=None, reader_id=None):
    name = normalize_name(name)
    if parent_id:
        parent = session.get(model, parent_id)
        if parent is None or (model is ShelfCategory and parent.reader_id != reader_id):
            raise CategoryError("父分类不存在")
        if len(node_path(session, parent)) >= MAX_CATEGORY_DEPTH:
            raise CategoryError("分类层级不能超过12层")
    if find_child(session, model, parent_id, name, reader_id):
        raise CategoryError("同级分类名称已存在")
    node = model(name=name, parent_id=parent_id, sort_order=0)
    if model is ShelfCategory:
        node.reader_id = reader_id
    session.add(node)
    session.commit()
    return node


def update_category(session, model, category_id, reader_id=None, name=None, parent_id=PARENT_UNCHANGED):
    node = session.get(model, category_id)
    if node is None or (model is ShelfCategory and node.reader_id != reader_id):
        raise CategoryError("分类不存在")
    new_parent_id = node.parent_id if parent_id is PARENT_UNCHANGED else parent_id
    if new_parent_id == node.id:
        raise CategoryError("分类不能移动到自身")
    all_nodes = _scope_filter(session.query(model), model, reader_id).all()
    if new_parent_id in descendants(all_nodes, node.id):
        raise CategoryError("分类不能移动到其后代")
    parent = session.get(model, new_parent_id) if new_parent_id else None
    if new_parent_id and (parent is None or (model is ShelfCategory and parent.reader_id != reader_id)):
        raise CategoryError("目标父分类不存在")
    target_name = normalize_name(name) if name is not None else node.name
    conflict = find_child(session, model, new_parent_id, target_name, reader_id)
    if conflict and conflict.id != node.id:
        raise CategoryError("目标位置存在同名分类")
    if parent and len(node_path(session, parent)) + _subtree_depth(all_nodes, node.id) > MAX_CATEGORY_DEPTH:
        raise CategoryError("移动后分类层级将超过12层")
    node.name = target_name
    node.parent_id = new_parent_id
    node.update_time = datetime.datetime.now()
    session.commit()
    return node


def _subtree_depth(nodes, category_id):
    children = {}
    for node in nodes:
        children.setdefault(node.parent_id, []).append(node.id)

    def depth(node_id):
        return 1 + max((depth(child) for child in children.get(node_id, [])), default=0)

    return depth(category_id)


def assign_book(session, model, category_id, book_id, reader_id=None):
    category = session.get(model, category_id)
    if category is None or (model is ShelfCategory and category.reader_id != reader_id):
        raise CategoryError("分类不存在")
    if model is LibraryCategory:
        link = session.get(LibraryBookCategory, book_id)
        if link is None:
            link = LibraryBookCategory(book_id=book_id, category_id=category_id)
            session.add(link)
        else:
            link.category_id = category_id
    else:
        wants = (
            session.query(ReadingState)
            .filter(ReadingState.reader_id == reader_id, ReadingState.book_id == book_id, ReadingState.wants == 1)
            .first()
        )
        if wants is None:
            raise CategoryError("书籍尚未加入个人书架")
        if session.get(ShelfCategoryBook, (reader_id, category_id, book_id)) is None:
            session.add(ShelfCategoryBook(reader_id=reader_id, category_id=category_id, book_id=book_id))
    session.commit()


def unassign_book(session, model, book_id, category_id=None, reader_id=None):
    if model is LibraryCategory:
        session.query(LibraryBookCategory).filter(LibraryBookCategory.book_id == book_id).delete(synchronize_session=False)
    else:
        query = session.query(ShelfCategoryBook).filter(
            ShelfCategoryBook.reader_id == reader_id, ShelfCategoryBook.book_id == book_id
        )
        if category_id is not None:
            query = query.filter(ShelfCategoryBook.category_id == category_id)
        query.delete(synchronize_session=False)
    session.commit()


def delete_empty_category(session, model, category_id, reader_id=None):
    node = session.get(model, category_id)
    if node is None or (model is ShelfCategory and node.reader_id != reader_id):
        raise CategoryError("分类不存在")
    if session.query(model).filter(model.parent_id == node.id).count():
        raise CategoryError("分类包含子分类，不能直接删除")
    link_model = LibraryBookCategory if model is LibraryCategory else ShelfCategoryBook
    if session.query(link_model).filter(link_model.category_id == node.id).count():
        raise CategoryError("分类包含书籍，不能直接删除")
    session.delete(node)
    session.commit()


def merge_categories(session, model, source_id, target_id, reader_id=None):
    if source_id == target_id:
        raise CategoryError("不能合并同一个分类")
    source = session.get(model, source_id)
    target = session.get(model, target_id)
    if (
        not source
        or not target
        or (model is ShelfCategory and (source.reader_id != reader_id or target.reader_id != reader_id))
    ):
        raise CategoryError("分类不存在")
    nodes = _scope_filter(session.query(model), model, reader_id).all()
    if target_id in descendants(nodes, source_id):
        raise CategoryError("不能合并到源分类的后代")

    for child in list(session.query(model).filter(model.parent_id == source.id).all()):
        conflict = find_child(session, model, target.id, child.name, reader_id)
        if conflict:
            merge_categories(session, model, child.id, conflict.id, reader_id)
        else:
            child.parent_id = target.id

    if model is LibraryCategory:
        session.query(LibraryBookCategory).filter(LibraryBookCategory.category_id == source.id).update(
            {LibraryBookCategory.category_id: target.id}, synchronize_session=False
        )
    else:
        links = session.query(ShelfCategoryBook).filter(ShelfCategoryBook.category_id == source.id).all()
        for link in links:
            if session.get(ShelfCategoryBook, (reader_id, target.id, link.book_id)) is None:
                session.add(ShelfCategoryBook(reader_id=reader_id, category_id=target.id, book_id=link.book_id))
            session.delete(link)
    session.delete(source)
    session.commit()


def category_book_ids(session, model, category_id, recursive=True, reader_id=None):
    nodes = _scope_filter(session.query(model), model, reader_id).all()
    category_ids = descendants(nodes, category_id) if recursive else {category_id}
    if model is LibraryCategory:
        rows = session.query(LibraryBookCategory.book_id).filter(LibraryBookCategory.category_id.in_(category_ids)).all()
    else:
        rows = (
            session.query(ShelfCategoryBook.book_id)
            .filter(ShelfCategoryBook.reader_id == reader_id, ShelfCategoryBook.category_id.in_(category_ids))
            .all()
        )
    return list(dict.fromkeys(row[0] for row in rows))
