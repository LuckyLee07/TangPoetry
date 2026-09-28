import XCTest
@testable import TangPoetry

final class ReadingHistoryTests: XCTestCase {
    @MainActor func testShortNarrationAndContinuedReadingAccumulateTwentySeconds() throws {
        let suite = "TangPoetryListeningReceipt.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let store = PoemStore(defaults: defaults)
        let poem = try XCTUnwrap(store.poems.first { $0.section == "五言绝句" })
        store.openPoem(poem.id)
        store.recordReadViewport(for: poem.id, endIsVisible: true)
        let active = ReadingSurface.narration.countsTime(inForeground: true, isCurrentNarrationPlaying: true)
        store.setReadingActive(active, now: 0)
        for second in 1...16 {
            store.sampleReading(now: Double(second))
            XCTAssertFalse(store.readIDs.contains(poem.id))
        }
        store.setReadingActive(false, now: 17) // Finished audio; player sheet is still open.
        for second in 18...20 { store.sampleReading(now: Double(second)) }
        XCTAssertFalse(store.readIDs.contains(poem.id))
        store.setReadingActive(true, now: 21) // Return to reading the poem.
        for second in 22...25 {
            store.sampleReading(now: Double(second))
            XCTAssertEqual(store.readIDs.contains(poem.id), second == 25)
        }
        XCTAssertTrue(PoemStore(defaults: defaults).readIDs.contains(poem.id))
    }

    func testPausedPlayerBackgroundAndOtherSheetsDoNotCountAsListening() {
        XCTAssertTrue(ReadingSurface.poem.countsTime(inForeground: true, isCurrentNarrationPlaying: false))
        XCTAssertFalse(ReadingSurface.narration.countsTime(inForeground: true, isCurrentNarrationPlaying: false))
        for surface in [ReadingSurface.poem, .narration, .covered] {
            XCTAssertFalse(surface.countsTime(inForeground: false, isCurrentNarrationPlaying: true))
        }
        XCTAssertFalse(ReadingSurface.covered.countsTime(inForeground: true, isCurrentNarrationPlaying: true))

        var session = ReadingSession()
        for t in 0...4 { _ = session.sample(id: "a", section: "五言绝句", active: true, endVisible: true, now: Double(t)) }
        for t in 5...25 { _ = session.sample(id: "a", section: "五言绝句", active: false, endVisible: true, now: Double(t)) }
        XCTAssertEqual(session.seconds, 4)
        for t in 26...41 { XCTAssertFalse(session.sample(id: "a", section: "五言绝句", active: true, endVisible: true, now: Double(t))) }
        XCTAssertTrue(session.sample(id: "a", section: "五言绝句", active: true, endVisible: true, now: 42))
    }

    func testAllGenresUseTheirOwnDurationAndRequireTheLastVerse() {
        let durations = ["五言绝句": 20, "七言绝句": 20, "五言律诗": 30, "七言律诗": 30,
                         "五言古诗": 40, "七言古诗": 40, "乐府": 40]
        for (section, seconds) in durations {
            var session = ReadingSession()
            for t in 0..<seconds {
                XCTAssertFalse(session.sample(id: "a", section: section, active: true, endVisible: true, now: Double(t)), section)
            }
            XCTAssertTrue(session.sample(id: "a", section: section, active: true, endVisible: true, now: Double(seconds)), section)
            XCTAssertFalse(session.sample(id: "a", section: section, active: true, endVisible: true, now: Double(seconds + 1)))
            var incomplete = ReadingSession()
            for t in 0...(seconds + 5) {
                XCTAssertFalse(incomplete.sample(id: "a", section: section, active: true, endVisible: false, now: Double(t)), section)
            }
            XCTAssertTrue(incomplete.sample(id: "a", section: section, active: true, endVisible: true, now: Double(seconds + 6)), section)
        }
    }

    @MainActor func testStoreUsesCatalogGenreAndResetsTimingWhenChangingPoems() throws {
        let suite = "TangPoetryHistoryGenres.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let store = PoemStore(defaults: defaults)
        let durations = ["五言绝句": 20, "七言绝句": 20, "五言律诗": 30, "七言律诗": 30,
                         "五言古诗": 40, "七言古诗": 40, "乐府": 40]
        XCTAssertEqual(Set(store.poems.map(\.section)), Set(durations.keys))
        store.setReadingActive(true)
        var now = ProcessInfo.processInfo.systemUptime
        for section in ["乐府", "七言绝句", "五言律诗", "五言绝句", "七言律诗", "五言古诗", "七言古诗"] {
            let poem = try XCTUnwrap(store.poems.first { $0.section == section })
            let seconds = try XCTUnwrap(durations[section])
            store.openPoem(poem.id)
            store.recordReadViewport(for: poem.id, endIsVisible: true)
            for t in 0..<seconds {
                store.sampleReading(now: now + Double(t))
                XCTAssertFalse(store.readIDs.contains(poem.id), section)
            }
            store.sampleReading(now: now + Double(seconds))
            XCTAssertTrue(store.readIDs.contains(poem.id), section)
            now += Double(seconds + 1)
        }
    }

