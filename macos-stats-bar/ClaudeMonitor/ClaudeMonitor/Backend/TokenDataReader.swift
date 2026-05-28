import Foundation
import os.log

// MARK: - Data models (matching the actual JSONL format)

/// Raw usage entry parsed from a JSONL file
struct UsageEntry: Identifiable {
    let id: String          // composite of message_id + request_id
    let timestamp: Date
    let inputTokens: Int
    let outputTokens: Int
    let cacheCreationTokens: Int
    let cacheReadTokens: Int
    let costUsd: Double
    let model: String
    let messageId: String
    let requestId: String
}

/// Aggregated token usage statistics
struct UsageStatistics {
    let totalInputTokens: Int
    let totalOutputTokens: Int
    let totalCacheReadTokens: Int
    let totalCacheCreationTokens: Int
    let totalCost: Double
    let modelDistribution: [String: Int]
    let entries: [UsageEntry]

    init(entries: [UsageEntry]) {
        self.entries = entries
        self.totalInputTokens = entries.reduce(0) { $0 + $1.inputTokens }
        self.totalOutputTokens = entries.reduce(0) { $0 + $1.outputTokens }
        self.totalCacheReadTokens = entries.reduce(0) { $0 + $1.cacheReadTokens }
        self.totalCacheCreationTokens = entries.reduce(0) { $0 + $1.cacheCreationTokens }
        self.totalCost = entries.reduce(0) { $0 + $1.costUsd }

        var modelDist: [String: Int] = [:]
        for entry in entries {
            let model = entry.model.isEmpty ? "unknown" : entry.model
            modelDist[model, default: 0] += 1
        }
        self.modelDistribution = modelDist
    }
}

// MARK: - Pricing model (mirrors Python pricing.py)

/// Per-model pricing in USD per 1M tokens
private struct ModelPricing {
    let input: Double
    let output: Double
    let cacheCreation: Double
    let cacheRead: Double

    /// Returns pricing for a given model name (matches Python FALLBACK_PRICING)
    static func forModel(_ model: String) -> ModelPricing {
        let lower = model.lowercased()
        if lower.contains("opus") {
            return ModelPricing(input: 15.0, output: 75.0, cacheCreation: 18.75, cacheRead: 1.5)
        } else if lower.contains("haiku") {
            return ModelPricing(input: 0.25, output: 1.25, cacheCreation: 0.3, cacheRead: 0.03)
        } else {
            // Default: Sonnet pricing
            return ModelPricing(input: 3.0, output: 15.0, cacheCreation: 3.75, cacheRead: 0.3)
        }
    }

    /// Calculates token cost in USD
    func calculateCost(input: Int, output: Int, cacheCreation: Int, cacheRead: Int) -> Double {
        let cost = (Double(input) / 1_000_000) * self.input
            + (Double(output) / 1_000_000) * self.output
            + (Double(cacheCreation) / 1_000_000) * self.cacheCreation
            + (Double(cacheRead) / 1_000_000) * self.cacheRead
        return (cost * 1_000_000).rounded() / 1_000_000
    }
}

// MARK: - Token data reader

/// Reads and parses ~/.claude/projects JSONL files — Swift equivalent of Python reader.py
class TokenDataReader {
    private let logger = Logger(subsystem: "com.claudemonitor.statusbar", category: "tokenreader")

