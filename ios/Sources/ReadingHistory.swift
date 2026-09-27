import Foundation

/// Only measured foreground reading time counts; a suspended app never gains elapsed time.
struct ReadingSession {
    private(set) var poemID: String?
    private(set) var seconds: Double = 0
    private var sawEnd = false
    private var last: Double?
    private var active = false
    private var suppressed = false
    private var completed = false

    mutating func suppress(_ id: String) {
        if poemID == id { suppressed = true }
    }

    static func requiredSeconds(for section: String) -> Double {
        switch section {
        case "五言绝句", "七言绝句": return 10
        case "五言律诗", "七言律诗": return 20
        default: return 30
        }
    }

    mutating func sample(id: String, section: String, active: Bool, endVisible: Bool, now: Double) -> Bool {
        if poemID != id { self = ReadingSession(); poemID = id }
        let requiredSeconds = Self.requiredSeconds(for: section)
        if active, self.active, let last {
            seconds = min(requiredSeconds, seconds + max(0, min(2, now - last)))
        }
        last = now
        self.active = active
        sawEnd = sawEnd || (active && endVisible)
        guard active, !suppressed, !completed, seconds >= requiredSeconds, sawEnd else { return false }
        completed = true
        return true
    }
}
