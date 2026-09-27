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
    let thumbnailFrame: ThumbnailFrame?
    let artworkMode: String?
    let artworkFocusY: Double?
    let searchText: String
}

/// A directory-specific square viewport; all coordinates use source-image width.
struct ThumbnailFrame: Decodable, Sendable {
    let x: Double
    let y: Double
    let side: Double
    let aspect: Double
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

struct PoemAnnotation: Decodable, Sendable {
    let text: String
    let source: String
    var sourceName: String {
        switch source {
        case "ctext": "中国哲学书电子化计划"
        case "chiuinan": "唐诗选本附注"
        case "唐诗三百首.json": "基础选本"
        default: source
        }
    }
}

struct PoemDetail: Decodable, Sendable {
    let id: String
    let title: String
    let author: String
    let sourceTitle: String
    let rubyLines: [[RubyToken]]
    let noteTitle: String
    let note: String
    let notes: [String]
    let interpretation: [String]
    let annotations: [PoemAnnotation]
    let variants: [PoemAnnotation]
    let preface: [String]
    var text: String { rubyLines.flatMap { $0 }.map(\.text).joined() }
}

struct ReaderSettings: Codable, Equatable {
    // Keep the stored key compatible with earlier versions; pronunciation is paused in the reader.
    var pinyin = false
    var notes = true
    var fontSize = 22
    var paper = "warm"

    func validated() -> Self {
        var copy = self
        copy.pinyin = false
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

    static func matches(_ poem: PoemSummary, query: String, category: String, collection: String, favorites: Set<String>, author: String = "all", readStatus: String = "all", readIDs: Set<String> = []) -> Bool {
        (readStatus != "read" || readIDs.contains(poem.id)) &&
        (readStatus != "unread" || !readIDs.contains(poem.id)) &&
        (collection != "featured" || poem.featured) &&
        (collection != "favorites" || favorites.contains(poem.id)) &&
        (category == "all" || category == poem.theme || category == poem.section) &&
        (author == "all" || author == poem.author) &&
        (query.isEmpty || normalize(poem.searchText).contains(normalize(query)))
    }
}

/// A live catalogue selection, rather than a frozen list of poem IDs.
/// Favorites therefore remain accurate when a reader adds or removes a bookmark.
struct ReadingScope: Codable, Equatable {
    var collection = "all"
    var category = "all"
    var author = "all"
    var query = ""
    var readStatus = "all"

    static let all = ReadingScope()
    var isAll: Bool { self == .all }
    var label: String {
        var parts: [String] = []
        if collection == "favorites" { parts.append("我的收藏") }
        if collection == "featured" { parts.append("推荐") }
        if readStatus == "read" { parts.append("已读") }
        if readStatus == "unread" { parts.append("未读") }
        if category != "all" { parts.append(category) }
        if author != "all" { parts.append(author) }
        if !query.isEmpty { parts.append("搜索：\(query)") }
        return parts.isEmpty ? "全库" : parts.joined(separator: " · ")
    }

    func poems(in catalog: [PoemSummary], favorites: Set<String>, readIDs: Set<String> = []) -> [PoemSummary] {
        catalog.filter {
            PoemFilter.matches($0, query: query, category: category,
                               collection: collection, favorites: favorites, author: author, readStatus: readStatus, readIDs: readIDs)
        }
    }
}

// Existing saved filters have no readStatus field; keep their other selections.
extension ReadingScope {
    private enum CodingKeys: String, CodingKey { case collection, category, author, query, readStatus }
    init(from decoder: Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        collection = try values.decodeIfPresent(String.self, forKey: .collection) ?? "all"
        category = try values.decodeIfPresent(String.self, forKey: .category) ?? "all"
        author = try values.decodeIfPresent(String.self, forKey: .author) ?? "all"
        query = try values.decodeIfPresent(String.self, forKey: .query) ?? ""
        let savedStatus = try values.decodeIfPresent(String.self, forKey: .readStatus) ?? "all"
        readStatus = ["all", "read", "unread"].contains(savedStatus) ? savedStatus : "all"
    }
}

/// An index into the canonical verse lines survives font and screen-size changes.
/// A nil line means the beginning, including the title and author.
struct ReadingBookmark: Codable, Equatable {
    var lineIndex: Int?

    func validated(lineCount: Int) -> Self {
        guard let lineIndex, lineCount > 0 else { return Self(lineIndex: nil) }
        return Self(lineIndex: min(max(0, lineIndex), lineCount - 1))
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
