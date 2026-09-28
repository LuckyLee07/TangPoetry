import XCTest
@testable import TangPoetry

final class CoverAtmosphereTests: XCTestCase {
    func testDrizzleStreaksFollowVelocityAndRemainShortAndFaint() {
        for index in 0..<48 {
            let size = CGSize(width: 390, height: 844)
            let drop = CoverRainDrop(index: index, time: 10, size: size)
            let next = CoverRainDrop(index: index, time: 10.001, size: size)
            XCTAssertGreaterThanOrEqual(drop.alpha, 0)
            XCTAssertLessThanOrEqual(drop.alpha, 0.30)
            XCTAssertGreaterThan(drop.end.y - drop.start.y, 3)
            XCTAssertLessThan(drop.end.y - drop.start.y, 9)
            if abs(next.start.y - drop.start.y) < 1 {
                XCTAssertEqual((next.start.x - drop.start.x) / (next.start.y - drop.start.y),
                               (drop.end.x - drop.start.x) / (drop.end.y - drop.start.y), accuracy: 0.000001)
            }
        }
    }

    func testPausedCoverFreezesItsPhaseAndResumesWithoutJumping() {
        var clock = CoverMotionClock()
        let date = Date(timeIntervalSinceReferenceDate: 100)
        XCTAssertEqual(clock.time(at: date), 0)
        clock.setRunning(true, at: date)
        XCTAssertEqual(clock.time(at: date.addingTimeInterval(5)), 5)
        clock.setRunning(false, at: date.addingTimeInterval(5))
        XCTAssertEqual(clock.time(at: date.addingTimeInterval(1000)), 5)
        clock.setRunning(true, at: date.addingTimeInterval(1000))
        XCTAssertEqual(clock.time(at: date.addingTimeInterval(1000)), 5)
        clock.setRunning(true, at: date.addingTimeInterval(1001))
        XCTAssertEqual(clock.time(at: date.addingTimeInterval(1002)), 7)
        clock.setRunning(false, at: date.addingTimeInterval(1002))
        clock.setRunning(false, at: date.addingTimeInterval(1004))
        XCTAssertEqual(clock.time(at: date.addingTimeInterval(1005)), 7)
    }
}
