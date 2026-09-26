import SwiftUI

struct LibraryView: View {
    @EnvironmentObject private var store: PoemStore
    @Environment(\.dismiss) private var dismiss
    @State private var query = ""
    @State private var category = "all"
    @State private var author = "all"
    @State var collection: String
    let select: (String, ReadingScope) -> Void

    private var scope: ReadingScope { ReadingScope(collection: collection, category: category, author: author, query: query) }
    private var results: [PoemSummary] {
        scope.poems(in: store.poems, favorites: store.favorites)
    }
    private var authors: [String] { Array(Set(store.poems.map(\.author))).sorted { $0.localizedStandardCompare($1) == .orderedAscending } }
    private var sections: [String] {
        var seen = Set<String>()
        return store.poems.map(\.section).filter { seen.insert($0).inserted }
    }
    private var groupedResults: [(section: String, poems: [PoemSummary])] {
        let groups = Dictionary(grouping: results, by: \.section)
        return sections.compactMap { section in
            guard let poems = groups[section] else { return nil }
            return (section, poems)
        }
    }
    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                Picker("诗集范围", selection: $collection) {
                    Text("全部").tag("all"); Text("精选").tag("featured"); Text("收藏").tag("favorites")
                }.pickerStyle(.segmented).padding(.horizontal).padding(.top, 8)
                ViewThatFits(in: .horizontal) {
                    HStack { resultCount; Spacer(); categoryPicker; authorPicker }
                    VStack(alignment: .leading, spacing: 4) { resultCount; categoryPicker; authorPicker }
                }.padding(.horizontal)
                if results.isEmpty {
                    ContentUnavailableView(collection == "favorites" && store.favorites.isEmpty ? "还没有收藏" : "没有找到相符的诗", systemImage: "book", description: Text("试试其他诗句或分类；在诗页轻点「藏」，留给下次重读。"))
                } else {
                    List {
                        ForEach(groupedResults, id: \.section) { group in
                            Section(group.section) {
                                ForEach(group.poems) { poem in
                                    Button { select(poem.id, scope) } label: {
                                        HStack(spacing: 14) {
                                            Artwork(path: poem.thumbnail).frame(width: 48, height: 64).clipped().clipShape(RoundedRectangle(cornerRadius: 4))
                                            VStack(alignment: .leading, spacing: 6) {
                                                Text(poem.title).font(.custom("STSongti-SC-Regular", size: 18, relativeTo: .headline)).foregroundStyle(.primary)
                                                Text(poem.author).font(.caption).foregroundStyle(.secondary)
                                            }
                                            Spacer(minLength: 0)
                                            if store.favorites.contains(poem.id) { Image(systemName: "bookmark.fill").accessibilityLabel("已收藏") }
                                            else if poem.featured { Text("精选").font(.caption2).foregroundStyle(.secondary) }
                                        }.padding(.vertical, 3)
                                    }.listRowBackground(store.settings.paperColor)
                                    .swipeActions { Button(store.favorites.contains(poem.id) ? "取消收藏" : "收藏") { store.toggleFavorite(poem.id) }.tint(.brown) }
                                }
                            }
                        }
                    }.listStyle(.plain).scrollContentBackground(.hidden)
                }
            }
            .background(store.settings.paperColor)
            .navigationTitle("诗笺目录").navigationBarTitleDisplayMode(.inline)
            .searchable(text: $query, placement: .navigationBarDrawer(displayMode: .always), prompt: "诗名、作者，或记得的一句")
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button("完成") { dismiss() } } }
        }.presentationDragIndicator(.visible)
    }

    private var resultCount: some View {
        Text("\(results.count) 首").font(.caption).foregroundStyle(.secondary)
            .accessibilityLabel("当前筛选共 \(results.count) 首")
    }

    private var categoryPicker: some View {
        Picker("分类", selection: $category) {
            Text("全部分类").tag("all")
            Section("体裁") { ForEach(sections, id: \.self) { Text($0).tag($0) } }
            Section("主题") { ForEach(Array(Set(store.poems.map(\.theme))).sorted(), id: \.self) { Text($0).tag($0) } }
        }.pickerStyle(.menu)
    }

    private var authorPicker: some View {
        Picker("作者", selection: $author) {
            Text("全部作者").tag("all")
            ForEach(authors, id: \.self) { name in
                Text("\(name) · \(store.poems.filter { $0.author == name }.count) 首").tag(name)
            }
        }.pickerStyle(.menu)
    }
}

