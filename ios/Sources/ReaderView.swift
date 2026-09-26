import SwiftUI
import UIKit

extension ReaderSettings {
    var paperColor: Color {
        switch paper {
        case "ivory": return Color(red: 0.98, green: 0.98, blue: 0.96)
        case "sage": return Color(red: 0.91, green: 0.93, blue: 0.90)
        default: return Color(red: 0.965, green: 0.945, blue: 0.902)
        }
    }
}

private enum ArtworkCache {
    static let cache: NSCache<NSString, UIImage> = {
        let result = NSCache<NSString, UIImage>()
        result.countLimit = 16
        result.totalCostLimit = 24 * 1024 * 1024
        return result
    }()
    static func image(_ path: String) -> UIImage? {
        if let cached = cache.object(forKey: path as NSString) { return cached }
        guard let url = try? BundledContent.url(path), let image = UIImage(contentsOfFile: url.path) else { return nil }
        cache.setObject(image, forKey: path as NSString, cost: Int(image.size.width * image.size.height * 4))
        return image
    }
}

struct Artwork: View {
    let path: String
    var body: some View {
        if let image = ArtworkCache.image(path) { Image(uiImage: image).resizable().scaledToFill().accessibilityHidden(true) }
        else { Color.clear }
    }
}

private enum ReaderSheet: String, Identifiable {
    case library, settings
    var id: String { rawValue }
}

struct ReaderView: View {
    @EnvironmentObject private var store: PoemStore
    @State private var home = true
    @State private var controls = true
    @State private var sheet: ReaderSheet?
    @State private var collection = "all"

    var body: some View {
        ZStack {
            store.settings.paperColor.ignoresSafeArea()
            if let error = store.loadError {
                ContentUnavailableView {
                    Label("诗库暂未打开", systemImage: "book.closed")
                } description: { Text(error) } actions: { Button("重试") { store.load() } }
            } else if home {
                cover
            } else {
                reader
            }
        }
        .foregroundStyle(Color(red: 0.19, green: 0.17, blue: 0.14))
        .sheet(item: $sheet) { item in
            switch item {
            case .library:
                LibraryView(collection: collection) { id in
                    store.selectedID = id
                    home = false
                    controls = true
                    sheet = nil
                }
            case .settings:
                SettingsView {
                    collection = "favorites"
                    sheet = .library
                }
            }
        }
    }

    private var cover: some View {
        GeometryReader { geometry in
            ZStack(alignment: .topTrailing) {
                Artwork(path: "Art/song-yuan-er-page.jpg").frame(width: geometry.size.width, height: geometry.size.height).clipped()
                LinearGradient(colors: [.clear, store.settings.paperColor], startPoint: .center, endPoint: .bottom)
                VStack(alignment: .trailing, spacing: 16) {
                    Text("唐\n诗\n三\n百\n首").font(.custom("STSongti-SC-Regular", size: 40, relativeTo: .largeTitle)).lineSpacing(4)
                    Text("诗").font(.title3).padding(8).background(Color(red: 0.63, green: 0.23, blue: 0.15), in: RoundedRectangle(cornerRadius: 5)).foregroundStyle(.white)
                }.padding(.top, 42).padding(.trailing, 42)
                VStack(spacing: 20) {
                    Spacer()
                    Text("孙洙选本 · 一页一诗，一诗一画").font(.caption).foregroundStyle(.secondary)
                    Text("\(store.poems.count) 首 · \(store.poems.filter(\.featured).count) 幅精选").font(.caption)
                    HStack(spacing: 12) {
                        Button(store.currentIndex == 0 ? "入卷" : "续读") { home = false }.buttonStyle(.borderedProminent)
                        Button("目录") { collection = "all"; sheet = .library }.buttonStyle(.bordered)
                        Button("精选") { collection = "featured"; sheet = .library }.buttonStyle(.bordered)
                    }.controlSize(.large).buttonBorderShape(.capsule)
                }.padding(.horizontal, 24).padding(.bottom, 34)
            }
        }
    }

