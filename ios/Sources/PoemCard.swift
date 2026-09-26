import SwiftUI
import UIKit

struct PoemCardLayout {
    static let width: CGFloat = 1080
    let titleLines: [String]
    let verseLines: [String]
    let titleFont: UIFont
    let verseFont: UIFont
    let verseTop: CGFloat
    let lineHeight: CGFloat
    let height: CGFloat

    init(title: String, lines: [String]) {
        titleFont = UIFont(name: "STSongti-SC-Regular", size: 64) ?? .systemFont(ofSize: 64)
        let longest = lines.map(\.count).max() ?? 8
        let fontSize: CGFloat = lines.count > 12 ? 48 : longest <= 6 ? 72 : 64
        let bodyFont = UIFont(name: "STSongti-SC-Regular", size: fontSize) ?? .systemFont(ofSize: fontSize)
        verseFont = bodyFont
        titleLines = Self.wrap(title, font: titleFont, width: 880)
        verseLines = lines.flatMap { Self.wrap($0, font: bodyFont, width: 872) }
        verseTop = 740 + CGFloat(titleLines.count) * 86 + 114
        lineHeight = fontSize * 1.75
        height = max(1620, verseTop + CGFloat(verseLines.count) * lineHeight + 160)
    }
    static func wrap(_ text: String, font: UIFont, width: CGFloat) -> [String] {
        var lines: [String] = [], current = ""
        for char in text {
            let trial = current + String(char)
            if !current.isEmpty && (trial as NSString).size(withAttributes: [.font: font]).width > width {
                if char.unicodeScalars.allSatisfy({ CharacterSet.punctuationCharacters.contains($0) }), current.count > 1 {
                    let previous = current.removeLast()
                    lines.append(current)
                    current = String(previous) + String(char)
                } else { lines.append(current); current = String(char) }
            } else { current = trial }
        }
        if !current.isEmpty { lines.append(current) }
        return lines
    }
}

actor PoemCardExporter {
    static let shared = PoemCardExporter()
    private var cleaned = false
    private var recency: [URL] = []

    func export(poem: PoemSummary, detail: PoemDetail) throws -> URL {
        let folder = FileManager.default.temporaryDirectory.appendingPathComponent("TangPoetryCards", isDirectory: true)
        try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
        if !cleaned {
            for file in try FileManager.default.contentsOfDirectory(at: folder, includingPropertiesForKeys: nil) where file.pathExtension == "png" {
                try? FileManager.default.removeItem(at: file)
            }
            cleaned = true
        }
        let url = folder.appendingPathComponent("\(poem.id).png")
        if !FileManager.default.fileExists(atPath: url.path) {
            let data = try autoreleasepool {
                let artURL = try BundledContent.url(poem.image)
                guard let art = UIImage(contentsOfFile: artURL.path) else { throw ContentError.missingResource(poem.image) }
                return Self.render(poem: poem, detail: detail, art: art)
            }
            try data.write(to: url, options: .atomic)
        }
        recency.removeAll { $0 == url }; recency.append(url)
        while recency.count > 8 { try? FileManager.default.removeItem(at: recency.removeFirst()) }
        return url
    }

    static func render(poem: PoemSummary, detail: PoemDetail, art: UIImage) -> Data {
        let lines = detail.rubyLines.map { $0.map(\.text).joined() }
        let layout = PoemCardLayout(title: poem.title, lines: lines)
        let format = UIGraphicsImageRendererFormat(); format.scale = 1; format.opaque = true
        let paper = UIColor(red: 0.965, green: 0.945, blue: 0.902, alpha: 1)
        let ink = UIColor(red: 0.19, green: 0.17, blue: 0.14, alpha: 1)
        let muted = UIColor(red: 0.44, green: 0.42, blue: 0.36, alpha: 1)
        return UIGraphicsImageRenderer(size: CGSize(width: PoemCardLayout.width, height: layout.height), format: format).pngData { renderer in
            let context = renderer.cgContext
            paper.setFill(); context.fill(CGRect(x: 0, y: 0, width: 1080, height: layout.height))
            context.saveGState()
            context.clip(to: CGRect(x: 0, y: 0, width: 1080, height: 740))
            let scale = 1080 / art.size.width
            art.draw(in: CGRect(x: 0, y: 0, width: 1080, height: art.size.height * scale))
            if let gradient = CGGradient(colorsSpace: CGColorSpaceCreateDeviceRGB(), colors: [paper.withAlphaComponent(0).cgColor, paper.cgColor] as CFArray, locations: [0, 1]) {
                context.drawLinearGradient(gradient, start: CGPoint(x: 0, y: 530), end: CGPoint(x: 0, y: 740), options: [])
            }
            context.restoreGState()
            func centered(_ value: String, y: CGFloat, font: UIFont, color: UIColor) {
                let style = NSMutableParagraphStyle(); style.alignment = .center
                (value as NSString).draw(in: CGRect(x: 90, y: y, width: 900, height: font.lineHeight * 1.5),
                                        withAttributes: [.font: font, .foregroundColor: color, .paragraphStyle: style])
            }
            for (index, line) in layout.titleLines.enumerated() { centered(line, y: 740 + CGFloat(index) * 86, font: layout.titleFont, color: ink) }
            centered("唐 · \(poem.author)", y: 740 + CGFloat(layout.titleLines.count) * 86 + 12, font: .systemFont(ofSize: 30), color: muted)
            for (index, line) in layout.verseLines.enumerated() { centered(line, y: layout.verseTop + CGFloat(index) * layout.lineHeight, font: layout.verseFont, color: ink) }
            muted.withAlphaComponent(0.25).setStroke(); context.setLineWidth(1)
            context.move(to: CGPoint(x: 440, y: layout.height - 112)); context.addLine(to: CGPoint(x: 640, y: layout.height - 112)); context.strokePath()
            centered("唐诗画笺 · 一页一诗", y: layout.height - 84, font: .systemFont(ofSize: 25), color: muted)
        }
    }
}

