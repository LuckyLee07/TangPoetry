#!/usr/bin/env swift
// Original vector geometry: a moonlit mountain on a folded poetry sheet.
// No fonts, external images, random values, or third-party dependencies.
import AppKit
import Foundation

let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
let destination = root.appendingPathComponent("ios/Assets.xcassets/AppIcon.appiconset")
try FileManager.default.createDirectory(at: destination, withIntermediateDirectories: true)

func rgb(_ hex: UInt32) -> CGColor {
    CGColor(red: CGFloat((hex >> 16) & 255) / 255,
            green: CGFloat((hex >> 8) & 255) / 255,
            blue: CGFloat(hex & 255) / 255, alpha: 1)
}

func render(size: Int) throws {
    let context = CGContext(data: nil, width: size, height: size, bitsPerComponent: 8, bytesPerRow: size * 4,
                            space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!
    context.scaleBy(x: CGFloat(size) / 1024, y: CGFloat(size) / 1024)
    context.translateBy(x: 0, y: 1024)
    context.scaleBy(x: 1, y: -1)
    context.setFillColor(rgb(0x34483F))
    context.fill(CGRect(x: 0, y: 0, width: 1024, height: 1024))

    // An offset darker sheet adds one quiet layer of depth.
    let shadow = CGPath(roundedRect: CGRect(x: 228, y: 180, width: 598, height: 716), cornerWidth: 25, cornerHeight: 25, transform: nil)
    context.setFillColor(rgb(0x2E3F37))
    context.addPath(shadow)
    context.fillPath()
    let page = CGMutablePath()
    page.move(to: CGPoint(x: 252, y: 144))
    page.addLine(to: CGPoint(x: 653, y: 144))
    page.addLine(to: CGPoint(x: 792, y: 284))
    page.addLine(to: CGPoint(x: 792, y: 836))
    page.addQuadCurve(to: CGPoint(x: 766, y: 862), control: CGPoint(x: 792, y: 862))
    page.addLine(to: CGPoint(x: 252, y: 862))
    page.addQuadCurve(to: CGPoint(x: 226, y: 836), control: CGPoint(x: 226, y: 862))
    page.addLine(to: CGPoint(x: 226, y: 170))
    page.addQuadCurve(to: CGPoint(x: 252, y: 144), control: CGPoint(x: 226, y: 144))
    page.closeSubpath()
    context.setFillColor(rgb(0xF4EFDF))
    context.addPath(page)
    context.fillPath()

    // Fold, sun-warmed moon, and a landscape made of simple brushlike curves.
    let fold = CGMutablePath()
    fold.move(to: CGPoint(x: 653, y: 144))
    fold.addLine(to: CGPoint(x: 653, y: 266))
    fold.addQuadCurve(to: CGPoint(x: 670, y: 284), control: CGPoint(x: 653, y: 284))
    fold.addLine(to: CGPoint(x: 792, y: 284))
    fold.closeSubpath()
    context.setFillColor(rgb(0xD3C7A5))
    context.addPath(fold)
    context.fillPath()
    context.setFillColor(rgb(0xCBAF6F))
    context.fillEllipse(in: CGRect(x: 553, y: 327, width: 112, height: 112))

    context.saveGState()
    context.addPath(page)
    context.clip()
    let distant = CGMutablePath()
    distant.move(to: CGPoint(x: 226, y: 553))
    distant.addCurve(to: CGPoint(x: 421, y: 457), control1: CGPoint(x: 296, y: 532), control2: CGPoint(x: 362, y: 472))
    distant.addCurve(to: CGPoint(x: 507, y: 508), control1: CGPoint(x: 440, y: 466), control2: CGPoint(x: 482, y: 509))
    distant.addCurve(to: CGPoint(x: 591, y: 479), control1: CGPoint(x: 530, y: 509), control2: CGPoint(x: 565, y: 484))
    distant.addCurve(to: CGPoint(x: 792, y: 568), control1: CGPoint(x: 654, y: 508), control2: CGPoint(x: 721, y: 551))
    distant.addLine(to: CGPoint(x: 792, y: 668))
    distant.addLine(to: CGPoint(x: 226, y: 668))
    distant.closeSubpath()
    context.setFillColor(rgb(0xC1C8B7))
    context.addPath(distant)
    context.fillPath()
    let near = CGMutablePath()
    near.move(to: CGPoint(x: 226, y: 601))
    near.addCurve(to: CGPoint(x: 420, y: 554), control1: CGPoint(x: 316, y: 625), control2: CGPoint(x: 348, y: 587))
    near.addCurve(to: CGPoint(x: 585, y: 594), control1: CGPoint(x: 464, y: 554), control2: CGPoint(x: 545, y: 605))
    near.addCurve(to: CGPoint(x: 706, y: 551), control1: CGPoint(x: 630, y: 583), control2: CGPoint(x: 669, y: 552))
    near.addCurve(to: CGPoint(x: 792, y: 580), control1: CGPoint(x: 738, y: 555), control2: CGPoint(x: 770, y: 581))
    near.addLine(to: CGPoint(x: 792, y: 674))
    near.addCurve(to: CGPoint(x: 226, y: 669), control1: CGPoint(x: 600, y: 721), control2: CGPoint(x: 418, y: 622))
    near.closeSubpath()
    context.setFillColor(rgb(0x7D927C))
    context.addPath(near)
    context.fillPath()
    context.restoreGState()

    context.setLineCap(.round)
    context.setStrokeColor(rgb(0x526C58))
    context.setLineWidth(13)
    context.move(to: CGPoint(x: 322, y: 750))
    context.addLine(to: CGPoint(x: 545, y: 750))
    context.move(to: CGPoint(x: 322, y: 789))
    context.addLine(to: CGPoint(x: 474, y: 789))
    context.strokePath()
    context.setFillColor(rgb(0xA86D4E))
    context.fill(CGRect(x: 643, y: 741, width: 50, height: 50))
    context.setStrokeColor(rgb(0xF4EFDF))
    context.setLineWidth(3)
    context.stroke(CGRect(x: 652, y: 750, width: 32, height: 32))

    let bitmap = NSBitmapImageRep(cgImage: context.makeImage()!)
    let data = bitmap.representation(using: .png, properties: [:])!
    try data.write(to: destination.appendingPathComponent("AppIcon-\(size).png"))
}

let slots: [(String, String, String, Int)] = [
    ("iphone", "20x20", "2x", 40), ("iphone", "20x20", "3x", 60),
    ("iphone", "29x29", "2x", 58), ("iphone", "29x29", "3x", 87),
    ("iphone", "40x40", "2x", 80), ("iphone", "40x40", "3x", 120),
    ("iphone", "60x60", "2x", 120), ("iphone", "60x60", "3x", 180),
    ("ios-marketing", "1024x1024", "1x", 1024)
]
for size in Set(slots.map { $0.3 }).sorted() { try render(size: size) }
let images = slots.map { ["idiom": $0.0, "size": $0.1, "scale": $0.2, "filename": "AppIcon-\($0.3).png"] }
let contents: [String: Any] = ["images": images, "info": ["author": "xcode", "version": 1]]
try JSONSerialization.data(withJSONObject: contents, options: [.prettyPrinted, .sortedKeys]).write(to: destination.appendingPathComponent("Contents.json"))
let assetInfo: [String: Any] = ["info": ["author": "xcode", "version": 1]]
try JSONSerialization.data(withJSONObject: assetInfo, options: [.prettyPrinted, .sortedKeys]).write(to: destination.deletingLastPathComponent().appendingPathComponent("Contents.json"))
print("Generated original opaque AppIcon: \(destination.path)")