    private var reader: some View {
        ZStack {
            TabView(selection: $store.selectedID) {
                ForEach(Array(store.poems.enumerated()), id: \.element.id) { index, poem in
                    Group {
                        if abs(index - store.currentIndex) <= 1 {
                            PoemPageView(poem: poem) { controls.toggle() }
                        } else { store.settings.paperColor }
                    }.tag(poem.id)
                }
            }.tabViewStyle(.page(indexDisplayMode: .never))
            if controls {
                VStack {
                    HStack(spacing: 10) {
                        tool("卷", label: "返回封面") { home = true }
                        Spacer()
                        tool("目录", label: "目录") { collection = "all"; sheet = .library }
                        tool("Aa", label: "阅读设置") { sheet = .settings }
                        tool(store.favorites.contains(store.selectedID) ? "已藏" : "藏", label: store.favorites.contains(store.selectedID) ? "取消收藏此诗" : "收藏此诗") { store.toggleFavorite(store.selectedID) }
                    }
                    Spacer()
                    HStack(spacing: 2) {
                        tool("拼音", label: store.settings.pinyin ? "隐藏拼音" : "显示拼音") { store.settings.pinyin.toggle() }
                        Spacer(minLength: 4)
                        Button { store.turn(-1) } label: { Image(systemName: "chevron.left").frame(width: 32, height: 44) }.disabled(store.currentIndex == 0).accessibilityLabel("上一首")
                        Text("\(store.currentIndex + 1) / \(store.poems.count)").font(.caption2).monospacedDigit().fixedSize()
                        Button { store.turn(1) } label: { Image(systemName: "chevron.right").frame(width: 32, height: 44) }.disabled(store.currentIndex == store.poems.count - 1).accessibilityLabel("下一首")
                        Spacer(minLength: 4)
                        tool("简注", label: store.settings.notes ? "隐藏简注" : "显示简注") { store.settings.notes.toggle() }
                    }
                }.padding(.horizontal, 22).padding(.vertical, 10)
            } else {
                VStack { Spacer(); tool("···", label: "显示阅读工具") { controls = true } }.padding(.bottom, 10)
            }
        }
    }

    private func tool(_ text: String, label: String, action: @escaping () -> Void) -> some View {
        Button(action: action) { Text(text).font(.system(size: 13)).padding(.horizontal, 10).frame(minWidth: 44, minHeight: 44).background(store.settings.paperColor.opacity(0.94), in: Capsule()).overlay(Capsule().strokeBorder(.primary.opacity(0.12))) }.accessibilityLabel(label)
    }
}

struct PoemPageView: View {
    @EnvironmentObject private var store: PoemStore
    let poem: PoemSummary
    let toggleControls: () -> Void
    @State private var detail: PoemDetail?
    @State private var failed = false
    @State private var retry = 0
    @State private var showNotes = false

    var body: some View {
        GeometryReader { geometry in
            ZStack {
                Artwork(path: poem.image).frame(width: geometry.size.width, height: geometry.size.height).clipped()
                LinearGradient(stops: [.init(color: .clear, location: 0.16), .init(color: store.settings.paperColor.opacity(0.95), location: 0.65)], startPoint: .top, endPoint: .bottom)
                VStack(spacing: 0) {
                    Text("第\(poem.order)首 · \(poem.section)").font(.caption2).foregroundStyle(.secondary).frame(maxWidth: .infinity, alignment: .leading).padding(.top, 68)
                    Spacer().frame(height: max(28, geometry.size.height * 0.28 - 80))
                    if let detail {
                        ScrollView {
                            VStack(spacing: 16) {
                                Text(poem.title).font(.custom("STSongti-SC-Regular", size: 25, relativeTo: .title2)).multilineTextAlignment(.center)
                                Text("唐 · \(poem.author)").font(.caption).foregroundStyle(.secondary).padding(.bottom, 4)
                                VStack(spacing: 10) {
                                    ForEach(detail.rubyLines.indices, id: \.self) { index in
                                        RubyLine(tokens: detail.rubyLines[index], pinyin: store.settings.pinyin, size: store.settings.fontSize)
                                    }
                                }
                            }.frame(maxWidth: .infinity).padding(.vertical, 6).padding(.bottom, 20)
                        }.onTapGesture(perform: toggleControls)
                        if store.settings.notes && !detail.note.isEmpty {
                            Button { showNotes = true } label: {
                                VStack(alignment: .leading, spacing: 8) {
                                    Divider()
                                    HStack { Text(detail.noteTitle).font(.caption.weight(.medium)); Spacer(); Text("展开").font(.caption2) }
                                    Text(detail.note).font(.caption).lineSpacing(4).lineLimit(2).foregroundStyle(.secondary)
                                }.padding(.top, 12).padding(.bottom, 12).frame(maxWidth: .infinity, alignment: .leading)
                            }.buttonStyle(.plain).accessibilityLabel("查看\(poem.title)的完整诗意和注释")
                        }
                    } else if failed {
                        VStack { Text("这一页暂时未能打开。"); Button("重试此页") { retry += 1 } }.frame(maxWidth: .infinity, maxHeight: .infinity)
                    } else { ProgressView("展卷中…").frame(maxWidth: .infinity, maxHeight: .infinity) }
                    Spacer().frame(height: 65)
                }.padding(.horizontal, 30)
            }
        }
        .task(id: "\(poem.id)-\(retry)") {
            failed = false
            do { detail = try await store.repository.detail(poem.id) } catch { failed = true }
        }
        .sheet(isPresented: $showNotes) {
            if let detail { NotesView(detail: detail) }
        }
    }
}

