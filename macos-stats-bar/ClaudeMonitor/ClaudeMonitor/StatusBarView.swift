//
//  StatusBarView.swift
//  ClaudeMonitor
//
//  Detail panel shown when the menu bar item is clicked.
//

import SwiftUI
import Charts

struct StatusBarView: View {
    @Environment(MonitoringViewModel.self) private var viewModel
    @State private var showingTodayStats = false
    @State private var showingChart = false
    @State private var showingSettings = false
    private var settings: AppSettings { AppSettings.shared }
    private var l10n: L10n { L10n.shared }

    var body: some View {
        if showingSettings {
            SettingsView { showingSettings = false }
        } else {
            mainView
        }
    }

    private var mainView: some View {
        VStack(spacing: 0) {
            // ── Header bar ──────────────────────────────────────────
            headerBar

            Divider()

            // ── Core stats cards ────────────────────────────────────
            statsGrid
                .padding(.horizontal, 16)
                .padding(.top, 12)

            // ── Project cost ranking ────────────────────────────────
            if settings.showProjectSection {
                Divider()
                    .padding(.vertical, 8)
                projectSection
                    .padding(.horizontal, 16)
            }

            // ── Recent records (latest 5) ───────────────────────────
            if settings.showRecentSection {
                Divider()
                    .padding(.vertical, 8)
                recentSection
                    .padding(.horizontal, 16)
            }

            // ── 30-day trend chart (collapsible) ────────────────────
            if settings.showChartSection {
                Divider()
                    .padding(.vertical, 8)
                chartSection
                    .padding(.horizontal, 16)
            }

            Divider()

            // ── Bottom toolbar ──────────────────────────────────────
            bottomBar
        }
        .frame(width: 340)
        .background(Color(.windowBackgroundColor))
    }

    // MARK: - Header bar

    private var headerBar: some View {
        HStack {
            Image(systemName: "cpu.fill")
                .foregroundColor(.accentColor)
            Text(l10n.str(.appTitle))
                .font(.headline)

            Spacer()

            // Last-updated time (always occupies space; spinner overlays while loading to prevent layout jitter)
            Text(viewModel.monitoringData.lastUpdated, format: .dateTime.hour().minute().second())
                .font(.caption2)
                .foregroundColor(.secondary)
                .opacity(viewModel.isLoading ? 0 : 1)
                .overlay {
                    if viewModel.isLoading {
                        ProgressView()
                            .scaleEffect(0.7)
                    }
                }

            Button {
                viewModel.refreshData()
            } label: {
                Image(systemName: "arrow.clockwise")
                    .imageScale(.small)
            }
            .buttonStyle(.borderless)
            .disabled(viewModel.isLoading)
            .keyboardShortcut("r", modifiers: .command)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
    }

    // MARK: - Core stats cards + live rates

    private var statsGrid: some View {
        let data = viewModel.monitoringData
        let rate = viewModel.tokenRate
        let cost = showingTodayStats ? data.todayCost : data.totalCost
        let inputTokens = showingTodayStats ? data.todayInputTokens : data.totalInputTokens
        let outputTokens = showingTodayStats ? data.todayOutputTokens : data.totalOutputTokens
        let cacheTokens = showingTodayStats ? data.todayCacheReadTokens : data.totalCacheReadTokens
        return VStack(spacing: 8) {
            // ── All / Today picker ───────────────────────────────────
            Picker("", selection: $showingTodayStats) {
                Text(l10n.str(.pickerAll)).tag(false)
                Text(l10n.str(.pickerToday)).tag(true)
            }
            .pickerStyle(.segmented)
            .labelsHidden()

            // ── Live rate bar (iStat-style) ──────────────────────────
            RateBar(rate: rate)

            // ── Stats cards (2×2) ────────────────────────────────────
            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 8) {
                StatCell(
                    icon: "dollarsign.circle.fill",
                    iconColor: .green,
                    label: showingTodayStats ? l10n.str(.todayCost) : l10n.str(.totalCost),
                    value: MonitoringViewModel.formatCost(cost)
                )
                StatCell(
                    icon: "arrow.down.circle.fill",
                    iconColor: .blue,
                    label: l10n.str(.inputTokens),
                    value: MonitoringViewModel.formatTokens(inputTokens)
                )
                StatCell(
                    icon: "arrow.up.circle.fill",
                    iconColor: .orange,
                    label: l10n.str(.outputTokens),
                    value: MonitoringViewModel.formatTokens(outputTokens)
                )
                StatCell(
                    icon: "memorychip.fill",
                    iconColor: .purple,
                    label: l10n.str(.cacheRead),
                    value: MonitoringViewModel.formatTokens(cacheTokens)
                )
            }
        }
    }

    // MARK: - Project cost ranking

