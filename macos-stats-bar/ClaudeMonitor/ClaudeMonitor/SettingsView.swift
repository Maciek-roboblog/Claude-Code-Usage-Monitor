import SwiftUI

struct SettingsView: View {
    var onDismiss: () -> Void = {}
    @Environment(MonitoringViewModel.self) private var viewModel
    private var settings: AppSettings { AppSettings.shared }
    private var l10n: L10n { L10n.shared }

    var body: some View {
        VStack(spacing: 0) {
            // ── Title bar ───────────────────────────────────────────
            HStack {
                Image(systemName: "gearshape.fill")
                    .foregroundColor(.accentColor)
                Text(l10n.str(.settingsTitle))
                    .font(.headline)
                Spacer()
                Button {
                    onDismiss()
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundColor(.secondary)
                        .imageScale(.medium)
                }
                .buttonStyle(.borderless)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 10)

            Divider()

            // ── Settings content ────────────────────────────────────
            VStack(alignment: .leading, spacing: 16) {

                // System
                settingsSectionHeader(title: l10n.str(.sectionSystem), icon: "desktopcomputer")

                SettingsToggleRow(
                    icon: "power",
                    iconColor: .green,
                    title: l10n.str(.launchAtLoginTitle),
                    subtitle: l10n.str(.launchAtLoginSubtitle),
                    isOn: Binding(
                        get: { settings.launchAtLogin },
                        set: { settings.launchAtLogin = $0 }
                    )
                )

                SettingsToggleRow(
                    icon: "dock.rectangle",
                    iconColor: .indigo,
                    title: l10n.str(.showDockIconTitle),
                    subtitle: l10n.str(.showDockIconSubtitle),
                    isOn: Binding(
                        get: { settings.showDockIcon },
                        set: { settings.showDockIcon = $0 }
                    )
                )

                RefreshIntervalRow(
                    interval: Binding(
                        get: { settings.refreshInterval },
                        set: { newValue in
                            settings.refreshInterval = newValue
                            viewModel.restartAutoRefresh()
                        }
                    )
                )

                Divider()

                // Language
                settingsSectionHeader(title: "语言 / Language", icon: "globe")

                Picker("", selection: Binding(
                    get: { settings.language },
                    set: { settings.language = $0 }
                )) {
                    ForEach(AppLanguage.allCases, id: \.self) { lang in
                        Text(lang.displayName).tag(lang)
                    }
                }
                .pickerStyle(.segmented)
                .labelsHidden()

                Divider()

                // Display
                settingsSectionHeader(title: l10n.str(.sectionDisplay), icon: "eye.fill")

                SettingsToggleRow(
                    icon: "folder.fill",
                    iconColor: .blue,
                    title: l10n.str(.topProjectsTitle),
                    subtitle: l10n.str(.topProjectsSubtitle),
                    isOn: Binding(
                        get: { settings.showProjectSection },
                        set: { settings.showProjectSection = $0 }
                    )
                )

                SettingsToggleRow(
                    icon: "clock.fill",
                    iconColor: .orange,
                    title: l10n.str(.recentRecordsTitle),
                    subtitle: l10n.str(.recentRecordsSubtitle),
                    isOn: Binding(
                        get: { settings.showRecentSection },
                        set: { settings.showRecentSection = $0 }
                    )
                )

                SettingsToggleRow(
                    icon: "chart.bar.fill",
                    iconColor: .purple,
                    title: l10n.str(.trendTitle),
                    subtitle: l10n.str(.trendSubtitle),
                    isOn: Binding(
                        get: { settings.showChartSection },
                        set: { settings.showChartSection = $0 }
                    )
                )
            }
            .padding(16)

            Spacer(minLength: 0)
        }
        .frame(width: 340)
        .background(Color(.windowBackgroundColor))
    }

    private func settingsSectionHeader(title: String, icon: String) -> some View {
        Label(title, systemImage: icon)
            .font(.caption)
            .fontWeight(.semibold)
            .foregroundColor(.secondary)
            .textCase(.uppercase)
            .frame(maxWidth: .infinity, alignment: .leading)
    }
}

// MARK: - Refresh interval row

private struct RefreshIntervalRow: View {
    @Binding var interval: Int

    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: "arrow.clockwise.circle.fill")
                .foregroundColor(.cyan)
                .imageScale(.medium)
                .frame(width: 22)

            VStack(alignment: .leading, spacing: 1) {
                Text(L10n.shared.str(.refreshIntervalTitle))
                    .font(.callout)
                Text(L10n.shared.str(.refreshIntervalSubtitle))
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }

            Spacer()

            Picker("", selection: $interval) {
                ForEach(AppSettings.refreshIntervalOptions, id: \.self) { sec in
                    Text(L10n.shared.refreshSec(sec)).tag(sec)
                }
            }
            .pickerStyle(.menu)
            .labelsHidden()
            .frame(width: 72)
        }
        .padding(.vertical, 2)
    }
}

// MARK: - Settings toggle row

private struct SettingsToggleRow: View {
    let icon: String
    let iconColor: Color
    let title: String
    let subtitle: String
    @Binding var isOn: Bool

    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: icon)
                .foregroundColor(iconColor)
                .imageScale(.medium)
                .frame(width: 22)

            VStack(alignment: .leading, spacing: 1) {
                Text(title)
                    .font(.callout)
                Text(subtitle)
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }

            Spacer()

            Toggle("", isOn: $isOn)
                .toggleStyle(.switch)
                .labelsHidden()
                .scaleEffect(0.8)
        }
        .padding(.vertical, 2)
    }
}
