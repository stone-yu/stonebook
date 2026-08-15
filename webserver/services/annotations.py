#!/usr/bin/env python3

import datetime
import json
import re

from webserver.models import BookAnnotation, ReadingState, ShelfCategory, ShelfCategoryBook
from webserver.services.categories import descendants


KINDS = {"highlight", "note"}
FORMATS = {"epub", "pdf", "txt"}
COLORS = {"#f6c85f", "#ef8a62", "#8ecae6", "#a7c957", "#cdb4db"}
CLIENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9:_-]{1,64}$")


class AnnotationError(ValueError):
    pass


def _text(value, limit, field):
    value = str(value or "").strip()
    if len(value) > limit:
        raise AnnotationError(f"{field}长度不能超过{limit}")
    return value


def validate_payload(data):
    client_id = _text(data.get("client_id"), 64, "client_id")
    kind = str(data.get("kind", ""))
    fmt = str(data.get("format", "")).lower()
    locator = data.get("locator") or {}
    if not CLIENT_ID_PATTERN.fullmatch(client_id):
        raise AnnotationError("client_id格式无效")
    if kind not in KINDS or fmt not in FORMATS:
        raise AnnotationError("批注类型或书籍格式无效")
    if not isinstance(locator, dict) or len(json.dumps(locator, ensure_ascii=False)) > 4096:
        raise AnnotationError("定位信息无效或过长")
    color = str(data.get("color") or "#f6c85f").lower()
    if color not in COLORS:
        raise AnnotationError("高亮颜色无效")
    quote = _text(data.get("quote"), 10000, "原文")
    content = _text(data.get("content"), 20000, "笔记")
    if kind == "highlight" and not quote:
        raise AnnotationError("高亮必须包含原文")
    if kind == "note" and not (quote or content):
        raise AnnotationError("笔记内容不能为空")
    return {
        "client_id": client_id,
        "kind": kind,
        "format": fmt,
        "locator": locator,
        "color": color,
        "quote": quote,
        "content": content,
        "prefix": _text(data.get("prefix"), 500, "前文"),
        "suffix": _text(data.get("suffix"), 500, "后文"),
        "chapter": _text(data.get("chapter"), 255, "章节"),
    }


def ensure_on_shelf(session, reader_id, book_id):
    state = session.query(ReadingState).filter_by(reader_id=reader_id, book_id=book_id).first()
    if state is None:
        state = ReadingState(book_id, reader_id)
        session.add(state)
    state.set_wants(True)


def upsert_annotation(session, reader_id, book_id, data, snapshot):
    values = validate_payload(data)
    ensure_on_shelf(session, reader_id, book_id)
    row = session.query(BookAnnotation).filter_by(reader_id=reader_id, book_id=book_id, client_id=values["client_id"]).first()
    if row is None:
        row = BookAnnotation(reader_id=reader_id, book_id=book_id)
        session.add(row)
    for key, value in values.items():
        setattr(row, key, value)
    row.book_title = _text(snapshot.get("title"), 500, "书名")
    row.book_authors = _text(", ".join(snapshot.get("authors") or []), 500, "作者")
    row.book_format = values["format"]
    row.book_deleted = False
    row.update_time = datetime.datetime.now()
    session.commit()
    return row


def update_annotation(session, reader_id, annotation_id, data):
    row = session.get(BookAnnotation, annotation_id)
    if row is None or row.reader_id != reader_id:
        raise AnnotationError("批注不存在")
    merged = serialize_annotation(row)
    merged.update(data)
    for key, value in validate_payload(merged).items():
        setattr(row, key, value)
    row.update_time = datetime.datetime.now()
    session.commit()
    return row


def delete_annotation(session, reader_id, annotation_id):
    row = session.get(BookAnnotation, annotation_id)
    if row is None or row.reader_id != reader_id:
        raise AnnotationError("批注不存在")
    session.delete(row)
    session.commit()


def mark_book_deleted(session, book_id, snapshot=None):
    snapshot = snapshot or {}
    rows = session.query(BookAnnotation).filter_by(book_id=book_id).all()
    for row in rows:
        row.book_deleted = True
        row.book_title = row.book_title or str(snapshot.get("title") or "")[:500]
        row.book_authors = row.book_authors or ", ".join(snapshot.get("authors") or [])[:500]
        row.update_time = datetime.datetime.now()
    session.commit()
    return len(rows)


def shelf_annotation_query(session, reader_id, category_id=None, recursive=True, detached=False, deleted=False):
    query = session.query(BookAnnotation).filter_by(reader_id=reader_id)
    if deleted:
        return query.filter(BookAnnotation.book_deleted.is_(True))
    if detached:
        shelf_ids = session.query(ReadingState.book_id).filter_by(reader_id=reader_id, wants=1)
        return query.filter(~BookAnnotation.book_id.in_(shelf_ids), BookAnnotation.book_deleted.is_(False))
    if category_id is None:
        book_ids = session.query(ReadingState.book_id).filter_by(reader_id=reader_id, wants=1)
        query = query.filter(BookAnnotation.book_id.in_(book_ids))
    else:
        if category_id == 0:
            categorized_ids = session.query(ShelfCategoryBook.book_id).filter_by(reader_id=reader_id)
            book_ids = session.query(ReadingState.book_id).filter(
                ReadingState.reader_id == reader_id,
                ReadingState.wants == 1,
                ~ReadingState.book_id.in_(categorized_ids),
            )
        else:
            nodes = session.query(ShelfCategory).filter_by(reader_id=reader_id).all()
            category_ids = descendants(nodes, category_id) if recursive else {category_id}
            book_ids = session.query(ShelfCategoryBook.book_id).filter(
                ShelfCategoryBook.reader_id == reader_id, ShelfCategoryBook.category_id.in_(category_ids)
            )
        query = query.filter(BookAnnotation.book_id.in_(book_ids))
    return query.filter(BookAnnotation.book_deleted.is_(False))


def serialize_annotation(row):
    if row.format == "txt":
        target_url = f"/book/{row.book_id}/readtxt?annotation={row.id}"
    else:
        target_url = f"/read/{row.book_id}?annotation={row.id}"
    return {
        "id": row.id,
        "book_id": row.book_id,
        "client_id": row.client_id,
        "kind": row.kind,
        "content": row.content,
        "quote": row.quote,
        "prefix": row.prefix,
        "suffix": row.suffix,
        "color": row.color,
        "chapter": row.chapter,
        "format": row.format,
        "locator": dict(row.locator or {}),
        "book_title": row.book_title,
        "book_authors": row.book_authors,
        "book_deleted": row.book_deleted,
        "target_url": None if row.book_deleted else target_url,
        "create_time": row.create_time.isoformat() if row.create_time else None,
        "update_time": row.update_time.isoformat() if row.update_time else None,
    }
