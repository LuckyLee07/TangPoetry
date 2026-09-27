import XCTest
@testable import TangPoetry

final class ReadingHistoryTests: XCTestCase {
    func testAllGenresUseTheirOwnDurationAndRequireTheLastVerse() {
        let durations = ["五言绝句": 10, "七言绝句": 10, "五言律诗": 20, "七言律诗": 20,
                         "五言古诗": 30, "七言古诗": 30, "乐府": 30]
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
        let durations = ["五言绝句": 10, "七言绝句": 10, "五言律诗": 20, "七言律诗": 20,
                         "五言古诗": 30, "七言古诗": 30, "乐府": 30]
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
        for t in 3602..<3616 { XCTAssertFalse(session.sample(id: "a", section: "五言律诗", active: true, endVisible: true, now: Double(t))) }
        XCTAssertTrue(session.sample(id: "a", section: "五言律诗", active: true, endVisible: true, now: 3616))
        for t in 0..<100 { XCTAssertFalse(session.sample(id: "poem-\(t)", section: "五言律诗", active: true, endVisible: true, now: Double(t))) }
    }

    func testManualUnreadWinsUntilANewReadingVisit() {
        var session = ReadingSession()
        for t in 0..<10 { _ = session.sample(id: "a", section: "五言律诗", active: true, endVisible: true, now: Double(t)) }
        session.suppress("a")
        for t in 10..<40 { XCTAssertFalse(session.sample(id: "a", section: "五言律诗", active: true, endVisible: true, now: Double(t))) }
        _ = session.sample(id: "b", section: "五言律诗", active: true, endVisible: true, now: 40)
        for t in 41..<61 { XCTAssertFalse(session.sample(id: "a", section: "五言律诗", active: true, endVisible: true, now: Double(t))) }
        XCTAssertTrue(session.sample(id: "a", section: "五言律诗", active: true, endVisible: true, now: 61))
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
