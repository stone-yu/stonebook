import pytest
import tornado.escape
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from webserver.models import (
    Base,
    LibraryBookCategory,
    LibraryCategory,
    Reader,
    ReadingState,
    ShelfCategory,
    ShelfCategoryBook,
)
from webserver.services.categories import (
    CategoryError,
    add_books_to_shelf,
    assign_book,
    assign_library_path,
    build_tree,
    category_book_ids,
    category_path_from_file,
    create_category,
    inherit_library_path,
    merge_categories,
    remove_book_from_shelf_categories,
    remove_books_from_shelf,
    serialize_category,
    update_category,
)


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add(Reader(username="reader", password="test"))
    db.commit()
    yield db
    db.close()


def test_scan_path_maps_only_parent_directories(tmp_path):
    root = tmp_path / "imports"
    book = root / "文学" / "中国文学" / "鲁迅" / "呐喊.epub"
    book.parent.mkdir(parents=True)
    book.touch()

    assert category_path_from_file(root, book) == ["文学", "中国文学", "鲁迅"]


def test_scan_root_book_stays_uncategorized_and_escape_is_rejected(tmp_path):
    root = tmp_path / "imports"
    root.mkdir()
    book = root / "三体.epub"
    book.touch()
    outside = tmp_path / "outside.epub"
    outside.touch()

    assert category_path_from_file(root, book) == []
    with pytest.raises(CategoryError, match="不在导入根目录"):
        category_path_from_file(root, outside)


def test_assign_library_path_is_idempotent_and_keeps_manual_assignment(session):
    leaf = assign_library_path(session, 101, ["文学", "中国文学", "鲁迅"])
    again = assign_library_path(session, 101, ["技术", "数据库"])

    assert again.id == leaf.id
    assert session.query(LibraryCategory).count() == 3
    assert session.get(LibraryBookCategory, 101).category.name == "鲁迅"


def test_parent_category_aggregates_descendant_books(session):
    assign_library_path(session, 101, ["文学", "中国文学", "鲁迅"])
    assign_library_path(session, 102, ["文学", "外国文学"])

    tree = build_tree(session, LibraryCategory)

    assert tree[0]["name"] == "文学"
    assert tree[0]["count"] == 2
    assert tree[0]["direct_count"] == 0
    assert set(category_book_ids(session, LibraryCategory, tree[0]["id"])) == {101, 102}


def test_same_name_is_allowed_under_different_parents(session):
    literature = create_category(session, LibraryCategory, "文学")
    technology = create_category(session, LibraryCategory, "技术")

    create_category(session, LibraryCategory, "历史", literature.id)
    create_category(session, LibraryCategory, "历史", technology.id)

    assert session.query(LibraryCategory).filter(LibraryCategory.name == "历史").count() == 2


def test_category_cannot_move_below_its_descendant(session):
    root = create_category(session, LibraryCategory, "文学")
    child = create_category(session, LibraryCategory, "中国文学", root.id)

    with pytest.raises(CategoryError, match="后代"):
        update_category(session, LibraryCategory, root.id, parent_id=child.id)


def test_category_can_move_back_to_root(session):
    root = create_category(session, LibraryCategory, "文学")
    child = create_category(session, LibraryCategory, "中国文学", root.id)

    update_category(session, LibraryCategory, child.id, parent_id=None)

    assert child.parent_id is None


@pytest.mark.parametrize("model,reader_id", [(LibraryCategory, None), (ShelfCategory, 1)])
def test_created_and_moved_category_response_is_json_serializable(session, model, reader_id):
    parent = create_category(session, model, "父分类", reader_id=reader_id)
    child = create_category(session, model, "子分类", reader_id=reader_id)

    created = serialize_category(child)
    update_category(session, model, child.id, reader_id=reader_id, parent_id=parent.id)
    moved = serialize_category(child)

    assert tornado.escape.json_decode(tornado.escape.json_encode({"category": created}))["category"]["name"] == "子分类"
    assert tornado.escape.json_decode(tornado.escape.json_encode({"category": moved}))["category"]["parent_id"] == parent.id
    assert isinstance(created["create_time"], str)
    assert isinstance(moved["update_time"], str)


def test_merge_moves_books_and_children(session):
    source = create_category(session, LibraryCategory, "旧分类")
    target = create_category(session, LibraryCategory, "新分类")
    child = create_category(session, LibraryCategory, "子分类", source.id)
    assign_book(session, LibraryCategory, source.id, 101)

    merge_categories(session, LibraryCategory, source.id, target.id)

    assert session.get(LibraryBookCategory, 101).category_id == target.id
    assert session.get(LibraryCategory, child.id).parent_id == target.id
    assert session.get(LibraryCategory, source.id) is None


