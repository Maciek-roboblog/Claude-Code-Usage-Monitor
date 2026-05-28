import AppKit
import SwiftUI
import ServiceManagement

@Observable
final class AppSettings {
    // MARK: - Display section toggles
    var showProjectSection: Bool {
        didSet { UserDefaults.standard.set(showProjectSection, forKey: "showProjectSection") }
    }
    var showRecentSection: Bool {
        didSet { UserDefaults.standard.set(showRecentSection, forKey: "showRecentSection") }
    }
    var showChartSection: Bool {
        didSet { UserDefaults.standard.set(showChartSection, forKey: "showChartSection") }
    }

    // MARK: - Refresh interval (seconds)
    var refreshInterval: Int {
        didSet { UserDefaults.standard.set(refreshInterval, forKey: "refreshInterval") }
    }
    static let refreshIntervalOptions = [3, 5, 10, 30, 60]

    // MARK: - Language
    var language: AppLanguage {
        didSet {
            UserDefaults.standard.set(language.rawValue, forKey: "appLanguage")
            L10n.shared.language = language
        }
    }

    // MARK: - Dock icon
    var showDockIcon: Bool {
        didSet {
            UserDefaults.standard.set(showDockIcon, forKey: "showDockIcon")
            NSApp.setActivationPolicy(showDockIcon ? .regular : .accessory)
        }
    }

    // MARK: - Launch at login
    var launchAtLogin: Bool {
        didSet {
            guard !applyingLaunchAtLogin, oldValue != launchAtLogin else { return }
            applyLaunchAtLogin(launchAtLogin)
        }
    }
    private var applyingLaunchAtLogin = false

    static let shared = AppSettings()

    private init() {
        let defaults = UserDefaults.standard
        // First launch: show all sections by default
        showProjectSection = defaults.object(forKey: "showProjectSection") as? Bool ?? true
        showRecentSection  = defaults.object(forKey: "showRecentSection")  as? Bool ?? true
        showChartSection   = defaults.object(forKey: "showChartSection")   as? Bool ?? true
        refreshInterval    = defaults.object(forKey: "refreshInterval")    as? Int  ?? 5
        showDockIcon       = defaults.object(forKey: "showDockIcon")       as? Bool ?? false

        let savedLang = defaults.string(forKey: "appLanguage") ?? ""
        // Default to the system language; fall back to English
        let systemLangCode = Locale.current.language.languageCode?.identifier ?? "en"
        language = AppLanguage(rawValue: savedLang)
            ?? AppLanguage(rawValue: systemLangCode)
            ?? .english

        // Read the actual launch-at-login state from the system (not UserDefaults)
        launchAtLogin = SMAppService.mainApp.status == .enabled

        L10n.shared.language = language
    }

    // MARK: - Launch at login implementation

    private func applyLaunchAtLogin(_ enable: Bool) {
        applyingLaunchAtLogin = true
        defer { applyingLaunchAtLogin = false }
        do {
            if enable {
                try SMAppService.mainApp.register()
            } else {
                try SMAppService.mainApp.unregister()
            }
        } catch {
            // Roll back to the actual system state on failure
            launchAtLogin = SMAppService.mainApp.status == .enabled
        }
    }
}
