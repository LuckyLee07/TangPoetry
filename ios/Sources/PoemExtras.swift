import SwiftUI

// Calendar-day selection is identical on web and iOS, independent of reading scope.
enum DailyPoem {
    static func index(date: Date, timeZone: TimeZone = .current, count: Int) -> Int? {
        guard count > 0 else { return nil }
        var local = Calendar(identifier: .gregorian)
        local.timeZone = timeZone
        let components = local.dateComponents([.year, .month, .day], from: date)
        var utc = Calendar(identifier: .gregorian)
        utc.timeZone = TimeZone(secondsFromGMT: 0)!
        guard let calendarDay = utc.date(from: components) else { return nil }
        let day = Int(floor(calendarDay.timeIntervalSince1970 / 86400))
        return ((day * 73 + 17) % count + count) % count
    }
    static func poem(in poems: [PoemSummary], date: Date = .now) -> PoemSummary? {
        let ordered = poems.sorted { $0.order < $1.order }
        guard let index = index(date: date, count: ordered.count) else { return nil }
        return ordered[index]
    }
}

struct CoverPoemButton: View {
    let poems: [PoemSummary]
    let open: (String) -> Void
    var body: some View {
        if let poem = poems.first(where: { $0.id == "tang-157-feng-yu" }) {
            Button { open(poem.id) } label: {
                VStack(spacing: 5) {
                    Text("画中诗").font(.caption)
                    Text("\(poem.title) · \(poem.author)")
                        .font(.custom("STSongti-SC-Regular", size: 17, relativeTo: .body))
                        .multilineTextAlignment(.center)
                }.frame(maxWidth: .infinity).padding(.vertical, 12)
            }.buttonStyle(.plain)
                .accessibilityLabel("画中诗，\(poem.title)，\(poem.author)")
                .accessibilityHint("打开与封面风雨意境相映的诗笺")
        }
    }
}

struct DailyPoemButton: View {
    let poems: [PoemSummary]
    let open: (String) -> Void
    var body: some View {
        TimelineView(.periodic(from: .now, by: 60)) { context in
            if let poem = DailyPoem.poem(in: poems, date: context.date) {
                Button { open(poem.id) } label: {
                    HStack(spacing: 12) {
                        VStack(alignment: .leading, spacing: 5) {
                            Text("每日一首").font(.caption).foregroundStyle(.secondary)
                            Text("\(poem.title) · \(poem.author)")
                                .font(.custom("STSongti-SC-Regular", size: 17, relativeTo: .body))
                                .fixedSize(horizontal: false, vertical: true)
                        }
                        Spacer(minLength: 0)
                        Image(systemName: "chevron.right").font(.caption).foregroundStyle(.secondary)
                    }.padding(.vertical, 8).contentShape(Rectangle())
                }.buttonStyle(.plain)
                    .accessibilityLabel("每日一首，\(poem.title)，\(poem.author)")
                    .accessibilityHint("打开今天的诗笺，每天更新")
            }
        }
    }
}

enum GentleMotionStyle: String {
    case petals, snow, leaves
    static func forPoem(_ id: String) -> Self? {
        switch id {
        case "tang-232-chun-xiao": return .petals
        case "tang-244-jiang-xue": return .snow
        case "tang-225-zhu-li-guan": return .leaves
        default: return nil
        }
    }
}

struct GentleArtworkMotion: View {
    let poemID: String
    let active: Bool
    @AppStorage("reader.gentleMotion") private var enabled = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.scenePhase) private var scenePhase
    @State private var lowPower = ProcessInfo.processInfo.isLowPowerModeEnabled

    var body: some View {
        Group {
            if enabled, active, !reduceMotion, !lowPower, scenePhase == .active,
               let style = GentleMotionStyle.forPoem(poemID) {
                TimelineView(.animation(minimumInterval: 1.0 / 24)) { context in
                    Canvas { canvas, size in
                        let time = context.date.timeIntervalSinceReferenceDate
                        let count = style == .snow ? 12 : 5
                        for index in 0..<count {
                            let phase = (time / (20 + Double(index % 5) * 3) + Double(index) * 0.217).truncatingRemainder(dividingBy: 1)
                            let x = size.width * (0.13 + Double(index % 7) * 0.115 + sin(phase * .pi * 2 + Double(index)) * 0.035)
                            let y = size.height * (0.105 + phase * 0.225)
                            let alpha = sin(phase * .pi) * (style == .snow ? 0.55 : 0.32)
                            let width: CGFloat = style == .snow ? 2.5 : 5
                            let height: CGFloat = style == .snow ? 2.5 : 2
                            var particle = canvas
                            particle.opacity = alpha
                            particle.translateBy(x: x, y: y)
                            particle.rotate(by: .radians(phase * .pi + Double(index)))
                            let color: Color = style == .snow ? .white : style == .petals
                                ? Color(red: 0.67, green: 0.41, blue: 0.35) : Color(red: 0.32, green: 0.40, blue: 0.29)
                            particle.fill(Path(ellipseIn: CGRect(x: 0, y: 0, width: width, height: height)), with: .color(color))
                        }
                    }
                }
            }
        }
        .allowsHitTesting(false).accessibilityHidden(true)
        .onReceive(NotificationCenter.default.publisher(for: .NSProcessInfoPowerStateDidChange)) { _ in
            lowPower = ProcessInfo.processInfo.isLowPowerModeEnabled
        }
    }
}

struct GentleMotionSetting: View {
    @AppStorage("reader.gentleMotion") private var enabled = false
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    var body: some View {
        Section {
            Toggle("画境微动", isOn: $enabled)
        } footer: {
            Text(reduceMotion ? "系统已开启「减少动态效果」，画境保持静止。" : "先在《春晓》《江雪》《竹里馆》试用轻微落花、雪点与竹叶。默认关闭，低电量模式和减少动态效果时暂停。")
        }
    }
}
