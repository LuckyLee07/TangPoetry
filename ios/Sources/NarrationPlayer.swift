import SwiftUI
import AVFoundation
import MediaPlayer

struct NarrationManifest: Decodable {
    struct Recipe: Decodable { let voiceLabel: String }
    let recipe: Recipe
    let tracks: [String: NarrationTrack]
}

struct NarrationTrack: Decodable {
    let id: String
    let title: String
    let author: String
    let file: String
    let duration: Double
}

@MainActor final class NarrationPlayer: NSObject, ObservableObject, AVAudioPlayerDelegate {
    @Published private(set) var track: NarrationTrack?
    @Published private(set) var voiceLabel = "云希 · 男声"
    @Published private(set) var isPlaying = false
    @Published private(set) var elapsed: Double = 0
    @Published private(set) var duration: Double = 0
    @Published private(set) var error: String?
    @Published var rate: Float = 1 { didSet { player?.rate = rate; updateNowPlaying() } }
    private var player: AVAudioPlayer?
    private var timer: Timer?
    @Published private var manifest: NarrationManifest?
    var previewTracks: [NarrationTrack] { (manifest?.tracks.values.map { $0 } ?? []).sorted { $0.id < $1.id } }
    func hasAudio(for id: String) -> Bool { manifest?.tracks[id] != nil }
    private var hasStarted = false
    private var observations: [NSObjectProtocol] = []
    private var commands: [(MPRemoteCommand, Any)] = []

    override init() {
        super.init()
        manifest = try? BundledContent.decode("Audio/manifest.json")
        let center = NotificationCenter.default
        observations.append(center.addObserver(forName: AVAudioSession.interruptionNotification, object: nil, queue: .main) { [weak self] note in
            let type = (note.userInfo?[AVAudioSessionInterruptionTypeKey] as? UInt).flatMap(AVAudioSession.InterruptionType.init)
            if type == .began { Task { @MainActor in self?.pause() } }
        })
        observations.append(center.addObserver(forName: AVAudioSession.routeChangeNotification, object: nil, queue: .main) { [weak self] note in
            let reason = (note.userInfo?[AVAudioSessionRouteChangeReasonKey] as? UInt).flatMap(AVAudioSession.RouteChangeReason.init)
            if reason == .oldDeviceUnavailable { Task { @MainActor in self?.pause() } }
        })
        let remote = MPRemoteCommandCenter.shared()
        commands = [
            (remote.playCommand, remote.playCommand.addTarget { [weak self] _ in
                Task { @MainActor in self?.play() }; return .success
            }),
            (remote.pauseCommand, remote.pauseCommand.addTarget { [weak self] _ in
                Task { @MainActor in self?.pause() }; return .success
            }),
            (remote.togglePlayPauseCommand, remote.togglePlayPauseCommand.addTarget { [weak self] _ in
                Task { @MainActor in self?.toggle() }; return .success
            }),
            (remote.changePlaybackPositionCommand, remote.changePlaybackPositionCommand.addTarget { [weak self] event in
                guard let event = event as? MPChangePlaybackPositionCommandEvent else { return .commandFailed }
                let time = event.positionTime
                Task { @MainActor in self?.seek(to: time) }; return .success
            })
        ]
        remote.nextTrackCommand.isEnabled = false
        remote.previousTrackCommand.isEnabled = false
        setCommandsEnabled(false)
    }

    deinit {
        timer?.invalidate()
        observations.forEach(NotificationCenter.default.removeObserver)
        commands.forEach { $0.0.removeTarget($0.1) }
    }

    func load(_ poem: PoemSummary) {
        if track?.id == poem.id, player != nil { return }
        stop()
        do {
            if manifest == nil { manifest = try BundledContent.decode("Audio/manifest.json") }
            guard let narration = manifest?.tracks[poem.id] else { return }
            guard narration.id == poem.id else { throw ContentError.missingResource(poem.id) }
            let audio = try AVAudioPlayer(contentsOf: BundledContent.url(narration.file))
            audio.enableRate = true
            audio.rate = rate
            audio.delegate = self
            guard audio.prepareToPlay(), audio.duration.isFinite, audio.duration > 0 else {
                throw ContentError.missingResource(narration.file)
            }
            player = audio
            track = narration
            duration = audio.duration
            voiceLabel = manifest?.recipe.voiceLabel ?? voiceLabel
            error = nil
        } catch {
            self.error = "这首诗的音频暂时未能打开，请重新打开「听诗」重试。"
        }
    }

