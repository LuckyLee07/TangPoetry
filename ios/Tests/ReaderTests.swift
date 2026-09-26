import XCTest
@testable import TangPoetry

final class ReaderTests: XCTestCase {
    func testBundledLibraryHasCompleteFeaturedContent() throws {
        let catalog: PoemCatalog = try BundledContent.decode("catalog.json")
        XCTAssertEqual(catalog.poems.count, 317)
        XCTAssertEqual(catalog.poems.filter(\.featured).count, 20)
        XCTAssertEqual(Set(catalog.poems.map(\.id)).count, 317)
        for poem in catalog.poems {
            let detail: PoemDetail = try BundledContent.decode("poems/\(poem.id).json")
            XCTAssertEqual(detail.id, poem.id)
            XCTAssertFalse(detail.text.isEmpty)
            XCTAssertNoThrow(try BundledContent.url(poem.image))
            XCTAssertNoThrow(try BundledContent.url(poem.thumbnail))
            if poem.featured { XCTAssertFalse(detail.note.isEmpty) }
        }
    }

    func testAliasesAndVerseSearch() throws {
        let catalog: PoemCatalog = try BundledContent.decode("catalog.json")
        let poem = try XCTUnwrap(catalog.poems.first { $0.id == "tang-233-ye-si" })
        for query in ["静夜思", "夜思", "床前明月光疑是地上霜", "舉頭望明月"] {
            XCTAssertTrue(PoemFilter.matches(poem, query: query, category: "all", collection: "all", favorites: []))
        }
        XCTAssertFalse(PoemFilter.matches(poem, query: "", category: "送别", collection: "all", favorites: []))
        XCTAssertFalse(PoemFilter.matches(poem, query: "", category: "all", collection: "favorites", favorites: []))
    }

    @MainActor func testIndependentFavoritesAndPersistedSettings() throws {
        let suite = "TangPoetryTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let store = PoemStore(defaults: defaults)
        store.toggleFavorite("tang-095-za-shi")
        XCTAssertFalse(store.favorites.contains("tang-228-za-shi"))
        store.settings.fontSize = 30
        store.settings.pinyin = false
        store.selectedID = "tang-233-ye-si"
        let restored = PoemStore(defaults: defaults)
        XCTAssertEqual(restored.selectedID, "tang-233-ye-si")
        XCTAssertEqual(restored.settings.fontSize, 30)
        XCTAssertFalse(restored.settings.pinyin)
        XCTAssertTrue(restored.favorites.contains("tang-095-za-shi"))
    }
}
