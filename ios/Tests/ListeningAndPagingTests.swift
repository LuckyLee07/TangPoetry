import XCTest
import SwiftUI
import AVFoundation
@testable import TangPoetry

final class ListeningAndPagingTests: XCTestCase {
    @MainActor func testCurlDeclinesVerticalPansWithoutOverridingUIKitRules() {
        final class Pan: UIPanGestureRecognizer {
            var speed = CGPoint.zero
            override func velocity(in view: UIView?) -> CGPoint { speed }
        }
        final class Rules: NSObject, UIGestureRecognizerDelegate {
            var allow = true
            func gestureRecognizerShouldBegin(_ gestureRecognizer: UIGestureRecognizer) -> Bool { allow }
        }
        let rules = Rules()
        let gate = HorizontalPageGesture(original: rules)
        let pan = Pan()
        pan.speed = CGPoint(x: 10, y: -500)
        XCTAssertFalse(gate.gestureRecognizerShouldBegin(pan))
        pan.speed = CGPoint(x: -500, y: 10)
        XCTAssertTrue(gate.gestureRecognizerShouldBegin(pan))
        rules.allow = false
        XCTAssertFalse(gate.gestureRecognizerShouldBegin(pan))
    }

    @MainActor func testPreviewActuallyPlaysPausesAndReplays() async throws {
        let catalog: PoemCatalog = try BundledContent.decode("catalog.json")
        let poem = try XCTUnwrap(catalog.poems.first { $0.title == "静夜思" })
        let player = NarrationPlayer()
        defer { player.stop() }
        player.load(poem)
        player.play()
        try await Task.sleep(for: .seconds(1.2))
        XCTAssertNil(player.error)
        XCTAssertTrue(player.isPlaying)
        XCTAssertGreaterThan(player.elapsed, 0)
        player.pause()
        XCTAssertFalse(player.isPlaying)
        let pausedAt = player.elapsed
        try await Task.sleep(for: .seconds(0.3))
        XCTAssertEqual(player.elapsed, pausedAt, accuracy: 0.01)
        player.seek(to: player.duration)
        player.play()
        XCTAssertLessThan(player.elapsed, 0.5)
        XCTAssertTrue(player.isPlaying)
    }

    @MainActor func testCancelledCurlDoesNotSaveDestinationAndExternalSelectionWins() throws {
        let catalog: PoemCatalog = try BundledContent.decode("catalog.json")
        let poems = Array(catalog.poems.prefix(4))
        var selected = poems[0].id
        let binding = Binding(get: { selected }, set: { selected = $0 })
        let parent = PoemPager(poems: poems, selectedID: binding, style: .curl, paperColor: .white) { _ in AnyView(Color.white) }
        let coordinator = PoemPager.Coordinator(parent)
        let pager = UIPageViewController(transitionStyle: .pageCurl, navigationOrientation: .horizontal)
        coordinator.pager = pager
        coordinator.reconcile(animated: false)
        let first = try XCTUnwrap(pager.viewControllers?.first)
        let second = try XCTUnwrap(coordinator.pageViewController(pager, viewControllerAfter: first))
        XCTAssertNil(coordinator.pageViewController(pager, viewControllerBefore: first))

        coordinator.pageViewController(pager, willTransitionTo: [second])
        coordinator.pageViewController(pager, didFinishAnimating: true, previousViewControllers: [first], transitionCompleted: false)
        XCTAssertEqual(selected, poems[0].id)

        coordinator.pageViewController(pager, willTransitionTo: [second])
        pager.setViewControllers([second], direction: .forward, animated: false)
        coordinator.pageViewController(pager, didFinishAnimating: true, previousViewControllers: [first], transitionCompleted: true)
        XCTAssertEqual(selected, poems[1].id)

        let third = try XCTUnwrap(coordinator.pageViewController(pager, viewControllerAfter: second))
        coordinator.pageViewController(pager, willTransitionTo: [third])
        selected = poems[3].id // A directory selection arrives during the gesture.
        pager.setViewControllers([third], direction: .forward, animated: false)
        coordinator.pageViewController(pager, didFinishAnimating: true, previousViewControllers: [second], transitionCompleted: true)
        XCTAssertEqual(selected, poems[3].id)
        XCTAssertEqual((pager.viewControllers?.first as? PoemPager.Page)?.poemID, poems[3].id)
        XCTAssertNil(coordinator.pageViewController(pager, viewControllerAfter: try XCTUnwrap(pager.viewControllers?.first)))
    }

    @MainActor func testFivePreviewTracksAreDecodableAndMatchTheirPoems() throws {
        let catalog: PoemCatalog = try BundledContent.decode("catalog.json")
        let manifest: NarrationManifest = try BundledContent.decode("Audio/manifest.json")
        XCTAssertEqual(manifest.tracks.count, 5)
        XCTAssertEqual(Set(manifest.tracks.values.map(\.title)), Set(["鹿柴", "春晓", "静夜思", "登鹳雀楼", "枫桥夜泊"]))
        for (id, track) in manifest.tracks {
            let poem = try XCTUnwrap(catalog.poems.first { $0.id == id })
            XCTAssertEqual(track.id, id)
            XCTAssertEqual(track.title, poem.title)
            XCTAssertEqual(track.author, poem.author)
            let audio = try AVAudioPlayer(contentsOf: BundledContent.url(track.file))
            XCTAssertTrue(audio.prepareToPlay())
            XCTAssertEqual(audio.duration, track.duration, accuracy: 0.15)
        }
    }

    @MainActor func testSeekingAndChangingPoemCannotReuseThePreviousAudio() throws {
        let catalog: PoemCatalog = try BundledContent.decode("catalog.json")
        let player = NarrationPlayer()
        let first = try XCTUnwrap(catalog.poems.first { $0.title == "静夜思" })
        let second = try XCTUnwrap(catalog.poems.first { $0.title == "鹿柴" })
        let unavailable = try XCTUnwrap(catalog.poems.first { $0.title == "长恨歌" })
        player.load(first)
        XCTAssertEqual(player.track?.id, first.id)
        XCTAssertFalse(player.isPlaying)
        player.seek(to: -100)
        XCTAssertEqual(player.elapsed, 0)
        player.seek(to: 1_000_000)
        XCTAssertEqual(player.elapsed, player.duration)
        player.seek(to: .nan)
        XCTAssertTrue(player.elapsed.isFinite)
        player.load(second)
        XCTAssertEqual(player.elapsed, 0)
        XCTAssertEqual(player.track?.id, second.id)
        player.load(unavailable)
        XCTAssertNil(player.track)
        XCTAssertNil(player.error) // Unselected poems show the preview chooser, not a fake failure.
        XCTAssertFalse(player.isPlaying)
        XCTAssertEqual(player.duration, 0)
        XCTAssertEqual(player.previewTracks.count, 5)
        player.stop()
    }
}
