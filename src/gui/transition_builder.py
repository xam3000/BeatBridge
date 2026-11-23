"""Native UI for loading tracks, choosing a pair and rendering a preview."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import uuid

from PySide6.QtCore import QEvent, QMimeData, QObject, QRunnable, QThreadPool, QTimer, QUrl, Qt, Signal
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .waveform import WaveformWidget
from .ml_transition import discover_control_models


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".flac", ".mp3", ".ogg", ".m4a"}
ANALYSIS_CACHE = REPOSITORY_ROOT / "output" / "pre_analysis"
FEATURE_CACHE = REPOSITORY_ROOT / "output" / "feature_cache"
TRANSITION_OUTPUT = REPOSITORY_ROOT / "output" / "gui_transitions"
TARGET_SAMPLE_RATE = 44_100


@dataclass
class TrackItem:
    path: Path
    status: str = "Noch nicht analysiert"
    bpm: float | None = None
    sample_rate: int | None = None
    beat_frames: tuple = ()
    downbeat_seconds: tuple[float, ...] = ()
    grid_source: str | None = None
    fallback_used: bool | None = None
    error: str | None = None


class _AnalysisSignals(QObject):
    finished = Signal(str, object, str)


class _CacheProbeTask(QRunnable):
    def __init__(self, path: Path, analysis_cache: Path):
        super().__init__()
        self.path = Path(path)
        self.analysis_cache = Path(analysis_cache)
        self.signals = _AnalysisSignals()

    def run(self):
        try:
            import librosa
            from src.analysis.models import unpack_analysis_result
            from src.analysis.pre_analysis import PreAnalysis

            analyser = PreAnalysis(str(self.analysis_cache) + os.sep)
            result = analyser.load_cached_analysis(self.path)
            if result is None:
                self.signals.finished.emit(str(self.path), None, "")
                return
            bpm, beat_frames, metadata = unpack_analysis_result(result)
            sample_rate = int(librosa.get_samplerate(str(self.path)))
            downbeats = tuple(
                int(frame[0]) / sample_rate
                for frame in beat_frames
                if isinstance(frame, (tuple, list)) and len(frame) >= 3 and int(frame[1]) == 1
            )
            self.signals.finished.emit(str(self.path), {
                "bpm": float(bpm),
                "beat_frames": tuple(beat_frames),
                "sample_rate": sample_rate,
                "downbeat_seconds": downbeats,
                "grid_source": metadata.grid_source,
                "fallback_used": metadata.fallback_used,
                "cache_status": analyser.previous_analysis_kind,
            }, "")
        except Exception as error:
            self.signals.finished.emit(str(self.path), None, f"{type(error).__name__}: {error}")


class TrackLibraryList(QListWidget):
    filesDropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)

    def mimeData(self, items):
        mime = QMimeData()
        paths = [item.data(Qt.ItemDataRole.UserRole) for item in items]
        mime.setUrls([QUrl.fromLocalFile(str(path)) for path in paths if path])
        mime.setData("application/x-beatbridge-library-tracks", "\n".join(paths).encode("utf-8"))
        return mime

    def dragEnterEvent(self, event):
        if event.source() is self:
            event.ignore()
            return
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.source() is self:
            event.ignore()
            return
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.source() is self:
            event.ignore()
            return
        paths = _local_paths_from_mime(event.mimeData())
        if paths:
            self.filesDropped.emit(paths)
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
            return
        super().dropEvent(event)


class SequenceDropPanel(QFrame):
    filesDropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasFormat("application/x-beatbridge-library-tracks"):
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasFormat("application/x-beatbridge-library-tracks"):
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        paths = _local_paths_from_mime(event.mimeData())
        if paths:
            QTimer.singleShot(0, lambda paths=paths: self.filesDropped.emit(paths))
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
            return
        super().dropEvent(event)


class ApplicationDropWidget(QWidget):
    filesDropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.source() is None and event.mimeData().hasUrls():
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.source() is None and event.mimeData().hasUrls():
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.source() is None:
            paths = _local_paths_from_mime(event.mimeData())
            if paths:
                self.filesDropped.emit(paths)
                event.setDropAction(Qt.DropAction.CopyAction)
                event.accept()
                return
        super().dropEvent(event)


class SequenceListWidget(QListWidget):
    tracksDropped = Signal(list, int)
    orderChanged = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragDropOverwriteMode(False)
        self.viewport().setAcceptDrops(True)
        self.viewport().installEventFilter(self)

    def eventFilter(self, watched, event):
        if watched is self.viewport() and event.type() in {
            QEvent.Type.DragEnter, QEvent.Type.DragMove, QEvent.Type.Drop,
        }:
            source = event.source() if hasattr(event, "source") else None
            mime = event.mimeData()
            is_track_drop = mime.hasUrls() or mime.hasFormat("application/x-beatbridge-library-tracks")
            if source not in (self, self.viewport()) and is_track_drop:
                if event.type() == QEvent.Type.Drop:
                    paths = _local_paths_from_mime(mime)
                    if paths:
                        row = self.indexAt(event.position().toPoint()).row()
                        insert_at = self.count() if row < 0 else row
                        QTimer.singleShot(
                            0,
                            lambda paths=paths, insert_at=insert_at: self.tracksDropped.emit(paths, insert_at),
                        )
                event.setDropAction(Qt.DropAction.CopyAction)
                event.accept()
                return True
        return super().eventFilter(watched, event)

    def dragEnterEvent(self, event):
        if event.source() is self or event.mimeData().hasUrls() or event.mimeData().hasFormat("application/x-beatbridge-library-tracks"):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.source() is self or event.mimeData().hasUrls() or event.mimeData().hasFormat("application/x-beatbridge-library-tracks"):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.source() in (self, self.viewport()):
            super().dropEvent(event)
            paths = [self.item(row).data(Qt.ItemDataRole.UserRole) for row in range(self.count())]
            self.orderChanged.emit(paths)
            return
        paths = []
        if event.mimeData().hasUrls():
            paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        elif event.mimeData().hasFormat("application/x-beatbridge-library-tracks"):
            raw = bytes(event.mimeData().data("application/x-beatbridge-library-tracks"))
            paths = raw.decode("utf-8").splitlines()
        if paths:
            row = self.indexAt(event.position().toPoint()).row()
            self.tracksDropped.emit(paths, self.count() if row < 0 else row)
            event.acceptProposedAction()
            return
        super().dropEvent(event)


class _TrackAnalysisTask(QRunnable):
    def __init__(self, path: Path, analysis_cache: Path):
        super().__init__()
        self.path = path
        self.analysis_cache = Path(analysis_cache)
        self.signals = _AnalysisSignals()

    def run(self):
        try:
            import librosa
            from src.analysis.models import unpack_analysis_result
            from src.analysis.pre_analysis import PreAnalysis

            analyser = PreAnalysis(str(self.analysis_cache) + os.sep)
            result = analyser(str(self.path))
            bpm, beat_frames, metadata = unpack_analysis_result(result)
            sample_rate = int(librosa.get_samplerate(str(self.path)))
            downbeats = []
            for frame in beat_frames:
                if isinstance(frame, (tuple, list)) and len(frame) >= 3 and int(frame[1]) == 1:
                    downbeats.append(int(frame[0]) / sample_rate)
            self.signals.finished.emit(
                str(self.path),
                {
                    "bpm": float(bpm),
                    "beat_frames": tuple(beat_frames),
                    "sample_rate": sample_rate,
                    "downbeat_seconds": tuple(downbeats),
                    "grid_source": metadata.grid_source,
                    "fallback_used": metadata.fallback_used,
                    "cache_status": analyser.previous_analysis_kind or "neu analysiert",
                },
                "",
            )
        except Exception as error:
            self.signals.finished.emit(str(self.path), None, f"{type(error).__name__}: {error}")


class _CueAnalysisTask(QRunnable):
    """Generate and feature-rank transition candidates inside both selections."""

    def __init__(self, source: TrackItem, target: TrackItem, source_range, target_range,
                 transition_bars: int, analysis_cache: Path):
        super().__init__()
        self.source = source
        self.target = target
        self.source_range = source_range
        self.target_range = target_range
        self.transition_bars = int(transition_bars)
        self.analysis_cache = Path(analysis_cache)
        self.signals = _RenderSignals()

    def run(self):
        try:
            import librosa
            import numpy as np
            from src.analysis.models import unpack_analysis_result
            from src.analysis.pre_analysis import PreAnalysis
            from src.candidates import BaselineCandidateGenerationConfig, TrackReference, generate_candidates
            from src.ranking import rank_candidates
            from src.tempo.cue_alignment import filter_candidate_grids

            analyzer = PreAnalysis(str(self.analysis_cache) + os.sep)
            source_result = analyzer(str(self.source.path))
            target_result = analyzer(str(self.target.path))
            source_bpm, source_frames, source_metadata = unpack_analysis_result(source_result)
            target_bpm, target_frames, target_metadata = unpack_analysis_result(target_result)
            source_rate = int(librosa.get_samplerate(str(self.source.path)))
            target_rate = int(librosa.get_samplerate(str(self.target.path)))

            def to_target_grid(frames, sample_rate):
                return tuple(
                    (int(round(int(frame[0]) * TARGET_SAMPLE_RATE / sample_rate)), int(frame[1]), int(frame[2]))
                    for frame in frames
                )

            source_range_samples = tuple(round(value * TARGET_SAMPLE_RATE) for value in self.source_range)
            target_range_samples = tuple(round(value * TARGET_SAMPLE_RATE) for value in self.target_range)
            source_grid = to_target_grid(source_frames, source_rate)
            target_grid = to_target_grid(target_frames, target_rate)
            generated = generate_candidates(
                TrackReference(str(self.source.path), _sha256_file(self.source.path)),
                float(source_bpm), source_grid,
                TrackReference(str(self.target.path), _sha256_file(self.target.path)),
                float(target_bpm), target_grid,
                source_grid_metadata=source_metadata,
                target_grid_metadata=target_metadata,
                config=BaselineCandidateGenerationConfig(
                    transition_lengths_bars=(self.transition_bars,),
                    approximate_grid_policy="allow",
                ),
                source_cutpoint_range_samples=source_range_samples,
                target_cutpoint_range_samples=target_range_samples,
            )
            generated = filter_candidate_grids(generated, source_grid, target_grid, TARGET_SAMPLE_RATE)
            if not generated.candidates:
                reasons = "; ".join(dict.fromkeys(item.message for item in generated.rejections))
                raise ValueError(reasons or "In den ausgewählten Bereichen wurden keine Cuepoint-Kandidaten gefunden.")
            candidates_to_rank = generated.candidates
            max_ranked_candidates = 400
            if len(candidates_to_rank) > max_ranked_candidates:
                # Keep candidates spread across the deterministic generation
                # order so a whole-track selection cannot exhaust memory.
                indices = np.linspace(
                    0, len(candidates_to_rank) - 1, max_ranked_candidates, dtype=np.int64
                )
                candidates_to_rank = tuple(candidates_to_rank[int(index)] for index in indices)
            ranked = rank_candidates(candidates_to_rank, target_sample_rate=TARGET_SAMPLE_RATE)
            if not ranked.scores:
                details = "; ".join(item.message for item in ranked.failures[:3])
                raise ValueError("Kandidaten konnten nicht bewertet werden" + (f": {details}" if details else "."))
            best = ranked.scores[0]
            candidate = next(item for item in candidates_to_rank if item.candidate_id == best.candidate_id)
            self.signals.finished.emit({
                "source_seconds": candidate.source_cutpoint.sample / TARGET_SAMPLE_RATE,
                "target_seconds": candidate.target_cutpoint.sample / TARGET_SAMPLE_RATE,
                "score": best.total_score,
                "candidate_count": len(generated.candidates),
                "ranked_count": len(ranked.scores),
                "ranker": ranked.ranker,
                "source_analysis": (float(source_bpm), tuple(source_frames), source_rate, source_metadata),
                "target_analysis": (float(target_bpm), tuple(target_frames), target_rate, target_metadata),
            }, "")
        except Exception as error:
            self.signals.finished.emit(None, f"{type(error).__name__}: {error}")


class _RenderSignals(QObject):
    finished = Signal(object, str)


class _MashupTask(QRunnable):
    def __init__(self, plan, destination, cache):
        super().__init__()
        self.plan, self.destination, self.cache = plan, destination, cache
        self.signals = _RenderSignals()

    def run(self):
        try:
            from src.analysis.pre_analysis import PreAnalysis
            from src.mashup import export_mashup

            export_mashup(self.plan, self.destination, PreAnalysis(self.cache))
            self.signals.finished.emit(str(self.destination / "mashup.wav"), "")
        except Exception as error:
            self.signals.finished.emit(None, str(error))


class _TransitionRenderTask(QRunnable):
    def __init__(self, source: TrackItem, target: TrackItem, source_seconds: float,
                 target_seconds: float, transition_bars: int, renderer: str,
                 analysis_cache: Path, model_run: Path | None = None):
        super().__init__()
        self.source = source
        self.target = target
        self.source_seconds = source_seconds
        self.target_seconds = target_seconds
        self.transition_bars = transition_bars
        self.renderer = renderer
        self.analysis_cache = Path(analysis_cache)
        self.model_run = Path(model_run) if model_run else None
        self.signals = _RenderSignals()

    def run(self):
        try:
            import numpy as np
            import soundfile as sf
            from src.analysis.models import unpack_analysis_result
            from src.analysis.pre_analysis import PreAnalysis
            from src.pipeline import render_transition
            from src.ranking import RenderedTransitionInput, rank_rendered_transitions

            analysis = PreAnalysis(str(self.analysis_cache) + os.sep)
            source_cut = int(round(self.source_seconds * TARGET_SAMPLE_RATE))
            target_cut = int(round(self.target_seconds * TARGET_SAMPLE_RATE))
            transition_beats = self.transition_bars * 4
            model_provenance = None
            if self.model_run is None:
                source_bpm = float(self.source.bpm) if self.source.bpm else float(unpack_analysis_result(analysis(str(self.source.path)))[0])
                target_bpm = float(self.target.bpm) if self.target.bpm else float(unpack_analysis_result(analysis(str(self.target.path)))[0])
                result = render_transition(
                    str(self.source.path), str(self.target.path), source_cut, target_cut,
                    renderer=self.renderer, baseline_bars=self.transition_bars,
                    target_sample_rate=TARGET_SAMPLE_RATE, analysis=analysis,
                    source_bpm=source_bpm, target_bpm=target_bpm,
                )
            else:
                from .ml_transition import render_model_transition

                result, model_provenance = render_model_transition(
                    self.source.path, self.target.path,
                    source_seconds=self.source_seconds, target_seconds=self.target_seconds,
                    source_bpm=None, target_bpm=None,
                    transition_bars=self.transition_bars,
                    analysis=analysis, analysis_cache=self.analysis_cache,
                    feature_cache=FEATURE_CACHE, model_run=self.model_run,
                )
                source_bpm = model_provenance["source_bpm"]
                target_bpm = model_provenance["target_bpm"]

            source_sha = _sha256_file(self.source.path)
            target_sha = _sha256_file(self.target.path)
            selected_method = model_provenance["model_name"] if model_provenance else self.renderer
            identity = "|".join((source_sha, target_sha, str(source_cut), str(target_cut), str(transition_beats), selected_method))
            transition_id = "manual-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
            run_id = uuid.uuid4().hex[:8]
            TRANSITION_OUTPUT.mkdir(parents=True, exist_ok=True)
            output_path = TRANSITION_OUTPUT / f"{transition_id}_{selected_method}_{run_id}.wav"
            temp_audio = output_path.with_name(f".{output_path.name}.{uuid.uuid4().hex}.tmp.wav")
            try:
                sf.write(str(temp_audio), np.asarray(result.audio).T, int(result.sample_rate), format="WAV")
                os.replace(temp_audio, output_path)
            finally:
                temp_audio.unlink(missing_ok=True)

            ranked = rank_rendered_transitions((
                RenderedTransitionInput(
                    candidate_id=transition_id,
                    renderer=selected_method,
                    audio=result.audio,
                    sample_rate=result.sample_rate,
                    transition_start_sample=result.transition_start_sample,
                    transition_end_sample=result.transition_end_sample,
                    transition_length_beats=transition_beats,
                    bpm=source_bpm,
                ),
            ))
            score = ranked.scores[0].to_dict() if ranked.scores else None
            payload = {
                "format_version": 1,
                "workflow": "manual_sequence_edge_transition_v1",
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "source": {"path": str(self.source.path), "sha256": source_sha, "requested_cue_seconds": self.source_seconds, "bpm": source_bpm},
                "target": {"path": str(self.target.path), "sha256": target_sha, "requested_cue_seconds": self.target_seconds, "bpm": target_bpm},
                "transition_id": transition_id,
                "renderer": selected_method,
                "transition_length_bars": self.transition_bars,
                "transition_length_beats": transition_beats,
                "output_file": output_path.name,
                "sample_rate": result.sample_rate,
                "sample_count": int(result.audio.shape[-1]),
                "transition_start_sample": result.transition_start_sample,
                "transition_end_sample": result.transition_end_sample,
                "tempo_backend": result.tempo_backend,
                "tempo_alignment": getattr(result, "tempo_alignment", None),
                "evaluation_type": "rendered_transition_baseline_v1" if model_provenance is None else "rendered_transition_with_learned_controls_v1",
                "evaluation": score,
                "evaluation_failures": [item.to_dict() for item in ranked.failures],
                "model": model_provenance,
            }
            sidecar_path = output_path.with_suffix(".json")
            temp_json = sidecar_path.with_name(f".{sidecar_path.name}.{uuid.uuid4().hex}.tmp")
            try:
                temp_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                os.replace(temp_json, sidecar_path)
            finally:
                temp_json.unlink(missing_ok=True)
            self.signals.finished.emit(
                {
                    "output_path": output_path,
                    "sidecar_path": sidecar_path,
                    "transition_id": transition_id,
                    "renderer": selected_method,
                    "bars": self.transition_bars,
                    "score": score,
                    "metric_failures": [item.message for item in ranked.failures],
                    "transition_start_sample": result.transition_start_sample,
                    "transition_end_sample": result.transition_end_sample,
                    "sample_rate": result.sample_rate,
                    "sample_count": int(result.audio.shape[-1]),
                    "tempo_backend": result.tempo_backend,
                },
                "",
            )
        except Exception as error:
            self.signals.finished.emit(None, f"{type(error).__name__}: {error}")


class TransitionBuilderWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BeatBridge — Übergang erstellen")
        self.resize(1540, 1000)
        self.setMinimumSize(1160, 790)
        self.tracks: dict[str, TrackItem] = {}
        self.analysis_cache = ANALYSIS_CACHE
        self._pool = QThreadPool.globalInstance()
        self._analysis_busy: set[str] = set()
        self._cache_probe_busy: set[str] = set()
        self._render_busy = False
        self._last_result = None
        self._playing_path: str | None = None
        self._last_source_path: str | None = None
        self._last_target_path: str | None = None
        self._source_cue_set = False
        self._target_cue_set = False
        self.sequence_tracks: list[str] = []
        self._sections: dict[str, tuple[float, float | None]] = {}
        self._active_edge_index: int | None = None
        self._edge_cues: dict[int, tuple[float, float, bool, bool]] = {}
        self._edge_ranges: dict[int, tuple[tuple | None, tuple | None]] = {}
        self._edge_settings: dict[int, tuple[int, str, str | None]] = {}
        self._edge_results: dict[int, dict] = {}

        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.audio_output.setVolume(0.85)
        self.player.setAudioOutput(self.audio_output)
        self.player.positionChanged.connect(self._on_player_position)
        self.player.playbackStateChanged.connect(self._on_player_state)
        self.player.errorOccurred.connect(self._on_player_error)

        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        central = ApplicationDropWidget(self)
        central.filesDropped.connect(self._import_audio_paths)
        main = QHBoxLayout(central)
        main.setContentsMargins(14, 12, 14, 12)
        main.setSpacing(14)

        library = QFrame()
        library.setObjectName("panel")
        library.setMinimumWidth(250)
        library.setMaximumWidth(340)
        library_layout = QVBoxLayout(library)
        library_title = QLabel("Trackbibliothek")
        library_title.setObjectName("sectionTitle")
        library_layout.addWidget(library_title)
        import_row = QHBoxLayout()
        self.add_tracks_button = QPushButton("＋ Audiodateien laden")
        self.add_tracks_button.clicked.connect(self._open_audio_dialog)
        self.remove_tracks_button = QPushButton("Entfernen")
        self.remove_tracks_button.clicked.connect(self._remove_selected_tracks)
        import_row.addWidget(self.add_tracks_button, 1)
        import_row.addWidget(self.remove_tracks_button)
        library_layout.addLayout(import_row)
        self.track_list = TrackLibraryList()
        self.track_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.track_list.filesDropped.connect(self._import_audio_paths)
        self.track_list.itemDoubleClicked.connect(self._analyze_selected_tracks)
        library_layout.addWidget(self.track_list, 1)
        self.sequence_add_button = QPushButton("＋ Zur Sequenz hinzufügen")
        self.sequence_add_button.clicked.connect(self._add_selected_to_sequence)
        library_layout.addWidget(self.sequence_add_button)
        self.analyze_button = QPushButton("Ausgewählte analysieren")
        self.analyze_button.clicked.connect(self._analyze_selected_tracks)
        library_layout.addWidget(self.analyze_button)
        cache_row = QHBoxLayout()
        self.cache_path = QLineEdit(str(self.analysis_cache))
        self.cache_path.setReadOnly(True)
        self.cache_path.setToolTip("Cachebasis; passende Einträge werden anhand Audio-SHA und Analyseversion geladen.")
        self.cache_path_button = QPushButton("Cacheordner …")
        self.cache_path_button.clicked.connect(self._choose_analysis_cache)
        cache_row.addWidget(self.cache_path, 1)
        cache_row.addWidget(self.cache_path_button)
        library_layout.addLayout(cache_row)
        library_note = QLabel("Tracks in die Sequenz ziehen · Originaldateien bleiben unverändert.")
        library_note.setObjectName("muted")
        library_note.setWordWrap(True)
        library_layout.addWidget(library_note)
        main.addWidget(library)

        workspace = QVBoxLayout()
        workspace.setSpacing(10)
        top_bar = QFrame()
        top_bar.setObjectName("topBar")
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(12, 6, 12, 6)
        brand_mark = QLabel("◖")
        brand_mark.setObjectName("brandMark")
        top_bar_layout.addWidget(brand_mark)
        title = QLabel("BeatBridge")
        title.setObjectName("brand")
        top_bar_layout.addWidget(title)
        top_bar_layout.addSpacing(20)
        project_label = QLabel("Mashup · aktuelle Sequenz")
        project_label.setObjectName("projectLabel")
        top_bar_layout.addWidget(project_label)
        top_bar_layout.addStretch(1)
        self.previous_edge_button = QPushButton("|◀")
        self.previous_edge_button.setToolTip("Vorheriger Übergang")
        self.previous_edge_button.clicked.connect(lambda: self.edge_combo.setCurrentIndex(max(0, self.edge_combo.currentIndex() - 1)))
        self.preview_button = QPushButton("▶ Vorschau")
        self.preview_button.setToolTip("Gerenderten Übergang abspielen oder pausieren")
        self.preview_button.clicked.connect(self._toggle_preview)
        self.next_edge_button = QPushButton("▶|")
        self.next_edge_button.setToolTip("Nächster Übergang")
        self.next_edge_button.clicked.connect(lambda: self.edge_combo.setCurrentIndex(min(self.edge_combo.count() - 1, self.edge_combo.currentIndex() + 1)))
        top_bar_layout.addWidget(self.previous_edge_button)
        top_bar_layout.addWidget(self.preview_button)
        top_bar_layout.addWidget(self.next_edge_button)
        workspace.addWidget(top_bar)
        header = QHBoxLayout()
        header.addWidget(QLabel("ARRANGEMENT"))
        header.addStretch(1)
        header.addWidget(QLabel("Klick setzt einen Cuepoint · Ziehen markiert den Suchbereich"))
        workspace.addLayout(header)

        sequence_panel = SequenceDropPanel()
        sequence_panel.setObjectName("panel")
        sequence_panel.filesDropped.connect(
            lambda paths: self._import_audio_paths(paths, len(self.sequence_tracks))
        )
        sequence_layout = QVBoxLayout(sequence_panel)
        sequence_header = QHBoxLayout()
        sequence_heading = QLabel("MASHUP-SEQUENZ · Song A → Song B → Song C …")
        sequence_heading.setObjectName("sectionTitle")
        sequence_header.addWidget(sequence_heading)
        sequence_header.addStretch(1)
        self.sequence_up_button = QPushButton("↑")
        self.sequence_up_button.clicked.connect(lambda: self._move_sequence_track(-1))
        self.sequence_down_button = QPushButton("↓")
        self.sequence_down_button.clicked.connect(lambda: self._move_sequence_track(1))
        self.sequence_remove_button = QPushButton("Aus Sequenz entfernen")
        self.sequence_remove_button.clicked.connect(self._remove_sequence_track)
        section_button = QPushButton("Songabschnitt …")
        section_button.clicked.connect(self._edit_section)
        self.export_button = QPushButton("Mashup exportieren …")
        self.export_button.clicked.connect(self._export_mashup)
        sequence_header.addWidget(section_button)
        sequence_header.addWidget(self.sequence_up_button)
        sequence_header.addWidget(self.sequence_down_button)
        sequence_header.addWidget(self.sequence_remove_button)
        sequence_header.addWidget(self.export_button)
        sequence_layout.addLayout(sequence_header)
        self.sequence_list = SequenceListWidget()
        self.sequence_list.setFlow(QListWidget.Flow.LeftToRight)
        self.sequence_list.setWrapping(False)
        self.sequence_list.setMaximumHeight(76)
        self.sequence_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.sequence_list.setToolTip("Tracks aus der Bibliothek oder dem Windows-Explorer hier ablegen. Zum Sortieren einen Sequenztrack ziehen.")
        self.sequence_list.currentRowChanged.connect(self._select_edge_for_sequence_row)
        self.sequence_list.tracksDropped.connect(self._import_audio_paths)
        self.sequence_list.orderChanged.connect(self._apply_dragged_sequence_order)
        sequence_layout.addWidget(self.sequence_list)
        workspace.addWidget(sequence_panel)

        pair_panel = QFrame()
        pair_panel.setObjectName("panel")
        pair_layout = QHBoxLayout(pair_panel)
        self.pair_title = QLabel("Noch kein Übergang gewählt")
        self.pair_title.setObjectName("sectionTitle")
        pair_layout.addWidget(self.pair_title)
        pair_layout.addStretch(1)
        self.source_combo = QComboBox()
        self.target_combo = QComboBox()
        self.edge_combo = QComboBox()
        self.edge_combo.setMinimumWidth(260)
        self.edge_combo.currentIndexChanged.connect(self._change_active_edge)
        pair_layout.addWidget(QLabel("AKTIVER PAARÜBERGANG"))
        pair_layout.addWidget(self.edge_combo, 1)
        self.source_combo.setVisible(False)
        self.target_combo.setVisible(False)
        self.source_combo.currentIndexChanged.connect(self._load_pair_waveforms)
        self.target_combo.currentIndexChanged.connect(self._load_pair_waveforms)
        workspace.addWidget(pair_panel)

        wave_split = QSplitter(Qt.Orientation.Vertical)
        source_group, self.source_wave, self._source_summary = self._build_track_wave_panel("A · Song A ausblenden")
        target_group, self.target_wave, self._target_summary = self._build_track_wave_panel("B · Song B einblenden")
        self.source_wave.set_accent_color("#29d4f0")
        self.target_wave.set_accent_color("#ff5f88")
        self.source_wave.cue_changed.connect(lambda seconds: self._set_cue("source", seconds))
        self.target_wave.cue_changed.connect(lambda seconds: self._set_cue("target", seconds))
        self.source_wave.range_changed.connect(lambda start, end: self._set_selected_range("source", start, end))
        self.target_wave.range_changed.connect(lambda start, end: self._set_selected_range("target", start, end))
        self.source_wave.range_cleared.connect(self._clear_selected_ranges)
        self.target_wave.range_cleared.connect(self._clear_selected_ranges)
        self.source_wave.duration_loaded.connect(lambda seconds: self._set_cue_limit("source", seconds))
        self.target_wave.duration_loaded.connect(lambda seconds: self._set_cue_limit("target", seconds))
        wave_split.addWidget(source_group)
        wave_split.addWidget(target_group)
        wave_split.setMinimumHeight(390)
        timeline_panel = QFrame()
        timeline_panel.setObjectName("panel")
        timeline_layout = QVBoxLayout(timeline_panel)
        timeline_header = QHBoxLayout()
        timeline_header.addWidget(QLabel("ÜBERGANG · 2 SPUREN"))
        timeline_header.addStretch(1)
        timeline_header.addWidget(QLabel("A → B"))
        timeline_layout.addLayout(timeline_header)
        timeline_layout.addWidget(wave_split, 1)

        controls = QFrame()
        controls.setObjectName("panel")
        controls.setMinimumWidth(270)
        controls.setMaximumWidth(330)
        controls_layout = QVBoxLayout(controls)
        controls_layout.addWidget(QLabel("ÜBERGANGSEINSTELLUNGEN"))
        controls_layout.addWidget(QLabel("A-CUEPOINT · SEKUNDEN"))
        self.source_cue = self._cue_input()
        self.source_cue.valueChanged.connect(self.source_wave.set_cue_seconds)
        self.source_cue.valueChanged.connect(lambda _value: self._mark_cue_set("source"))
        self.source_cue.editingFinished.connect(lambda: self._mark_cue_set("source"))
        controls_layout.addWidget(self.source_cue)
        play_source = QPushButton("▶ A")
        play_source.clicked.connect(lambda: self._play_track("source"))
        controls_layout.addWidget(play_source)
        controls_layout.addWidget(QLabel("B-CUEPOINT · SEKUNDEN"))
        self.target_cue = self._cue_input()
        self.target_cue.valueChanged.connect(self.target_wave.set_cue_seconds)
        self.target_cue.valueChanged.connect(lambda _value: self._mark_cue_set("target"))
        self.target_cue.editingFinished.connect(lambda: self._mark_cue_set("target"))
        controls_layout.addWidget(self.target_cue)
        play_target = QPushButton("▶ B")
        play_target.clicked.connect(lambda: self._play_track("target"))
        controls_layout.addWidget(play_target)
        controls_layout.addWidget(QLabel("LÄNGE"))
        self.length_combo = QComboBox()
        for bars in (1, 2, 3, 4):
            self.length_combo.addItem("1 Takt" if bars == 1 else f"{bars} Takte", bars)
        self.length_combo.setCurrentIndex(self.length_combo.findData(2))
        controls_layout.addWidget(self.length_combo)
        self.find_cues_button = QPushButton("Beste Cuepoints in Bereichen suchen")
        self.find_cues_button.setToolTip("Ziehe in beiden Wellenformen einen Bereich auf. Der Cue-Point-Analyzer bewertet darin passende Downbeats.")
        self.find_cues_button.clicked.connect(self._analyze_cue_ranges)
        controls_layout.addWidget(self.find_cues_button)
        controls_layout.addWidget(QLabel("BASELINE-RENDERER"))
        self.renderer_combo = QComboBox()
        for label, value in (("Equal Power", "equal_power"), ("Linearer Fade", "fade"), ("Hard Cut", "simple")):
            self.renderer_combo.addItem(label, value)
        controls_layout.addWidget(self.renderer_combo)
        controls_layout.addWidget(QLabel("ML-MODELL"))
        self.model_combo = QComboBox()
        self.model_combo.addItem("Kein ML-Modell · Baseline", None)
        for label, run_path in discover_control_models(REPOSITORY_ROOT / "output" / "training_runs"):
            self.model_combo.addItem(label, str(run_path))
        self.model_combo.currentIndexChanged.connect(self._on_model_changed)
        for combo in (self.length_combo, self.renderer_combo, self.model_combo):
            combo.activated.connect(self._invalidate_preview)
        controls_layout.addWidget(self.model_combo, 1)
        model_note = QLabel("Das ausgewählte Modell sagt die Mixing-Kontrollen für dieses Paar voraus. Modelle sind experimentell.")
        model_note.setObjectName("muted")
        model_note.setWordWrap(True)
        controls_layout.addWidget(model_note)
        self.render_button = QPushButton("Übergang rendern & bewerten")
        self.render_button.setObjectName("primary")
        self.render_button.clicked.connect(self._render_transition)
        controls_layout.addWidget(self.render_button)
        controls_layout.addStretch(1)
        editor_layout = QHBoxLayout()
        editor_layout.addWidget(timeline_panel, 1)
        editor_layout.addWidget(controls)
        workspace.addLayout(editor_layout, 1)

        result_panel = QFrame()
        result_panel.setObjectName("panel")
        result_layout = QVBoxLayout(result_panel)
        result_header = QHBoxLayout()
        result_heading = QLabel("Vorschau und technische Bewertung")
        result_heading.setObjectName("sectionTitle")
        result_header.addWidget(result_heading)
        result_header.addStretch(1)
        self.metric_label = QLabel("Noch kein Übergang gerendert · Bewertet wird das erzeugte Audio")
        self.metric_label.setObjectName("metric")
        result_header.addWidget(self.metric_label)
        result_layout.addLayout(result_header)
        self.result_wave = WaveformWidget()
        self.result_wave.setMinimumHeight(105)
        self.result_wave.setMaximumHeight(145)
        result_layout.addWidget(self.result_wave)
        self.result_detail = QLabel("Wähle beide Cuepoints und rendere eine Vorschau.")
        self.result_detail.setObjectName("muted")
        self.result_detail.setWordWrap(True)
        self.result_detail.setTextFormat(Qt.TextFormat.PlainText)
        result_layout.addWidget(self.result_detail)
        workspace.addWidget(result_panel)

        self.status_label = QLabel("Audiodateien laden oder in die Sequenz ziehen. Cache wird beim Import geprüft; Cuepoints in der Wellenform setzen.")
        self.status_label.setObjectName("status")
        self.status_label.setTextFormat(Qt.TextFormat.PlainText)
        workspace.addWidget(self.status_label)

        workspace_widget = QWidget()
        workspace_widget.setLayout(workspace)
        main.addWidget(workspace_widget, 1)
        self.setCentralWidget(central)

        open_action = QAction("Audiodateien laden", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._open_audio_dialog)
        self.addAction(open_action)
        analyze_action = QAction("Ausgewählte Tracks analysieren", self)
        analyze_action.setShortcut(QKeySequence("Ctrl+I"))
        analyze_action.triggered.connect(self._analyze_selected_tracks)
        self.addAction(analyze_action)

    def _choose_analysis_cache(self):
        chosen = QFileDialog.getExistingDirectory(
            self, "BeatBridge-Analyse-Cache auswählen", str(self.analysis_cache)
        )
        if chosen:
            self.analysis_cache = Path(chosen).expanduser().resolve()
            self.cache_path.setText(str(self.analysis_cache))
            self.status_label.setText(
                "Cacheordner gesetzt. Beim nächsten Analysieren werden passende SHA- und versionsgebundene Einträge geladen."
            )

    def _add_selected_to_sequence(self):
        selected = [item.data(Qt.ItemDataRole.UserRole) for item in self.track_list.selectedItems()]
        added = [path for path in selected if path not in self.sequence_tracks]
        if not added:
            self.status_label.setText("Wähle zuerst einen oder mehrere neue Songs in der Bibliothek aus.")
            return
        sequence = self.sequence_tracks + added
        self._replace_sequence(sequence, select_edge=max(0, len(sequence) - 2))

    def _edit_section(self):
        row = self.sequence_list.currentRow()
        if row < 0:
            self.status_label.setText("Wähle einen Song in der Sequenz.")
            return
        path = self.sequence_tracks[row]
        import librosa

        try:
            duration = librosa.get_duration(path=path)
        except Exception as error:
            self.status_label.setText(f"Trackdauer konnte nicht gelesen werden: {error}")
            return
        left, right = self._sections.get(path, (0.0, None))
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Songabschnitt · {Path(path).stem}")
        layout = QVBoxLayout(dialog)
        start, end = self._cue_input(), self._cue_input()
        for label, box, value in (("Anfang", start, left), ("Ende", end, right or duration)):
            box.setDecimals(3)
            box.setMaximum(duration)
            box.setValue(value)
            layout.addWidget(QLabel(label))
            layout.addWidget(box)
        controls = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        controls.accepted.connect(dialog.accept)
        controls.rejected.connect(dialog.reject)
        layout.addWidget(controls)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if start.value() >= end.value():
            self.status_label.setText("Der Abschnitt muss vor seinem Ende beginnen.")
            return
        right = None if end.value() == end.maximum() else end.value()
        self._sections[path] = start.value(), right
        self._refresh_sequence()

    def _export_plan(self):
        self._remember_active_edge()
        if len(self.sequence_tracks) < 2:
            raise ValueError("Füge mindestens zwei Songs zur Sequenz hinzu.")
        sections, edges = [], []
        for path in self.sequence_tracks:
            start, end = self._sections.get(path, (0.0, None))
            sections.append(dict(path=Path(path).as_posix(), start_seconds=start, end_seconds=end))
        for index in range(len(sections) - 1):
            cue = self._edge_cues.get(index)
            if not cue or not all(cue[2:]):
                raise ValueError(f"Setze beide Cuepoints für Übergang {index + 1}.")
            bars, renderer, model = self._edge_settings.get(index, (4, "equal_power", None))
            if model:
                raise ValueError(f"Wähle für Übergang {index + 1} einen Baseline-Renderer. "
                                 "ML-Modelle sind im Paarvergleich verfügbar.")
            edges.append(dict(source_seconds=cue[0], target_seconds=cue[1], bars=bars, renderer=renderer))
        return dict(format_version=1, sections=sections, edges=edges)

    def _export_mashup(self):
        try:
            plan = self._export_plan()
        except ValueError as error:
            self.status_label.setText(str(error))
            return
        parent = QFileDialog.getExistingDirectory(self, "Zielordner für WAV und Exportmanifest auswählen")
        if not parent:
            return
        destination = Path(parent) / ("BeatBridge-" + uuid.uuid4().hex[:12])
        task = _MashupTask(plan, destination, self.analysis_cache)
        task.signals.finished.connect(self._on_mashup_exported, Qt.ConnectionType.QueuedConnection)
        self.export_button.setEnabled(False)
        self.status_label.setText("Die Sequenz wird mit den gewählten Abschnitten und Übergängen exportiert …")
        self._pool.start(task)

    def _on_mashup_exported(self, path, error):
        self.export_button.setEnabled(True)
        self.status_label.setText(f"Mashup-Export fehlgeschlagen: {error}" if error else f"Mashup gespeichert: {path}")

    def _replace_sequence(self, sequence, *, select_edge):
        self._remember_active_edge()
        old = {pair: i for i, pair in enumerate(zip(self.sequence_tracks, self.sequence_tracks[1:]))}
        new = list(zip(sequence, sequence[1:]))
        for state in (self._edge_cues, self._edge_ranges, self._edge_settings, self._edge_results):
            kept = {i: state[old[pair]] for i, pair in enumerate(new) if pair in old and old[pair] in state}
            state.clear()
            state.update(kept)
        self.sequence_tracks = list(sequence)
        self._active_edge_index = None
        self._refresh_sequence(select_edge=select_edge)

    def _refresh_sequence(self, *, select_edge=None):
        if not hasattr(self, "sequence_list"):
            return
        selected_row = self.sequence_list.currentRow()
        self.sequence_list.blockSignals(True)
        self.sequence_list.clear()
        for index, path in enumerate(self.sequence_tracks):
            track = self.tracks.get(path)
            title = track.path.stem if track else Path(path).stem
            bpm = f" · {track.bpm:.1f} BPM" if track and track.bpm else ""
            section = self._sections.get(path)
            span = ""
            if section:
                stop = "Ende" if section[1] is None else f"{section[1]:.2f} s"
                span = f" · {section[0]:.2f} s – {stop}"
            item = QListWidgetItem(f"{chr(65 + index)}  {title}{bpm}{span}")
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setToolTip(str(path))
            self.sequence_list.addItem(item)
        self.sequence_list.blockSignals(False)
        self.edge_combo.blockSignals(True)
        self.edge_combo.clear()
        for index, (source, target) in enumerate(zip(self.sequence_tracks, self.sequence_tracks[1:])):
            source_name = self.tracks[source].path.stem if source in self.tracks else Path(source).stem
            target_name = self.tracks[target].path.stem if target in self.tracks else Path(target).stem
            state = " · ✓ Vorschau" if index in self._edge_results else " · offen"
            self.edge_combo.addItem(f"{chr(65 + index)} → {chr(66 + index)} · {source_name} → {target_name}{state}", index)
        if select_edge is None:
            select_edge = self._active_edge_index if self._active_edge_index is not None else min(selected_row, self.edge_combo.count() - 1)
        if self.edge_combo.count():
            self.edge_combo.setCurrentIndex(max(0, min(int(select_edge), self.edge_combo.count() - 1)))
        self.edge_combo.blockSignals(False)
        self._change_active_edge(self.edge_combo.currentIndex())

    def _remember_active_edge(self):
        if self._active_edge_index is not None and hasattr(self, "source_cue"):
            self._edge_cues[self._active_edge_index] = (
                self.source_cue.value(), self.target_cue.value(),
                self._source_cue_set, self._target_cue_set,
            )
            self._edge_settings[self._active_edge_index] = (
                int(self.length_combo.currentData()),
                str(self.renderer_combo.currentData()),
                self.model_combo.currentData(),
            )
            source_range = self.source_wave.selection_range_seconds
            target_range = self.target_wave.selection_range_seconds
            self._edge_ranges[self._active_edge_index] = (source_range, target_range)

    def _change_active_edge(self, index):
        self._remember_active_edge()
        if index < 0 or index + 1 >= len(self.sequence_tracks):
            self._active_edge_index = None
            self.pair_title.setText("Noch kein Übergang gewählt")
            self.source_combo.blockSignals(True)
            self.target_combo.blockSignals(True)
            self.source_combo.setCurrentIndex(-1)
            self.target_combo.setCurrentIndex(-1)
            self.source_combo.blockSignals(False)
            self.target_combo.blockSignals(False)
            self._load_pair_waveforms()
            self._last_result = None
            self.result_wave.clear("Füge zwei oder mehr Songs zur Sequenz hinzu.")
            self.metric_label.setText("Noch keine technische Bewertung")
            self.result_detail.setText("Jedes benachbarte Songpaar erhält einen eigenen Übergang.")
            if hasattr(self, "status_label"):
                self.status_label.setText("Füge mindestens zwei Songs zur Sequenz hinzu; jeder Nachbar erhält einen eigenen Übergang.")
            return
        self._active_edge_index = int(index)
        settings = self._edge_settings.get(index, (4, "equal_power", None))
        self.length_combo.setCurrentIndex(self.length_combo.findData(settings[0]))
        self.renderer_combo.setCurrentIndex(self.renderer_combo.findData(settings[1]))
        model_index = self.model_combo.findData(settings[2])
        self.model_combo.setCurrentIndex(max(0, model_index))
        source_path, target_path = self.sequence_tracks[index:index + 2]
        self.source_combo.blockSignals(True)
        self.target_combo.blockSignals(True)
        self.source_combo.setCurrentIndex(self.source_combo.findData(source_path))
        self.target_combo.setCurrentIndex(self.target_combo.findData(target_path))
        self.source_combo.blockSignals(False)
        self.target_combo.blockSignals(False)
        source_name = self.tracks[source_path].path.stem
        target_name = self.tracks[target_path].path.stem
        self.pair_title.setText(f"{chr(65 + index)} → {chr(66 + index)} · {source_name} → {target_name}")
        if self.sequence_list.currentRow() not in (index, index + 1):
            self.sequence_list.setCurrentRow(index)
        self._load_pair_waveforms()
        cues = self._edge_cues.get(index)
        self.source_cue.blockSignals(True)
        self.target_cue.blockSignals(True)
        self.source_cue.setValue(cues[0] if cues else 0.0)
        self.target_cue.setValue(cues[1] if cues else 0.0)
        self.source_cue.blockSignals(False)
        self.target_cue.blockSignals(False)
        self._source_cue_set = cues[2] if cues else False
        self._target_cue_set = cues[3] if cues else False
        self.source_wave.set_cue_seconds(cues[0] if cues and cues[2] else None)
        self.target_wave.set_cue_seconds(cues[1] if cues and cues[3] else None)
        ranges = self._edge_ranges.get(index, (None, None))
        for wave, bounds in zip((self.source_wave, self.target_wave), ranges):
            if bounds is None:
                wave.clear_selection_range(notify=False)
            else:
                wave.set_selection_range(*bounds)
        saved_result = self._edge_results.get(index)
        if saved_result:
            self._show_transition_result(saved_result)
        else:
            self._last_result = None
            self.result_wave.clear("Für diesen Paarübergang wurde noch keine Vorschau gerendert.")
            self.metric_label.setText("Noch keine technische Bewertung")
            self.result_detail.setText("Setze beide Cuepoints und rendere diesen Übergang.")

    def _select_edge_for_sequence_row(self, row):
        if self.edge_combo.count() and row >= 0:
            self.edge_combo.setCurrentIndex(min(int(row), self.edge_combo.count() - 1))

    def _invalidate_preview(self, *_):
        if self._edge_results.pop(self._active_edge_index, None) is not None:
            self._last_result = None
            self.result_wave.clear("Für die geänderten Einstellungen eine neue Vorschau rendern.")
            self.metric_label.setText("Noch keine technische Bewertung")
            self.result_detail.setText("")
            index = self._active_edge_index
            self.edge_combo.setItemText(index, self.edge_combo.itemText(index).replace("✓ Vorschau", "offen"))

    def _move_sequence_track(self, offset):
        row = self.sequence_list.currentRow()
        target = row + int(offset)
        if row < 0 or target < 0 or target >= len(self.sequence_tracks):
            return
        sequence = self.sequence_tracks.copy()
        sequence[row], sequence[target] = sequence[target], sequence[row]
        self._replace_sequence(sequence, select_edge=max(0, min(row, target, len(sequence) - 2)))
        self.sequence_list.setCurrentRow(target)

    def _remove_sequence_track(self):
        row = self.sequence_list.currentRow()
        if row < 0:
            return
        self._replace_sequence(self.sequence_tracks[:row] + self.sequence_tracks[row + 1:],
                               select_edge=max(0, row - 1))

    def _mark_cue_set(self, role):
        setattr(self, "_source_cue_set" if role == "source" else "_target_cue_set", True)
        if self._active_edge_index is not None:
            cues = (
                self.source_cue.value(), self.target_cue.value(),
                self._source_cue_set, self._target_cue_set,
            )
            if self._edge_cues.get(self._active_edge_index) != cues:
                self._invalidate_preview()
            self._edge_cues[self._active_edge_index] = cues

    def _on_model_changed(self, *_):
        is_ml = bool(self.model_combo.currentData())
        self.renderer_combo.setEnabled(not is_ml)
        self.length_combo.setEnabled(not is_ml)
        if is_ml and int(self.length_combo.currentData()) != 4:
            self.length_combo.setCurrentIndex(self.length_combo.findData(4))
        self.status_label.setText(
            "ML-Controller ausgewählt; experimentelle Modellkontrolle, nur mit vier Takten."
            if is_ml else "Equal Power/Fade als technische Baseline ausgewählt."
        )

    def _build_track_wave_panel(self, title):
        frame = QFrame()
        frame.setObjectName("laneA" if title.startswith("A ·") else "laneB")
        layout = QVBoxLayout(frame)
        heading_row = QHBoxLayout()
        heading = QLabel(title)
        heading.setObjectName("trackHeading")
        heading_row.addWidget(heading)
        summary = QLabel("Track noch nicht ausgewählt")
        summary.setObjectName("muted")
        summary.setMinimumWidth(0)
        summary.setMaximumHeight(24)
        summary.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        summary.setWordWrap(False)
        heading_row.addWidget(summary, 1)
        layout.addLayout(heading_row)
        waveform = WaveformWidget()
        waveform.setMinimumHeight(195)
        waveform.set_cue_selection_enabled(True)
        layout.addWidget(waveform, 1)
        summary.setTextFormat(Qt.TextFormat.PlainText)
        return frame, waveform, summary

    def _cue_input(self):
        box = QDoubleSpinBox()
        box.setDecimals(2)
        box.setRange(0.0, 86_400.0)
        box.setSingleStep(0.25)
        box.setSuffix(" s")
        return box

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #101a21; color: #e4edf1; font-size: 13px; }
            QFrame#panel { background: #15232c; border: 1px solid #2b414d; border-radius: 7px; }
            QFrame#topBar { background: #111e26; border: 1px solid #2b414d; border-radius: 7px; }
            QFrame#laneA { background: #112630; border: 1px solid #235265; border-radius: 7px; }
            QFrame#laneB { background: #2b1c29; border: 1px solid #694052; border-radius: 7px; }
            QLabel#brand { color: #45d5ee; font-size: 21px; font-weight: 700; }
            QLabel#brandMark { color: #45d5ee; font-size: 25px; font-weight: 700; }
            QLabel#projectLabel { color: #bdcbd1; font-size: 14px; }
            QLabel#sectionTitle { color: #dce8ed; font-weight: 650; }
            QLabel#trackHeading { color: #b5c8d0; font-weight: 650; }
            QLabel#muted { color: #9aadb7; }
            QLabel#metric { color: #c8b6ff; font-weight: 650; }
            QLabel#status { color: #a8bac3; padding: 3px; }
            QPushButton, QComboBox, QDoubleSpinBox { background: #1b303b; border: 1px solid #3a5664; border-radius: 5px; padding: 7px 9px; }
            QPushButton:hover { background: #24404d; }
            QPushButton#primary { color: #071317; background: #45d5ee; font-weight: 700; padding-inline: 14px; }
            QPushButton:disabled { color: #71838b; background: #17232a; }
            QListWidget { background: #0d171d; border: 1px solid #2b414d; border-radius: 5px; alternate-background-color: #13212a; }
            QListWidget::item { padding: 9px 6px; border-bottom: 1px solid #22343e; }
            QListWidget::item:selected { background: #254653; }
            QDoubleSpinBox { min-width: 88px; }
        """)

    def _open_audio_dialog(self):
        patterns = " ".join(f"*{suffix}" for suffix in sorted(SUPPORTED_AUDIO_EXTENSIONS))
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Audiodateien zur Trackbibliothek hinzufügen", str(Path.cwd()),
            f"Audiodateien ({patterns});;Alle Dateien (*.*)",
        )
        if not paths:
            return
        self._import_audio_paths(paths)

    def _import_audio_paths(self, paths, sequence_insert_index=None):
        added_paths = []
        paths_for_sequence = []
        for raw_path in paths:
            path = Path(raw_path).expanduser().resolve()
            if path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS or not path.is_file():
                continue
            key = str(path)
            if key not in self.tracks:
                self.tracks[key] = TrackItem(path, status="Cache wird geprüft …")
                added_paths.append(key)
            if sequence_insert_index is not None:
                paths_for_sequence.append(key)
        self._refresh_tracks()
        if sequence_insert_index is not None:
            insert_at = max(0, min(int(sequence_insert_index), len(self.sequence_tracks)))
            new_sequence_paths = [path for path in dict.fromkeys(paths_for_sequence) if path not in self.sequence_tracks]
            if new_sequence_paths:
                sequence = self.sequence_tracks[:insert_at] + new_sequence_paths + self.sequence_tracks[insert_at:]
                self._replace_sequence(sequence, select_edge=max(0, min(insert_at - 1, len(sequence) - 2)))
        for key in added_paths:
            self._probe_track_cache(key)
        if added_paths:
            self.status_label.setText(f"{len(added_paths)} Track(s) importiert. Gültige Analyse-Caches werden geprüft; Cache-Misses bleiben als nicht analysiert markiert.")
        elif sequence_insert_index is not None:
            self.status_label.setText("Track(s) zur Sequenz hinzugefügt.")

    def _probe_track_cache(self, path):
        if path in self._cache_probe_busy or path not in self.tracks:
            return
        self._cache_probe_busy.add(path)
        task = _CacheProbeTask(self.tracks[path].path, self.analysis_cache)
        task.signals.finished.connect(self._on_cache_probe_finished)
        self._pool.start(task)

    def _on_cache_probe_finished(self, path, result, error):
        self._cache_probe_busy.discard(path)
        track = self.tracks.get(path)
        if track is None:
            return
        if error:
            track.status = "Cache-Prüfung fehlgeschlagen"
            track.error = error
        elif result is None:
            track.status = "Nicht analysiert"
            track.error = None
        else:
            track.status = "Fallback · Analyse wiederholbar" if result["fallback_used"] else "Analysiert · Cache geladen"
            track.bpm = result["bpm"]
            track.sample_rate = result["sample_rate"]
            track.beat_frames = result["beat_frames"]
            track.downbeat_seconds = result["downbeat_seconds"]
            track.grid_source = result["grid_source"]
            track.fallback_used = result["fallback_used"]
            track.error = None
        self._refresh_tracks()

    def _apply_dragged_sequence_order(self, paths):
        ordered = [str(path) for path in paths if str(path) in self.tracks]
        if ordered == self.sequence_tracks:
            return
        self._replace_sequence(ordered, select_edge=0)
        self.status_label.setText("Sequenz neu sortiert. Stelle die Cuepoints für neu entstandene Songpaare ein.")

    def _remove_selected_tracks(self):
        selected = [item.data(Qt.ItemDataRole.UserRole) for item in self.track_list.selectedItems()]
        if not selected:
            return
        for path in selected:
            if path not in self._analysis_busy:
                self.tracks.pop(path, None)
                self._sections.pop(path, None)
        self._replace_sequence([path for path in self.sequence_tracks if path in self.tracks], select_edge=0)
        self._refresh_tracks()

    def _refresh_tracks(self):
        previous_edge = self._active_edge_index
        self._remember_active_edge()
        self._active_edge_index = None
        selected = {item.data(Qt.ItemDataRole.UserRole) for item in self.track_list.selectedItems()}
        self.track_list.clear()
        for path, track in self.tracks.items():
            bpm_text = f" · {track.bpm:.1f} BPM" if track.bpm is not None else ""
            item = QListWidgetItem(f"{track.path.name}\n{track.status}{bpm_text}")
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setToolTip(str(track.path) + (f"\n{track.error}" if track.error else ""))
            self.track_list.addItem(item)
            if path in selected:
                item.setSelected(True)
        self._refresh_pair_combos()
        self._refresh_sequence(select_edge=previous_edge)

    def _refresh_pair_combos(self):
        source_before = self.source_combo.currentData()
        target_before = self.target_combo.currentData()
        values = list(self.tracks.items())
        for combo in (self.source_combo, self.target_combo):
            combo.blockSignals(True)
            combo.clear()
            for path, track in values:
                label = track.path.name + (f" · {track.bpm:.1f} BPM" if track.bpm is not None else "")
                combo.addItem(label, path)
            combo.blockSignals(False)
        if source_before in self.tracks:
            self.source_combo.setCurrentIndex(self.source_combo.findData(source_before))
        elif values:
            self.source_combo.setCurrentIndex(0)
        if target_before in self.tracks:
            self.target_combo.setCurrentIndex(self.target_combo.findData(target_before))
        elif len(values) > 1:
            self.target_combo.setCurrentIndex(1)
        elif values:
            self.target_combo.setCurrentIndex(0)
        self._load_pair_waveforms()

    def _load_pair_waveforms(self, *_):
        for role, combo, waveform, summary, cue_input in (
            ("source", self.source_combo, self.source_wave, self._source_summary, self.source_cue),
            ("target", self.target_combo, self.target_wave, self._target_summary, self.target_cue),
        ):
            path = combo.currentData()
            track = self.tracks.get(path) if path else None
            last_path_attr = "_last_source_path" if role == "source" else "_last_target_path"
            if path != getattr(self, last_path_attr):
                cue_input.blockSignals(True)
                cue_input.setValue(0.0)
                cue_input.setMaximum(86_400.0)
                cue_input.blockSignals(False)
                setattr(self, last_path_attr, path)
                setattr(self, "_source_cue_set" if role == "source" else "_target_cue_set", False)
            if track is None:
                waveform.clear("Lade zuerst eine Audiodatei.")
                summary.setText("Track noch nicht ausgewählt")
                cue_input.setMaximum(86_400.0)
                continue
            if waveform.audio_path != str(track.path.resolve()):
                waveform.set_audio_path(track.path)
            waveform.set_cue_selection_enabled(True)
            waveform.set_beat_times(track.downbeat_seconds)
            waveform.set_cue_seconds(cue_input.value() if cue_input.value() > 0 else None)
            summary.setText(self._track_summary(track))
            summary.setToolTip(self._track_detail(track))

    def _track_summary(self, track):
        bpm = f"{track.bpm:.2f} BPM" if track.bpm is not None else "Nicht analysiert"
        return f"{track.path.name} · {bpm}"

    def _track_detail(self, track):
        summary = self._track_summary(track)
        grid = f"Grid: {track.grid_source or 'nicht verfügbar'}"
        if track.fallback_used is True:
            grid += " · Fallback-Grid"
        elif track.fallback_used is False:
            grid += " · erkannt"
        return f"{summary}\n{grid}"

    def _set_cue(self, role, seconds):
        widget = self.source_cue if role == "source" else self.target_cue
        setattr(self, "_source_cue_set" if role == "source" else "_target_cue_set", True)
        widget.blockSignals(True)
        widget.setValue(seconds)
        widget.blockSignals(False)
        (self.source_wave if role == "source" else self.target_wave).set_cue_seconds(seconds)
        self._mark_cue_set(role)

    def _set_selected_range(self, role, start, end):
        if self._active_edge_index is None:
            return
        source_range = self.source_wave.selection_range_seconds
        target_range = self.target_wave.selection_range_seconds
        if role == "source":
            source_range = (start, end)
        else:
            target_range = (start, end)
        self._edge_ranges[self._active_edge_index] = (source_range, target_range)
        if source_range is not None and target_range is not None:
            self.status_label.setText(
                f"Bereiche gewählt: A {source_range[0]:.1f}–{source_range[1]:.1f} s · "
                f"B {target_range[0]:.1f}–{target_range[1]:.1f} s. Jetzt Cuepoints suchen."
            )

    def _clear_selected_ranges(self):
        if self._active_edge_index is not None:
            self._edge_ranges.pop(self._active_edge_index, None)

    def _analyze_cue_ranges(self):
        if self._active_edge_index is None:
            self.status_label.setText("Wähle zuerst einen Paarübergang in der Sequenz.")
            return
        source_range = self.source_wave.selection_range_seconds
        target_range = self.target_wave.selection_range_seconds
        if source_range is None or target_range is None:
            self.status_label.setText("Ziehe zuerst in beiden Wellenformen einen Bereich auf.")
            return
        source_path, target_path = self.source_combo.currentData(), self.target_combo.currentData()
        if not source_path or not target_path or source_path == target_path:
            self.status_label.setText("Für die Cuepoint-Suche müssen zwei unterschiedliche Songs ausgewählt sein.")
            return
        edge_index = self._active_edge_index
        task = _CueAnalysisTask(
            self.tracks[source_path], self.tracks[target_path], source_range, target_range,
            int(self.length_combo.currentData()), self.analysis_cache,
        )
        task.signals.finished.connect(
            lambda result, error: self._on_cue_analysis_finished(result, error, edge_index, source_path, target_path),
            Qt.ConnectionType.QueuedConnection,
        )
        self.find_cues_button.setEnabled(False)
        self.status_label.setText("Cue-Point-Analyzer prüft Downbeats und bewertet Kandidaten in den markierten Bereichen …")
        self._pool.start(task)

    def _on_cue_analysis_finished(self, result, error, edge_index, source_path, target_path):
        self.find_cues_button.setEnabled(True)
        if error:
            self.status_label.setText(f"Cuepoint-Suche fehlgeschlagen: {error}")
            return
        for path, role in ((source_path, "source_analysis"), (target_path, "target_analysis")):
            track = self.tracks.get(path)
            if track is None:
                continue
            bpm, beat_frames, sample_rate, metadata = result[role]
            track.bpm = bpm
            track.beat_frames = beat_frames
            track.sample_rate = sample_rate
            track.downbeat_seconds = tuple(
                int(frame[0]) / sample_rate
                for frame in beat_frames
                if isinstance(frame, (tuple, list)) and len(frame) >= 3 and int(frame[1]) == 1
            )
            track.grid_source = metadata.grid_source
            track.fallback_used = metadata.fallback_used
            track.status = "Fallback · Analyse wiederholbar" if metadata.fallback_used else "Analysiert"
        if (
            self._active_edge_index != edge_index
            or self.source_combo.currentData() != source_path
            or self.target_combo.currentData() != target_path
        ):
            self.status_label.setText("Cuepoints gefunden, aber der aktive Übergang wurde inzwischen gewechselt.")
            return
        self._set_cue("source", result["source_seconds"])
        self._set_cue("target", result["target_seconds"])
        self._refresh_tracks()
        self.status_label.setText(
            f"Cue-Point-Analyzer: beste von {result['ranked_count']}/{result['candidate_count']} "
            f"Kandidaten · A {result['source_seconds']:.2f} s · B {result['target_seconds']:.2f} s · "
            f"Feature-Score {result['score']:.3f}. Cuepoints sind für den Rendern-Button gesetzt."
        )

    def _set_cue_limit(self, role, duration):
        box = self.source_cue if role == "source" else self.target_cue
        box.setMaximum(max(0.0, duration))
        waveform = self.source_wave if role == "source" else self.target_wave
        waveform.set_cue_seconds(box.value() if box.value() > 0 else None)

    def _analyze_selected_tracks(self, *_):
        selected = [item.data(Qt.ItemDataRole.UserRole) for item in self.track_list.selectedItems()]
        if not selected:
            selected = [path for path in (self.source_combo.currentData(), self.target_combo.currentData()) if path]
        selected = list(dict.fromkeys(selected))
        started = 0
        for path in selected:
            track = self.tracks.get(path)
            if track is None or path in self._analysis_busy:
                continue
            track.status = "Analyse läuft …"
            track.error = None
            task = _TrackAnalysisTask(track.path, self.analysis_cache)
            task.signals.finished.connect(self._on_analysis_finished)
            self._analysis_busy.add(path)
            self._pool.start(task)
            started += 1
        self._refresh_tracks()
        if started:
            self.status_label.setText(f"Analyse für {started} Track(s) gestartet. Cache und Ergebnis werden lokal gespeichert.")
        else:
            self.status_label.setText("Die ausgewählten Tracks sind bereits in Analyse oder es gibt keine Auswahl.")

    def _on_analysis_finished(self, path, result, error):
        self._analysis_busy.discard(path)
        track = self.tracks.get(path)
        if track is None:
            return
        if error:
            track.status = "Analyse fehlgeschlagen"
            track.error = error
            self.status_label.setText(f"Analyse fehlgeschlagen für {track.path.name}: {error}")
        else:
            track.status = "Fallback · Analyse wiederholbar" if result["fallback_used"] else "Analysiert"
            track.bpm = result["bpm"]
            track.sample_rate = result["sample_rate"]
            track.beat_frames = result["beat_frames"]
            track.downbeat_seconds = result["downbeat_seconds"]
            track.grid_source = result["grid_source"]
            track.fallback_used = result["fallback_used"]
            cache_status = result.get("cache_status")
            if track.fallback_used:
                cache_label = "Fallback-Grid · aufTAKT beim nächsten Analysieren erneut versuchen"
            elif cache_status == "legacy":
                cache_label = "historischer Analyse-Cache"
            else:
                cache_label = "erkanntes Beatgrid"
            self.status_label.setText(f"{track.path.name}: {track.bpm:.2f} BPM · {len(track.downbeat_seconds)} Downbeats · {cache_label}")
        self._refresh_tracks()
        self._load_pair_waveforms()

    def _play_track(self, role):
        combo = self.source_combo if role == "source" else self.target_combo
        path = combo.currentData()
        if not path:
            self.status_label.setText(f"Wähle zuerst einen Track für Song {'A' if role == 'source' else 'B'}.")
            return
        self._play_path(path)

    def _toggle_preview(self):
        if self._last_result is None:
            self.status_label.setText("Für diesen Übergang gibt es noch keine gerenderte Vorschau.")
            return
        if self._playing_path == str(self._last_result["output_path"]) and self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self._play_path(self._last_result["output_path"])

    def _play_path(self, path):
        if self._playing_path == str(path) and self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            return
        self._playing_path = str(path)
        self.player.setSource(QUrl.fromLocalFile(str(path)))
        self.player.play()

    def _render_transition(self):
        if self._active_edge_index is None:
            self.status_label.setText("Füge mindestens zwei Songs zur Sequenz hinzu und wähle den Übergang zwischen Nachbarn.")
            return
        source_path = self.source_combo.currentData()
        target_path = self.target_combo.currentData()
        if not source_path or not target_path:
            self.status_label.setText("Lade mindestens zwei Tracks und wähle Song A sowie Song B.")
            return
        if source_path == target_path:
            self.status_label.setText("Song A und Song B müssen für einen Übergang unterschiedliche Tracks sein.")
            return
        source_seconds = self.source_cue.value()
        target_seconds = self.target_cue.value()
        if not self._source_cue_set or not self._target_cue_set:
            self.status_label.setText("Setze beide Cuepoints durch Klick in die Wellenformen oder über die Zeitfelder.")
            return
        source = self.tracks[source_path]
        target = self.tracks[target_path]
        bars = int(self.length_combo.currentData())
        renderer = str(self.renderer_combo.currentData())
        task = _TransitionRenderTask(
            source, target, source_seconds, target_seconds, bars, renderer,
            self.analysis_cache, self.model_combo.currentData(),
        )
        requested = ((source_seconds, target_seconds, True, True), (bars, renderer, self.model_combo.currentData()))
        task.signals.finished.connect(
            lambda result, error: self._on_render_finished(result, error, (source_path, target_path), requested),
            Qt.ConnectionType.QueuedConnection,
        )
        self._render_busy = True
        self.render_button.setEnabled(False)
        self.edge_combo.setEnabled(False)
        self.sequence_up_button.setEnabled(False)
        self.sequence_down_button.setEnabled(False)
        self.sequence_remove_button.setEnabled(False)
        self.sequence_add_button.setEnabled(False)
        self.status_label.setText("BeatBridge analysiert bei Bedarf, richtet Cuepoints am Downbeat aus und rendert die Vorschau …")
        self.metric_label.setText("Render läuft …")
        self._pool.start(task)

    def _on_render_finished(self, result, error, pair, requested):
        self._render_busy = False
        self.render_button.setEnabled(True)
        self.edge_combo.setEnabled(True)
        self.sequence_up_button.setEnabled(True)
        self.sequence_down_button.setEnabled(True)
        self.sequence_remove_button.setEnabled(True)
        self.sequence_add_button.setEnabled(True)
        if error:
            self.status_label.setText(f"Übergang fehlgeschlagen: {error}")
            self.metric_label.setText("Bewertung nicht verfügbar")
            return
        pairs = list(zip(self.sequence_tracks, self.sequence_tracks[1:]))
        if pair not in pairs:
            self.status_label.setText("Vorschau gespeichert. Das Songpaar wurde aus der Sequenz entfernt.")
            return
        edge_index = pairs.index(pair)
        self._remember_active_edge()
        if (self._edge_cues.get(edge_index), self._edge_settings.get(edge_index)) != requested:
            self.status_label.setText("Vorschau gespeichert. Die Einstellungen des Songpaars wurden inzwischen geändert.")
            return
        self._edge_results[edge_index] = result
        self._refresh_sequence(select_edge=self._active_edge_index)
        if self._active_edge_index != edge_index:
            self.status_label.setText(f"Übergang {chr(65 + edge_index)} → {chr(66 + edge_index)} gerendert und gespeichert.")
            return
        self._show_transition_result(result)

    def _show_transition_result(self, result):
        self._last_result = result
        output_path = result["output_path"]
        self.player.stop()
        self._playing_path = str(output_path)
        self.player.setSource(QUrl.fromLocalFile(str(output_path)))
        self.result_wave.set_audio_path(
            output_path,
            transition_start=result["transition_start_sample"],
            transition_end=result["transition_end_sample"],
        )
        self.result_wave.set_duration(
            int(round(result["sample_count"] * 1000 / result["sample_rate"]))
        )
        score = result.get("score")
        if score:
            self.metric_label.setText(f"Render-Metrik · {score['total_score']:.3f} / 1.000")
            components = " · ".join(f"{name}: {value:.3f}" for name, value in score.get("component_scores", {}).items())
        else:
            self.metric_label.setText("Render-Metrik nicht verfügbar")
            components = "; ".join(result.get("metric_failures", [])) or "Kein Score im Protokoll verfügbar."
        self.result_detail.setText(
            f"{result['renderer']} · {result['bars']} Takte · {result['tempo_backend']} · "
            f"{output_path}\n{components}\nTechnische Metrik des gerenderten Audios; kein Nachweis menschlicher Hörqualität."
        )
        self.status_label.setText(f"Vorschau und Provenienz gespeichert unter {result['sidecar_path']}")

    def _on_player_position(self, position):
        if self._last_result and self._playing_path == str(self._last_result["output_path"]):
            self.result_wave.set_position(position)
            return
        for combo, waveform in ((self.source_combo, self.source_wave), (self.target_combo, self.target_wave)):
            if combo.currentData() == self._playing_path:
                waveform.set_position(position)

    def _on_player_state(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.status_label.setText(f"Wiedergabe: {Path(self._playing_path).name if self._playing_path else 'Audio'}")

    def _on_player_error(self, error, error_string):
        if error != QMediaPlayer.Error.NoError:
            self.status_label.setText(f"Audiofehler: {error_string or error}")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as audio_file:
        for chunk in iter(lambda: audio_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _local_paths_from_mime(mime):
    if mime.hasUrls():
        return [url.toLocalFile() for url in mime.urls() if url.isLocalFile()]
    if mime.hasFormat("application/x-beatbridge-library-tracks"):
        raw = bytes(mime.data("application/x-beatbridge-library-tracks"))
        return raw.decode("utf-8").splitlines()
    return []
