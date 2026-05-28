import Foundation
import Observation
import os.log

// MARK: - Monitoring data model

struct MonitoringData {
    var totalCost: Double = 0
    var totalInputTokens: Int = 0
    var totalOutputTokens: Int = 0
    var totalCacheReadTokens: Int = 0
    // Today's stats
    var todayCost: Double = 0
    var todayInputTokens: Int = 0
    var todayOutputTokens: Int = 0
    var todayCacheReadTokens: Int = 0
    var projectCosts: [String: Double] = [:]
    var modelDistribution: [String: Int] = [:]
    var recentEntries: [UsageEntry] = []
    var lastUpdated: Date = Date()

    static var empty: MonitoringData { MonitoringData() }
}

// MARK: - Token rate (per-second delta)

struct TokenRate {
    /// Input tokens/s (upstream: tokens you send to Claude)
    var inputPerSec: Double = 0
    /// Output tokens/s (downstream: tokens Claude sends back)
    var outputPerSec: Double = 0

    var hasActivity: Bool { inputPerSec > 0 || outputPerSec > 0 }
}

// MARK: - Background load result

private struct LoadResult: Sendable {
    let stats: UsageStatistics
    let todayStats: UsageStatistics
    let projects: [String: UsageStatistics]
    let dailyData: [Date: UsageStatistics]
}

// MARK: - Monitoring view model

@Observable
@MainActor
final class MonitoringViewModel {
    var monitoringData: MonitoringData = .empty
    var tokenRate: TokenRate = TokenRate()
    var isLoading = false
    var errorMessage: String?
    /// 30-day per-day history used by the bar chart
    var dailyHistory: [(day: Date, cost: Double, tokens: Int)] = []

    private let logger = Logger(subsystem: "com.claudemonitor.statusbar", category: "viewmodel")
    private let tokenReader = TokenDataReader()
    nonisolated(unsafe) private var autoRefreshTask: Task<Void, Never>?

    /// Reset timestamp persisted in UserDefaults
    private var resetDate: Date? {
        get { UserDefaults.standard.object(forKey: "statsResetDate") as? Date }
        set { UserDefaults.standard.set(newValue, forKey: "statsResetDate") }
    }

    // Previous sample values used to compute the per-interval delta
    private var lastSampleInput: Int = 0
    private var lastSampleOutput: Int = 0
    private var lastSampleTime: Date = Date()
    private var isFirstLoad = true

    // Sliding-window rate smoothing: keep the last N samples
    private var inputHistory: [Double] = []
    private var outputHistory: [Double] = []
    private let historySize = 5

    init() {
        startAutoRefresh()
    }

    // MARK: - Data loading

    func refreshData() {
        Task {
            await loadData()
        }
    }

    private func loadData() async {
        guard !isLoading else { return }
        isLoading = true
        errorMessage = nil

        let reader = tokenReader
        let capturedResetDate = resetDate
        let result = await Task.detached(priority: .userInitiated) {
            let allData = reader.loadAllData(since: capturedResetDate, daysBack: 30)
            let stats      = UsageStatistics(entries: allData.allEntries)
            let todayStats = UsageStatistics(entries: allData.todayEntries)
            let projects   = allData.projectEntries.mapValues { UsageStatistics(entries: $0) }
            let dailyData  = allData.dailyEntries.mapValues  { UsageStatistics(entries: $0) }
            return LoadResult(stats: stats, todayStats: todayStats, projects: projects, dailyData: dailyData)
        }.value

        updateMonitoringData(from: result.stats, todayStats: result.todayStats, projectData: result.projects, dailyData: result.dailyData)

        if result.stats.entries.isEmpty {
            errorMessage = L10n.shared.str(.noDataError)
        }

        isLoading = false
    }