    private var projectSection: some View {
        VStack(alignment: .leading, spacing: 6) {
            SectionHeader(title: l10n.str(.projectSectionTitle), systemImage: "folder.fill")

            if viewModel.monitoringData.projectCosts.isEmpty {
                Text(l10n.str(.noProjectData))
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .frame(maxWidth: .infinity, alignment: .center)
                    .padding(.vertical, 4)
            } else {
                let topProjects = viewModel.getTopProjects(limit: 5)
                let maxCost = topProjects.first?.1 ?? 1
                ForEach(topProjects, id: \.0) { name, cost in
                    ProjectRow(name: name, cost: cost, maxCost: maxCost)
                }
            }
        }
    }

    // MARK: - Recent records

    private var recentSection: some View {
        VStack(alignment: .leading, spacing: 6) {
            SectionHeader(title: l10n.str(.recentSectionTitle), systemImage: "clock.fill")

            let entries = viewModel.monitoringData.recentEntries.suffix(5).reversed()
            if entries.isEmpty {
                Text(l10n.str(.noRecentData))
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .frame(maxWidth: .infinity, alignment: .center)
                    .padding(.vertical, 4)
            } else {
                ForEach(Array(entries)) { entry in
                    RecentEntryRow(entry: entry)
                }
            }
        }
    }

    // MARK: - 30-day trend chart (collapsible)

    private var chartSection: some View {
        VStack(alignment: .leading, spacing: 6) {
            Button {
                withAnimation(.easeInOut(duration: 0.2)) {
                    showingChart.toggle()
                }
            } label: {
                HStack {
                    SectionHeader(title: l10n.str(.chartSectionTitle), systemImage: "chart.bar.fill")
                    Spacer()
                    Image(systemName: showingChart ? "chevron.up" : "chevron.down")
                        .imageScale(.small)
                        .foregroundColor(.secondary)
                }
            }
            .buttonStyle(.borderless)

            if showingChart {
                DailyBarChart(history: viewModel.dailyHistory)
                    .frame(height: 90)
                    .transition(.opacity.combined(with: .move(edge: .top)))
            }
        }
    }

    // MARK: - Bottom toolbar

    private var bottomBar: some View {
        HStack {
            // Error indicator
            if viewModel.errorMessage != nil {
                Image(systemName: "exclamationmark.triangle.fill")
                    .foregroundColor(.orange)
                    .imageScale(.small)
                Text(l10n.str(.noDataError))
                    .font(.caption2)
                    .foregroundColor(.secondary)
                    .lineLimit(1)
            } else {
                // Top model summary
                if let topModel = viewModel.getModelStatistics().first {
                    Image(systemName: "sparkles")
                        .imageScale(.small)
                        .foregroundColor(.secondary)
                    Text(topModel.0)
                        .font(.caption2)
                        .foregroundColor(.secondary)
                        .lineLimit(1)
                }
            }

            Spacer()

            // Settings button
            Button {
                showingSettings = true
            } label: {
                Image(systemName: "gearshape")
                    .imageScale(.small)
            }
            .buttonStyle(.borderless)
            .foregroundColor(.secondary)

            // Reset button
            Button(l10n.str(.resetButton)) {
                viewModel.resetStats()
            }
            .font(.caption)
            .buttonStyle(.borderless)
            .foregroundColor(.secondary)

            // Quit button
            Button(l10n.str(.quitButton)) {
                NSApplication.shared.terminate(nil)
            }
            .font(.caption)
            .buttonStyle(.borderless)
            .foregroundColor(.secondary)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 8)
    }
}

// MARK: - Sub-view: live rate bar (iStat Menus-style double row)

private struct RateBar: View {
    let rate: TokenRate

    var body: some View {
        HStack(spacing: 0) {
            // Input rate (tokens you send to Claude)
            HStack(spacing: 5) {
                Image(systemName: "arrow.up")
                    .foregroundColor(.blue)
                    .imageScale(.small)
                VStack(alignment: .leading, spacing: 0) {
                    Text(L10n.shared.str(.rateInputLabel))
                        .font(.system(size: 9))
                        .foregroundColor(.secondary)
                    Text(MonitoringViewModel.formatRate(rate.inputPerSec))
                        .font(.system(size: 13, weight: .semibold, design: .monospaced))
                        .foregroundColor(rate.inputPerSec > 0 ? .blue : .primary)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            Divider().frame(height: 28)

            // Output rate (tokens Claude sends back)
            HStack(spacing: 5) {
                Image(systemName: "arrow.down")
                    .foregroundColor(.orange)
                    .imageScale(.small)
                VStack(alignment: .leading, spacing: 0) {
                    Text(L10n.shared.str(.rateOutputLabel))
                        .font(.system(size: 9))
                        .foregroundColor(.secondary)
                    Text(MonitoringViewModel.formatRate(rate.outputPerSec))
                        .font(.system(size: 13, weight: .semibold, design: .monospaced))
                        .foregroundColor(rate.outputPerSec > 0 ? .orange : .primary)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.leading, 12)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(Color(.controlBackgroundColor))
        .cornerRadius(8)
        // Highlight border when active
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .strokeBorder(
                    rate.hasActivity ? Color.accentColor.opacity(0.4) : Color.clear,
                    lineWidth: 1
                )
        )
        .animation(.easeInOut(duration: 0.3), value: rate.hasActivity)
    }
}

// MARK: - Sub-view: stats card

private struct StatCell: View {
    let icon: String
    let iconColor: Color
    let label: String
    let value: String

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: icon)
                .foregroundColor(iconColor)
                .imageScale(.medium)
                .frame(width: 20)

            VStack(alignment: .leading, spacing: 1) {
                Text(label)
                    .font(.caption2)
                    .foregroundColor(.secondary)
                Text(value)
                    .font(.system(size: 13, weight: .semibold, design: .monospaced))
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(10)
        .background(Color(.controlBackgroundColor))
        .cornerRadius(8)
    }
}

// MARK: - Sub-view: project row with cost bar

private struct ProjectRow: View {
    let name: String
    let cost: Double
    let maxCost: Double

    var body: some View {
        VStack(alignment: .leading, spacing: 3) {
            HStack {
                // Directory name from ~/.claude/projects, percent-decoded
                Text(decodedName)
                    .font(.caption)
                    .lineLimit(1)
                    .truncationMode(.middle)
                Spacer()
                Text(MonitoringViewModel.formatCost(cost))
                    .font(.system(size: 11, weight: .semibold, design: .monospaced))
            }
            // Cost-share progress bar
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    RoundedRectangle(cornerRadius: 2)
                        .fill(Color(.separatorColor))
                        .frame(height: 3)
                    RoundedRectangle(cornerRadius: 2)
                        .fill(Color.accentColor.opacity(0.7))
                        .frame(width: max(4, geo.size.width * CGFloat(cost / max(maxCost, 0.0001))), height: 3)
                }
            }
            .frame(height: 3)
        }
    }

