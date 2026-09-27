import SwiftUI
import UIKit

/// Idle time is measured only while reading. Any new interaction invalidates the old deadline.
@MainActor final class ReaderControls: ObservableObject {
    @Published private(set) var isVisible = true
    private var blockers: Set<String> = []
    private var pendingHide: Task<Void, Never>?
    private let delay: Duration

    init(delay: Duration = .seconds(6)) { self.delay = delay }
    deinit { pendingHide?.cancel() }

    func setSuspended(_ reason: String, _ suspended: Bool) {
        if suspended { blockers.insert(reason) } else { blockers.remove(reason) }
        interacted()
    }

    func interacted(reveal: Bool = false) {
        pendingHide?.cancel()
        pendingHide = nil
        if reveal { isVisible = true }
        guard isVisible, blockers.isEmpty else { return }
        pendingHide = Task { [weak self, delay] in
            do { try await Task.sleep(for: delay) } catch { return }
            guard let self, !Task.isCancelled, self.blockers.isEmpty else { return }
            self.isVisible = false
            self.pendingHide = nil
        }
    }

    func toggle() {
        isVisible.toggle()
        interacted()
    }
}

/// Observe touches without recognizing a competing pan/tap or cancelling UIKit's page curl.
struct ReaderTouchObserver: UIViewRepresentable {
    let changed: (Bool) -> Void
    func makeUIView(context: Context) -> ObserverView { ObserverView(changed: changed) }
    func updateUIView(_ uiView: ObserverView, context: Context) { uiView.observer.changed = changed }
    static func dismantleUIView(_ uiView: ObserverView, coordinator: ()) { uiView.detach() }

    final class ObserverView: UIView {
        let observer: TouchObserver
        weak var observedWindow: UIWindow?
        init(changed: @escaping (Bool) -> Void) {
            observer = TouchObserver()
            observer.changed = changed
            super.init(frame: .zero)
            isUserInteractionEnabled = false
        }
        required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }
        override func didMoveToWindow() {
            super.didMoveToWindow()
            guard observedWindow !== window else { return }
            detach()
            window?.addGestureRecognizer(observer)
            observedWindow = window
        }
        func detach() {
            observedWindow?.removeGestureRecognizer(observer)
            observedWindow = nil
        }
    }

    final class TouchObserver: UIGestureRecognizer {
        var changed: (Bool) -> Void = { _ in }
        private var touches = Set<UITouch>()
        init() {
            super.init(target: nil, action: nil)
            cancelsTouchesInView = false
            delaysTouchesBegan = false
            delaysTouchesEnded = false
        }
        override func canPrevent(_ preventedGestureRecognizer: UIGestureRecognizer) -> Bool { false }
        override func canBePrevented(by preventingGestureRecognizer: UIGestureRecognizer) -> Bool { false }
        override func touchesBegan(_ touches: Set<UITouch>, with event: UIEvent) {
            self.touches.formUnion(touches)
            changed(true)
        }
        override func touchesEnded(_ touches: Set<UITouch>, with event: UIEvent) { finish(touches) }
        override func touchesCancelled(_ touches: Set<UITouch>, with event: UIEvent) { finish(touches) }
        private func finish(_ ended: Set<UITouch>) {
            touches.subtract(ended)
            if touches.isEmpty { changed(false); state = .failed }
        }
        override func reset() {
            super.reset()
            if !touches.isEmpty { touches.removeAll(); changed(false) }
        }
    }
}