    private func updateMonitoringData(from stats: UsageStatistics, todayStats: UsageStatistics, projectData: [String: UsageStatistics], dailyData: [Date: UsageStatistics]) {
        let now = Date()
        let newInput = stats.totalInputTokens
        let newOutput = stats.totalOutputTokens

        // Compute rate; skip the first load to avoid a spurious spike
        if !isFirstLoad {
            let elapsed = now.timeIntervalSince(lastSampleTime)
            if elapsed > 0 {
                let rawInputRate = Double(max(0, newInput - lastSampleInput)) / elapsed
                let rawOutputRate = Double(max(0, newOutput - lastSampleOutput)) / elapsed

                // Sliding-window average
                inputHistory.append(rawInputRate)
                outputHistory.append(rawOutputRate)
                if inputHistory.count > historySize { inputHistory.removeFirst() }
                if outputHistory.count > historySize { outputHistory.removeFirst() }

                let inputCount = Double(inputHistory.count)
                let outputCount = Double(outputHistory.count)
                tokenRate = TokenRate(
                    inputPerSec: inputCount > 0 ? inputHistory.reduce(0, +) / inputCount : 0,
                    outputPerSec: outputCount > 0 ? outputHistory.reduce(0, +) / outputCount : 0
                )
            }
        } else {
            isFirstLoad = false
        }

        lastSampleInput = newInput
        lastSampleOutput = newOutput
        lastSampleTime = now

        var updated = MonitoringData()
        updated.totalCost = stats.totalCost
        updated.totalInputTokens = newInput
        updated.totalOutputTokens = newOutput
        updated.totalCacheReadTokens = stats.totalCacheReadTokens
        updated.todayCost = todayStats.totalCost
        updated.todayInputTokens = todayStats.totalInputTokens
        updated.todayOutputTokens = todayStats.totalOutputTokens
        updated.todayCacheReadTokens = todayStats.totalCacheReadTokens
        updated.modelDistribution = stats.modelDistribution
        updated.recentEntries = Array(stats.entries.suffix(5))
        updated.lastUpdated = now
        updated.projectCosts = projectData.mapValues { $0.totalCost }

        dailyHistory = dailyData
            .sorted { $0.key < $1.key }
            .map { (day: $0.key, cost: $0.value.totalCost, tokens: $0.value.totalInputTokens + $0.value.totalOutputTokens) }

        monitoringData = updated
        logger.info("Rate: ↑\(String(format: "%.1f", self.tokenRate.inputPerSec))/s ↓\(String(format: "%.1f", self.tokenRate.outputPerSec))/s")
    }

    // MARK: - Auto-refresh

    private func startAutoRefresh() {
        autoRefreshTask?.cancel()
        refreshData()
        let interval = AppSettings.shared.refreshInterval
        autoRefreshTask = Task { [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(interval))
                guard !Task.isCancelled else { break }
                await self?.loadData()
            }
        }
    }

    func restartAutoRefresh() {
        inputHistory = []
        outputHistory = []
        startAutoRefresh()
    }

    // MARK: - Data queries

    func getTopProjects(limit: Int = 5) -> [(String, Double)] {
        monitoringData.projectCosts
            .sorted { $0.value > $1.value }
            .prefix(limit)
            .map { ($0.key, $0.value) }
    }

    func getModelStatistics() -> [(String, Int)] {
        monitoringData.modelDistribution
            .sorted { $0.value > $1.value }
            .map { ($0.key, $0.value) }
    }

    /// Resets the stats start time without deleting JSONL files (filtering only)
    func resetStats() {
        UserDefaults.standard.set(Date(), forKey: "statsResetDate")
        dailyHistory = []
        monitoringData = .empty
        inputHistory = []
        outputHistory = []
        lastSampleInput = 0
        lastSampleOutput = 0
        lastSampleTime = Date()
        isFirstLoad = true
        refreshData()
    }

    // MARK: - Formatting helpers

    static func formatCost(_ cost: Double) -> String {
        String(format: "$%.2f", cost)
    }

    static func formatTokens(_ count: Int) -> String {
        if count >= 100_000_000 {
            return String(format: "%.1f M", Double(count) / 1_000_000)
        } else if count >= 1_000_000 {
            return "\(count / 1_000) K"
        } else if count >= 1_000 {
            return String(format: "%.1f K", Double(count) / 1_000)
        }
        return String(count)
    }

    /// Formats a token-per-second rate; unit scales: t/s → Kt/s → Mt/s → Gt/s
    static func formatRate(_ tokensPerSec: Double) -> String {
        switch tokensPerSec {
        case ..<0.1:
            return "0 T/s"
        case ..<1_000:
            return String(format: "%.0f t/s", tokensPerSec)
        case ..<1_000_000:
            return String(format: "%.1fK t/s", tokensPerSec / 1_000)
        case ..<1_000_000_000:
            return String(format: "%.1fM t/s", tokensPerSec / 1_000_000)
        default:
            return String(format: "%.1fG t/s", tokensPerSec / 1_000_000_000)
        }
    }
}
