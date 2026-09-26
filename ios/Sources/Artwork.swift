import SwiftUI
import UIKit
import ImageIO

/// Display dimensions are rounded up to reduce duplicate cache entries during layout.
struct ArtworkRequest: Hashable, Sendable {
    let path: String
    let pixelWidth: Int
    let pixelHeight: Int

    init(path: String, size: CGSize, scale: CGFloat) {
        self.path = path
        func pixels(_ value: CGFloat) -> Int {
            guard value.isFinite, scale.isFinite else { return 64 }
            let scaled = min(4096, max(0, value) * max(1, scale))
            return min(4096, max(64, Int(ceil(scaled / 64)) * 64))
        }
        pixelWidth = pixels(size.width)
        pixelHeight = pixels(size.height)
    }
}

/// A strict decoded-byte and item-count budget; active SwiftUI images are separate.
final class ArtworkImageCache: @unchecked Sendable {
    private struct Entry {
        let image: UIImage
        let cost: Int
        var access: UInt64
    }
    private let lock = NSLock()
    private let byteLimit: Int
    private let countLimit: Int
    private var entries: [ArtworkRequest: Entry] = [:]
    private var byteCount = 0
    private var clock: UInt64 = 0

    init(byteLimit: Int = 32 * 1024 * 1024, countLimit: Int = 24) {
        self.byteLimit = byteLimit
        self.countLimit = countLimit
    }

    func image(for request: ArtworkRequest) -> UIImage? {
        lock.lock()
        defer { lock.unlock() }
        guard var entry = entries[request] else { return nil }
        clock &+= 1
        entry.access = clock
        entries[request] = entry
        return entry.image
    }

    func insert(_ image: UIImage, for request: ArtworkRequest) {
        guard let pixels = image.cgImage else { return }
        let cost = pixels.bytesPerRow * pixels.height
        lock.lock()
        defer { lock.unlock() }
        if let old = entries.removeValue(forKey: request) { byteCount -= old.cost }
        guard cost <= byteLimit, countLimit > 0 else { return }
        while byteCount + cost > byteLimit || entries.count >= countLimit {
            guard let oldest = entries.min(by: { $0.value.access < $1.value.access }) else { break }
            byteCount -= oldest.value.cost
            entries.removeValue(forKey: oldest.key)
        }
        clock &+= 1
        entries[request] = Entry(image: image, cost: cost, access: clock)
        byteCount += cost
    }

    func removeAll() {
        lock.lock()
        defer { lock.unlock() }
        entries.removeAll()
        byteCount = 0
    }

    var retainedBytes: Int {
        lock.lock()
        defer { lock.unlock() }
        return byteCount
    }
}

/// File I/O and immediate ImageIO decoding happen on at most two background workers.
final class ArtworkLoader: @unchecked Sendable {
    static let shared = ArtworkLoader()
    private let cache = ArtworkImageCache()
    private let queue: OperationQueue = {
        let queue = OperationQueue()
        queue.name = "com.tangpoetry.artwork"
        queue.qualityOfService = .userInitiated
        queue.maxConcurrentOperationCount = 2
        return queue
    }()
    private var memoryObserver: NSObjectProtocol?

    private init() {
        memoryObserver = NotificationCenter.default.addObserver(
            forName: UIApplication.didReceiveMemoryWarningNotification, object: nil, queue: nil
        ) { [weak self] _ in self?.cache.removeAll() }
    }

    deinit {
        if let memoryObserver { NotificationCenter.default.removeObserver(memoryObserver) }
    }

    func image(for request: ArtworkRequest) async -> UIImage? {
        if let cached = cache.image(for: request) { return cached }
        return await withCheckedContinuation { continuation in
            queue.addOperation { [self] in
                // A preceding operation may already have filled this entry.
                if let cached = cache.image(for: request) {
                    continuation.resume(returning: cached)
                    return
                }
                let image: UIImage? = autoreleasepool {
                    guard let url = try? BundledContent.url(request.path) else { return nil }
                    return Self.decode(url: url, request: request)
                }
                if let image { cache.insert(image, for: request) }
                continuation.resume(returning: image)
            }
        }
    }

    static func decode(url: URL, request: ArtworkRequest) -> UIImage? {
        let options = [kCGImageSourceShouldCache: false] as CFDictionary
        guard let source = CGImageSourceCreateWithURL(url as CFURL, options),
              let properties = CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [CFString: Any],
              let width = properties[kCGImagePropertyPixelWidth] as? CGFloat,
              let height = properties[kCGImagePropertyPixelHeight] as? CGFloat,
              width > 0, height > 0 else { return nil }
        // Aspect-fill needs enough pixels along both axes, including wide covers.
        let factor = min(1, max(CGFloat(request.pixelWidth) / width, CGFloat(request.pixelHeight) / height))
        let maximum = max(1, Int(ceil(max(width, height) * factor)))
        let thumbnailOptions: [CFString: Any] = [
            kCGImageSourceCreateThumbnailFromImageAlways: true,
            kCGImageSourceCreateThumbnailWithTransform: true,
            kCGImageSourceShouldCacheImmediately: true,
            kCGImageSourceThumbnailMaxPixelSize: maximum
        ]
        guard let image = CGImageSourceCreateThumbnailAtIndex(source, 0, thumbnailOptions as CFDictionary) else { return nil }
        return UIImage(cgImage: image)
    }
}

struct Artwork: View {
    let path: String
    @Environment(\.displayScale) private var displayScale
    @State private var loaded: (request: ArtworkRequest, image: UIImage)?

    var body: some View {
        GeometryReader { geometry in
            let request = ArtworkRequest(path: path, size: geometry.size, scale: displayScale)
            Group {
                if let loaded, loaded.request.path == path {
                    Image(uiImage: loaded.image).resizable().scaledToFill()
                } else {
                    Color.clear
                }
            }
            .frame(width: geometry.size.width, height: geometry.size.height)
            .task(id: request) {
                let image = await ArtworkLoader.shared.image(for: request)
                guard !Task.isCancelled else { return }
                loaded = image.map { (request, $0) }
            }
        }
        .accessibilityHidden(true)
    }
}