struct SettingsView: View {
    @EnvironmentObject private var store: PoemStore
    @Environment(\.dismiss) private var dismiss
    let openFavorites: () -> Void
    let sharePoem: () -> Void
    var body: some View {
        NavigationStack {
            Form {
                Section("阅读") {
                    Toggle("显示简注", isOn: $store.settings.notes)
                    Picker("诗文字号", selection: $store.settings.fontSize) {
                        Text("小").tag(20); Text("标准").tag(22); Text("大").tag(26); Text("特大").tag(30)
                    }
                    Picker("界面纸色", selection: $store.settings.paper) {
                        Text("暖纸").tag("warm"); Text("素白").tag("ivory"); Text("青笺").tag("sage")
                    }
                }
                Section {
                    Button("保存或分享当前诗笺", action: sharePoem)
                    Button("我的收藏 · \(store.favorites.count) 首", action: openFavorites)
                }
                GentleMotionSetting()
                Section("关于唐诗画笺") {
                    Text("一页一诗，一诗一画。")
                    Text("所有诗词与插画均内置，可离线阅读。收藏、设置与阅读位置仅保存在当前设备，无需账号，无广告、无统计追踪。")
                    Text("诗文按体裁分卷，同一体裁内保留选本顺序，部分题名使用常用别名。诗文与简注持续校订。版本 0.5.0")
                }.font(.footnote).foregroundStyle(.secondary)
            }.scrollContentBackground(.hidden).background(store.settings.paperColor)
            .navigationTitle("阅读设置").navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button("完成") { dismiss() } } }
        }.presentationDragIndicator(.visible)
    }
}

struct NotesView: View {
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var store: PoemStore
    let detail: PoemDetail
    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 28) {
                    NotesSection(title: "诗意", paragraphs: detail.interpretation)
                    NotesSection(title: "字词解释", paragraphs: detail.annotations.map(\.text))
                    if !detail.variants.isEmpty {
                        VStack(alignment: .leading, spacing: 12) {
                            Text("异文").font(.headline).accessibilityAddTraits(.isHeader)
                            Text("以下为选本原有校记，保留不同说法。")
                                .font(.caption).foregroundStyle(.secondary)
                            ForEach(Array(detail.variants.enumerated()), id: \.offset) { _, variant in
                                VStack(alignment: .leading, spacing: 5) {
                                    Text(variant.text).font(.body).lineSpacing(6).textSelection(.enabled)
                                    Text("来源：\(variant.sourceName)").font(.caption).foregroundStyle(.secondary)
                                }
                            }
                        }
                    }
                    NotesSection(title: "题序", paragraphs: detail.preface.isEmpty ? [] : [detail.preface.joined()])
                    NotesSection(title: "原题", paragraphs: detail.sourceTitle == detail.title ? [] : [detail.sourceTitle])
                }.frame(maxWidth: .infinity, alignment: .leading).padding(24)
            }.background(store.settings.paperColor)
            .navigationTitle(detail.title).navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button("完成") { dismiss() } } }
        }
        .presentationDetents([.fraction(0.58)])
        .presentationContentInteraction(.scrolls)
        .presentationDragIndicator(.visible)
    }
}

private struct NotesSection: View {
    let title: String
    let paragraphs: [String]

    var body: some View {
        if !paragraphs.isEmpty {
            VStack(alignment: .leading, spacing: 12) {
                Text(title).font(.headline).accessibilityAddTraits(.isHeader)
                ForEach(Array(paragraphs.enumerated()), id: \.offset) { _, paragraph in
                    Text(paragraph).font(.body).lineSpacing(6).textSelection(.enabled)
                }
            }.frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}
