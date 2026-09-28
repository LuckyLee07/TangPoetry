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
    @Published private(set) var readIDs: Set<String>
    private var readingSnapshot: Set<String>?
    private var readSession = ReadingSession()
    private var readingActive = false
    private var endVisible: [String: Bool] = [:]
    @Published var selectedID: String { didSet {
        defaults.set(selectedID, forKey: "reader.position")
        if oldValue != selectedID { flushReadingProgress() }
    } }
    @Published var favorites: Set<String> { didSet {
        defaults.set(Array(favorites).sorted(), forKey: "reader.favorites")
        reconcileFavorites(previous: oldValue)
    } }
    @Published var settings: ReaderSettings { didSet { if let data = try? JSONEncoder().encode(settings) { defaults.set(data, forKey: "reader.settings") } } }
    @Published private(set) var readingScope: ReadingScope { didSet {
        if let data = try? JSONEncoder().encode(readingScope) { defaults.set(data, forKey: "reader.scope") }
    } }
    let repository = PoemRepository()
    private let defaults: UserDefaults
    private var bookmarks: [String: ReadingBookmark]
    private var progressSaveTask: Task<Void, Never>?
    private var progressIsDirty = false

    init(defaults: UserDefaults = .standard, autoload: Bool = true) {
        self.defaults = defaults
        readIDs = Set(defaults.stringArray(forKey: "reader.readIDs.v1") ?? [])
        readingSnapshot = defaults.stringArray(forKey: "reader.readingSnapshot").map(Set.init)
        selectedID = defaults.string(forKey: "reader.position") ?? ""
        favorites = Set(defaults.stringArray(forKey: "reader.favorites") ?? [])
        readingScope = defaults.data(forKey: "reader.scope")
            .flatMap { try? JSONDecoder().decode(ReadingScope.self, from: $0) } ?? .all
        bookmarks = defaults.data(forKey: "reader.bookmarks")
            .flatMap { try? JSONDecoder().decode([String: ReadingBookmark].self, from: $0) } ?? [:]
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
            readIDs.formIntersection(Set(poems.map(\.id)))
            if readingScope.readStatus != "all", readingSnapshot == nil {
                saveReadingSnapshot(Set(readingScope.poems(in: poems, favorites: favorites, readIDs: readIDs).map(\.id)))
            }
            if !poems.contains(where: { $0.id == selectedID }) { selectedID = poems[0].id }
            favorites.formIntersection(Set(poems.map(\.id)))
            if !readingPoems.contains(where: { $0.id == selectedID }) { readingScope = .all }
            bookmarks = bookmarks.filter { id, _ in poems.contains { $0.id == id } }
            loadError = nil
        } catch { loadError = error.localizedDescription }
    }

    var currentIndex: Int { poems.firstIndex { $0.id == selectedID } ?? 0 }
    var readingPoems: [PoemSummary] { scopedPoems(favorites: favorites) }
    private func scopedPoems(favorites: Set<String>) -> [PoemSummary] {
        if readingScope.readStatus != "all", let readingSnapshot {
            var base = readingScope
            base.readStatus = "all"
            return base.poems(in: poems, favorites: favorites).filter { readingSnapshot.contains($0.id) }
        }
        return readingScope.poems(in: poems, favorites: favorites, readIDs: readIDs)
    }

    private func saveReadingSnapshot(_ ids: Set<String>?) {
        readingSnapshot = ids
        if let ids { defaults.set(Array(ids).sorted(), forKey: "reader.readingSnapshot") }
        else { defaults.removeObject(forKey: "reader.readingSnapshot") }
    }
    var readingIndex: Int { readingPoems.firstIndex { $0.id == selectedID } ?? 0 }
    var readingScopeLabel: String { readingScope.label }

    func openReadingScope(_ scope: ReadingScope, selecting id: String) {
        let results = scope.poems(in: poems, favorites: favorites, readIDs: readIDs)
        guard results.contains(where: { $0.id == id }) else { openPoem(id); return }
        saveReadingSnapshot(scope.readStatus == "all" ? nil : Set(results.map(\.id)))
        readSession = ReadingSession()
        readingScope = scope
        selectedID = id
    }

    func openPoem(_ id: String, preservingScope: Bool = false) {
        guard poems.contains(where: { $0.id == id }) else { return }
        if !preservingScope || !readingPoems.contains(where: { $0.id == id }) { returnToLibraryScope() }
        selectedID = id
    }

    func returnToLibraryScope() { saveReadingSnapshot(nil); readingScope = .all }

    func turn(_ offset: Int) {
        let results = readingPoems
        let index = readingIndex + offset
        guard results.indices.contains(index) else { return }
        selectedID = results[index].id
    }
    func toggleFavorite(_ id: String) {
        if favorites.contains(id) { favorites.remove(id) } else { favorites.insert(id) }
    }

    private func reconcileFavorites(previous: Set<String>) {
        guard readingScope.collection == "favorites", !poems.isEmpty else { return }
        let results = readingPoems
        guard !results.contains(where: { $0.id == selectedID }) else { return }
        guard !results.isEmpty else { readingScope = .all; return }
        let previousResults = scopedPoems(favorites: previous)
        let oldIndex = previousResults.firstIndex { $0.id == selectedID } ?? 0
        selectedID = results[min(oldIndex, results.count - 1)].id
    }

    func setRead(_ id: String, _ value: Bool, manual: Bool = true) {
        guard poems.contains(where: { $0.id == id }) else { return }
        if manual { readSession.suppress(id) }
        if value { readIDs.insert(id) } else { readIDs.remove(id) }
        defaults.set(Array(readIDs).sorted(), forKey: "reader.readIDs.v1")
    }

    func beginReadingVisit() { readSession = ReadingSession() }
    func setReadingActive(_ active: Bool, now: Double = ProcessInfo.processInfo.systemUptime) {
        readingActive = active
        sampleReading(now: now)
    }
    func recordReadViewport(for id: String, endIsVisible: Bool) { endVisible[id] = endIsVisible }
    func clearReadViewport(for id: String) { endVisible.removeValue(forKey: id) }
    func sampleReading(now: Double = ProcessInfo.processInfo.systemUptime) {
        guard let poem = poems.first(where: { $0.id == selectedID }) else { return }
        let ready = endVisible[selectedID] != nil
        if readSession.sample(id: selectedID, section: poem.section, active: readingActive && ready && !readIDs.contains(selectedID),
                              endVisible: endVisible[selectedID] == true, now: now) {
            setRead(selectedID, true, manual: false)
        }
    }

    func readingBookmark(for id: String, lineCount: Int) -> ReadingBookmark {
        (bookmarks[id] ?? ReadingBookmark(lineIndex: nil)).validated(lineCount: lineCount)
    }

    func recordReadingBookmark(_ bookmark: ReadingBookmark, for id: String, lineCount: Int) {
        // Neighboring pages may be laid out by TabView; only the visible page may save.
        guard id == selectedID, poems.contains(where: { $0.id == id }) else { return }
        let bookmark = bookmark.validated(lineCount: lineCount)
        guard bookmarks[id] != bookmark else { return }
        bookmarks[id] = bookmark
        progressIsDirty = true
        progressSaveTask?.cancel()
        progressSaveTask = Task { [weak self] in
            try? await Task.sleep(for: .seconds(0.8))
            guard !Task.isCancelled else { return }
            self?.flushReadingProgress()
        }
    }

    func flushReadingProgress() {
        progressSaveTask?.cancel()
        progressSaveTask = nil
        guard progressIsDirty, let data = try? JSONEncoder().encode(bookmarks) else { return }
        defaults.set(data, forKey: "reader.bookmarks")
        progressIsDirty = false
    }
}
