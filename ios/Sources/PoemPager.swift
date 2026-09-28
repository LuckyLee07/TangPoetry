import SwiftUI
import UIKit

enum PageTurnStyle: String, CaseIterable, Identifiable {
    case curl, slide, instant
    var id: String { rawValue }
    var title: String {
        switch self { case .curl: "纸页卷动"; case .slide: "轻柔平移"; case .instant: "无动画" }
    }
}

/// UIKit owns the finger-tracking curl, reverse gesture and cancelled transition.
/// SwiftUI continues to own poem layout and reading progress.
struct PoemPager: UIViewControllerRepresentable {
    let poems: [PoemSummary]
    @Binding var selectedID: String
    let style: PageTurnStyle
    let paperColor: UIColor
    var contentRevision = ""
    let content: (PoemSummary) -> AnyView

    func makeCoordinator() -> Coordinator { Coordinator(self) }

    func makeUIViewController(context: Context) -> UIPageViewController {
        let pager = UIPageViewController(transitionStyle: style == .curl ? .pageCurl : .scroll,
                                        navigationOrientation: .horizontal,
                                        options: [.spineLocation: UIPageViewController.SpineLocation.min.rawValue])
        pager.isDoubleSided = false
        pager.dataSource = context.coordinator
        pager.delegate = context.coordinator
        pager.view.backgroundColor = paperColor
        context.coordinator.pager = pager
        context.coordinator.reconcile(animated: false)
        // Keep UIKit's recognizer group intact: its pan depends on its tap
        // recognizer. Disabling the tap also prevents interactive page curls.
        if style == .curl {
            for pan in pager.gestureRecognizers.compactMap({ $0 as? UIPanGestureRecognizer }) {
                let gate = HorizontalPageGesture(original: pan.delegate)
                context.coordinator.gestureGates.append(gate)
                pan.delegate = gate
                pan.cancelsTouchesInView = false
            }
        }
        if style == .instant {
            pager.dataSource = nil
            for scroll in pager.view.subviews.compactMap({ $0 as? UIScrollView }) {
                scroll.isScrollEnabled = false
            }
            let swipeLeft = UISwipeGestureRecognizer(target: context.coordinator, action: #selector(Coordinator.swipe(_:)))
            swipeLeft.direction = .left
            let swipeRight = UISwipeGestureRecognizer(target: context.coordinator, action: #selector(Coordinator.swipe(_:)))
            swipeRight.direction = .right
            pager.view.addGestureRecognizer(swipeLeft)
            pager.view.addGestureRecognizer(swipeRight)
        }
        return pager
    }

    func updateUIViewController(_ pager: UIPageViewController, context: Context) {
        let coordinator = context.coordinator
        let needsRefresh = coordinator.parent.contentRevision != contentRevision || !coordinator.parent.paperColor.isEqual(paperColor)
        coordinator.parent = self
        pager.view.backgroundColor = paperColor
        // Do not replace a page's render tree while UIKit is curling its surface.
        if !coordinator.transitioning {
            if needsRefresh { coordinator.refreshContent() }
            coordinator.reconcile(animated: style != .instant)
        }
    }

    static func dismantleUIViewController(_ pager: UIPageViewController, coordinator: Coordinator) {
        coordinator.active = false
        pager.delegate = nil
        pager.dataSource = nil
    }

    @MainActor final class Page: UIHostingController<AnyView> {
        let poemID: String
        init(poem: PoemSummary, root: AnyView, paper: UIColor) {
            poemID = poem.id
            super.init(rootView: root)
            safeAreaRegions = []
            view.backgroundColor = paper
            view.isOpaque = true
        }
        @available(*, unavailable) required init?(coder: NSCoder) { fatalError() }
    }

    @MainActor final class Coordinator: NSObject, UIPageViewControllerDataSource, UIPageViewControllerDelegate {
        var parent: PoemPager
        weak var pager: UIPageViewController?
        var transitioning = false
        var active = true
        var gestureStartID: String?
        var gestureGates: [HorizontalPageGesture] = []
        private var pages: [String: Page] = [:]

        init(_ parent: PoemPager) { self.parent = parent }

        private func page(_ poem: PoemSummary) -> Page {
            if let existing = pages[poem.id] { return existing }
            let result = Page(poem: poem, root: parent.content(poem), paper: parent.paperColor)
            pages[poem.id] = result
            return result
        }

        func refreshContent() {
            for poem in parent.poems {
                guard let page = pages[poem.id] else { continue }
                page.rootView = parent.content(poem)
                page.view.backgroundColor = parent.paperColor
            }
        }

        func reconcile(animated: Bool) {
            guard active, !transitioning, let pager,
                  let target = parent.poems.firstIndex(where: { $0.id == parent.selectedID }) else { return }
            let currentID = (pager.viewControllers?.first as? Page)?.poemID
            if currentID == parent.selectedID { trimCache(); return }
            let current = parent.poems.firstIndex { $0.id == currentID }
            let direction: UIPageViewController.NavigationDirection = target < (current ?? target) ? .reverse : .forward
            // Directory/scope jumps land immediately; only adjacent poems curl.
            let shouldAnimate = animated && current.map { abs($0 - target) == 1 } == true
            transitioning = true
            pager.setViewControllers([page(parent.poems[target])], direction: direction, animated: shouldAnimate) { [weak self] _ in
                guard let self, self.active else { return }
                self.transitioning = false
                self.refreshContent()
                // A newer button tap or directory selection wins over an older animation.
                self.reconcile(animated: self.parent.style != .instant)
            }
        }

        private func trimCache() {
            guard let index = parent.poems.firstIndex(where: { $0.id == parent.selectedID }) else { return }
            let near = max(0, index - 1)...min(parent.poems.count - 1, index + 1)
            let ids = Set(near.map { parent.poems[$0].id })
            guard Set(pages.keys) != ids else { return }
            pages = pages.filter { ids.contains($0.key) }
            // Pre-layout both neighbors so the first curl does not reveal a loading page.
            for offset in near {
                let neighbor = page(parent.poems[offset])
                neighbor.view.frame = pager?.view.bounds ?? .zero
                neighbor.view.setNeedsLayout()
                neighbor.view.layoutIfNeeded()
            }
        }

        private func neighbor(of controller: UIViewController, offset: Int) -> UIViewController? {
            guard let current = controller as? Page,
                  let index = parent.poems.firstIndex(where: { $0.id == current.poemID }),
                  parent.poems.indices.contains(index + offset) else { return nil }
            return page(parent.poems[index + offset])
        }

        func pageViewController(_ pageViewController: UIPageViewController, viewControllerBefore viewController: UIViewController) -> UIViewController? {
            neighbor(of: viewController, offset: -1)
        }
        func pageViewController(_ pageViewController: UIPageViewController, viewControllerAfter viewController: UIViewController) -> UIViewController? {
            neighbor(of: viewController, offset: 1)
        }
        func pageViewController(_ pageViewController: UIPageViewController, willTransitionTo pendingViewControllers: [UIViewController]) {
            transitioning = true
            gestureStartID = parent.selectedID
        }
        func pageViewController(_ pageViewController: UIPageViewController, didFinishAnimating finished: Bool,
                                previousViewControllers: [UIViewController], transitionCompleted completed: Bool) {
            transitioning = false
            if completed, parent.selectedID == gestureStartID,
               let current = pageViewController.viewControllers?.first as? Page,
               parent.poems.contains(where: { $0.id == current.poemID }) {
                parent.selectedID = current.poemID
            }
            gestureStartID = nil
            refreshContent()
            reconcile(animated: false)
        }

        @objc func swipe(_ gesture: UISwipeGestureRecognizer) {
            guard let index = parent.poems.firstIndex(where: { $0.id == parent.selectedID }) else { return }
            let next = index + (gesture.direction == .left ? 1 : -1)
            guard parent.poems.indices.contains(next) else { return }
            parent.selectedID = parent.poems[next].id
        }
    }
}

/// A page curl's pan is otherwise eager to consume vertical scrolling as well.
/// Forward all of UIKit's other arbitration rules to its original delegate.
final class HorizontalPageGesture: NSObject, UIGestureRecognizerDelegate {
    weak var original: UIGestureRecognizerDelegate?
    init(original: UIGestureRecognizerDelegate?) { self.original = original }

    func gestureRecognizerShouldBegin(_ gestureRecognizer: UIGestureRecognizer) -> Bool {
        if let pan = gestureRecognizer as? UIPanGestureRecognizer {
            let velocity = pan.velocity(in: pan.view)
            guard abs(velocity.x) > abs(velocity.y) * 1.15 else { return false }
        }
        return original?.gestureRecognizerShouldBegin?(gestureRecognizer) ?? true
    }

    func gestureRecognizer(_ gestureRecognizer: UIGestureRecognizer,
                           shouldRecognizeSimultaneouslyWith otherGestureRecognizer: UIGestureRecognizer) -> Bool {
        if otherGestureRecognizer is HorizontalScrollBlocker {
            return true
        }
        if otherGestureRecognizer is UIPanGestureRecognizer, otherGestureRecognizer.view is UIScrollView {
            // Preserve UIKit's curl/scroll arbitration. The inner scroll's
            // failure dependency on HorizontalScrollBlocker rejects horizontal
            // pans before they begin, without preventing the curl recognizer.
            return true
        }
        return original?.gestureRecognizer?(gestureRecognizer, shouldRecognizeSimultaneouslyWith: otherGestureRecognizer) ?? false
    }

    override func responds(to selector: Selector!) -> Bool {
        super.responds(to: selector) || (original?.responds(to: selector) ?? false)
    }

    override func forwardingTarget(for selector: Selector!) -> Any? {
        if original?.responds(to: selector) == true { return original }
        return super.forwardingTarget(for: selector)
    }
}
