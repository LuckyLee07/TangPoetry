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

private enum ReaderSheet: String, Identifiable {
    case library, settings, share, narration
    var id: String { rawValue }
}

struct ReaderView: View {
    @EnvironmentObject private var store: PoemStore
    @Environment(\.scenePhase) private var scenePhase
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @AppStorage("reader.pageTurnStyle") private var pageTurnStyle = PageTurnStyle.curl.rawValue
    @StateObject private var narration = NarrationPlayer()
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
                LibraryView(collection: collection) { id, scope in
                    store.openReadingScope(scope, selecting: id)
                    home = false
                    controls = true
                    sheet = nil
                }
            case .settings:
                SettingsView(openFavorites: {
                    collection = "favorites"
                    sheet = .library
                }, sharePoem: { sheet = .share })
            case .share:
                if let poem = store.poems.first(where: { $0.id == store.selectedID }) {
                    PoemCardView(poem: poem)
                }
            case .narration:
                NarrationView(player: narration)
            }
        }
        .onChange(of: scenePhase) { _, phase in
            if phase != .active { store.flushReadingProgress() }
        }
        .onChange(of: home) { _, isHome in
            if isHome { store.flushReadingProgress() }
        }
        .onChange(of: store.selectedID) { _, id in
            if narration.track?.id != id { narration.stop() }
        }
    }

    private var cover: some View {
        GeometryReader { geometry in
            Group {
                if dynamicTypeSize.isAccessibilitySize || (geometry.size.height < 650 && dynamicTypeSize >= .xxLarge) {
                    ScrollView {
                        VStack(spacing: 24) {
                            Text("唐诗三百首").font(.custom("STSongti-SC-Regular", size: 32, relativeTo: .largeTitle))
                                .multilineTextAlignment(.center).accessibilityAddTraits(.isHeader)
                            DailyPoemButton(poems: store.poems, open: openDailyPoem)
                            Text("\(store.poems.count) 首 · 一页一诗，一诗一画").font(.caption)
                            VStack(spacing: 16) { coverButtons }.controlSize(.large).buttonBorderShape(.capsule)
                        }.frame(maxWidth: .infinity).padding(28)
                    }
                } else {
            ZStack(alignment: .topTrailing) {
                VStack(alignment: .trailing, spacing: 16) {
                    Text(dynamicTypeSize.isAccessibilitySize ? "唐诗三百首" : "唐\n诗\n三\n百\n首")
                        .font(.custom("STSongti-SC-Regular", size: 40, relativeTo: .largeTitle)).lineSpacing(4)
                        .accessibilityLabel("唐诗三百首").accessibilityAddTraits(.isHeader)
                    Text("诗").font(.title3).padding(8).background(Color(red: 0.63, green: 0.23, blue: 0.15), in: RoundedRectangle(cornerRadius: 5)).foregroundStyle(.white)
                }.padding(.top, 42).padding(.trailing, 42)
                VStack(spacing: 20) {
                    Spacer()
                    DailyPoemButton(poems: store.poems, open: openDailyPoem)
                    Text("孙洙选本 · 一页一诗，一诗一画").font(.caption).foregroundStyle(.secondary)
                    Text("\(store.poems.count) 首 · \(store.poems.filter(\.dedicatedArt).count) 幅画笺").font(.caption)
                    ViewThatFits(in: .horizontal) {
                        HStack(spacing: 12) { coverButtons }
                        VStack(spacing: 12) { coverButtons }
                    }.controlSize(.large).buttonBorderShape(.capsule)
                }.padding(.horizontal, 24).padding(.bottom, 34)
            }
                }
            }
            .frame(width: geometry.size.width, height: geometry.size.height)
            .background {
                GeometryReader { canvas in
                    ZStack {
                        Artwork(path: "Art/song-yuan-er-page.jpg")
                        LinearGradient(colors: [.clear, store.settings.paperColor], startPoint: .center, endPoint: .bottom)
                    }.frame(width: canvas.size.width, height: canvas.size.height).clipped()
                }.ignoresSafeArea(.container)
            }
        }
    }

    private func openDailyPoem(_ id: String) {
        store.openPoem(id)
        home = false
        controls = true
    }

    @ViewBuilder private var coverButtons: some View {
        Button(store.currentIndex == 0 ? "入卷" : "续读") { home = false }.buttonStyle(.borderedProminent)
        Button("目录") { collection = "all"; sheet = .library }.buttonStyle(.bordered)
        Button("精选") { collection = "featured"; sheet = .library }.buttonStyle(.bordered)
    }

    private var reader: some View {
        // Keep the original safe reading area for typography and controls, while
        // the paging container itself fills the screen so its artwork is not clipped.
        GeometryReader { readingArea in
            ZStack {
                let style = reduceMotion ? PageTurnStyle.instant : (PageTurnStyle(rawValue: pageTurnStyle) ?? .curl)
                PoemPager(poems: store.readingPoems, selectedID: $store.selectedID,
                          style: style, paperColor: UIColor(store.settings.paperColor),
                          contentRevision: "\(readingArea.size)-\(readingArea.safeAreaInsets)-\(sheet == nil)") { poem in
                    AnyView(PoemPageView(poem: poem, readingSize: readingArea.size,
                                        readingInsets: readingArea.safeAreaInsets, motionActive: sheet == nil) { controls.toggle() }
                        .environmentObject(store)
                        .foregroundStyle(Color(red: 0.19, green: 0.17, blue: 0.14)))
                }.id(style).ignoresSafeArea(.container)
                if controls {
                    VStack {
                        HStack(spacing: 10) {
                            tool("卷", label: "返回封面") { home = true }
                            Spacer()
                            tool("目录", label: "目录") { collection = "all"; sheet = .library }
                            tool("Aa", label: "阅读设置") { sheet = .settings }
                            tool(store.favorites.contains(store.selectedID) ? "已藏" : "藏", label: store.favorites.contains(store.selectedID) ? "取消收藏此诗" : "收藏此诗") { store.toggleFavorite(store.selectedID) }
                        }
                        if !store.readingScope.isAll {
                            Menu {
                                Button("回到全库", action: store.returnToLibraryScope)
                            } label: {
                                HStack(spacing: 6) {
                                    Text(store.readingScopeLabel).lineLimit(1)
                                    Image(systemName: "chevron.down")
                                }.font(.system(size: 12)).padding(.horizontal, 12).frame(minHeight: 44)
                                    .background(store.settings.paperColor.opacity(0.94), in: Capsule())
                            }
                            .accessibilityLabel("阅读范围：\(store.readingScopeLabel)，共 \(store.readingPoems.count) 首")
                            .accessibilityHint("双击可回到全库")
                        }
                        Spacer()
                        ZStack {
                            HStack(spacing: 2) {
                                Button { store.turn(-1) } label: { Image(systemName: "chevron.left").font(.system(size: 17)).frame(width: 44, height: 44) }.disabled(store.readingIndex == 0).accessibilityLabel("上一首")
                                Text("\(store.readingIndex + 1) / \(store.readingPoems.count)").font(.system(size: 11)).monospacedDigit().fixedSize()
                                    .accessibilityLabel("\(store.readingScopeLabel)，第 \(store.readingIndex + 1) 首，共 \(store.readingPoems.count) 首")
                                Button { store.turn(1) } label: { Image(systemName: "chevron.right").font(.system(size: 17)).frame(width: 44, height: 44) }.disabled(store.readingIndex == store.readingPoems.count - 1).accessibilityLabel("下一首")
                            }
                            HStack {
                                tool(narration.isPlaying ? "听着" : narration.hasAudio(for: store.selectedID) ? "听诗" : "试听",
                                     label: narration.isPlaying ? "打开朗读播放器，正在播放" : narration.hasAudio(for: store.selectedID) ? "朗读这首诗" : "朗读试听，五首诗") {
                                    if let poem = store.poems.first(where: { $0.id == store.selectedID }) {
                                        narration.load(poem)
                                        sheet = .narration
                                    }
                                }
                                Spacer()
                                tool("简注", label: store.settings.notes ? "隐藏简注" : "显示简注") { store.settings.notes.toggle() }
                            }
                        }
                    }.padding(.horizontal, 22).padding(.vertical, 10)
                } else {
                    VStack { Spacer(); tool("···", label: "显示阅读工具") { controls = true } }.padding(.bottom, 10)
                }
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
    let readingSize: CGSize
    let readingInsets: EdgeInsets
    let motionActive: Bool
    let toggleControls: () -> Void
    @State private var detail: PoemDetail?
    @State private var failed = false
    @State private var retry = 0
    @State private var showNotes = false
    @ScaledMetric(relativeTo: .title2) private var scaledBase: CGFloat = 22

    var body: some View {
        GeometryReader { geometry in
            let hasNote = store.settings.notes && !(detail?.note.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ?? true)
            let layout = PoemLayout.resolve(
                section: poem.section, lines: detail?.rubyLines.map { $0.map(\.text).joined() } ?? [],
                title: poem.title, author: poem.author, size: readingSize,
                fontSetting: store.settings.fontSize, dynamicScale: scaledBase / 22,
                textStart: poem.textStart.map { CGFloat($0) }, showsNote: hasNote
            )
            ZStack(alignment: .topLeading) {
                Artwork(path: poem.image).frame(width: geometry.size.width, height: geometry.size.height).clipped()
                    .contentShape(Rectangle()).onTapGesture(perform: toggleControls)
                GentleArtworkMotion(poemID: poem.id, active: motionActive && !showNotes && store.selectedID == poem.id)
                ZStack(alignment: .top) {
                    Text(poem.section).font(.caption2).foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity, alignment: .leading).padding(.top, 68).padding(.horizontal, layout.horizontalPadding)
                        .allowsHitTesting(false)
                    VStack(spacing: 0) {
                        if let detail {
                            ResumablePoemText(poem: poem, detail: detail, layout: layout,
                                              width: readingSize.width, showsNote: hasNote,
                                              openNotes: { showNotes = true }, toggleControls: toggleControls)
                        } else if failed {
                            VStack { Text("这一页暂时未能打开。"); Button("重试此页") { retry += 1 } }.frame(maxWidth: .infinity, maxHeight: .infinity)
                        } else { ProgressView("展卷中…").frame(maxWidth: .infinity, maxHeight: .infinity) }
                    }
                    .frame(height: max(0, readingSize.height - layout.contentTop - 65), alignment: .top)
                    .clipped()
                    .padding(.top, layout.contentTop).padding(.horizontal, layout.horizontalPadding)
                }
                .frame(width: readingSize.width, height: readingSize.height, alignment: .top)
                .offset(x: readingInsets.leading, y: readingInsets.top)
            }
        }.ignoresSafeArea(.container)
        .task(id: "\(poem.id)-\(retry)") {
            failed = false
            do { detail = try await store.repository.detail(poem.id) } catch { failed = true }
        }
        .sheet(isPresented: $showNotes) {
            if let detail { NotesView(detail: detail) }
        }
    }
}

private struct VerseGlyph {
    let text: String
    var punctuation = ""
}

struct VerseLine: View {
    let tokens: [RubyToken]
    let fontSize: CGFloat
    private var cellWidth: CGFloat { fontSize * 1.18 }
    private var glyphs: [VerseGlyph] {
        let characters = tokens.flatMap { Array($0.text) }
        let isPunctuation: (Character) -> Bool = { character in
            character.unicodeScalars.allSatisfy { CharacterSet.punctuationCharacters.contains($0) }
        }
        let lastTextIndex = characters.lastIndex { !isPunctuation($0) } ?? -1
        var result: [VerseGlyph] = []
        for (index, character) in characters.enumerated() {
            if index > lastTextIndex && !result.isEmpty {
                result[result.count - 1].punctuation.append(character)
            } else {
                result.append(VerseGlyph(text: String(character)))
            }
        }
        return result
    }

    var body: some View {
        let glyphs = self.glyphs
        // Punctuation hangs outside the character grid, so all five- or seven-character
        // lines share the same columns regardless of their final punctuation.
        VerseGrid(cellWidth: cellWidth, hangingWidth: CGFloat(glyphs.map { $0.punctuation.count }.max() ?? 0) * fontSize, rowSpacing: fontSize * 0.35) {
            ForEach(Array(glyphs.enumerated()), id: \.offset) { _, glyph in
                Text(glyph.text)
                    .font(.custom("STSongti-SC-Regular", fixedSize: fontSize))
                    .fixedSize()
                    .frame(width: cellWidth, height: fontSize * 1.45)
                    .overlay(alignment: .leading) {
                        if !glyph.punctuation.isEmpty {
                            Text(glyph.punctuation)
                                .font(.custom("STSongti-SC-Regular", fixedSize: fontSize))
                                .fixedSize()
                                .offset(x: cellWidth)
                        }
                    }
            }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(tokens.map(\.text).joined())
    }
}

struct VerseGrid: Layout {
    let cellWidth: CGFloat
    let hangingWidth: CGFloat
    let rowSpacing: CGFloat

    private func columns(for width: CGFloat, count: Int) -> Int {
        min(max(1, count), max(1, Int((max(0, width - hangingWidth * 2) / cellWidth).rounded(.down))))
    }

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let width = proposal.width ?? CGFloat(subviews.count) * cellWidth + hangingWidth * 2
        guard !subviews.isEmpty else { return CGSize(width: width, height: 0) }
        let columns = columns(for: width, count: subviews.count)
        let rowCount = (subviews.count + columns - 1) / columns
        let cellHeight = subviews.map { $0.sizeThatFits(.unspecified).height }.max() ?? 0
        return CGSize(width: width, height: CGFloat(rowCount) * cellHeight + CGFloat(rowCount - 1) * rowSpacing)
    }

    static func rowOrigin(width: CGFloat, count: Int, cellWidth: CGFloat, hangingWidth: CGFloat) -> CGFloat {
        // At the largest accessibility sizes even a single centered glyph may
        // leave too little room for its punctuation. Shift only that overflow.
        max(0, min((width - CGFloat(count) * cellWidth) / 2,
                   width - CGFloat(count) * cellWidth - hangingWidth))
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        guard !subviews.isEmpty else { return }
        let columns = columns(for: bounds.width, count: subviews.count)
        let cellHeight = subviews.map { $0.sizeThatFits(.unspecified).height }.max() ?? 0
        for start in stride(from: 0, to: subviews.count, by: columns) {
            let count = min(columns, subviews.count - start)
            let x = bounds.minX + Self.rowOrigin(width: bounds.width, count: count,
                                                 cellWidth: cellWidth, hangingWidth: hangingWidth)
            let y = bounds.minY + CGFloat(start / columns) * (cellHeight + rowSpacing)
            for offset in 0..<count {
                subviews[start + offset].place(
                    at: CGPoint(x: x + CGFloat(offset) * cellWidth, y: y),
                    proposal: ProposedViewSize(width: cellWidth, height: cellHeight)
                )
            }
        }
    }
}
