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

    @MainActor func testNarrationActuallyPlaysPausesAndReplays() async throws {
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

    @MainActor func testOpeningListeningAutoplaysButDismissalAndManualPauseCancelThePendingStart() async throws {
        let catalog: PoemCatalog = try BundledContent.decode("catalog.json")
        let player = NarrationPlayer()
        defer { player.stop() }
        player.load(catalog.poems[0])
        player.playAfterPresentation(delay: .milliseconds(60))
        XCTAssertFalse(player.isPlaying)
        try await Task.sleep(for: .milliseconds(180))
        XCTAssertTrue(player.isPlaying)
        player.seek(to: 3)
        player.playAfterPresentation(delay: .milliseconds(60))
        try await Task.sleep(for: .milliseconds(180))
        XCTAssertGreaterThanOrEqual(player.elapsed, 3, "Reopening must not restart active playback")
        player.pause()
        player.playAfterPresentation(delay: .milliseconds(60))
        player.cancelPendingPlayback() // Sheet dismissed or app backgrounded.
        try await Task.sleep(for: .milliseconds(180))
        XCTAssertFalse(player.isPlaying)
        player.playAfterPresentation(delay: .milliseconds(60))
        player.pause()
        try await Task.sleep(for: .milliseconds(180))
        XCTAssertFalse(player.isPlaying)
        player.playAfterPresentation(delay: .milliseconds(60))
        player.load(catalog.poems[1])
        try await Task.sleep(for: .milliseconds(180))
        XCTAssertFalse(player.isPlaying, "A stale request cannot start the newly selected poem")
    }

    @MainActor func testReadingIdleResetsAndWaitsForEverySuspensionToEnd() async throws {
        let controls = ReaderControls(delay: .milliseconds(100))
        controls.interacted()
        try await Task.sleep(for: .milliseconds(60))
        controls.interacted()
        try await Task.sleep(for: .milliseconds(60))
        XCTAssertTrue(controls.isVisible)
        controls.setSuspended("touch", true)
        controls.setSuspended("sheet", true)
        controls.setSuspended("touch", false)
        try await Task.sleep(for: .milliseconds(150))
        XCTAssertTrue(controls.isVisible)
        controls.setSuspended("sheet", false)
        try await Task.sleep(for: .milliseconds(150))
        XCTAssertFalse(controls.isVisible)
        controls.interacted() // Page turns and compact playback must preserve hidden chrome.
        controls.setSuspended("touch", true)
        controls.setSuspended("touch", false)
        try await Task.sleep(for: .milliseconds(150))
        XCTAssertFalse(controls.isVisible)
        controls.interacted(reveal: true)
        controls.setSuspended("voiceOver", true)
        try await Task.sleep(for: .milliseconds(150))
        XCTAssertTrue(controls.isVisible)
        controls.toggle() // Manual visibility remains available even with auto-hide disabled.
        XCTAssertFalse(controls.isVisible)
        controls.interacted(reveal: true)
        XCTAssertTrue(controls.isVisible)
    }

    @MainActor func testCompactListeningSharesPlaybackAndResumesWithoutResettingPosition() throws {
        let catalog: PoemCatalog = try BundledContent.decode("catalog.json")
        let player = NarrationPlayer()
        defer { player.stop() }
        let first = catalog.poems[0], next = catalog.poems[1]
        player.toggle(first)
        XCTAssertTrue(player.isPlaying)
        XCTAssertEqual(player.track?.id, first.id)
        player.seek(to: 5)
        player.toggle(first)
        XCTAssertFalse(player.isPlaying)
        XCTAssertEqual(player.elapsed, 5, accuracy: 0.1)
        player.toggle(first)
        XCTAssertTrue(player.isPlaying)
        XCTAssertEqual(player.elapsed, 5, accuracy: 0.1)
        player.toggle(next)
        XCTAssertEqual(player.track?.id, next.id)
        XCTAssertTrue(player.isPlaying)
        XCTAssertLessThan(player.elapsed, 0.1)
        player.seek(to: player.duration)
        player.pause()
        player.toggle(next)
        XCTAssertTrue(player.isPlaying)
        XCTAssertLessThan(player.elapsed, 0.1)
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

    @MainActor func testFullLibraryTracksAreDecodableAndMatchTheirPoems() throws {
        let catalog: PoemCatalog = try BundledContent.decode("catalog.json")
        let manifest: NarrationManifest = try BundledContent.decode("Audio/manifest.json")
        XCTAssertEqual(manifest.recipe.voiceLabel, "晓晓 · 诗歌朗读")
        XCTAssertEqual(manifest.tracks.count, catalog.poems.count)
        XCTAssertEqual(Set(manifest.tracks.keys), Set(catalog.poems.map(\.id)))
        XCTAssertEqual(manifest.trackOrder, catalog.poems.map(\.id))
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
        let longPoem = try XCTUnwrap(catalog.poems.first { $0.title == "长恨歌" })
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
        player.load(longPoem)
        XCTAssertEqual(player.track?.id, longPoem.id)
        XCTAssertNil(player.error)
        XCTAssertFalse(player.isPlaying)
        XCTAssertGreaterThan(player.duration, 180)
        XCTAssertEqual(player.elapsed, 0)
        XCTAssertEqual(player.availableTracks.map(\.id), catalog.poems.map(\.id))
        player.stop()
    }
}
