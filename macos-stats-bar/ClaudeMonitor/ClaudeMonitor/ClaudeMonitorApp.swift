//
//  ClaudeMonitorApp.swift
//  ClaudeMonitor
//

import AppKit
import SwiftUI

@main
struct ClaudeMonitorApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    @State private var viewModel = MonitoringViewModel()

    var body: some Scene {
        MenuBarExtra {
            StatusBarView()
                .environment(viewModel)
        } label: {
            MenuBarLabel()
                .environment(viewModel)
        }
        .menuBarExtraStyle(.window)
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        let showDock = UserDefaults.standard.object(forKey: "showDockIcon") as? Bool ?? false
        NSApp.setActivationPolicy(showDock ? .regular : .accessory)

        let isSandboxed = ProcessInfo.processInfo.environment["APP_SANDBOX_CONTAINER_ID"] != nil
        if isSandboxed && !BookmarkManager.shared.hasBookmark {
            BookmarkManager.shared.requestAccess()
        }
    }
}

// MARK: - Menu bar icon

private struct MenuBarLabel: View {
    @Environment(MonitoringViewModel.self) private var viewModel

    var body: some View {
        let rate = viewModel.tokenRate
        if rate.hasActivity {
            // Active: double-row token rates
            let rate1 = MonitoringViewModel.formatRate(rate.inputPerSec)
            let rate2 = MonitoringViewModel.formatRate(rate.outputPerSec)
            Image(nsImage: makeMenuBarImage(rate1: rate1, rate2: rate2))
        } else {
            // Idle: single-row total cost
            let cost = MonitoringViewModel.formatCost(viewModel.monitoringData.totalCost)
            Image(nsImage: makeCostImage(cost: cost))
        }
    }
}

// MARK: - NSImage cache (avoid redrawing when the displayed string hasn't changed)

private enum ImageCache {
    static var costKey: String = ""
    static var costImage: NSImage?
    static var rateKey: String = ""
    static var rateImage: NSImage?
}

// MARK: - NSImage rendering (idle: single-row total cost)

private func makeCostImage(cost: String) -> NSImage {
    if cost == ImageCache.costKey, let cached = ImageCache.costImage { return cached }
    let H: CGFloat = 22
    let font = NSFont.monospacedDigitSystemFont(ofSize: 12, weight: .medium)
    let attrs: [NSAttributedString.Key: Any] = [
        .font: font,
        .foregroundColor: NSColor.labelColor
    ]
    let textSize = (cost as NSString).size(withAttributes: attrs)
    let W = max(58, ceil(textSize.width) + 8)
    let startX = floor((W - textSize.width) / 2)   // horizontally centered
    let startY = floor((H - textSize.height) / 2)   // vertically centered

    let image = NSImage(size: NSSize(width: W, height: H), flipped: true) { _ in
        (cost as NSString).draw(
            at: NSPoint(x: startX, y: startY),
            withAttributes: attrs
        )
        return true
    }
    image.isTemplate = true
    ImageCache.costKey = cost
    ImageCache.costImage = image
    return image
}

// MARK: - NSImage rendering (active: iStat Menus-style double-row rates)
//
// Layout:
//   ↗  [right-aligned rate]     ← top row: input
//   ↙  [right-aligned rate]     ← bottom row: output
//
//   Arrow left-aligned, numbers right-aligned, rows tightly packed (iStats-style)

private func makeMenuBarImage(rate1: String, rate2: String) -> NSImage {
    let key = "\(rate1)|\(rate2)"
    if key == ImageCache.rateKey, let cached = ImageCache.rateImage { return cached }

    let H: CGFloat    = 22   // fixed menu bar height
    let minW: CGFloat = 58   // minimum width to avoid a too-narrow icon when rate is 0

    // Numbers: monospaced, medium weight
    let numFont   = NSFont.monospacedDigitSystemFont(ofSize: 10, weight: .medium)
    // Arrows: same size for visual consistency
    let arrowFont = NSFont.systemFont(ofSize: 10, weight: .medium)

    let arrowAttrs: [NSAttributedString.Key: Any] = [
        .font: arrowFont,
        .foregroundColor: NSColor.labelColor
    ]
    let numAttrs: [NSAttributedString.Key: Any] = [
        .font: numFont,
        .foregroundColor: NSColor.labelColor
    ]

    let arrow1 = "↗" as NSString
    let arrow2 = "↙" as NSString

    let a1Size = arrow1.size(withAttributes: arrowAttrs)
    let r1Size = (rate1 as NSString).size(withAttributes: numAttrs)
    let r2Size = (rate2 as NSString).size(withAttributes: numAttrs)

    // glyphH: controls arrow row spacing (tuned value, do not change)
    let glyphH    = ceil(numFont.capHeight - 3)
    // textLineH: actual rendered line height for number Y positioning (prevents clipping)
    let textLineH = ceil(r1Size.height - 2)
    let arrowW = ceil(a1Size.width)
    let textW  = ceil(max(r1Size.width, r2Size.width))

    let rowGap: CGFloat = 1
    let arrowTotalH = glyphH * 2 + rowGap
    let textTotalH  = textLineH * 2 + rowGap

    let W = max(minW, arrowW + 2 + textW)

    // Arrow block and number block are each vertically centered independently
    let arrowStartY = floor((H - arrowTotalH) / 2)
    let textStartY  = floor((H - textTotalH)  / 2)

    let image = NSImage(size: NSSize(width: W, height: H), flipped: true) { _ in
        // ── Row 1: ↗ input rate ──────────────────────────────────
        let arrowOff = floor((glyphH - a1Size.height) / 2)
        arrow1.draw(at: NSPoint(x: 0, y: arrowStartY + arrowOff), withAttributes: arrowAttrs)
        // Number: right-aligned, Y based on textStartY (no clipping)
        (rate1 as NSString).draw(
            at: NSPoint(x: W - r1Size.width, y: textStartY),
            withAttributes: numAttrs
        )

        // ── Row 2: ↙ output rate ─────────────────────────────────
        let arrowRow2Y = arrowStartY + glyphH + rowGap
        let textRow2Y  = textStartY  + textLineH + rowGap
        arrow2.draw(at: NSPoint(x: 0, y: arrowRow2Y + arrowOff), withAttributes: arrowAttrs)
        (rate2 as NSString).draw(
            at: NSPoint(x: W - r2Size.width, y: textRow2Y),
            withAttributes: numAttrs
        )

        return true
    }
    image.isTemplate = true
    ImageCache.rateKey = key
    ImageCache.rateImage = image
    return image
}
