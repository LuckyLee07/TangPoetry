import SwiftUI
import UIKit

/// The vertical scroll waits for this horizontal-only recognizer to fail.
/// This leaves UIKit/SwiftUI's scroll delegates intact and lets the page turn
/// track the same horizontal gesture without waking the vertical scroll bar.
struct PoemScrollDirectionLock: UIViewRepresentable {
    func makeUIView(context: Context) -> Marker {
        let marker = Marker()
        marker.isUserInteractionEnabled = false
        marker.accessibilityElementsHidden = true
        return marker
    }
    func updateUIView(_ uiView: Marker, context: Context) { uiView.attach() }
    static func dismantleUIView(_ uiView: Marker, coordinator: ()) { uiView.detach() }

    final class Marker: UIView {
        weak var scrollView: UIScrollView?
        private(set) var blocker: HorizontalScrollBlocker?

        override func didMoveToWindow() {
            super.didMoveToWindow()
            if window == nil { detach() } else { attach() }
        }

        override func didMoveToSuperview() { super.didMoveToSuperview(); attach() }
        override func layoutSubviews() { super.layoutSubviews(); attach() }

        func attach() {
            guard window != nil else { return }
            var ancestor = superview
            while let view = ancestor, !(view is UIScrollView) { ancestor = view.superview }
            guard let scroll = ancestor as? UIScrollView, scroll !== scrollView else { return }
            detach()
            let blocker = HorizontalScrollBlocker()
            scroll.addGestureRecognizer(blocker)
            scroll.panGestureRecognizer.require(toFail: blocker)
            scroll.isDirectionalLockEnabled = true
            scroll.showsHorizontalScrollIndicator = false
            scrollView = scroll
            self.blocker = blocker
        }

        func detach() {
            if let blocker { scrollView?.removeGestureRecognizer(blocker) }
            blocker = nil
            scrollView = nil
        }
    }
}

class HorizontalScrollBlocker: UIPanGestureRecognizer, UIGestureRecognizerDelegate {
    init() {
        super.init(target: nil, action: nil)
        delegate = self
        cancelsTouchesInView = false
        delaysTouchesBegan = false
        delaysTouchesEnded = false
        maximumNumberOfTouches = 1
    }

    func gestureRecognizerShouldBegin(_ gestureRecognizer: UIGestureRecognizer) -> Bool {
        let speed = velocity(in: view)
        return abs(speed.x) > abs(speed.y) * 1.15
    }

    // A direction probe must never stop a page curl, slide, tap, or VoiceOver.
    override func canPrevent(_ preventedGestureRecognizer: UIGestureRecognizer) -> Bool { false }
    override func canBePrevented(by preventingGestureRecognizer: UIGestureRecognizer) -> Bool { false }
}
