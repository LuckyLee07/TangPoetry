import XCTest
@testable import TangPoetry

final class ReaderTests: XCTestCase {
    private func layout(characters: Int, verses: Int, width: CGFloat = 390, height: CGFloat = 760,
                        title: String = "山居秋暝",
                        fontSetting: Int = 22, dynamicScale: CGFloat = 1,
                        textStart: CGFloat? = nil, showsNote: Bool = true) -> PoemLayout {
        PoemLayout.resolve(
            section: "乐府", lines: Array(repeating: String(repeating: "山", count: characters) + "。", count: verses),
            title: title, author: "王维", size: CGSize(width: width, height: height),
            fontSetting: fontSetting, dynamicScale: dynamicScale, textStart: textStart, showsNote: showsNote
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
        XCTAssertEqual(fiveQuatrain.contentTop, 760 * 0.45 - 70, accuracy: 0.01)
        XCTAssertEqual(fiveRegulated.contentTop, 760 * 0.39 - 70, accuracy: 0.01)
        XCTAssertEqual(medium.contentTop, fiveRegulated.contentTop, accuracy: 0.01)
        XCTAssertEqual(ballad.contentTop, fiveRegulated.contentTop, accuracy: 0.01)
        // Relative to the type-fitting baseline, the poem is 45pt higher and the note 25pt lower.
        XCTAssertEqual(fiveQuatrain.contentTop + fiveQuatrain.noteTopPadding,
                       760 * 0.45 - 25 + 12 + 25, accuracy: 0.01)
        XCTAssertLessThan(fiveRegulated.lineSpacing, fiveQuatrain.lineSpacing)
        XCTAssertGreaterThan(ballad.estimatedContentHeight, 760)
        XCTAssertGreaterThanOrEqual(ballad.fontSize, 18)
    }

    func testCompactPagesScrollWithinWhitespaceInsteadOfMovingOverArtwork() {
        let quatrain = layout(characters: 7, verses: 4, width: 320, height: 568)
        let regulated = layout(characters: 7, verses: 8, width: 320, height: 500)
        XCTAssertEqual(quatrain.contentTop, 568 * 0.45 - 70, accuracy: 0.01)
        XCTAssertEqual(regulated.contentTop, 500 * 0.39 - 70, accuracy: 0.01)
        XCTAssertGreaterThanOrEqual(regulated.fontSize, 20)
        XCTAssertGreaterThan(regulated.estimatedContentHeight, 500 - regulated.contentTop - 65)
        XCTAssertLessThanOrEqual(regulated.fontSize * (7 * 1.18 + 2), 320 - regulated.horizontalPadding * 2)
        let shortTitle = layout(characters: 5, verses: 8, width: 320, height: 650)
        let longTitle = layout(characters: 5, verses: 8, width: 320, height: 650,
                               title: String(repeating: "山", count: 30))
        XCTAssertLessThan(longTitle.titleSize, shortTitle.titleSize)
        XCTAssertEqual(longTitle.contentTop, shortTitle.contentTop, accuracy: 0.01)
        XCTAssertGreaterThan(longTitle.estimatedContentHeight, shortTitle.estimatedContentHeight)
        let limitedHeight = layout(characters: 5, verses: 4, width: 320, height: 200)
        XCTAssertEqual(limitedHeight.contentTop, 100, accuracy: 0.01)
        XCTAssertEqual(limitedHeight.noteTopPadding, 37, accuracy: 0.01)
    }

    func testUserSizeAndDynamicTypeRetainAReadableScaledFloor() {
        let normal = layout(characters: 7, verses: 120, width: 320, height: 568)
        let enlarged = layout(characters: 7, verses: 120, width: 320, height: 568,
                              fontSetting: 30, dynamicScale: 1.6)
        XCTAssertGreaterThan(enlarged.fontSize, normal.fontSize)
        XCTAssertGreaterThanOrEqual(enlarged.fontSize + 0.001, 18 * 30 / 22 * 1.6)
        XCTAssertGreaterThan(enlarged.estimatedContentHeight, normal.estimatedContentHeight)
        XCTAssertEqual(enlarged.contentTop, normal.contentTop, accuracy: 0.01)
    }

    func testPoemsWithoutVisibleNotesUseAvailableWhitespace() {
        let annotated = layout(characters: 7, verses: 4)
        let unannotated = layout(characters: 7, verses: 4, showsNote: false)
        XCTAssertEqual(unannotated.contentTop - annotated.contentTop, 60, accuracy: 0.01)
        XCTAssertEqual(unannotated.fontSize, annotated.fontSize)
        XCTAssertEqual(unannotated.lineSpacing, annotated.lineSpacing)
        XCTAssertEqual(unannotated.estimatedContentHeight, annotated.estimatedContentHeight)
        XCTAssertLessThanOrEqual(unannotated.contentTop + unannotated.estimatedContentHeight, 760 - 65)

        let compact = layout(characters: 7, verses: 8, width: 320, height: 500)
        let compactWithoutNotes = layout(characters: 7, verses: 8, width: 320, height: 500, showsNote: false)
        XCTAssertEqual(compactWithoutNotes.contentTop, compact.contentTop)
        let long = layout(characters: 7, verses: 120)
        let longWithoutNotes = layout(characters: 7, verses: 120, showsNote: false)
        XCTAssertEqual(longWithoutNotes.contentTop, long.contentTop)
        XCTAssertEqual(longWithoutNotes.fontSize, long.fontSize)
    }

    func testArtworkSpecificTextStartCanMoveDownButNeverBackIntoThePainting() {
        let lower = layout(characters: 5, verses: 4, textStart: 0.52)
        let aboveReadingArea = layout(characters: 5, verses: 4, textStart: 0.20)
        let belowPage = layout(characters: 5, verses: 4, textStart: 1)
        XCTAssertEqual(lower.contentTop, 760 * 0.52 - 70, accuracy: 0.01)
        XCTAssertEqual(aboveReadingArea.contentTop, 760 * 0.45 - 70, accuracy: 0.01)
        XCTAssertEqual(belowPage.contentTop, 760 * 0.7 - 70, accuracy: 0.01)
        XCTAssertGreaterThanOrEqual(belowPage.fontSize, 22)
    }

    func testBundledArtworkRefreshesUseFullPageIllustrations() throws {
        let catalog: PoemCatalog = try BundledContent.decode("catalog.json")
        XCTAssertTrue(catalog.poems.allSatisfy { $0.artworkMode == nil && $0.artworkFocusY == nil })
        let refreshedIDs = ["tang-002-gan-yu-qi-er", "tang-003-gan-yu-qi-san", "tang-004-gan-yu-qi-si",
                            "tang-224-lu-chai", "tang-232-chun-xiao", "tang-244-jiang-xue", "tang-312-wei-cheng-qu"]
        for id in refreshedIDs {
            let poem = try XCTUnwrap(catalog.poems.first { $0.id == id })
            XCTAssertEqual(poem.image, "Art/\(id)-v2-page.jpg")
            XCTAssertEqual(poem.thumbnail, "Art/\(id)-v2-thumb.jpg")
            XCTAssertTrue(poem.dedicatedArt)
        }
        let quietNight = try XCTUnwrap(catalog.poems.first { $0.id == "tang-233-ye-si" })
        XCTAssertNil(quietNight.artworkMode)
        XCTAssertEqual(try XCTUnwrap(quietNight.textStart), 0.52, accuracy: 0.001)
        let mountainAutumn = try XCTUnwrap(catalog.poems.first { $0.id == "tang-116-shan-ju-qiu-ming" })
        XCTAssertNil(mountainAutumn.artworkMode)
        XCTAssertNil(mountainAutumn.textStart)
    }

    func testBundledLibraryReadsInGenreVolumesWithOriginalOrderWithinEachVolume() throws {
        let catalog: PoemCatalog = try BundledContent.decode("catalog.json")
        let expected = ["五言绝句", "七言绝句", "五言律诗", "七言律诗", "五言古诗", "七言古诗", "乐府"]
        var seen = Set<String>()
        let sections = catalog.poems.map(\.section).filter { seen.insert($0).inserted }
        XCTAssertEqual(sections, expected)
        let rank = Dictionary(uniqueKeysWithValues: expected.enumerated().map { ($0.element, $0.offset) })
        let sorted = catalog.poems.sorted { first, second in
            if first.section == second.section { return first.order < second.order }
            return rank[first.section, default: Int.max] < rank[second.section, default: Int.max]
        }
        XCTAssertEqual(catalog.poems.map(\.id), sorted.map(\.id))
    }

    func testBundledLibraryHasCompleteIllustratedContent() throws {
        let catalog: PoemCatalog = try BundledContent.decode("catalog.json")
        XCTAssertEqual(catalog.poems.count, 317)
        XCTAssertEqual(catalog.poems.filter(\.featured).count, 20)
        XCTAssertEqual(catalog.poems.filter(\.dedicatedArt).count, 317)
        XCTAssertEqual(Set(catalog.poems.map(\.image)).count, 317)
        XCTAssertEqual(Set(catalog.poems.map(\.id)).count, 317)
        XCTAssertNoThrow(try BundledContent.url("Art/song-yuan-er-page.jpg"))
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
        let resumed = restored.poems[restored.currentIndex]
        XCTAssertEqual(resumed.id, "tang-233-ye-si")
        XCTAssertEqual(resumed.section, "五言绝句")
        XCTAssertNotEqual(restored.currentIndex, resumed.order - 1)
        XCTAssertEqual(restored.settings.fontSize, 30)
        XCTAssertFalse(restored.settings.pinyin)
        XCTAssertTrue(restored.favorites.contains("tang-095-za-shi"))
    }
}
