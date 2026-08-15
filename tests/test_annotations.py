import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from webserver.models import Base, BookAnnotation, Reader, ReadingState, ShelfCategory, ShelfCategoryBook
from webserver.services.annotations import (
    AnnotationError,
    delete_annotation,
    mark_book_deleted,
    shelf_annotation_query,
    update_annotation,
    upsert_annotation,
)


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add_all([Reader(username="one", password="test"), Reader(username="two", password="test")])
    db.commit()
    yield db
    db.close()


def payload(client_id="ann-1", **changes):
    data = {
        "client_id": client_id,
        "kind": "highlight",
        "format": "epub",
        "quote": "人是为活着本身而活着的",
        "content": "",
        "color": "#f6c85f",
        "chapter": "第一章",
        "prefix": "福贵说",
        "suffix": "。",
        "locator": {"cfi": "epubcfi(/6/4)"},
    }
    data.update(changes)
    return data


def test_upsert_is_idempotent_and_automatically_adds_book_to_shelf(session):
    first = upsert_annotation(session, 1, 101, payload(), {"title": "活着", "authors": ["余华"]})
    second = upsert_annotation(session, 1, 101, payload(content="反复读"), {"title": "活着", "authors": ["余华"]})

    assert first.id == second.id
    assert session.query(BookAnnotation).count() == 1
    assert session.get(ReadingState, (101, 1)).wants == 1
    assert second.content == "反复读"


def test_annotations_are_private_and_owner_checked(session):
    row = upsert_annotation(session, 1, 101, payload(), {"title": "活着", "authors": ["余华"]})

    with pytest.raises(AnnotationError, match="不存在"):
        update_annotation(session, 2, row.id, {"content": "越权"})
    with pytest.raises(AnnotationError, match="不存在"):
        delete_annotation(session, 2, row.id)


def test_invalid_highlight_and_oversized_locator_are_rejected(session):
    with pytest.raises(AnnotationError, match="必须包含原文"):
        upsert_annotation(session, 1, 101, payload(quote=""), {"title": "活着"})
    with pytest.raises(AnnotationError, match="定位信息"):
        upsert_annotation(session, 1, 101, payload(locator={"data": "x" * 5000}), {"title": "活着"})


def test_category_query_follows_current_shelf_categories(session):
    row = upsert_annotation(session, 1, 101, payload(), {"title": "活着", "authors": ["余华"]})
    root = ShelfCategory(reader_id=1, name="文学")
    child = ShelfCategory(reader_id=1, name="中国文学", parent=root)
    session.add_all([root, child])
    session.flush()
    link = ShelfCategoryBook(reader_id=1, category_id=child.id, book_id=101)
    session.add(link)
    session.commit()

    assert shelf_annotation_query(session, 1, root.id, recursive=True).one().id == row.id
    assert shelf_annotation_query(session, 1, root.id, recursive=False).count() == 0

    link.category_id = root.id
    session.commit()
    assert shelf_annotation_query(session, 1, root.id, recursive=False).one().id == row.id


def test_removed_shelf_book_is_detached_but_annotation_survives(session):
    row = upsert_annotation(session, 1, 101, payload(), {"title": "活着"})
    session.get(ReadingState, (101, 1)).set_wants(False)
    session.commit()

    assert shelf_annotation_query(session, 1, detached=True).one().id == row.id
    assert shelf_annotation_query(session, 1).count() == 0


def test_deleted_book_keeps_annotation_snapshot(session):
    row = upsert_annotation(session, 1, 101, payload(), {"title": "活着", "authors": ["余华"]})

    assert mark_book_deleted(session, 101, {"title": "新标题"}) == 1
    assert row.book_deleted is True
    assert row.book_title == "活着"


def test_uncategorized_and_deleted_filters(session):
    upsert_annotation(session, 1, 101, payload("uncategorized"), {"title": "未分类", "authors": []})
    upsert_annotation(session, 1, 102, payload("categorized"), {"title": "已分类", "authors": []})
    category = ShelfCategory(reader_id=1, name="技术")
    session.add(category)
    session.flush()
    session.add(ShelfCategoryBook(reader_id=1, category_id=category.id, book_id=102))
    session.commit()

    rows = shelf_annotation_query(session, 1, category_id=0).all()
    assert [row.book_id for row in rows] == [101]

    mark_book_deleted(session, 101, {"title": "未分类"})
    assert shelf_annotation_query(session, 1, deleted=True).one().book_id == 101
    assert shelf_annotation_query(session, 1, category_id=0).count() == 0
