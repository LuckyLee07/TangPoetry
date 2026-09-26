import XCTest
import UIKit
@testable import TangPoetry

final class ArtworkTests: XCTestCase {
    private func image(width: Int, height: Int) -> UIImage {
        let format = UIGraphicsImageRendererFormat()
        format.scale = 1
        return UIGraphicsImageRenderer(size: CGSize(width: width, height: height), format: format).image { context in
            UIColor.black.setFill()
            context.fill(CGRect(x: 0, y: 0, width: width, height: height))
        }
    }

    func testCacheKeepsRecentlyUsedImagesWithinDecodedByteBudget() {
        let pixels = image(width: 100, height: 100)
        let cost = pixels.cgImage!.bytesPerRow * pixels.cgImage!.height
        let cache = ArtworkImageCache(byteLimit: cost * 2, countLimit: 10)
        let first = ArtworkRequest(path: "first", size: CGSize(width: 100, height: 100), scale: 1)
        let second = ArtworkRequest(path: "second", size: CGSize(width: 100, height: 100), scale: 1)
        let third = ArtworkRequest(path: "third", size: CGSize(width: 100, height: 100), scale: 1)
        cache.insert(pixels, for: first)
        cache.insert(pixels, for: second)
        XCTAssertNotNil(cache.image(for: first))
        cache.insert(pixels, for: third)
        XCTAssertNil(cache.image(for: second))
        XCTAssertNotNil(cache.image(for: first))
        XCTAssertNotNil(cache.image(for: third))
        XCTAssertLessThanOrEqual(cache.retainedBytes, cost * 2)
        cache.removeAll()
        XCTAssertEqual(cache.retainedBytes, 0)
    }

    func testCacheDoesNotRetainOneImageLargerThanItsBudget() {
        let cache = ArtworkImageCache(byteLimit: 10, countLimit: 1)
        let request = ArtworkRequest(path: "large", size: CGSize(width: 100, height: 100), scale: 1)
        cache.insert(image(width: 100, height: 100), for: request)
        XCTAssertNil(cache.image(for: request))
        XCTAssertEqual(cache.retainedBytes, 0)
    }

    func testThumbnailDecodeFitsDisplayWithoutDecodingTheWholePainting() throws {
        let url = try BundledContent.url("Art/song-yuan-er-page.jpg")
        let request = ArtworkRequest(path: "cover", size: CGSize(width: 48, height: 64), scale: 3)
        let thumbnail = try XCTUnwrap(ArtworkLoader.decode(url: url, request: request)?.cgImage)
        XCTAssertGreaterThanOrEqual(thumbnail.width, 191)
        XCTAssertGreaterThanOrEqual(thumbnail.height, request.pixelHeight)
        XCTAssertLessThan(thumbnail.width, 400)
        XCTAssertLessThan(thumbnail.height, 600)
    }
    /// Pipeline stress only: this measures awaited resource reads, not UI frame
    /// rate, resident process memory, or a physical-device performance budget.
    func testContinuousArtworkLoadingAcrossFiftyPoems() async throws {
        let catalog: PoemCatalog = try BundledContent.decode("catalog.json")
        let poems = Array(catalog.poems.prefix(50))
        XCTAssertEqual(poems.count, 50)
        XCTAssertEqual(Set(poems.map(\.image)).count, 50)
        let started = ProcessInfo.processInfo.systemUptime
        var requests = 0
        var repeatedRequests = 0
        var decodedPixels = 0
        var maximumRequestSeconds = 0.0

        for (index, poem) in poems.enumerated() {
            let request = ArtworkRequest(path: poem.image,
                                         size: CGSize(width: 390, height: 844), scale: 3)
            let requestStarted = ProcessInfo.processInfo.systemUptime
            let loaded = await ArtworkLoader.shared.image(for: request)
            maximumRequestSeconds = max(maximumRequestSeconds,
                                        ProcessInfo.processInfo.systemUptime - requestStarted)
            requests += 1
            let image = try XCTUnwrap(loaded, "Failed to decode \(poem.id)")
            let pixels = try XCTUnwrap(image.cgImage, "Missing decoded pixels: \(poem.id)")
            XCTAssertGreaterThan(pixels.width, 320, poem.id)
            XCTAssertGreaterThan(pixels.height, 568, poem.id)
            decodedPixels += pixels.width * pixels.height

            // Returning to the immediately preceding page should reuse its
            // decoded image rather than allocate another full-size bitmap.
            if [9, 24, 49].contains(index) {
                let repeated = await ArtworkLoader.shared.image(for: request)
                XCTAssertTrue(repeated === image, "Adjacent request did not reuse \(poem.id)")
                requests += 1
                repeatedRequests += 1
            }
        }

        let elapsed = ProcessInfo.processInfo.systemUptime - started
        let metrics: [String: Any] = [
            "kind": "artwork-loader-sequential-test",
            "distinctPaintings": poems.count,
            "requests": requests,
            "adjacentCacheRequests": repeatedRequests,
            "validatedDecodedPixels": decodedPixels,
            "elapsedSeconds": elapsed,
            "maximumAwaitedRequestSeconds": maximumRequestSeconds,
            "measurement": "resource pipeline only; not UI FPS or process peak memory"
        ]
        let data = try JSONSerialization.data(withJSONObject: metrics, options: [.sortedKeys])
        print("ARTWORK_PIPELINE_METRICS " + String(decoding: data, as: UTF8.self))
    }

}
