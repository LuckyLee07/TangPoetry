import SwiftUI

private enum PoemScrollAnchor: Hashable {
    case heading
    case line(Int)
}

private struct VerseFramePreferenceKey: PreferenceKey {
    static var defaultValue: [PoemScrollAnchor: CGRect] = [:]
    static func reduce(value: inout [PoemScrollAnchor: CGRect], nextValue: () -> [PoemScrollAnchor: CGRect]) {
        value.merge(nextValue(), uniquingKeysWith: { _, new in new })
    }
}

private struct ReadingRestorationKey: Equatable {
    let poemID: String
    let fontSize: CGFloat
    let width: CGFloat
}

/// Scroll restoration is tied to a verse, so changing the phone or type size does
/// not restore an unrelated pixel offset. Measurements never write defaults.
struct ResumablePoemText: View {
    @EnvironmentObject private var store: PoemStore
    let poem: PoemSummary
    let detail: PoemDetail
    let layout: PoemLayout
    let width: CGFloat
    let viewportHeight: CGFloat
    let showsNote: Bool
    let openNotes: () -> Void
    let toggleControls: () -> Void
    let readingActivity: () -> Void
    @State private var restoredKey: ReadingRestorationKey?
    @State private var measuredFrames: [PoemScrollAnchor: CGRect] = [:]

    private var coordinateSpace: String { "poem-scroll-\(poem.id)" }
    private var restorationKey: ReadingRestorationKey {
        ReadingRestorationKey(poemID: poem.id, fontSize: layout.fontSize, width: width)
    }

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                VStack(spacing: layout.bodySpacing) {
                    VStack(spacing: layout.headerSpacing) {
                        Text(poem.title).font(.custom("STSongti-SC-Regular", fixedSize: layout.titleSize))
                            .multilineTextAlignment(.center).fixedSize(horizontal: false, vertical: true)
                            .contentShape(Rectangle()).onTapGesture(perform: toggleControls)
                            .accessibilityAddTraits(.isHeader)
                        Text("\(poem.dynasty ?? "唐") · \(poem.author)").font(.system(size: layout.authorSize)).foregroundStyle(.secondary)
                            .contentShape(Rectangle()).onTapGesture(perform: toggleControls)
                    }
                    .id(PoemScrollAnchor.heading)
                    .background(frameReader(.heading))
                    VStack(spacing: layout.lineSpacing) {
                        ForEach(detail.rubyLines.indices, id: \.self) { index in
                            VerseLine(tokens: detail.rubyLines[index], fontSize: layout.fontSize)
                                .id(PoemScrollAnchor.line(index))
                                .background(frameReader(.line(index)))
                                .contentShape(Rectangle()).onTapGesture(perform: toggleControls)
                                .accessibilityElement(children: .ignore)
                                .accessibilityLabel(detail.rubyLines[index].map(\.text).joined())
                        }
                    }
                    // Keep every verse as a separate accessible element. A named,
                    // tappable parent can collapse the lines into one AX node.
                    if !detail.note.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                        Button(action: openNotes) {
                            VStack(alignment: .leading, spacing: 8) {
                                Divider()
                                HStack { Text(detail.noteTitle).font(.caption.weight(.medium)); Spacer(); Text("展开").font(.caption2) }
                                Text(detail.note).font(.caption).lineSpacing(4).lineLimit(2).foregroundStyle(.secondary)
                            }.padding(.top, layout.noteTopPadding).padding(.bottom, 12).frame(maxWidth: .infinity, alignment: .leading)
                                .fixedSize(horizontal: false, vertical: true)
                        }.buttonStyle(.plain)
                            .opacity(showsNote ? 1 : 0)
                            .allowsHitTesting(showsNote)
                            .accessibilityHidden(!showsNote)
                            .accessibilityLabel("查看\(poem.title)的完整诗意和注释")
                            .accessibilityValue(detail.note)
                    }
                }.frame(maxWidth: .infinity).padding(.bottom, 20)
                    .background(PoemScrollDirectionLock().allowsHitTesting(false))
            }
            .scrollBounceBehavior(.basedOnSize, axes: .vertical)
            .coordinateSpace(name: coordinateSpace)
            .onPreferenceChange(VerseFramePreferenceKey.self) { frames in
                measuredFrames = frames
                recordViewport(frames)
                // New font/width measurements can arrive before the new task starts.
                // Never let those measurements overwrite the verse awaiting restoration.
                guard restoredKey == restorationKey, !frames.isEmpty else { return }
                if store.selectedID == poem.id { readingActivity() }
                let line: Int?
                if let heading = frames[.heading], heading.maxY > 0 {
                    line = nil
                } else {
                    line = detail.rubyLines.indices.first { (frames[.line($0)]?.maxY ?? -.infinity) > 0 }
                        ?? detail.rubyLines.indices.last
                }
                store.recordReadingBookmark(ReadingBookmark(lineIndex: line), for: poem.id, lineCount: detail.rubyLines.count)
            }
            .onAppear {
                // Cached pages can reappear with identical geometry, so no new
                // preference callback is guaranteed after onDisappear cleared it.
                recordViewport(measuredFrames)
            }
            .task(id: restorationKey) {
                let key = restorationKey
                restoredKey = nil
                let bookmark = store.readingBookmark(for: poem.id, lineCount: detail.rubyLines.count)
                // Let the newly measured rows enter the scroll view before resolving their IDs.
                await Task.yield()
                guard !Task.isCancelled else { return }
                proxy.scrollTo(bookmark.lineIndex.map(PoemScrollAnchor.line) ?? .heading, anchor: .top)
                await Task.yield()
                guard !Task.isCancelled else { return }
                restoredKey = key
            }
            .onDisappear {
                store.clearReadViewport(for: poem.id)
                restoredKey = nil
                store.flushReadingProgress()
            }
        }
    }

    private func recordViewport(_ frames: [PoemScrollAnchor: CGRect]) {
        if let index = detail.rubyLines.indices.last, let last = frames[.line(index)] {
            store.recordReadViewport(for: poem.id, endIsVisible: last.maxY > 0 && last.maxY <= viewportHeight + 2)
        }
    }

    private func frameReader(_ anchor: PoemScrollAnchor) -> some View {
        GeometryReader { geometry in
            Color.clear.preference(key: VerseFramePreferenceKey.self,
                                   value: [anchor: geometry.frame(in: .named(coordinateSpace))])
        }
    }
}