def test_shelf_inherits_global_path_and_allows_multiple_categories(session):
    assign_library_path(session, 101, ["文学", "鲁迅"])
    state = ReadingState(101, 1)
    state.set_wants(True)
    session.add(state)
    session.commit()

    inherited = inherit_library_path(session, 1, 101)
    extra = create_category(session, ShelfCategory, "待读", reader_id=1)
    assign_book(session, ShelfCategory, extra.id, 101, 1)

    links = session.query(ShelfCategoryBook).filter(ShelfCategoryBook.reader_id == 1).all()
    assert inherited.name == "鲁迅"
    assert {link.category_id for link in links} == {inherited.id, extra.id}


def test_category_books_are_added_to_shelf_with_paths_and_idempotency(session):
    assign_library_path(session, 101, ["文学", "中国文学"])
    assign_library_path(session, 102, ["文学", "外国文学"])

    first = add_books_to_shelf(session, 1, [101, 102])
    second = add_books_to_shelf(session, 1, [101, 102])

    states = session.query(ReadingState).filter(ReadingState.reader_id == 1, ReadingState.wants == 1).all()
    links = session.query(ShelfCategoryBook).filter(ShelfCategoryBook.reader_id == 1).all()
    assert first == {"total": 2, "added": 2, "skipped": 0}
    assert second == {"total": 2, "added": 0, "skipped": 2}
    assert {state.book_id for state in states} == {101, 102}
    assert {link.category.name for link in links} == {"中国文学", "外国文学"}


def test_category_bulk_shelf_only_changes_requested_books(session):
    assign_library_path(session, 101, ["文学"])
    assign_library_path(session, 102, ["技术"])

    result = add_books_to_shelf(session, 1, [101])

    assert result["total"] == 1
    assert session.query(ReadingState).filter(ReadingState.reader_id == 1, ReadingState.wants == 1).count() == 1
    assert session.query(ShelfCategoryBook).filter(ShelfCategoryBook.reader_id == 1).one().book_id == 101


def test_removing_book_from_shelf_clears_only_links(session):
    category = create_category(session, ShelfCategory, "待读", reader_id=1)
    state = ReadingState(101, 1)
    state.set_wants(True)
    session.add(state)
    session.commit()
    assign_book(session, ShelfCategory, category.id, 101, 1)

    remove_book_from_shelf_categories(session, 1, 101)

    assert session.query(ShelfCategoryBook).count() == 0
    assert session.get(ShelfCategory, category.id) is not None


def test_remove_books_from_shelf_clears_membership_and_category_links(session):
    assign_library_path(session, 101, ["文学", "中国文学"])
    assign_library_path(session, 102, ["文学", "外国文学"])
    add_books_to_shelf(session, 1, [101, 102])

    result = remove_books_from_shelf(session, 1, [101, 102])

    assert result == {"total": 2, "removed": 2, "skipped": 0}
    assert session.query(ReadingState).filter(ReadingState.reader_id == 1, ReadingState.wants == 1).count() == 0
    assert session.query(ShelfCategoryBook).filter(ShelfCategoryBook.reader_id == 1).count() == 0


def test_remove_books_from_shelf_is_idempotent_for_already_removed_books(session):
    assign_library_path(session, 101, ["文学"])
    add_books_to_shelf(session, 1, [101])

    first = remove_books_from_shelf(session, 1, [101])
    second = remove_books_from_shelf(session, 1, [101])

    assert first == {"total": 1, "removed": 1, "skipped": 0}
    assert second == {"total": 1, "removed": 0, "skipped": 1}


def test_remove_books_from_shelf_preserves_other_books_on_shelf(session):
    assign_library_path(session, 101, ["文学"])
    assign_library_path(session, 102, ["技术"])
    add_books_to_shelf(session, 1, [101, 102])

    result = remove_books_from_shelf(session, 1, [101])

    assert result == {"total": 1, "removed": 1, "skipped": 0}
    assert session.query(ReadingState).filter(ReadingState.book_id == 101, ReadingState.reader_id == 1).one().is_wants() is False
    assert session.query(ReadingState).filter(ReadingState.book_id == 102, ReadingState.reader_id == 1).one().is_wants() is True
    assert {link.book_id for link in session.query(ShelfCategoryBook).filter(ShelfCategoryBook.reader_id == 1).all()} == {102}



def test_category_path_depth_is_limited(tmp_path):
    root = tmp_path / "imports"
    book = root.joinpath(*(f"level-{index}" for index in range(13)), "book.epub")
    book.parent.mkdir(parents=True)
    book.touch()

    with pytest.raises(CategoryError, match="12层"):
        category_path_from_file(root, book)


def test_database_migration_creates_new_category_tables(tmp_path):
    from webserver.migrate_db import compare_and_migrate

    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    Reader.__table__.create(engine)

    assert compare_and_migrate(engine) is True
    tables = set(inspect(engine).get_table_names())
    assert {
        "library_categories",
        "library_book_categories",
        "shelf_categories",
        "shelf_category_books",
        "book_annotations",
    }.issubset(tables)
