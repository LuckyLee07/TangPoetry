import Foundation

struct PoemCatalog: Decodable, Sendable {
    let schemaVersion: Int
    let poems: [PoemSummary]
}

struct PoemSummary: Decodable, Identifiable, Sendable {
    let id: String
    let order: Int
    let title: String
    let aliases: [String]
    let author: String
    let section: String
    let theme: String
    let featured: Bool
    let dedicatedArt: Bool
    let image: String
    let thumbnail: String
    let searchText: String
}

struct RubyToken: Decodable, Sendable {
    let text: String
    let pinyin: String
    init(from decoder: Decoder) throws {
        var values = try decoder.unkeyedContainer()
        text = try values.decode(String.self)
        pinyin = try values.decode(String.self)
    }
}

struct PoemDetail: Decodable, Sendable {
    let id: String
    let title: String
    let author: String
    let rubyLines: [[RubyToken]]
    let noteTitle: String
    let note: String
    let notes: [String]
    var text: String { rubyLines.flatMap { $0 }.map(\.text).joined() }
}

struct ReaderSettings: Codable, Equatable {
    var pinyin = true
    var notes = true
    var fontSize = 22
    var paper = "warm"

    func validated() -> Self {
        var copy = self
        if ![20, 22, 26, 30].contains(copy.fontSize) { copy.fontSize = 22 }
        if !["warm", "ivory", "sage"].contains(copy.paper) { copy.paper = "warm" }
        return copy
    }
}

enum PoemFilter {
    static func normalize(_ value: String) -> String {
        value.precomposedStringWithCompatibilityMapping.lowercased()
            .components(separatedBy: .whitespacesAndNewlines.union(CharacterSet(charactersIn: "，。！？；、,.!?;·"))).joined()
    }

    static func matches(_ poem: PoemSummary, query: String, category: String, collection: String, favorites: Set<String>) -> Bool {
        (collection != "featured" || poem.featured) &&
        (collection != "favorites" || favorites.contains(poem.id)) &&
        (category == "all" || category == poem.theme || category == poem.section) &&
        (query.isEmpty || normalize(poem.searchText).contains(normalize(query)))
    }
}

enum ContentError: Error, LocalizedError {
    case missingResource(String)
    var errorDescription: String? { "诗库资源未能打开，请重试。" }
}

enum BundledContent {
    static func url(_ path: String) throws -> URL {
        guard let root = Bundle.main.resourceURL else { throw ContentError.missingResource(path) }
        let url = root.appendingPathComponent("Content").appendingPathComponent(path)
        guard FileManager.default.fileExists(atPath: url.path) else { throw ContentError.missingResource(path) }
        return url
    }
    static func decode<T: Decodable>(_ path: String) throws -> T {
        try JSONDecoder().decode(T.self, from: Data(contentsOf: url(path)))
    }
}
