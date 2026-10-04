import XCTest
import CoreText
@testable import TangPoetry

final class VolumeSelectionTests: XCTestCase {
    private func catalog(_ prefix: String) throws -> PoemCatalog {
        let poems = (1...2).map { index -> [String: Any] in
            ["id": "\(prefix)-\(index)", "order": index, "title": "诗\(index)", "aliases": [],
             "author": "作者", "section": "五言绝句", "theme": "山水", "featured": index == 1,
             "dedicatedArt": true, "image": "Art/\(prefix)-\(index).jpg", "thumbnail": "Art/\(prefix)-\(index)-thumb.jpg", "searchText": "诗 作者"]
        }
        return try JSONDecoder().decode(PoemCatalog.self, from: JSONSerialization.data(withJSONObject:
            ["schemaVersion": 1, "poems": poems, "coverPoemID": "\(prefix)-1", "subtitle": "\(prefix) 选本", "narrationAvailable": false]))
    }

    @MainActor func testSwitchingVolumesPreservesBookmarksFavoritesReadRecordsAndScope() throws {
        let suite = "TangPoetryVolumeTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let first = try catalog("first"), second = try catalog("second")
        let loader: (ReaderVolume) throws -> PoemCatalog = { $0 == .first ? first : second }
        let store = PoemStore(defaults: defaults, availableVolumes: [.first, .second], catalogLoader: loader)
        XCTAssertEqual(store.volume, .first)
        store.favorites = ["first-2"]
        store.setRead("first-2", true)
        let firstScope = ReadingScope(collection: "favorites")
        store.openReadingScope(firstScope, selecting: "first-2")
        store.recordReadingBookmark(ReadingBookmark(lineIndex: 3), for: "first-2", lineCount: 4)
        store.settings.fontSize = 30

        store.switchVolume(.second)
        XCTAssertEqual(store.selectedID, "second-1")
        XCTAssertTrue(store.favorites.isEmpty)
        XCTAssertTrue(store.readIDs.isEmpty)
        XCTAssertTrue(store.readingScope.isAll)
        XCTAssertEqual(store.poems[0].image, "Volumes/2/Art/second-1.jpg")
        XCTAssertEqual(defaults.string(forKey: "reader.position"), "first-2")
        XCTAssertEqual(defaults.stringArray(forKey: "reader.favorites"), ["first-2"])
        XCTAssertEqual(defaults.stringArray(forKey: "reader.readIDs.v1"), ["first-2"])
        store.favorites = ["second-1"]
        store.setRead("second-1", true)
        store.openReadingScope(ReadingScope(collection: "favorites"), selecting: "second-1")
        store.recordReadingBookmark(ReadingBookmark(lineIndex: 1), for: "second-1", lineCount: 4)

        store.switchVolume(.first)
        XCTAssertEqual(store.selectedID, "first-2")
        XCTAssertEqual(store.favorites, ["first-2"])
        XCTAssertEqual(store.readIDs, ["first-2"])
        XCTAssertEqual(store.readingScope, firstScope)
        XCTAssertEqual(store.readingBookmark(for: "first-2", lineCount: 4).lineIndex, 3)
        XCTAssertEqual(store.settings.fontSize, 30)
        XCTAssertEqual(store.poems[0].image, "Art/first-1.jpg")

        store.switchVolume(.second)
        XCTAssertEqual(store.readingBookmark(for: "second-1", lineCount: 4).lineIndex, 1)
        let restored = PoemStore(defaults: defaults, availableVolumes: [.first, .second], catalogLoader: loader)
        XCTAssertEqual(restored.volume, .second)
        XCTAssertEqual(restored.selectedID, "second-1")
        XCTAssertEqual(restored.favorites, ["second-1"])
        XCTAssertEqual(restored.readIDs, ["second-1"])
        XCTAssertEqual(restored.readingScope.collection, "favorites")
        XCTAssertEqual(restored.coverPoemID, "second-1")
        XCTAssertFalse(restored.narrationAvailable)
    }

    @MainActor func testMissingOptionalSecondVolumeFallsBackToExistingFirstVolumeRecords() throws {
        let suite = "TangPoetryMissingVolumeTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        defaults.set("2", forKey: "reader.volume")
        defaults.set("first-2", forKey: "reader.position")
        let first = try catalog("first")
        let store = PoemStore(defaults: defaults, availableVolumes: [.first], catalogLoader: { _ in first })
        XCTAssertEqual(store.volume, .first)
        XCTAssertEqual(store.selectedID, "first-2")
        store.switchVolume(.second)
        XCTAssertEqual(store.volume, .first)
    }

    func testOptionalBundledSecondVolumeHasCompleteContentAndReadableGlyphs() throws {
        guard ReaderVolume.available.contains(.second) else { throw XCTSkip("Optional second-volume bundle is not included") }
        let catalog: PoemCatalog = try BundledContent.decode("Volumes/2/catalog.json")
        XCTAssertEqual(catalog.poems.count, 305)
        XCTAssertEqual(Set(catalog.poems.map(\.id)).count, 305)
        XCTAssertEqual(catalog.poems.filter(\.featured).count, 20)
        XCTAssertEqual(Set(catalog.poems.map(\.order)), Set(1...305))
        for poem in catalog.poems {
            let detail: PoemDetail = try BundledContent.decode("Volumes/2/poems/\(poem.id).json")
            XCTAssertEqual(detail.id, poem.id)
            XCTAssertEqual(detail.title, poem.title)
            XCTAssertFalse(detail.text.isEmpty)
            XCTAssertFalse(detail.note.isEmpty)
            XCTAssertFalse(detail.interpretation.isEmpty)
            XCTAssertEqual(detail.notes, detail.annotations.map(\.text))
            XCTAssertNoThrow(try BundledContent.url("Volumes/2/" + poem.image))
            XCTAssertNoThrow(try BundledContent.url("Volumes/2/" + poem.thumbnail))
            if poem.order == 28 {
                XCTAssertTrue(detail.text.contains("贫寠"))
                XCTAssertFalse(detail.text.contains("𪧘"))
            }
            if poem.order == 183 {
                XCTAssertTrue(poem.title.contains("郑礒"))
                XCTAssertTrue(poem.aliases.contains(where: { $0.contains("𥐟") }))
                XCTAssertTrue(detail.sourceTitle.contains("𥐟"))
                XCTAssertTrue(detail.readingSourceTitle.contains("礒"))
                XCTAssertFalse(detail.readingSourceTitle.contains("𥐟"))
            }
        }
        let font = CTFontCreateWithName("STSongti-SC-Regular" as CFString, 22, nil)
        for character in ["寠", "礒", "𫶇", "盩", "厔"] {
            let string = character as NSString
            let fallback = CTFontCreateForString(font, string, CFRange(location: 0, length: string.length))
            XCTAssertFalse((CTFontCopyPostScriptName(fallback) as String).contains("LastResort"), character)
            let units = Array(character.utf16)
            var glyphs = [CGGlyph](repeating: 0, count: units.count)
            XCTAssertTrue(CTFontGetGlyphsForCharacters(fallback, units, &glyphs, units.count), character)
            XCTAssertTrue(glyphs.contains(where: { $0 != 0 }), character)
        }
    }
}
