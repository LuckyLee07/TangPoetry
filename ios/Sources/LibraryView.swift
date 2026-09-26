import SwiftUI

struct LibraryView: View {
    @EnvironmentObject private var store: PoemStore
    @Environment(\.dismiss) private var dismiss
    @State private var query = ""
    @State private var category = "all"
    @State var collection: String
    let select: (String) -> Void

    private var results: [PoemSummary] {
        store.poems.filter { PoemFilter.matches($0, query: query, category: category, collection: collection, favorites: store.favorites) }
    }
    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                Picker("诗集范围", selection: $collection) {
                    Text("全部").tag("all"); Text("精选").tag("featured"); Text("收藏").tag("favorites")
                }.pickerStyle(.segmented).padding(.horizontal).padding(.top, 8)
                HStack {
                    Text("\(results.count) 首").font(.caption).foregroundStyle(.secondary)
                    Spacer()
                    Picker("分类", selection: $category) {
                        Text("全部分类").tag("all")
                        Section("主题") { ForEach(Array(Set(store.poems.map(\.theme))).sorted(), id: \.self) { Text($0).tag($0) } }
                        Section("体裁") { ForEach(Array(Set(store.poems.map(\.section))).sorted(), id: \.self) { Text($0).tag($0) } }
                    }.pickerStyle(.menu)
                }.padding(.horizontal)
                if results.isEmpty {
                    ContentUnavailableView(collection == "favorites" && store.favorites.isEmpty ? "还没有收藏" : "没有找到相符的诗", systemImage: "book", description: Text("试试其他诗句或分类；在诗页轻点「藏」，留给下次重读。"))
                } else {
                    List(results) { poem in
                        Button { select(poem.id) } label: {
                            HStack(spacing: 14) {
                                Artwork(path: poem.thumbnail).frame(width: 48, height: 64).clipped().clipShape(RoundedRectangle(cornerRadius: 4))
                                VStack(alignment: .leading, spacing: 6) {
                                    Text(poem.title).font(.custom("STSongti-SC-Regular", size: 18, relativeTo: .headline)).foregroundStyle(.primary)
                                    Text("\(poem.order). \(poem.author) · \(poem.section)").font(.caption).foregroundStyle(.secondary)
                                }
                                Spacer(minLength: 0)
                                if store.favorites.contains(poem.id) { Image(systemName: "bookmark.fill").accessibilityLabel("已收藏") }
                                else if poem.featured { Text("精选").font(.caption2).foregroundStyle(.secondary) }
                            }.padding(.vertical, 3)
                        }.listRowBackground(store.settings.paperColor)
                        .swipeActions { Button(store.favorites.contains(poem.id) ? "取消收藏" : "收藏") { store.toggleFavorite(poem.id) }.tint(.brown) }
                    }.listStyle(.plain).scrollContentBackground(.hidden)
                }
            }
            .background(store.settings.paperColor)
            .navigationTitle("诗笺目录").navigationBarTitleDisplayMode(.inline)
            .searchable(text: $query, placement: .navigationBarDrawer(displayMode: .always), prompt: "诗名、作者，或记得的一句")
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button("完成") { dismiss() } } }
        }.presentationDragIndicator(.visible)
    }
}

struct SettingsView: View {
    @EnvironmentObject private var store: PoemStore
    @Environment(\.dismiss) private var dismiss
    let openFavorites: () -> Void
    var body: some View {
        NavigationStack {
            Form {
                Section("阅读") {
                    Toggle("显示简注", isOn: $store.settings.notes)
                    Picker("诗文字号", selection: $store.settings.fontSize) {
                        Text("小").tag(20); Text("标准").tag(22); Text("大").tag(26); Text("特大").tag(30)
                    }
                    Picker("纸色", selection: $store.settings.paper) {
                        Text("暖纸").tag("warm"); Text("素白").tag("ivory"); Text("青笺").tag("sage")
                    }
                }
                Section { Button("我的收藏 · \(store.favorites.count) 首", action: openFavorites) }
                Section("关于唐诗画笺") {
                    Text("一页一诗，一诗一画。")
                    Text("所有诗词与插画均内置，可离线阅读。收藏、设置与阅读位置仅保存在当前设备，无需账号，无广告、无统计追踪。")
                    Text("诗文按选本书序整理，部分题名使用常用别名。诗文与简注持续校订。版本 0.2")
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
                VStack(alignment: .leading, spacing: 20) {
                    Text(detail.noteTitle).font(.title3)
                    Text(detail.note).lineSpacing(6)
                    ForEach(Array(detail.notes.enumerated()), id: \.offset) { _, note in Text(note).font(.body).lineSpacing(5) }
                }.frame(maxWidth: .infinity, alignment: .leading).padding(24)
            }.background(store.settings.paperColor)
            .navigationTitle(detail.title).navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button("完成") { dismiss() } } }
        }.presentationDragIndicator(.visible)
    }
}
