#!/usr/bin/env python3

import tornado.escape

from webserver import utils
from webserver.handlers.base import BaseHandler, auth, is_admin, js
from webserver.models import LibraryBookCategory, LibraryCategory, ShelfCategory, ShelfCategoryBook
from webserver.services.categories import (
    CategoryError,
    add_books_to_shelf,
    assign_book,
    build_tree,
    category_book_ids,
    create_category,
    delete_empty_category,
    merge_categories,
    serialize_category,
    unassign_book,
    update_category,
)


def request_json(handler):
    return tornado.escape.json_decode(handler.request.body or b"{}")


def error_response(error):
    return {"err": "category.invalid", "msg": str(error)}


def formatted_books(handler, book_ids):
    books = {book["id"]: book for book in handler.get_books(ids=book_ids)}
    result = [utils.BookFormatter(handler, books[book_id]).format() for book_id in book_ids if book_id in books]
    return handler.attach_reading_states(result)


class LibraryCategoryTree(BaseHandler):
    @js
    def get(self):
        visible_ids = {book["id"] for book in self.get_books()}
        links = (
            self.session.query(LibraryBookCategory).filter(LibraryBookCategory.book_id.in_(visible_ids)).all()
            if visible_ids
            else []
        )
        assignments = {link.book_id: link.category_id for link in links}
        return {
            "err": "ok",
            "tree": build_tree(self.session, LibraryCategory, visible_book_ids=visible_ids),
            "uncategorized_count": len(visible_ids - set(assignments)),
            "book_categories": assignments,
        }


class LibraryCategoryBooks(BaseHandler):
    @js
    def get(self, category_id):
        recursive = self.get_argument("recursive", "true").lower() != "false"
        if category_id == "0":
            assigned = {row[0] for row in self.session.query(LibraryBookCategory.book_id).all()}
            ids = [book["id"] for book in self.get_books() if book["id"] not in assigned]
        else:
            category = self.session.get(LibraryCategory, int(category_id))
            if category is None:
                return {"err": "category.not_found", "msg": "分类不存在"}
            ids = category_book_ids(self.session, LibraryCategory, category.id, recursive)
        books = formatted_books(self, ids)
        return {"err": "ok", "total": len(books), "books": books}


class LibraryCategoryShelf(BaseHandler):
    @js
    @auth
    def post(self, category_id):
        category = self.session.get(LibraryCategory, int(category_id))
        if category is None:
            return {"err": "category.not_found", "msg": "分类不存在"}
        data = request_json(self)
        recursive = data.get("recursive", True) is not False
        category_ids = category_book_ids(self.session, LibraryCategory, category.id, recursive)
        visible_ids = {book["id"] for book in self.get_books(ids=category_ids)} if category_ids else set()
        result = add_books_to_shelf(self.session, self.user_id(), [bid for bid in category_ids if bid in visible_ids])
        return {"err": "ok", **result}


class LibraryCategoryAdmin(BaseHandler):
    @js
    @is_admin
    def post(self):
        data = request_json(self)
        action = data.get("action")
        try:
            if action == "create":
                node = create_category(self.session, LibraryCategory, data.get("name"), data.get("parent_id"))
                return {"err": "ok", "category": serialize_category(node)}
            if action == "update":
                changes = {}
                if "name" in data:
                    changes["name"] = data["name"]
                if "parent_id" in data:
                    changes["parent_id"] = data["parent_id"]
                node = update_category(self.session, LibraryCategory, int(data["category_id"]), **changes)
                return {"err": "ok", "category": serialize_category(node)}
            if action == "merge":
                merge_categories(self.session, LibraryCategory, int(data["source_id"]), int(data["target_id"]))
                return {"err": "ok"}
            if action == "delete":
                delete_empty_category(self.session, LibraryCategory, int(data["category_id"]))
                return {"err": "ok"}
            if action == "assign":
                assign_book(self.session, LibraryCategory, int(data["category_id"]), int(data["book_id"]))
                return {"err": "ok"}
            if action == "unassign":
                unassign_book(self.session, LibraryCategory, int(data["book_id"]))
                return {"err": "ok"}
            return {"err": "params.error", "msg": "不支持的分类操作"}
        except (CategoryError, KeyError, TypeError, ValueError) as error:
            self.session.rollback()
            return error_response(error)


class ShelfCategoryTree(BaseHandler):
    @js
    @auth
    def get(self):
        return {"err": "ok", "tree": build_tree(self.session, ShelfCategory, self.user_id())}

    @js
    @auth
    def post(self):
        data = request_json(self)
        action = data.get("action")
        reader_id = self.user_id()
        try:
            if action == "create":
                node = create_category(self.session, ShelfCategory, data.get("name"), data.get("parent_id"), reader_id)
                return {"err": "ok", "category": serialize_category(node)}
            if action == "update":
                changes = {}
                if "name" in data:
                    changes["name"] = data["name"]
                if "parent_id" in data:
                    changes["parent_id"] = data["parent_id"]
                node = update_category(self.session, ShelfCategory, int(data["category_id"]), reader_id=reader_id, **changes)
                return {"err": "ok", "category": serialize_category(node)}
            if action == "merge":
                merge_categories(
                    self.session,
                    ShelfCategory,
                    int(data["source_id"]),
                    int(data["target_id"]),
                    reader_id,
                )
                return {"err": "ok"}
            if action == "delete":
                delete_empty_category(self.session, ShelfCategory, int(data["category_id"]), reader_id)
                return {"err": "ok"}
            if action == "assign":
                assign_book(self.session, ShelfCategory, int(data["category_id"]), int(data["book_id"]), reader_id)
                return {"err": "ok"}
            if action == "unassign":
                unassign_book(
                    self.session,
                    ShelfCategory,
                    int(data["book_id"]),
                    data.get("category_id"),
                    reader_id,
                )
                return {"err": "ok"}
            return {"err": "params.error", "msg": "不支持的分类操作"}
        except (CategoryError, KeyError, TypeError, ValueError) as error:
            self.session.rollback()
            return error_response(error)


class ShelfCategoryBooks(BaseHandler):
    @js
    @auth
    def get(self, category_id):
        reader_id = self.user_id()
        recursive = self.get_argument("recursive", "true").lower() != "false"
        category = self.session.get(ShelfCategory, int(category_id))
        if category is None or category.reader_id != reader_id:
            return {"err": "category.not_found", "msg": "分类不存在"}
        ids = category_book_ids(self.session, ShelfCategory, category.id, recursive, reader_id)
        books = formatted_books(self, ids)
        links = (
            self.session.query(ShelfCategoryBook)
            .filter(ShelfCategoryBook.reader_id == reader_id, ShelfCategoryBook.book_id.in_(ids))
            .all()
            if ids
            else []
        )
        category_map = {}
        for link in links:
            category_map.setdefault(link.book_id, []).append(link.category_id)
        for book in books:
            book["shelf_category_ids"] = category_map.get(book["id"], [])
        return {"err": "ok", "total": len(books), "books": books}


def routes():
    return [
        (r"/api/categories", LibraryCategoryTree),
        (r"/api/categories/([0-9]+)/books", LibraryCategoryBooks),
        (r"/api/categories/([0-9]+)/shelf", LibraryCategoryShelf),
        (r"/api/admin/categories", LibraryCategoryAdmin),
        (r"/api/shelf/categories", ShelfCategoryTree),
        (r"/api/shelf/categories/([0-9]+)/books", ShelfCategoryBooks),
    ]
