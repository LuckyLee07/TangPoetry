import XCTest
@testable import TangPoetry

final class ExtrasTests: XCTestCase {
    func testDailyPoemUsesLocalDateAndDoesNotRepeatWithinEditionCycle() throws {
        let formatter = ISO8601DateFormatter()
        let zone = TimeZone(secondsFromGMT: 8 * 3600)!
        let morning = try XCTUnwrap(formatter.date(from: "2026-09-25T16:01:00Z"))
        let evening = try XCTUnwrap(formatter.date(from: "2026-09-26T15:59:00Z"))
        XCTAssertEqual(DailyPoem.index(date: morning, timeZone: zone, count: 320), DailyPoem.index(date: evening, timeZone: zone, count: 320))
        XCTAssertNotEqual(DailyPoem.index(date: morning, timeZone: zone, count: 320), DailyPoem.index(date: morning.addingTimeInterval(86400), timeZone: zone, count: 320))
        XCTAssertNil(DailyPoem.index(date: morning, count: 0))
        XCTAssertEqual(Set((0..<320).compactMap { DailyPoem.index(date: morning.addingTimeInterval(Double($0) * 86400), timeZone: zone, count: 320) }).count, 320)
    }
    func testFullPoemShareCardsPreserveTextAtBoundedImageSize() throws {
        let catalog: PoemCatalog = try BundledContent.decode("catalog.json")
        for poem in catalog.poems {
            let detail: PoemDetail = try BundledContent.decode("poems/\(poem.id).json")
            let lines = detail.rubyLines.map { $0.map(\.text).joined() }
            let layout = PoemCardLayout(title: poem.title, lines: lines)
            XCTAssertEqual(layout.verseLines.joined(), lines.joined(), poem.id)
            XCTAssertEqual(layout.titleLines.joined(), poem.title, poem.id)
            XCTAssertLessThan(layout.height * PoemCardLayout.width, 16_000_000, poem.id)
            XCTAssertGreaterThan(layout.height, layout.verseTop + CGFloat(layout.verseLines.count) * layout.lineHeight, poem.id)
        }
    }
    func testLargestTextKeepsHangingPunctuationInsideNarrowReadingArea() {
        let origin = VerseGrid.rowOrigin(width: 278, count: 1, cellWidth: 112, hangingWidth: 95)
        XCTAssertGreaterThanOrEqual(origin, 0)
        XCTAssertLessThanOrEqual(origin + 112 + 95, 278)
        XCTAssertEqual(VerseGrid.rowOrigin(width: 340, count: 7, cellWidth: 28, hangingWidth: 24), 72)
    }
    func testMotionTrialIsLimitedToThreePoems() {
        XCTAssertEqual(GentleMotionStyle.forPoem("tang-232-chun-xiao"), .petals)
        XCTAssertEqual(GentleMotionStyle.forPoem("tang-244-jiang-xue"), .snow)
        XCTAssertEqual(GentleMotionStyle.forPoem("tang-225-zhu-li-guan"), .leaves)
        XCTAssertNil(GentleMotionStyle.forPoem("tang-233-ye-si"))
    }
}