    func toggle() { isPlaying ? pause() : play() }

    func play() {
        guard let player else { return }
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playback, mode: .spokenAudio)
            try session.setActive(true)
            if elapsed >= duration - 0.1 { player.currentTime = 0 }
            player.rate = rate
            guard player.play() else { throw ContentError.missingResource(track?.file ?? "") }
            error = nil
            isPlaying = true
            hasStarted = true
            elapsed = player.currentTime
            setCommandsEnabled(true)
            updateNowPlaying()
            timer?.invalidate()
            let progressTimer = Timer(timeInterval: 0.2, repeats: true) { [weak self] _ in
                Task { @MainActor in
                    guard let self, self.isPlaying else { return }
                    self.elapsed = self.player?.currentTime ?? 0
                }
            }
            timer = progressTimer
            RunLoop.main.add(progressTimer, forMode: .common)
        } catch { self.error = "暂时无法播放，请再试一次。" }
    }

    func pause() {
        player?.pause()
        elapsed = player?.currentTime ?? elapsed
        isPlaying = false
        timer?.invalidate()
        timer = nil
        updateNowPlaying()
        if hasStarted { try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation) }
    }

    func seek(to time: Double) {
        guard time.isFinite, let player else { return }
        elapsed = min(max(time, 0), duration)
        player.currentTime = elapsed
        updateNowPlaying()
    }

    func stop() {
        player?.stop()
        player = nil
        timer?.invalidate()
        timer = nil
        track = nil
        isPlaying = false
        hasStarted = false
        elapsed = 0
        duration = 0
        error = nil
        MPNowPlayingInfoCenter.default().nowPlayingInfo = nil
        setCommandsEnabled(false)
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
    }

    private func setCommandsEnabled(_ enabled: Bool) {
        commands.forEach { $0.0.isEnabled = enabled }
    }

    private func updateNowPlaying() {
        guard hasStarted, let track, player != nil else { return }
        MPNowPlayingInfoCenter.default().nowPlayingInfo = [
            MPMediaItemPropertyTitle: track.title,
            MPMediaItemPropertyArtist: "唐 · \(track.author)",
            MPMediaItemPropertyAlbumTitle: "唐诗画笺 · 听诗",
            MPMediaItemPropertyPlaybackDuration: duration,
            MPNowPlayingInfoPropertyElapsedPlaybackTime: elapsed,
            MPNowPlayingInfoPropertyPlaybackRate: isPlaying ? rate : 0,
            MPNowPlayingInfoPropertyDefaultPlaybackRate: rate
        ]
    }

    nonisolated func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        Task { @MainActor [weak self] in
            guard let self, self.player === player else { return }
            self.pause()
            self.elapsed = flag ? self.duration : player.currentTime
            if !flag { self.error = "播放中断，请重新播放。" }
            self.updateNowPlaying()
        }
    }

    nonisolated func audioPlayerDecodeErrorDidOccur(_ player: AVAudioPlayer, error: Error?) {
        Task { @MainActor [weak self] in
            guard let self, self.player === player else { return }
            self.pause()
            self.error = "音频未能解码，请重新打开「听诗」重试。"
            self.player = nil
            self.setCommandsEnabled(false)
        }
    }
}