    func testModalBackgroundAndPageChangesDoNotEarnReadingTime() {
        var session = ReadingSession()
        for t in 0...5 { _ = session.sample(id: "a", section: "五言律诗", active: true, endVisible: true, now: Double(t)) }
        _ = session.sample(id: "a", section: "五言律诗", active: false, endVisible: true, now: 6)
        _ = session.sample(id: "a", section: "五言律诗", active: false, endVisible: true, now: 3600)
        XCTAssertFalse(session.sample(id: "a", section: "五言律诗", active: true, endVisible: true, now: 3601))
        XCTAssertEqual(session.seconds, 5)
        for t in 3602..<3626 { XCTAssertFalse(session.sample(id: "a", section: "五言律诗", active: true, endVisible: true, now: Double(t))) }
        XCTAssertTrue(session.sample(id: "a", section: "五言律诗", active: true, endVisible: true, now: 3626))
        for t in 0..<100 { XCTAssertFalse(session.sample(id: "poem-\(t)", section: "五言律诗", active: true, endVisible: true, now: Double(t))) }
    }

    func testManualUnreadWinsUntilANewReadingVisit() {
        var session = ReadingSession()
        for t in 0..<10 { _ = session.sample(id: "a", section: "五言律诗", active: true, endVisible: true, now: Double(t)) }
        session.suppress("a")
        for t in 10..<40 { XCTAssertFalse(session.sample(id: "a", section: "五言律诗", active: true, endVisible: true, now: Double(t))) }
        _ = session.sample(id: "b", section: "五言律诗", active: true, endVisible: true, now: 40)
        for t in 41..<71 { XCTAssertFalse(session.sample(id: "a", section: "五言律诗", active: true, endVisible: true, now: Double(t))) }
        XCTAssertTrue(session.sample(id: "a", section: "五言律诗", active: true, endVisible: true, now: 71))
    }

    @MainActor func testReceiptsPersistWithoutInferringLegacyBookmarksAndFiltersKeepCurrentPoem() throws {
        let suite = "TangPoetryHistoryTests.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        defaults.set("tang-233-ye-si", forKey: "reader.position")
        defaults.set(try JSONEncoder().encode(["tang-233-ye-si": ReadingBookmark(lineIndex: 3)]), forKey: "reader.bookmarks")
        defaults.set(Data(#"{"collection":"featured","author":"王维","category":"五言绝句","query":""}"#.utf8), forKey: "reader.scope")
        let legacy = try JSONDecoder().decode(ReadingScope.self, from: try XCTUnwrap(defaults.data(forKey: "reader.scope")))
        let store = PoemStore(defaults: defaults)
        XCTAssertTrue(store.readIDs.isEmpty)
        XCTAssertEqual(legacy.readStatus, "all")
        XCTAssertEqual(legacy.author, "王维")
        let scope = ReadingScope(collection: "featured", category: "五言绝句", author: "王维", readStatus: "unread")
        let sequence = scope.poems(in: store.poems, favorites: [], readIDs: store.readIDs)
        XCTAssertGreaterThan(sequence.count, 1)
        store.openReadingScope(scope, selecting: sequence[0].id)
        store.setRead(sequence[0].id, true)
        XCTAssertEqual(store.selectedID, sequence[0].id)
        XCTAssertEqual(store.readingPoems.map(\.id), sequence.map(\.id))
        XCTAssertFalse(scope.poems(in: store.poems, favorites: [], readIDs: store.readIDs).contains { $0.id == sequence[0].id })
        let restored = PoemStore(defaults: defaults)
        XCTAssertEqual(restored.readIDs, [sequence[0].id])
        XCTAssertEqual(restored.selectedID, sequence[0].id)
        XCTAssertEqual(restored.readingPoems.map(\.id), sequence.map(\.id))
        restored.turn(1)
        XCTAssertEqual(restored.selectedID, sequence[1].id)
        restored.setRead(sequence[0].id, false)
        XCTAssertTrue(PoemStore(defaults: defaults).readIDs.isEmpty)
        restored.setRead("missing", true)
        XCTAssertTrue(restored.readIDs.isEmpty)
    }

    @MainActor func testOnlyVisibleReadyPoemCanReceiveAutomaticReceipt() throws {
        let suite = "TangPoetryHistoryViewport.\(UUID().uuidString)"
        let defaults = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { defaults.removePersistentDomain(forName: suite) }
        let store = PoemStore(defaults: defaults)
        let current = store.poems[0].id, neighbor = store.poems[1].id
        store.openPoem(current)
        store.setReadingActive(true)
        store.recordReadViewport(for: neighbor, endIsVisible: true)
        let now = ProcessInfo.processInfo.systemUptime
        for t in 0...25 { store.sampleReading(now: now + Double(t)) }
        XCTAssertTrue(store.readIDs.isEmpty)
        store.recordReadViewport(for: current, endIsVisible: true)
        for t in 26...46 { store.sampleReading(now: now + Double(t)) }
        XCTAssertEqual(store.readIDs, [current])
    }
}
