import AppKit
import Foundation
import OSLog

private let logger = Logger(subsystem: "com.claudemonitor.statusbar", category: "BookmarkManager")
private let bookmarkKey = "claudeProjectsBookmark"

/// Manages Security-Scoped Bookmark access to ~/.claude/projects
final class BookmarkManager {
    static let shared = BookmarkManager()
    private init() {}

    // MARK: - Public API

    /// Returns the resolved ~/.claude/projects path if bookmark access is available, otherwise nil.
    func resolvedPath() -> String? {
        if let url = resolveBookmark() {
            return url.path
        }
        return nil
    }

    /// Returns true if a valid bookmark is already stored.
    var hasBookmark: Bool {
        UserDefaults.standard.data(forKey: bookmarkKey) != nil
    }

    /// Presents NSOpenPanel pre-navigated to ~/.claude/projects and stores the resulting bookmark.
    /// Must be called on the main thread.
    @MainActor
    @discardableResult
    func requestAccess() -> Bool {
        let panel = NSOpenPanel()
        panel.message = NSLocalizedString(
            "ClaudeMonitor needs access to your Claude data folder to display usage statistics.",
            comment: "Sandbox permission panel message"
        )
        panel.prompt = NSLocalizedString("Grant Access", comment: "Sandbox permission panel button")
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.canCreateDirectories = false
        panel.allowsMultipleSelection = false

        // Pre-navigate to ~/.claude/projects if it exists, otherwise ~/.claude
        let home = realHomeDirectory()
        let projectsURL = URL(fileURLWithPath: home + "/.claude/projects")
        let claudeURL   = URL(fileURLWithPath: home + "/.claude")
        if FileManager.default.fileExists(atPath: projectsURL.path) {
            panel.directoryURL = projectsURL
        } else if FileManager.default.fileExists(atPath: claudeURL.path) {
            panel.directoryURL = claudeURL
        }

        guard panel.runModal() == .OK, let url = panel.url else {
            logger.warning("User cancelled folder access panel")
            return false
        }

        return storeBookmark(for: url)
    }

    // MARK: - Private helpers

    private func storeBookmark(for url: URL) -> Bool {
        do {
            let data = try url.bookmarkData(
                options: .withSecurityScope,
                includingResourceValuesForKeys: nil,
                relativeTo: nil
            )
            UserDefaults.standard.set(data, forKey: bookmarkKey)
            logger.info("Bookmark stored for \(url.path)")
            return true
        } catch {
            logger.error("Failed to create bookmark: \(error)")
            return false
        }
    }

    private func resolveBookmark() -> URL? {
        guard let data = UserDefaults.standard.data(forKey: bookmarkKey) else { return nil }
        var isStale = false
        do {
            let url = try URL(
                resolvingBookmarkData: data,
                options: .withSecurityScope,
                relativeTo: nil,
                bookmarkDataIsStale: &isStale
            )
            if isStale {
                _ = storeBookmark(for: url)
            }
            guard url.startAccessingSecurityScopedResource() else {
                logger.error("startAccessingSecurityScopedResource failed for \(url.path)")
                return nil
            }
            return url
        } catch {
            logger.error("Failed to resolve bookmark: \(error)")
            UserDefaults.standard.removeObject(forKey: bookmarkKey)
            return nil
        }
    }

    private func realHomeDirectory() -> String {
        if let pw = getpwuid(getuid()), let dir = pw.pointee.pw_dir {
            return String(cString: dir)
        }
        return FileManager.default.homeDirectoryForCurrentUser.path
    }
}