    private var decodedName: String {
        // Directory names under ~/.claude/projects are URL-encoded; decode and take the last segment
        let decoded = name.removingPercentEncoding ?? name
        return decoded.components(separatedBy: "/").last ?? decoded
    }
}

// MARK: - Sub-view: recent entry row

private struct RecentEntryRow: View {
    let entry: UsageEntry

    var body: some View {
        HStack(spacing: 6) {
            // Model badge
            Text(shortModel)
                .font(.system(size: 10, weight: .medium))
                .padding(.horizontal, 5)
                .padding(.vertical, 2)
                .background(Color.accentColor.opacity(0.15))
                .foregroundColor(.accentColor)
                .cornerRadius(4)

            // Token summary
            Text("↓\(MonitoringViewModel.formatTokens(entry.inputTokens)) ↑\(MonitoringViewModel.formatTokens(entry.outputTokens))")
                .font(.caption2)
                .foregroundColor(.secondary)

            Spacer()

            // Cost
            Text(MonitoringViewModel.formatCost(entry.costUsd))
                .font(.system(size: 11, weight: .semibold, design: .monospaced))
                .foregroundColor(entry.costUsd > 0 ? .primary : .secondary)

            // Time
            Text(entry.timestamp, format: .dateTime.hour().minute())
                .font(.caption2)
                .foregroundColor(.secondary)
                .frame(width: 36, alignment: .trailing)
        }
    }

    private var shortModel: String {
        // e.g. claude-3-5-sonnet-20241022 → "sonnet"
        let m = entry.model.lowercased()
        if m.contains("opus") { return "opus" }
        if m.contains("sonnet") { return "sonnet" }
        if m.contains("haiku") { return "haiku" }
        return String(entry.model.prefix(6))
    }
}

// MARK: - Sub-view: section header

private struct SectionHeader: View {
    let title: String
    let systemImage: String

    var body: some View {
        Label(title, systemImage: systemImage)
            .font(.caption)
            .fontWeight(.semibold)
            .foregroundColor(.secondary)
            .textCase(.uppercase)
    }
}

// MARK: - Sub-view: 30-day daily cost bar chart

private struct DailyBarChart: View {
    let history: [(day: Date, cost: Double, tokens: Int)]

    var body: some View {
        if history.isEmpty {
            Text(L10n.shared.str(.noChartData))
                .font(.caption)
                .foregroundColor(.secondary)
                .frame(maxWidth: .infinity, alignment: .center)
                .padding(.vertical, 8)
        } else {
            Chart(history, id: \.day) { item in
                BarMark(
                    x: .value(L10n.shared.axisDate, item.day, unit: .day),
                    y: .value(L10n.shared.axisCost, item.cost)
                )
                .foregroundStyle(Color.accentColor.gradient)
                .cornerRadius(2)
            }
            .chartXAxis {
                AxisMarks(values: .stride(by: .day, count: 7)) { _ in
                    AxisGridLine()
                    AxisValueLabel(format: .dateTime.month(.abbreviated).day())
                        .font(.system(size: 9))
                }
            }
            .chartYAxis {
                AxisMarks(position: .leading, values: .automatic(desiredCount: 3)) { value in
                    AxisGridLine()
                    AxisValueLabel {
                        if let v = value.as(Double.self) {
                            Text(String(format: "$%.2f", v))
                                .font(.system(size: 9))
                        }
                    }
                }
            }
            .chartPlotStyle { plotArea in
                plotArea.background(Color(.controlBackgroundColor))
            }
        }
    }
}