struct NarrationView: View {
    @ObservedObject var player: NarrationPlayer
    @EnvironmentObject private var store: PoemStore
    @Environment(\.dismiss) private var dismiss
    @State private var seeking = false
    @State private var seekTime: Double = 0

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: player.track == nil && player.error == nil ? 12 : 22) {
                    if player.track == nil && player.error == nil {
                        Text("先听五首").font(.title2)
                        Text("试试声音和节奏，选一首开始。")
                            .font(.callout).foregroundStyle(.secondary)
                        ForEach(player.previewTracks, id: \.id) { track in
                            Button { select(track) } label: {
                                HStack {
                                    Text(track.title)
                                    Spacer()
                                    Text(track.author).font(.caption).foregroundStyle(.secondary)
                                    Image(systemName: "play.circle").font(.title3)
                                }.frame(minHeight: 44)
                            }.accessibilityLabel("试听\(track.title)，\(track.author)")
                        }
                    } else {
                    VStack(spacing: 10) {
                        Text(player.track?.title ?? "听诗")
                            .font(.custom("STSongti-SC-Regular", size: 28, relativeTo: .title))
                            .multilineTextAlignment(.center).accessibilityAddTraits(.isHeader)
                        if let track = player.track { Text("唐 · \(track.author)").foregroundStyle(.secondary) }
                        Text("AI 朗读 · \(player.voiceLabel)").font(.caption).foregroundStyle(.secondary)
                    }
                    if let error = player.error {
                        Text(error).font(.callout).foregroundStyle(.secondary).multilineTextAlignment(.center)
                    }
                    VStack(spacing: 4) {
                        Slider(value: Binding(get: { seeking ? seekTime : player.elapsed }, set: {
                            seekTime = $0
                            if !seeking { player.seek(to: $0) }
                        }),
                               in: 0...max(1, player.duration)) { editing in
                            if editing { seekTime = player.elapsed }
                            else { player.seek(to: seekTime) }
                            seeking = editing
                        }
                        .disabled(player.track == nil)
                        .accessibilityLabel("朗读进度")
                        .accessibilityValue("\(timestamp(seeking ? seekTime : player.elapsed))，共 \(timestamp(player.duration))")
                        HStack {
                            Text(timestamp(seeking ? seekTime : player.elapsed))
                            Spacer()
                            Text(timestamp(player.duration))
                        }.font(.caption.monospacedDigit()).foregroundStyle(.secondary)
                    }
                    HStack(spacing: 32) {
                        Button { player.seek(to: player.elapsed - 10) } label: {
                            Image(systemName: "gobackward.10").font(.title2).frame(width: 48, height: 48)
                        }.accessibilityLabel("后退十秒")
                        Button(action: player.toggle) {
                            Image(systemName: player.isPlaying ? "pause.fill" : "play.fill")
                                .font(.system(size: 25)).frame(width: 72, height: 72)
                                .background(Color.brown.opacity(0.10), in: Circle())
                        }.accessibilityLabel(player.isPlaying ? "暂停朗读" : "播放朗读")
                        Button { player.seek(to: player.elapsed + 10) } label: {
                            Image(systemName: "goforward.10").font(.title2).frame(width: 48, height: 48)
                        }.accessibilityLabel("前进十秒")
                    }.disabled(player.track == nil)
                    Picker("朗读速度", selection: $player.rate) {
                        Text("0.85×").tag(Float(0.85))
                        Text("1×").tag(Float(1))
                        Text("1.15×").tag(Float(1.15))
                        Text("1.3×").tag(Float(1.3))
                    }.pickerStyle(.segmented)
                    Menu("更换试听诗 · \(player.previewTracks.count) 首") {
                        ForEach(player.previewTracks, id: \.id) { track in
                            Button("\(track.title) · \(track.author)") { select(track) }
                        }
                    }.frame(minHeight: 44)
                    Text("离线试听 · 锁屏后也可继续听")
                        .font(.caption).foregroundStyle(.secondary)
                    }
                }.padding(.horizontal, 28).padding(.vertical, 24)
            }
            .background(store.settings.paperColor)
            .navigationTitle("听诗").navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button("完成") { dismiss() } } }
        }
        .tint(.brown)
        .presentationDetents([.fraction(0.58), .large])
        .presentationContentInteraction(.scrolls)
        .presentationDragIndicator(.visible)
    }

    private func select(_ track: NarrationTrack) {
        guard let poem = store.poems.first(where: { $0.id == track.id }) else { return }
        store.openPoem(poem.id)
        player.load(poem)
        player.play()
    }

    private func timestamp(_ seconds: Double) -> String {
        let value = Int(max(0, seconds))
        return String(format: "%d:%02d", value / 60, value % 60)
    }
}
