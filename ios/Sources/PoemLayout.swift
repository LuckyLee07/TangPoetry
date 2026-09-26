import Foundation

/// A reading layout derives from the actual poem, since 古诗 and 乐府 can have any length.
struct PoemLayout {
    enum Length: Equatable { case quatrain, regulated, medium, long }

    let length: Length
    let fontSize: CGFloat
    let titleSize: CGFloat
    let authorSize: CGFloat
    let lineSpacing: CGFloat
    let headerSpacing: CGFloat
    let bodySpacing: CGFloat
    let horizontalPadding: CGFloat
    let contentTop: CGFloat
    let estimatedContentHeight: CGFloat

    static func resolve(
        section: String, lines: [String], title: String, author: String,
        size: CGSize, fontSetting: Int, dynamicScale: CGFloat = 1,
        notesHeight: CGFloat = 0
    ) -> Self {
        let lineLengths = lines.map { line in
            line.filter { character in
                !character.unicodeScalars.allSatisfy {
                    CharacterSet.punctuationCharacters.union(.whitespacesAndNewlines).contains($0)
                }
            }.count
        }
        let orderedLengths = lineLengths.filter { $0 > 0 }.sorted()
        let typicalLength = orderedLengths.isEmpty
            ? (section.contains("七言") ? 7 : 5)
            : orderedLengths[orderedLengths.count / 2]
        let isFiveCharacter = typicalLength <= 5
        let length: Length
        switch lines.count {
        case 0...4: length = .quatrain
        case 5...8: length = .regulated
        case 9...12: length = .medium
        default: length = .long
        }

        let baseSize: CGFloat
        let minimumSize: CGFloat
        let topFraction: CGFloat
        let gapRatio: CGFloat
        switch length {
        case .quatrain:
            baseSize = isFiveCharacter ? 26 : 24
            minimumSize = isFiveCharacter ? 22 : 21
            topFraction = 0.34
            gapRatio = 0.30
        case .regulated:
            baseSize = isFiveCharacter ? 22 : 21
            minimumSize = 20
            topFraction = 0.215
            gapRatio = 0.19
        case .medium:
            baseSize = 20
            minimumSize = 19
            topFraction = 0.18
            gapRatio = 0.20
        case .long:
            baseSize = isFiveCharacter ? 20 : 19
            minimumSize = 18
            topFraction = 0.155
            gapRatio = 0.24
        }

        let accessibilityScale = max(0.8, dynamicScale)
        let readingScale = CGFloat(fontSetting) / 22 * accessibilityScale
        let minimum = minimumSize * readingScale
        let horizontalPadding = min(30, max(20, size.width * 0.065))
        let textWidth = max(1, size.width - horizontalPadding * 2)
        let titleSize = CGFloat(title.count > 14 ? 21 : title.count > 9 ? 23 : 26) * accessibilityScale
        let authorSize = 12 * accessibilityScale
        let headerSpacing = 7 * accessibilityScale
        let bodySpacing = (length == .quatrain ? 15.0 : 10.0) * accessibilityScale
        let bottomReserve: CGFloat = 65
        let minimumTop = max(100, 82 + 14 * accessibilityScale)
        let preferredTop = max(minimumTop, size.height * topFraction)
        let contentBottom = max(minimumTop, size.height - bottomReserve - notesHeight)

        // Mirror VerseGrid's cells and punctuation reserve. At accessibility sizes,
        // wrapping wins over shrinking below the user's scaled reading size floor.
        let gridMetrics = lines.map { line -> (cells: Int, punctuation: Int) in
            let characters = Array(line)
            let lastText = characters.lastIndex { character in
                !character.unicodeScalars.allSatisfy { CharacterSet.punctuationCharacters.contains($0) }
            }
            guard let lastText else { return (max(1, characters.count), 0) }
            return (lastText + 1, characters.count - lastText - 1)
        }
        let maximumGridWidth = gridMetrics.map { CGFloat($0.cells) * 1.18 + CGFloat($0.punctuation * 2) }.max() ?? 1
        let widthFit = textWidth / max(1, maximumGridWidth)
        var fontSize = max(minimum, min(baseSize * readingScale, widthFit))

        func contentHeight(at font: CGFloat) -> CGFloat {
            let titleLines = max(1, ceil(CGFloat(title.count) * titleSize / textWidth))
            let authorLines = max(1, ceil(CGFloat(author.count + 4) * authorSize / textWidth))
            let header = titleLines * titleSize * 1.3 + headerSpacing + authorLines * authorSize * 1.35 + bodySpacing
            let body = gridMetrics.reduce(CGFloat.zero) { total, line in
                let columns = max(1, Int(((textWidth - CGFloat(line.punctuation * 2) * font) / (font * 1.18)).rounded(.down)))
                let rows = CGFloat(max(1, Int(ceil(Double(line.cells) / Double(columns)))))
                return total + rows * font * 1.45 + max(0, rows - 1) * font * 0.35
            }
            return header + body + CGFloat(max(0, lines.count - 1)) * font * gapRatio + 20
        }

        // Short forms try to fit on one page. Long poems keep a readable size and
        // scroll; fitting an entire ballad would make the text unusably small.
        if length != .long && contentHeight(at: fontSize) > contentBottom - preferredTop {
            var lower = minimum
            var upper = fontSize
            for _ in 0..<12 {
                let candidate = (lower + upper) / 2
                if contentHeight(at: candidate) <= contentBottom - preferredTop { lower = candidate }
                else { upper = candidate }
            }
            fontSize = lower
        }
        let height = contentHeight(at: fontSize)
        let contentTop = length == .long
            ? preferredTop
            : max(minimumTop, min(preferredTop, contentBottom - height))
        return Self(
            length: length, fontSize: fontSize, titleSize: titleSize, authorSize: authorSize,
            lineSpacing: fontSize * gapRatio, headerSpacing: headerSpacing, bodySpacing: bodySpacing,
            horizontalPadding: horizontalPadding, contentTop: contentTop,
            estimatedContentHeight: height
        )
    }
}
