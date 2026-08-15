#!/usr/bin/env python3

import tornado.escape

from webserver.handlers.base import BaseHandler, auth, js
from webserver.models import BookAnnotation
from webserver.services.annotations import (
    AnnotationError,
    delete_annotation,
    serialize_annotation,
    shelf_annotation_query,
    update_annotation,
    upsert_annotation,
)


def body_json(handler):
    return tornado.escape.json_decode(handler.request.body or b"{}")


class BookAnnotations(BaseHandler):
    @js
    @auth
    def get(self, book_id):
        book_id = int(book_id)
        if not self.get_book(book_id, raise_exception=False):
            return {"err": "book.not_found", "msg": "书籍不存在"}
        rows = (
            self.session.query(BookAnnotation)
            .filter_by(reader_id=self.user_id(), book_id=book_id)
            .order_by(BookAnnotation.create_time.asc())
            .all()
        )
        return {"err": "ok", "annotations": [serialize_annotation(row) for row in rows]}

    @js
    @auth
    def post(self, book_id):
        book_id = int(book_id)
        book = self.get_book(book_id, raise_exception=False)
        if not book or not self.can_view_book(book_id):
            return {"err": "book.not_found", "msg": "书籍不存在"}
        try:
            row = upsert_annotation(self.session, self.user_id(), book_id, body_json(self), book)
            return {"err": "ok", "annotation": serialize_annotation(row)}
        except (AnnotationError, TypeError, ValueError) as error:
            self.session.rollback()
            return {"err": "annotation.invalid", "msg": str(error)}


class BookAnnotationItem(BaseHandler):
    @js
    @auth
    def put(self, book_id, annotation_id):
        row = self.session.get(BookAnnotation, int(annotation_id))
        if row is None or row.book_id != int(book_id):
            return {"err": "annotation.not_found", "msg": "批注不存在"}
        try:
            row = update_annotation(self.session, self.user_id(), row.id, body_json(self))
            return {"err": "ok", "annotation": serialize_annotation(row)}
        except (AnnotationError, TypeError, ValueError) as error:
            self.session.rollback()
            return {"err": "annotation.invalid", "msg": str(error)}

    @js
    @auth
    def delete(self, book_id, annotation_id):
        row = self.session.get(BookAnnotation, int(annotation_id))
        if row is None or row.book_id != int(book_id):
            return {"err": "annotation.not_found", "msg": "批注不存在"}
        try:
            delete_annotation(self.session, self.user_id(), row.id)
            return {"err": "ok"}
        except AnnotationError as error:
            self.session.rollback()
            return {"err": "annotation.invalid", "msg": str(error)}


class ShelfAnnotations(BaseHandler):
    @js
    @auth
    def get(self):
        category_arg = self.get_argument("category_id", None)
        category_id = int(category_arg) if category_arg not in (None, "") else None
        recursive = self.get_argument("recursive", "true").lower() != "false"
        detached = self.get_argument("detached", "false").lower() == "true"
        deleted = self.get_argument("deleted", "false").lower() == "true"
        query = shelf_annotation_query(self.session, self.user_id(), category_id, recursive, detached, deleted)
        kind = self.get_argument("kind", "")
        keyword = self.get_argument("q", "").strip()
        if kind:
            query = query.filter(BookAnnotation.kind == kind)
        if keyword:
            pattern = f"%{keyword}%"
            query = query.filter(
                BookAnnotation.content.like(pattern)
                | BookAnnotation.quote.like(pattern)
                | BookAnnotation.book_title.like(pattern)
            )
        total = query.count()
        page = max(1, int(self.get_argument("page", 1)))
        size = min(100, max(1, int(self.get_argument("size", 30))))
        rows = query.order_by(BookAnnotation.update_time.desc()).limit(size).offset((page - 1) * size).all()
        return {"err": "ok", "total": total, "annotations": [serialize_annotation(row) for row in rows]}


def routes():
    return [
        (r"/api/book/([0-9]+)/annotations", BookAnnotations),
        (r"/api/book/([0-9]+)/annotations/([0-9]+)", BookAnnotationItem),
        (r"/api/shelf/annotations", ShelfAnnotations),
    ]
