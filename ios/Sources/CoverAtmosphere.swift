import SwiftUI

/// Freeze the phase while a sheet, background state, or accessibility preference pauses motion.
struct CoverMotionClock {
    private var elapsed: TimeInterval = 0
    private var startedAt: Date?

    func time(at date: Date) -> TimeInterval {
        elapsed + (startedAt.map { max(0, date.timeIntervalSince($0)) } ?? 0)
    }

    mutating func setRunning(_ running: Bool, at date: Date) {
        guard running != (startedAt != nil) else { return }
        elapsed = time(at: date)
        startedAt = running ? date : nil
    }
}

struct CoverAtmosphere: View {
    let active: Bool
    let paperColor: Color
    @AppStorage("reader.coverMotion") private var enabled = true
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.scenePhase) private var scenePhase
    @State private var lowPower = ProcessInfo.processInfo.isLowPowerModeEnabled
    @State private var clock = CoverMotionClock()

    @State private var layers: [UIImage]?
    private var available: Bool { enabled && !reduceMotion && !lowPower && layers != nil }
    private var running: Bool { available && active && scenePhase == .active }

    var body: some View {
        GeometryReader { geometry in
            TimelineView(.animation(minimumInterval: 1.0 / 60, paused: !running)) { timeline in
                let time = clock.time(at: timeline.date)
                let crop = Self.crop(for: geometry.size)
                ZStack {
                    if available, let layers {
                        coverImage(layers[0], size: geometry.size)
                        coverImage(layers[1], size: geometry.size)
                            .colorEffect(ShaderLibrary.coverOriginalLower(.float2(geometry.size), .float4(crop.x, crop.y, crop.z, crop.w)))
                        coverImage(layers[2], size: geometry.size)
                            .colorEffect(ShaderLibrary.coverWillowCutout())
                            .blur(radius: 0.4)
                            .distortionEffect(
                                ShaderLibrary.coverWillowBranches(.float2(geometry.size), .float4(crop.x, crop.y, crop.z, crop.w), .float(Float(time))),
                                maxSampleOffset: CGSize(width: 20, height: 2)
                            )
                    } else {
                        Artwork(path: "Art/song-yuan-er-page.jpg")
                    }
                    LinearGradient(colors: [.clear, paperColor], startPoint: .center, endPoint: .bottom)
                    // Rain must sit above the paper wash; otherwise the already faint drops disappear.
                    if available {
                        Canvas { context, size in
                            drawRain(in: context, size: size, time: time)
                        }
                    }
                }.frame(width: geometry.size.width, height: geometry.size.height).clipped()
            }
            .task(id: geometry.size) {
                let paths = ["Cover/background.png", "Art/song-yuan-er-page.jpg", "Cover/willow-matte.png"]
                var loaded: [UIImage] = []
                for path in paths {
                    let request = ArtworkRequest(path: path, size: geometry.size, scale: 2)
                    guard let image = await ArtworkLoader.shared.image(for: request), !Task.isCancelled else { return }
                    loaded.append(image)
                }
                layers = loaded
            }
        }
        .allowsHitTesting(false).accessibilityHidden(true)
        .onChange(of: running, initial: true) { _, value in clock.setRunning(value, at: .now) }
        .onDisappear { clock.setRunning(false, at: .now) }
        .onReceive(NotificationCenter.default.publisher(for: .NSProcessInfoPowerStateDidChange)) { _ in
            lowPower = ProcessInfo.processInfo.isLowPowerModeEnabled
        }
    }

    private func coverImage(_ image: UIImage, size: CGSize) -> some View {
        Image(uiImage: image).resizable().scaledToFill()
            .frame(width: size.width, height: size.height).clipped()
    }

    static func crop(for size: CGSize) -> SIMD4<Float> {
        let scale = max(size.width / 941, size.height / 1672)
        let width = size.width / (941 * scale), height = size.height / (1672 * scale)
        return SIMD4(Float((1 - width) / 2), Float((1 - height) / 2), Float(width), Float(height))
    }

    private func drawRain(in context: GraphicsContext, size: CGSize, time: TimeInterval) {
        for index in 0..<48 {
            let drop = CoverRainDrop(index: index, time: time, size: size)
            let ink = index % 4 == 0 ? Color.white : Color(red: 90.0 / 255, green: 99.0 / 255, blue: 93.0 / 255)
            let gradient = Gradient(stops: [
                .init(color: ink.opacity(0), location: 0),
                .init(color: ink.opacity(drop.alpha), location: 0.30),
                .init(color: ink.opacity(drop.alpha), location: 0.75),
                .init(color: ink.opacity(0), location: 1)
            ])
            var line = Path()
            line.move(to: drop.start); line.addLine(to: drop.end)
            context.stroke(line, with: .linearGradient(gradient, startPoint: drop.start, endPoint: drop.end),
                           style: StrokeStyle(lineWidth: drop.width, lineCap: .round))
        }
    }

}

struct CoverRainDrop {
    let start: CGPoint
    let end: CGPoint
    let alpha: Double
    let width: Double

    private static func hash(_ value: Double) -> Double {
        let raw = (sin(value * 127.1 + 311.7) * 43758.5453).truncatingRemainder(dividingBy: 1)
        return (raw + 1).truncatingRemainder(dividingBy: 1)
    }

    init(index: Int, time: TimeInterval, size: CGSize) {
        let i = Double(index)
        let duration = 2.7 + Self.hash(i + 1) * 1.3
        let life = time / duration + Self.hash(i + 80)
        let cycle = floor(life), phase = life - cycle
        let seed = i * 17 + cycle * 131
        let vx = 8 + Self.hash(seed + 2) * 7, vy = size.height * 0.85 / duration
        let age = phase * duration
        let x = Self.hash(seed + 3) * (size.width + 30) - 30 + vx * age
        let y = -12 + vy * age
        let exposure = 0.023 + Self.hash(seed + 5) * 0.007
        let quietTitle = x / size.width > 0.70 && y / size.height < 0.53 ? 0.35 : 1.0
        let fade = min(1, phase * 15) * max(0, min(1, (0.79 - y / size.height) / 0.13))
        start = CGPoint(x: x, y: y)
        end = CGPoint(x: x + vx * exposure, y: y + vy * exposure)
        alpha = (0.18 + Self.hash(seed + 7) * 0.10) * fade * quietTitle * min(1, time / 2)
        width = 0.7 + Self.hash(seed + 9) * 0.2
    }
}

struct CoverMotionSetting: View {
    @AppStorage("reader.coverMotion") private var enabled = true
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    var body: some View {
        Section {
            Toggle("首页风雨", isOn: $enabled)
        } footer: {
            Text(reduceMotion ? "系统已开启「减少动态效果」，首页保持静止。" : "柳条轻摆，细雨轻落。默认开启，低电量模式下暂停。")
        }
    }
}
