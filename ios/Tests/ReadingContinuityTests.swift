import XCTest
@testable import TangPoetry

final class ReadingContinuityTests: XCTestCase {
    @MainActor func testScopedReadingUsesCurrentFiltersAndRestoresAfterRelaunch() throws {
        let suite = "TangPoetryContinuityTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let store = PoemStore(defaults: defaults)
        let scope = ReadingScope(category: "五言绝句", author: "王维")
        let expected = store.poems.filter { $0.section == "五言绝句" && $0.author == "王维" }
        XCTAssertGreaterThan(expected.count, 1)
        store.openReadingScope(scope, selecting: expected[0].id)
        XCTAssertEqual(store.readingPoems.map(\.id), expected.map(\.id))
        store.turn(-1)
        XCTAssertEqual(store.selectedID, expected[0].id)
        store.turn(1)
        XCTAssertEqual(store.selectedID, expected[1].id)

        let restored = PoemStore(defaults: defaults)
        XCTAssertEqual(restored.readingScope, scope)
        XCTAssertEqual(restored.selectedID, expected[1].id)
        XCTAssertEqual(restored.readingIndex, 1)
        restored.returnToLibraryScope()
        XCTAssertEqual(restored.readingPoems.count, 320)
        XCTAssertEqual(restored.selectedID, expected[1].id)
    }

    @MainActor func testFavoriteRemovalAdvancesWithinScopeAndEmptyScopeKeepsCurrentPoem() throws {
        let suite = "TangPoetryContinuityTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let store = PoemStore(defaults: defaults)
        let ids = Array(store.poems.prefix(3).map(\.id))
        store.favorites = Set(ids)
        store.openReadingScope(ReadingScope(collection: "favorites"), selecting: ids[1])
        store.toggleFavorite(ids[1])
        XCTAssertEqual(store.selectedID, ids[2])
        XCTAssertEqual(store.readingPoems.map(\.id), [ids[0], ids[2]])
        store.toggleFavorite(ids[2])
        XCTAssertEqual(store.selectedID, ids[0])
        store.toggleFavorite(ids[0])
        XCTAssertTrue(store.readingScope.isAll)
        XCTAssertEqual(store.selectedID, ids[0])
        XCTAssertEqual(store.readingPoems.count, 320)
    }

    @MainActor func testBookmarksAreSavedByPoemIDAndOnlyForTheVisiblePage() throws {
        let suite = "TangPoetryContinuityTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        // An existing installation has only the old poem position key.
        let oldID = "tang-233-ye-si"
        defaults.set(oldID, forKey: "reader.position")
        let store = PoemStore(defaults: defaults)
        XCTAssertEqual(store.selectedID, oldID)
        XCTAssertTrue(store.readingScope.isAll)
        XCTAssertNil(store.readingBookmark(for: oldID, lineCount: 4).lineIndex)

        let neighbor = try XCTUnwrap(store.poems.first { $0.id != oldID })
        store.recordReadingBookmark(ReadingBookmark(lineIndex: 2), for: neighbor.id, lineCount: 4)
        XCTAssertNil(store.readingBookmark(for: neighbor.id, lineCount: 4).lineIndex)
        store.recordReadingBookmark(ReadingBookmark(lineIndex: 2), for: oldID, lineCount: 4)
        XCTAssertNil(defaults.data(forKey: "reader.bookmarks"), "Scroll measurements must not write defaults on every event")
        store.flushReadingProgress()
        let restored = PoemStore(defaults: defaults)
        XCTAssertEqual(restored.readingBookmark(for: oldID, lineCount: 4).lineIndex, 2)
        XCTAssertNil(restored.readingBookmark(for: neighbor.id, lineCount: 4).lineIndex)
        // A future content correction can shorten the poem safely.
        XCTAssertEqual(restored.readingBookmark(for: oldID, lineCount: 2).lineIndex, 1)
    }

    @MainActor func testOpeningOutsideASelectionReturnsToTheLibraryWithoutLosingProgress() throws {
        let suite = "TangPoetryContinuityTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let store = PoemStore(defaults: defaults)
        let selected = try XCTUnwrap(store.poems.first { $0.author == "王维" })
        let other = try XCTUnwrap(store.poems.first { $0.author != "王维" })
        store.openReadingScope(ReadingScope(author: "王维"), selecting: selected.id)
        store.recordReadingBookmark(ReadingBookmark(lineIndex: 1), for: selected.id, lineCount: 4)
        store.openPoem(other.id, preservingScope: true)
        XCTAssertTrue(store.readingScope.isAll)
        XCTAssertEqual(store.selectedID, other.id)
        let restored = PoemStore(defaults: defaults)
        XCTAssertEqual(restored.readingBookmark(for: selected.id, lineCount: 4).lineIndex, 1)
    }

    func testBookmarkValidationHandlesCorruptOrChangedLineCounts() {
        XCTAssertNil(ReadingBookmark(lineIndex: 2).validated(lineCount: 0).lineIndex)
        XCTAssertEqual(ReadingBookmark(lineIndex: -5).validated(lineCount: 8).lineIndex, 0)
        XCTAssertEqual(ReadingBookmark(lineIndex: 1000).validated(lineCount: 8).lineIndex, 7)
    }
}