    // Static formatter instances created once per process lifetime.
    // ISO8601DateFormatter is thread-safe; DateFormatter is not, but loadData() is
    // guarded by the isLoading mutex so concurrent access is prevented.
    private static let isoWithFractional: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f
    }()

    private static let isoBasic: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime]
        return f
    }()

    private static let fallbackDateFormatters: [DateFormatter] = {
        return ["yyyy-MM-dd'T'HH:mm:ss.SSSSSS", "yyyy-MM-dd'T'HH:mm:ss"].map { fmt in
            let f = DateFormatter()
            f.locale = Locale(identifier: "en_US_POSIX")
            f.dateFormat = fmt
            return f
        }
    }()

    // Per-file parse cache keyed by absolute path, storing (mtime, parsed entries).
    // When mtime is unchanged the cache is returned directly, skipping disk I/O and JSON parsing.
    private struct FileCache {
        var mtime: Date
        var entries: [UsageEntry]
    }
    private var fileCache: [String: FileCache] = [:]

    init() {}

    // MARK: - Real home directory (bypasses sandbox container)

    /// Returns the user's real home directory regardless of App Sandbox.
    /// Inside a sandbox, FileManager.homeDirectoryForCurrentUser and ~ both resolve to the
    /// container directory. We read /etc/passwd via getpwuid(getuid()) to get the actual home.
    private func realHomeDirectory() -> String {
        if let pw = getpwuid(getuid()), let homeDir = pw.pointee.pw_dir {
            return String(cString: homeDir)
        }
        // Fallback: try the HOME environment variable
        if let home = ProcessInfo.processInfo.environment["HOME"] {
            return home
        }
        // Last resort: standard home (may be the sandbox container)
        return FileManager.default.homeDirectoryForCurrentUser.path
    }

    /// Returns the real path to a Claude data directory
    private func claudeDataPath(relativePath: String = ".claude/projects") -> String {
        return realHomeDirectory() + "/" + relativePath
    }

    // MARK: - Public API

    /// Loads usage entries from disk.
    /// - Parameters:
    ///   - dataPath: Override directory path; nil uses the default ~/.claude/projects.
    ///   - hoursBack: Only return entries from the last N hours; nil returns all.
    ///   - since: Hard lower-bound timestamp (used after a stats reset); takes the later of this and hoursBack.
    func loadUsageEntries(dataPath: String? = nil, hoursBack: Int? = nil, since: Date? = nil) -> [UsageEntry] {
        let expandedPath: String
        if let path = dataPath {
            // Expand ~ using the real home directory
            if path.hasPrefix("~/") {
                expandedPath = realHomeDirectory() + path.dropFirst(1)
            } else {
                expandedPath = path
            }
        } else {
            expandedPath = claudeDataPath()
        }

        let fileManager = FileManager.default

        guard fileManager.fileExists(atPath: expandedPath) else {
            logger.warning("Data directory not found: \(expandedPath)")
            return []
        }

        let hoursBackDate: Date? = hoursBack.map { Date().addingTimeInterval(-Double($0) * 3600) }
        let cutoffDate: Date? = [hoursBackDate, since].compactMap { $0 }.max()

        let jsonlFiles = findJsonlFiles(in: expandedPath, fileManager: fileManager)
        guard !jsonlFiles.isEmpty else {
            logger.info("No .jsonl files found in: \(expandedPath)")
            return []
        }

        var seenHashes = Set<String>()
        var allEntries: [UsageEntry] = []

        for filePath in jsonlFiles {
            let entries = parseFile(at: filePath, cutoffDate: cutoffDate, seenHashes: &seenHashes)
            allEntries.append(contentsOf: entries)
        }

        let sorted = allEntries.sorted { $0.timestamp < $1.timestamp }
        logger.info("Loaded \(sorted.count) entries from \(jsonlFiles.count) files")
        return sorted
    }

    /// Returns aggregated statistics
    func getStatistics(hoursBack: Int? = nil, since: Date? = nil) -> UsageStatistics {
        UsageStatistics(entries: loadUsageEntries(hoursBack: hoursBack, since: since))
    }

    /// Single-pass scan that produces all groupings needed by MonitoringViewModel
    struct AllData: Sendable {
        let allEntries: [UsageEntry]
        let todayEntries: [UsageEntry]
        let projectEntries: [String: [UsageEntry]]
        let dailyEntries: [Date: [UsageEntry]]
    }

    func loadAllData(since: Date? = nil, daysBack: Int = 30) -> AllData {
        let expandedPath = BookmarkManager.shared.resolvedPath() ?? claudeDataPath()
        let fileManager = FileManager.default

        guard fileManager.fileExists(atPath: expandedPath) else {
            logger.warning("Data directory not found: \(expandedPath)")
            return AllData(allEntries: [], todayEntries: [], projectEntries: [:], dailyEntries: [:])
        }

        let jsonlFiles = findJsonlFiles(in: expandedPath, fileManager: fileManager)
        guard !jsonlFiles.isEmpty else {
            return AllData(allEntries: [], todayEntries: [], projectEntries: [:], dailyEntries: [:])
        }

        let calendar = Calendar.current
        let now = Date()
        let startOfToday = calendar.startOfDay(for: now)
        let todayCutoff = startOfToday
        let dailyCutoff = calendar.date(byAdding: .day, value: -daysBack, to: startOfToday)
            ?? now.addingTimeInterval(-Double(daysBack) * 86400)
        // Early-skip cutoff:
        // - when `since` is set: min(since, dailyCutoff), because allEntries needs the full
        //   range from `since` onward and we must not cut it with dailyCutoff alone
        // - when `since` is nil: only use dailyCutoff for early-skipping (allEntries needs
        //   full history, so we cannot apply dailyCutoff as a hard lower bound)
        let overallCutoff: Date? = since.map { min($0, dailyCutoff) }

        var seenHashes = Set<String>()
        var allEntries: [UsageEntry] = []
        var todayEntries: [UsageEntry] = []
        var projectEntries: [String: [UsageEntry]] = [:]
        var dailyEntries: [Date: [UsageEntry]] = [:]

        for filePath in jsonlFiles {
            let dirPath = (filePath as NSString).deletingLastPathComponent
            let projectName = (dirPath as NSString).lastPathComponent

            // rawEntriesForFile is mtime-cached and returns complete file entries (no time filter)
            let fileEntries = rawEntriesForFile(at: filePath, seenHashes: &seenHashes)

            for entry in fileEntries {
                // Projects: full history (matches original getProjectData(cutoffDate: nil) behaviour)
                projectEntries[projectName, default: []].append(entry)

                // Early-skip entries that are definitely not needed (perf optimisation, not correctness)
                if let cutoff = overallCutoff, entry.timestamp < cutoff { continue }

                // All entries (filtered by since if set)
                if since == nil || entry.timestamp >= since! {
                    allEntries.append(entry)
                }
                // Today's entries
                if entry.timestamp >= todayCutoff {
                    todayEntries.append(entry)
                }
                // Per-day entries (last daysBack days only)
                if entry.timestamp >= dailyCutoff {
                    let comps = calendar.dateComponents([.year, .month, .day], from: entry.timestamp)
                    if let dayDate = calendar.date(from: comps) {
                        dailyEntries[dayDate, default: []].append(entry)
                    }
                }
            }
        }

        allEntries.sort { $0.timestamp < $1.timestamp }
        logger.info("loadAllData: \(allEntries.count) entries from \(jsonlFiles.count) files")
        return AllData(
            allEntries: allEntries,
            todayEntries: todayEntries,
            projectEntries: projectEntries,
            dailyEntries: dailyEntries
        )
    }

    /// Groups entries by hour
    func getHourlyData(hoursBack: Int = 24) -> [Date: UsageStatistics] {
        let entries = loadUsageEntries(hoursBack: hoursBack)
        let calendar = Calendar.current
        var grouped: [Date: [UsageEntry]] = [:]

        for entry in entries {
            let comps = calendar.dateComponents([.year, .month, .day, .hour], from: entry.timestamp)
            guard let hourDate = calendar.date(from: comps) else { continue }
            grouped[hourDate, default: []].append(entry)
        }

        return grouped.mapValues { UsageStatistics(entries: $0) }
    }

    /// Groups entries by day for the last N days
    func getDailyData(daysBack: Int = 30, since: Date? = nil) -> [Date: UsageStatistics] {
        let calendar = Calendar.current
        // Start from midnight daysBack days ago to avoid day-boundary edge cases
        let startOfToday = calendar.startOfDay(for: Date())
        let startDate = calendar.date(byAdding: .day, value: -daysBack, to: startOfToday) ?? Date().addingTimeInterval(-Double(daysBack) * 86400)
        let effectiveSince = [startDate, since].compactMap { $0 }.max()

        let entries = loadUsageEntries(since: effectiveSince)
        var grouped: [Date: [UsageEntry]] = [:]

        for entry in entries {
            let comps = calendar.dateComponents([.year, .month, .day], from: entry.timestamp)
            guard let dayDate = calendar.date(from: comps) else { continue }
            grouped[dayDate, default: []].append(entry)
        }

        return grouped.mapValues { UsageStatistics(entries: $0) }
    }

    /// Groups entries by project (directory name of the containing JSONL file)
    func getProjectData(dataPath: String? = nil) -> [String: UsageStatistics] {
        let expandedPath: String
        if let path = dataPath {
            if path.hasPrefix("~/") {
                expandedPath = realHomeDirectory() + path.dropFirst(1)
            } else {
                expandedPath = path
            }
        } else {
            expandedPath = claudeDataPath()
        }

        let fileManager = FileManager.default
        let jsonlFiles = findJsonlFiles(in: expandedPath, fileManager: fileManager)
        var seenHashes = Set<String>()
        var projectEntries: [String: [UsageEntry]] = [:]

        for filePath in jsonlFiles {
            let dirPath = (filePath as NSString).deletingLastPathComponent
            let projectName = (dirPath as NSString).lastPathComponent

            let entries = parseFile(at: filePath, cutoffDate: nil, seenHashes: &seenHashes)
            if !entries.isEmpty {
                projectEntries[projectName, default: []].append(contentsOf: entries)
            }
        }

        return projectEntries.mapValues { UsageStatistics(entries: $0) }
    }

    // MARK: - Private helpers

    private func findJsonlFiles(in dirPath: String, fileManager: FileManager) -> [String] {
        guard let enumerator = fileManager.enumerator(atPath: dirPath) else { return [] }
        var result: [String] = []
        while let relative = enumerator.nextObject() as? String {
            if relative.hasSuffix(".jsonl") {
                result.append((dirPath as NSString).appendingPathComponent(relative))
            }
        }
        return result
    }

    /// Reads and parses a single JSONL file with mtime-based caching (no time filtering — stores all entries).
    /// On a cache hit the cached entries' hashes are inserted into seenHashes to keep deduplication correct.
    private func rawEntriesForFile(at filePath: String, seenHashes: inout Set<String>) -> [UsageEntry] {
        let attrs = try? FileManager.default.attributesOfItem(atPath: filePath)
        let mtime = attrs?[.modificationDate] as? Date

        // Cache only "cold" files (not modified in the last 60 s).
        // Active files being written by Claude have 1-second mtime granularity;
        // caching them would hide entries appended within the same second.
        let isStale = mtime.map { Date().timeIntervalSince($0) > 60 } ?? false
        if isStale, let mtime, let cached = fileCache[filePath], cached.mtime == mtime {
            for entry in cached.entries {
                let hash = "\(entry.messageId):\(entry.requestId)"
                if !entry.messageId.isEmpty && !entry.requestId.isEmpty {
                    seenHashes.insert(hash)
                }
            }
            return cached.entries
        }

        guard let content = try? String(contentsOfFile: filePath, encoding: .utf8) else {
            logger.warning("Cannot read file: \(filePath)")
            return []
        }

        var entries: [UsageEntry] = []
        let lines = content.components(separatedBy: .newlines)

        for line in lines {
            let trimmed = line.trimmingCharacters(in: .whitespaces)
            guard !trimmed.isEmpty else { continue }

            guard let data = trimmed.data(using: .utf8),
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
                continue
            }

            guard let timestampStr = json["timestamp"] as? String,
                  let timestamp = parseTimestamp(timestampStr) else {
                continue
            }

            let tokens = extractTokens(from: json)
            guard tokens.input > 0 || tokens.output > 0 || tokens.cacheRead > 0 || tokens.cacheCreate > 0 else {
                continue
            }

            let messageId = extractMessageId(from: json)
            let requestId = (json["request_id"] as? String) ?? (json["requestId"] as? String) ?? ""
            let hash = "\(messageId):\(requestId)"
            if !messageId.isEmpty && !requestId.isEmpty {
                if seenHashes.contains(hash) { continue }
                seenHashes.insert(hash)
            }

            let model = extractModel(from: json)
            let costUsd = calculateCost(from: json, model: model, tokens: tokens)

            entries.append(UsageEntry(
                id: hash.isEmpty ? UUID().uuidString : hash,
                timestamp: timestamp,
                inputTokens: tokens.input,
                outputTokens: tokens.output,
                cacheCreationTokens: tokens.cacheCreate,
                cacheReadTokens: tokens.cacheRead,
                costUsd: costUsd,
                model: model,
                messageId: messageId,
                requestId: requestId
            ))
        }

        if let mtime {
            fileCache[filePath] = FileCache(mtime: mtime, entries: entries)
        }
        return entries
    }

    /// Time-filtered wrapper around rawEntriesForFile, used by the legacy loadUsageEntries API
    private func parseFile(at filePath: String, cutoffDate: Date?, seenHashes: inout Set<String>) -> [UsageEntry] {
        let all = rawEntriesForFile(at: filePath, seenHashes: &seenHashes)
        guard let cutoff = cutoffDate else { return all }
        return all.filter { $0.timestamp >= cutoff }
    }

    // MARK: - Field extraction helpers

    private typealias TokenCounts = (input: Int, output: Int, cacheRead: Int, cacheCreate: Int)

    /// Extracts token counts, matching Python TokenExtractor.extract_tokens():
    /// - For type=="assistant": message.usage > usage > top-level
    /// - For all other types:  usage > message.usage > top-level
    private func extractTokens(from json: [String: Any]) -> TokenCounts {
        let isAssistant = (json["type"] as? String) == "assistant"
        let message = json["message"] as? [String: Any]
        let messageUsage = message?["usage"] as? [String: Any]
        let topUsage = json["usage"] as? [String: Any]

        var sources: [[String: Any]] = []

        if isAssistant {
            if let mu = messageUsage { sources.append(mu) }
            if let tu = topUsage { sources.append(tu) }
            sources.append(json)
        } else {
            if let tu = topUsage { sources.append(tu) }
            if let mu = messageUsage { sources.append(mu) }
            sources.append(json)
        }

        for source in sources {
            let input = intValue(source, keys: ["input_tokens", "inputTokens", "prompt_tokens"])
            let output = intValue(source, keys: ["output_tokens", "outputTokens", "completion_tokens"])

            if input > 0 || output > 0 {
                let cacheCreate = intValue(source, keys: ["cache_creation_tokens", "cache_creation_input_tokens", "cacheCreationInputTokens"])
                let cacheRead = intValue(source, keys: ["cache_read_input_tokens", "cache_read_tokens", "cacheReadInputTokens"])
                return (input: input, output: output, cacheRead: cacheRead, cacheCreate: cacheCreate)
            }
        }

        return (0, 0, 0, 0)
    }

    private func intValue(_ dict: [String: Any], keys: [String]) -> Int {
        for key in keys {
            if let v = dict[key] as? Int, v > 0 { return v }
            if let v = dict[key] as? Double, v > 0 { return Int(v) }
        }
        return 0
    }

    private func extractMessageId(from json: [String: Any]) -> String {
        if let mid = json["message_id"] as? String { return mid }
        if let msg = json["message"] as? [String: Any], let id = msg["id"] as? String { return id }
        return ""
    }

    /// Extracts the model name, matching Python DataConverter.extract_model_name
    private func extractModel(from json: [String: Any]) -> String {
        let message = json["message"] as? [String: Any]
        let usage = json["usage"] as? [String: Any]
        let request = json["request"] as? [String: Any]

        let candidates: [String?] = [
            message?["model"] as? String,
            json["model"] as? String,
            json["Model"] as? String,
            usage?["model"] as? String,
            request?["model"] as? String,
        ]

        for candidate in candidates {
            if let model = candidate, !model.isEmpty {
                return model
            }
        }
        return "unknown"
    }

    /// Calculates cost in USD, matching Python calculate_cost_for_entry AUTO mode:
    /// use the recorded cost_usd/cost field when present; fall back to the pricing model otherwise.
    private func calculateCost(from json: [String: Any], model: String, tokens: TokenCounts) -> Double {
        if let cost = json["cost_usd"] as? Double, cost > 0 { return cost }
        if let cost = json["cost"] as? Double, cost > 0 { return cost }

        let pricing = ModelPricing.forModel(model)
        return pricing.calculateCost(
            input: tokens.input,
            output: tokens.output,
            cacheCreation: tokens.cacheCreate,
            cacheRead: tokens.cacheRead
        )
    }

    /// Parses an ISO 8601 timestamp string (with or without fractional seconds)
    private func parseTimestamp(_ str: String) -> Date? {
        var normalized = str
        // Normalise Z suffix to +00:00, matching Python TimestampProcessor
        if normalized.hasSuffix("Z") {
            normalized = String(normalized.dropLast()) + "+00:00"
        }

        if let date = TokenDataReader.isoWithFractional.date(from: normalized) { return date }
        if let date = TokenDataReader.isoBasic.date(from: normalized) { return date }

        for formatter in TokenDataReader.fallbackDateFormatters {
            if let date = formatter.date(from: str) { return date }
        }

        return nil
    }
}
