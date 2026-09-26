import SwiftUI

actor PoemRepository {
    private var cache: [String: PoemDetail] = [:]
    private var recency: [String] = []

    func detail(_ id: String) throws -> PoemDetail {
        recency.removeAll { $0 == id }
        if let poem = cache[id] { recency.append(id); return poem }
        let poem: PoemDetail = try BundledContent.decode("poems/\(id).json")
        cache[id] = poem
        recency.append(id)
        while recency.count > 12 { cache.removeValue(forKey: recency.removeFirst()) }
        return poem
    }
}

@MainActor
final class PoemStore: ObservableObject {
    @Published private(set) var poems: [PoemSummary] = []
    @Published var loadError: String?
    @Published var selectedID: String { didSet { defaults.set(selectedID, forKey: "reader.position") } }
    @Published var favorites: Set<String> { didSet { defaults.set(Array(favorites).sorted(), forKey: "reader.favorites") } }
    @Published var settings: ReaderSettings { didSet { if let data = try? JSONEncoder().encode(settings) { defaults.set(data, forKey: "reader.settings") } } }
    let repository = PoemRepository()
    private let defaults: UserDefaults

    init(defaults: UserDefaults = .standard, autoload: Bool = true) {
        self.defaults = defaults
        selectedID = defaults.string(forKey: "reader.position") ?? ""
        favorites = Set(defaults.stringArray(forKey: "reader.favorites") ?? [])
        if let data = defaults.data(forKey: "reader.settings"), let saved = try? JSONDecoder().decode(ReaderSettings.self, from: data) {
            settings = saved.validated()
        } else { settings = ReaderSettings() }
        if autoload { load() }
    }

    func load() {
        do {
            let catalog: PoemCatalog = try BundledContent.decode("catalog.json")
            guard !catalog.poems.isEmpty else { throw ContentError.missingResource("catalog.json") }
            poems = catalog.poems
            if !poems.contains(where: { $0.id == selectedID }) { selectedID = poems[0].id }
            favorites.formIntersection(Set(poems.map(\.id)))
            loadError = nil
        } catch { loadError = error.localizedDescription }
    }

    var currentIndex: Int { poems.firstIndex { $0.id == selectedID } ?? 0 }
    func turn(_ offset: Int) {
        let index = currentIndex + offset
        guard poems.indices.contains(index) else { return }
        selectedID = poems[index].id
    }
    func toggleFavorite(_ id: String) {
        if favorites.contains(id) { favorites.remove(id) } else { favorites.insert(id) }
    }
}