struct PoemCardView: View {
    let poem: PoemSummary
    @EnvironmentObject private var store: PoemStore
    @Environment(\.dismiss) private var dismiss
    @State private var exportURL: URL?
    @State private var image: UIImage?
    @State private var failed = false
    @State private var retry = 0
    @State private var activity = false

    var body: some View {
        NavigationStack {
            Group {
                if let image {
                    ScrollView {
                        Image(uiImage: image).resizable().scaledToFit()
                            .accessibilityLabel("\(poem.title)，\(poem.author)的完整诗笺分享图")
                    }.background(store.settings.paperColor)
                } else if failed {
                    ContentUnavailableView {
                        Label("诗笺暂未生成", systemImage: "photo")
                    } description: { Text("请稍后再试，诗文和收藏仍已保留。") }
                    actions: { Button("重试") { retry += 1 } }
                } else { ProgressView("正在制作诗笺…") }
            }
            .navigationTitle("诗笺预览").navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("完成") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button { activity = true } label: { Label("保存或分享", systemImage: "square.and.arrow.up") }
                        .disabled(exportURL == nil).accessibilityLabel("保存或分享诗笺")
                }
            }
        }
        .task(id: retry) {
            failed = false
            do {
                let detail = try await store.repository.detail(poem.id)
                let url = try await PoemCardExporter.shared.export(poem: poem, detail: detail)
                guard !Task.isCancelled else { return }
                image = UIImage(contentsOfFile: url.path); exportURL = image == nil ? nil : url
                failed = image == nil
            } catch { if !Task.isCancelled { failed = true } }
        }
        .sheet(isPresented: $activity) { if let exportURL { PoemActivityView(url: exportURL) } }
    }
}

private struct PoemActivityView: UIViewControllerRepresentable {
    let url: URL
    func makeUIViewController(context: Context) -> UIActivityViewController {
        UIActivityViewController(activityItems: [url], applicationActivities: nil)
    }
    func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {}
}