private struct RubyGroup {
    let token: RubyToken
    var punctuation = ""
}

struct RubyLine: View {
    let tokens: [RubyToken]
    let pinyin: Bool
    let size: Int
    @ScaledMetric(relativeTo: .title2) private var scaledBase: CGFloat = 22
    private var fontSize: CGFloat { scaledBase * CGFloat(size) / 22 }
    private var groups: [RubyGroup] {
        var result: [RubyGroup] = []
        for token in tokens {
            if token.pinyin.isEmpty && !result.isEmpty { result[result.count - 1].punctuation += token.text }
            else { result.append(RubyGroup(token: token)) }
        }
        return result
    }
    var body: some View {
        CenteredFlow(spacing: 3) {
            ForEach(Array(groups.enumerated()), id: \.offset) { _, group in
                HStack(alignment: .bottom, spacing: 0) {
                    VStack(spacing: 5) {
                        if pinyin { Text(group.token.pinyin).font(.system(size: max(10, fontSize * 0.43))).foregroundStyle(.secondary).fixedSize() }
                        Text(group.token.text).font(.custom("STSongti-SC-Regular", size: fontSize))
                    }.frame(minWidth: fontSize)
                    if !group.punctuation.isEmpty { Text(group.punctuation).font(.custom("STSongti-SC-Regular", size: fontSize)) }
                }
            }
        }.accessibilityElement(children: .ignore).accessibilityLabel(tokens.map(\.text).joined())
    }
}

struct CenteredFlow: Layout {
    var spacing: CGFloat
    private func rows(_ subviews: Subviews, width: CGFloat) -> [[Int]] {
        var result: [[Int]] = [], row: [Int] = [], used: CGFloat = 0
        for index in subviews.indices {
            let size = subviews[index].sizeThatFits(.unspecified)
            if !row.isEmpty && used + spacing + size.width > width { result.append(row); row = []; used = 0 }
            used += (row.isEmpty ? 0 : spacing) + size.width
            row.append(index)
        }
        if !row.isEmpty { result.append(row) }
        return result
    }
    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let width = proposal.width ?? 320
        let heights = rows(subviews, width: width).map { row in row.map { subviews[$0].sizeThatFits(.unspecified).height }.max() ?? 0 }
        return CGSize(width: width, height: heights.reduce(0, +) + CGFloat(max(0, heights.count - 1)) * 12)
    }
    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var y = bounds.minY
        for row in rows(subviews, width: bounds.width) {
            let sizes = row.map { subviews[$0].sizeThatFits(.unspecified) }
            let width = sizes.map(\.width).reduce(0, +) + CGFloat(max(0, row.count - 1)) * spacing
            let height = sizes.map(\.height).max() ?? 0
            var x = bounds.midX - width / 2
            for (offset, index) in row.enumerated() {
                subviews[index].place(at: CGPoint(x: x, y: y + height - sizes[offset].height), proposal: ProposedViewSize(sizes[offset]))
                x += sizes[offset].width + spacing
            }
            y += height + 12
        }
    }
}
