import XCTest
@testable import TangPoetry

final class ReaderTests: XCTestCase {
    private func layout(characters: Int, verses: Int, width: CGFloat = 390, height: CGFloat = 760,
                        title: String = "山居秋暝", notesHeight: CGFloat = 96,
                        fontSetting: Int = 22, dynamicScale: CGFloat = 1) -> PoemLayout {
        PoemLayout.resolve(
            section: "乐府", lines: Array(repeating: String(repeating: "山", count: characters) + "。", count: verses),
            title: title, author: "王维", size: CGSize(width: width, height: height),
            fontSetting: fontSetting, dynamicScale: dynamicScale, notesHeight: notesHeight
        )
    }

    func testTypographyUsesVerseLengthAndActualMeter() {
        let fiveQuatrain = layout(characters: 5, verses: 4)
        let sevenQuatrain = layout(characters: 7, verses: 4)
        let fiveRegulated = layout(characters: 5, verses: 8)
        let sevenRegulated = layout(characters: 7, verses: 8)
        let medium = layout(characters: 5, verses: 12)
        let ballad = layout(characters: 7, verses: 120)
        XCTAssertEqual(fiveQuatrain.length, .quatrain)
        XCTAssertEqual(fiveQuatrain.fontSize, 26, accuracy: 0.01)
        XCTAssertEqual(sevenQuatrain.fontSize, 24, accuracy: 0.01)
        XCTAssertEqual(fiveRegulated.fontSize, 22, accuracy: 0.01)
        XCTAssertEqual(sevenRegulated.fontSize, 21, accuracy: 0.01)
        XCTAssertEqual(medium.length, .medium)
        XCTAssertEqual(ballad.length, .long)
        XCTAssertLessThan(fiveRegulated.contentTop, fiveQuatrain.contentTop)
        XCTAssertLessThan(medium.contentTop, fiveRegulated.contentTop)
        XCTAssertLessThan(ballad.contentTop, fiveRegulated.contentTop)
        XCTAssertLessThan(fiveRegulated.lineSpacing, fiveQuatrain.lineSpacing)
        XCTAssertGreaterThan(ballad.estimatedContentHeight, 760)
        XCTAssertGreaterThanOrEqual(ballad.fontSize, 18)
    }

    func testCompactPageAccountsForNotesAndTitleWithoutUnreadableType() {
        let withNotes = layout(characters: 7, verses: 8, width: 320, height: 568, notesHeight: 110)
        let withoutNotes = layout(characters: 7, verses: 8, width: 320, height: 568, notesHeight: 0)
        XCTAssertGreaterThanOrEqual(withNotes.fontSize, 20)
        XCTAssertLessThanOrEqual(withNotes.fontSize, withoutNotes.fontSize)
        XCTAssertLessThanOrEqual(withNotes.contentTop, withoutNotes.contentTop)
        XCTAssertLessThanOrEqual(withNotes.fontSize * (7 * 1.18 + 2), 320 - withNotes.horizontalPadding * 2)
        let shortTitle = layout(characters: 5, verses: 8, width: 320, height: 650, notesHeight: 100)
        let longTitle = layout(characters: 5, verses: 8, width: 320, height: 650,
                               title: String(repeating: "山", count: 30), notesHeight: 100)
        XCTAssertLessThan(longTitle.titleSize, shortTitle.titleSize)
        XCTAssertLessThan(longTitle.contentTop, shortTitle.contentTop)
    }

    func testUserSizeAndDynamicTypeRetainAReadableScaledFloor() {
        let normal = layout(characters: 7, verses: 120, width: 320, height: 568)
        let enlarged = layout(characters: 7, verses: 120, width: 320, height: 568,
                              fontSetting: 30, dynamicScale: 1.6)
        XCTAssertGreaterThan(enlarged.fontSize, normal.fontSize)
        XCTAssertGreaterThanOrEqual(enlarged.fontSize + 0.001, 18 * 30 / 22 * 1.6)
        XCTAssertGreaterThan(enlarged.estimatedContentHeight, normal.estimatedContentHeight)
    }

    func testBundledLibraryHasCompleteIllustratedContent() throws {
        let catalog: PoemCatalog = try BundledContent.decode("catalog.json")
        XCTAssertEqual(catalog.poems.count, 317)
        XCTAssertEqual(catalog.poems.filter(\.featured).count, 20)
        XCTAssertEqual(catalog.poems.filter(\.dedicatedArt).count, 317)
        XCTAssertEqual(Set(catalog.poems.map(\.image)).count, 317)
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
        // Existing installations may have saved pronunciation as enabled.
        store.settings.pinyin = true
        store.selectedID = "tang-233-ye-si"
        let restored = PoemStore(defaults: defaults)
        XCTAssertEqual(restored.selectedID, "tang-233-ye-si")
        XCTAssertEqual(restored.settings.fontSize, 30)
        XCTAssertFalse(restored.settings.pinyin)
        XCTAssertTrue(restored.favorites.contains("tang-095-za-shi"))
    }
}
