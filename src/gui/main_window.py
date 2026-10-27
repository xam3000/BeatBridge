"""Native Qt Widgets review window for one BeatBridge batch manifest."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .manifest import BatchReview, ReviewVariant, load_batch_manifest, load_saved_selection, save_selection
from .waveform import WaveformWidget


class BeatBridgeMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BeatBridge — Übergangsreview")
        self.resize(1500, 980)
        self.setMinimumSize(1120, 760)
        self._review: BatchReview | None = None
        self._candidates: dict[str, dict] = {}
        self._variants: list[ReviewVariant] = []
        self._current_variant: ReviewVariant | None = None
        self._saved_variant_key: str | None = None

        self._player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._audio_output.setVolume(0.8)
        self._player.setAudioOutput(self._audio_output)
        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.playbackStateChanged.connect(self._on_playback_state_changed)
        self._player.errorOccurred.connect(self._on_player_error)

        self._build_ui()
        self._apply_style()
        self._update_empty_state()

    def _build_ui(self):
        central = QWidget(self)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(14, 12, 14, 10)
        outer.setSpacing(10)

        toolbar = QHBoxLayout()
        brand = QLabel("BeatBridge")
        brand.setObjectName("brand")
        toolbar.addWidget(brand)
        toolbar.addWidget(QLabel("Übergangsreview · native Python-App"))
        toolbar.addStretch(1)
        self.open_button = QPushButton("Batchmanifest öffnen…")
        self.open_button.clicked.connect(self._open_manifest_dialog)
        toolbar.addWidget(self.open_button)
        outer.addLayout(toolbar)

        self.manifest_label = QLabel("Kein Batchmanifest geöffnet")
        self.manifest_label.setObjectName("muted")
        self.manifest_label.setTextFormat(Qt.TextFormat.PlainText)
        outer.addWidget(self.manifest_label)

        pair_frame = QFrame()
        pair_frame.setObjectName("panel")
        pair_layout = QHBoxLayout(pair_frame)
        self.source_label = self._track_card("A · Quelle")
        self.target_label = self._track_card("B · Ziel")
        pair_layout.addWidget(self.source_label[0], 1)
        pair_layout.addWidget(self.target_label[0], 1)
        outer.addWidget(pair_frame)

        split = QSplitter(Qt.Orientation.Horizontal)
        self.variant_table = QTableWidget(0, 9)
        self.variant_table.setHorizontalHeaderLabels(
            ["Auswahl", "Candidate", "Renderer", "Feature-Rang", "Feature-Score", "Auswahl-Rang", "Auswahl-Score", "Render-Rang", "Render-Score"]
        )
        self.variant_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.variant_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.variant_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.variant_table.setAlternatingRowColors(True)
        self.variant_table.verticalHeader().setVisible(False)
        self.variant_table.horizontalHeader().setStretchLastSection(True)
        self.variant_table.itemSelectionChanged.connect(self._on_variant_selected)
        split.addWidget(self.variant_table)

        detail_panel = QFrame()
        detail_panel.setObjectName("panel")
        detail_layout = QVBoxLayout(detail_panel)
        heading = QLabel("Variante und Messwerte")
        heading.setObjectName("sectionTitle")
        detail_layout.addWidget(heading)
        self.variant_title = QLabel("Keine Variante ausgewählt")
        self.variant_title.setObjectName("variantTitle")
        self.variant_title.setTextFormat(Qt.TextFormat.PlainText)
        detail_layout.addWidget(self.variant_title)
        self.details_form = QFormLayout()
        self.details_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        detail_layout.addLayout(self.details_form)
        self.failure_label = QLabel("")
        self.failure_label.setObjectName("muted")
        self.failure_label.setWordWrap(True)
        self.failure_label.setTextFormat(Qt.TextFormat.PlainText)
        detail_layout.addWidget(self.failure_label)
        detail_layout.addStretch(1)
        split.addWidget(detail_panel)
        split.setSizes([920, 470])
        outer.addWidget(split, 1)

        wave_heading = QLabel("Wellenform der ausgewählten Renderdatei")
        wave_heading.setObjectName("sectionTitle")
        outer.addWidget(wave_heading)
        self.waveform = WaveformWidget()
        outer.addWidget(self.waveform)

        transport = QHBoxLayout()
        self.play_button = QPushButton("▶ Abspielen")
        self.play_button.clicked.connect(self._toggle_playback)
        self.stop_button = QPushButton("■ Stopp")
        self.stop_button.clicked.connect(self._stop_playback)
        transport.addWidget(self.play_button)
        transport.addWidget(self.stop_button)
        self.position_label = QLabel("00:00 / 00:00")
        self.position_label.setMinimumWidth(100)
        transport.addWidget(self.position_label)
        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setRange(0, 0)
        self.position_slider.sliderMoved.connect(self._player.setPosition)
        transport.addWidget(self.position_slider, 1)
        self.save_button = QPushButton("Auswahl separat speichern")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self._save_selection)
        transport.addWidget(self.save_button)
        outer.addLayout(transport)

        self.status_label = QLabel("Öffne ein BeatBridge-Paarmanifest, um zu beginnen.")
        self.status_label.setObjectName("status")
        self.status_label.setTextFormat(Qt.TextFormat.PlainText)
        outer.addWidget(self.status_label)
        self.setCentralWidget(central)

        open_action = QAction("Batchmanifest öffnen", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._open_manifest_dialog)
        self.addAction(open_action)
        play_action = QAction("Wiedergabe/Pause", self)
        play_action.setShortcut(QKeySequence("Space"))
        play_action.triggered.connect(self._toggle_playback)
        self.addAction(play_action)

    @staticmethod
    def _track_card(title):
        frame = QFrame()
        frame.setObjectName("trackCard")
        layout = QVBoxLayout(frame)
        heading = QLabel(title)
        heading.setObjectName("trackHeading")
        value = QLabel("Nicht verfügbar")
        value.setWordWrap(True)
        value.setTextFormat(Qt.TextFormat.PlainText)
        value.setObjectName("trackValue")
        layout.addWidget(heading)
        layout.addWidget(value)
        return frame, value

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #101a21; color: #e4edf1; font-size: 13px; }
            QFrame#panel, QFrame#trackCard { background: #15232c; border: 1px solid #2b414d; border-radius: 7px; }
            QFrame#trackCard { background: #0d1b22; padding: 3px; }
            QLabel#brand { color: #45d5ee; font-size: 21px; font-weight: 700; padding-right: 12px; }
            QLabel#muted { color: #9aadb7; }
            QLabel#sectionTitle { color: #dce8ed; font-weight: 650; }
            QLabel#trackHeading { color: #9aadb7; font-weight: 650; }
            QLabel#trackValue { font-size: 14px; }
            QLabel#variantTitle { color: #45d5ee; font-size: 15px; font-weight: 650; }
            QLabel#status { color: #a8bac3; padding-top: 3px; }
            QPushButton { background: #1b303b; border: 1px solid #3a5664; border-radius: 5px; padding: 8px 12px; }
            QPushButton:hover { background: #24404d; }
            QPushButton:disabled { color: #71838b; background: #17232a; }
            QPushButton#primary { color: #071317; background: #45d5ee; font-weight: 700; }
            QTableWidget { background: #0d171d; alternate-background-color: #13212a; gridline-color: #273b45; selection-background-color: #254653; }
            QHeaderView::section { background: #1b2b34; color: #aebfc7; padding: 7px; border: 0; border-right: 1px solid #2d414b; }
            QSlider::groove:horizontal { background: #263a44; height: 5px; border-radius: 2px; }
            QSlider::handle:horizontal { background: #45d5ee; width: 13px; margin: -5px 0; border-radius: 6px; }
        """)

    def _open_manifest_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "BeatBridge-Paarmanifest öffnen",
            str(Path.cwd()),
            "JSON-Manifeste (manifest.json);;JSON-Dateien (*.json)",
        )
        if path:
            self.open_manifest(Path(path))

    def open_manifest(self, path: Path):
        try:
            review = load_batch_manifest(path)
        except ValueError as error:
            QMessageBox.critical(self, "Manifest konnte nicht geöffnet werden", str(error))
            return

        self._stop_playback()
        self._review = review
        self._variants = list(review.variants)
        self._candidates = review.candidates
        self._saved_variant_key = load_saved_selection(review)
        self.manifest_label.setText(str(review.manifest_path))
        self.setWindowTitle(f"BeatBridge — {review.manifest_path.parent.name}")
        self._populate_pair_summary()
        self._populate_variant_table()
        self.status_label.setText(
            f"Format {review.format_version} · {len(review.variants)} Varianten · "
            f"{len(review.failures)} dokumentierte Fehler · Ranking: {review.ranking_method}"
        )
        if review.variants:
            preferred = next(
                (i for i, item in enumerate(review.variants) if item.key == self._saved_variant_key),
                0,
            )
            self.variant_table.selectRow(preferred)
        else:
            self._current_variant = None
            self.variant_title.setText("Keine erfolgreich gerenderte Variante")
            self._set_detail_rows({"Fehler": self._format_failures(review.failures)})
            self.waveform.clear("Dieses Manifest enthält keine gerenderten WAV-Varianten.")
        self._update_save_button()
        self.failure_label.setText(self._format_failures(review.failures) if review.failures else "Keine Renderfehler im Manifest dokumentiert.")

    def _populate_pair_summary(self):
        if self._review is None:
            return
        candidates = self._candidates
        candidate = next(iter(candidates.values()), {})
        source = candidate.get("source_track", {}) if isinstance(candidate, dict) else {}
        target = candidate.get("target_track", {}) if isinstance(candidate, dict) else {}
        self.source_label[1].setText(self._track_text("A", source, candidate.get("source_cutpoint", {}), candidate.get("source_bpm")))
        self.target_label[1].setText(self._track_text("B", target, candidate.get("target_cutpoint", {}), candidate.get("target_bpm")))

    @staticmethod
    def _track_text(role, track, cutpoint, bpm):
        path = str(track.get("path", "Nicht verfügbar")) if isinstance(track, dict) else "Nicht verfügbar"
        sha = str(track.get("sha256", "Nicht verfügbar")) if isinstance(track, dict) else "Nicht verfügbar"
        cutpoint = cutpoint if isinstance(cutpoint, dict) else {}
        lines = [Path(path).name if path != "Nicht verfügbar" else path]
        lines.append(f"{role} · {bpm:.2f} BPM" if isinstance(bpm, (float, int)) else f"{role} · BPM nicht verfügbar")
        if cutpoint:
            lines.append(
                f"Cue: Takt {cutpoint.get('bar_index', '–')} · Beat {cutpoint.get('beat_index', '–')} · "
                f"Sample {cutpoint.get('sample', '–')}"
            )
        lines.append(f"SHA-256: {sha[:16]}…" if sha != "Nicht verfügbar" else "Track-SHA nicht verfügbar")
        return "\n".join(lines)

    def _populate_variant_table(self):
        self.variant_table.blockSignals(True)
        self.variant_table.setRowCount(len(self._variants))
        for row, variant in enumerate(self._variants):
            saved_mark = "✓" if variant.key == self._saved_variant_key else ""
            cells = [
                saved_mark,
                variant.candidate_id,
                variant.renderer,
                _display_int(variant.candidate_rank),
                _display_score(variant.candidate_score),
                _display_int(variant.selection_rank),
                _display_score(variant.selection_score),
                _display_int(variant.transition_rank),
                _display_score(variant.transition_score),
            ]
            for column, text in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if column in (0, 3, 4, 5, 6, 7, 8):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.variant_table.setItem(row, column, item)
        self.variant_table.resizeColumnsToContents()
        self.variant_table.blockSignals(False)

    def _on_variant_selected(self):
        row = self.variant_table.currentRow()
        if row < 0 or row >= len(self._variants):
            return
        variant = self._variants[row]
        if self._current_variant is not None and self._current_variant.key != variant.key:
            self._stop_playback()
        self._current_variant = variant
        audio_available = variant.status == "rendered" and variant.audio_path.is_file()
        self._player.setSource(QUrl.fromLocalFile(str(variant.audio_path)) if audio_available else QUrl())
        self.waveform.set_variant(variant)
        self.variant_title.setText(f"{variant.renderer} · {variant.candidate_id}")
        self._populate_details(variant)
        self.position_slider.setRange(0, 0)
        self.position_label.setText("00:00 / 00:00")
        self._update_save_button()

    def _populate_details(self, variant):
        candidate = variant.candidate if isinstance(variant.candidate, dict) else {}
        source_cue = candidate.get("source_cutpoint", {})
        target_cue = candidate.get("target_cutpoint", {})
        bars = candidate.get("transition_length_bars", "Nicht verfügbar")
        details = {
            "Status": variant.status,
            "Candidate-ID": variant.candidate_id,
            "Taktlänge": f"{bars} Takte" if bars != "Nicht verfügbar" else "Nicht verfügbar",
            "Source-Cue": _format_cutpoint(source_cue),
            "Target-Cue": _format_cutpoint(target_cue),
            "Feature-Rang / Score": f"{_display_int(variant.candidate_rank)} / {_display_score(variant.candidate_score)}",
            f"Auswahl · {variant.selection_method}": f"{_display_int(variant.selection_rank)} / {_display_score(variant.selection_score)}",
            "Render-Rang / Score": f"{_display_int(variant.transition_rank)} / {_display_score(variant.transition_score)}",
            "Rendergrenzen": _format_boundaries(variant),
            "Datei": str(variant.audio_path) if variant.status == "rendered" else f"{variant.output_file} ({variant.status})",
        }
        for key, value in variant.candidate_components.items():
            details[f"Feature-Komponente · {key}"] = _format_value(value)
        for key, value in variant.candidate_measurements.items():
            details[f"Messung · {key}"] = _format_value(value)
        for key, value in variant.transition_components.items():
            details[f"Renderkomponente · {key}"] = _format_value(value)
        self._set_detail_rows(details)

    def _set_detail_rows(self, details):
        while self.details_form.rowCount():
            self.details_form.removeRow(0)
        for key, value in details.items():
            label = QLabel(str(key))
            label.setObjectName("muted")
            label.setTextFormat(Qt.TextFormat.PlainText)
            value_label = QLabel(str(value))
            value_label.setWordWrap(True)
            value_label.setTextFormat(Qt.TextFormat.PlainText)
            value_label.setToolTip(str(value))
            self.details_form.addRow(label, value_label)

    def _toggle_playback(self):
        if self._current_variant is None:
            self.status_label.setText("Wähle zuerst eine gerenderte WAV-Variante aus.")
            return
        if self._current_variant.status != "rendered" or not self._current_variant.audio_path.is_file():
            self.status_label.setText(f"WAV nicht verfügbar: {self._current_variant.status}")
            return
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def _stop_playback(self):
        self._player.stop()
        self._player.setPosition(0)

    def _on_position_changed(self, position):
        self.waveform.set_position(position)
        self.position_slider.setValue(position)
        self.position_label.setText(f"{_format_time(position)} / {_format_time(self._player.duration())}")

    def _on_duration_changed(self, duration):
        self.position_slider.setRange(0, max(0, duration))
        self.position_slider.setValue(self._player.position())
        self.waveform.set_duration(duration)
        self.position_label.setText(f"{_format_time(self._player.position())} / {_format_time(duration)}")

    def _on_playback_state_changed(self, state):
        self.play_button.setText("Ⅱ Pause" if state == QMediaPlayer.PlaybackState.PlayingState else "▶ Abspielen")

    def _on_player_error(self, error, error_string):
        if error != QMediaPlayer.Error.NoError:
            self.status_label.setText(f"Audiofehler: {error_string or error}")

    def _save_selection(self):
        if self._review is None or self._current_variant is None:
            return
        try:
            sidecar = save_selection(self._review, self._current_variant)
        except OSError as error:
            QMessageBox.critical(self, "Auswahl konnte nicht gespeichert werden", str(error))
            return
        self._saved_variant_key = self._current_variant.key
        self._populate_variant_table()
        self.status_label.setText(f"Auswahl separat gespeichert: {sidecar}")
        self._update_save_button()

    def _update_save_button(self):
        enabled = self._review is not None and self._current_variant is not None
        self.save_button.setEnabled(bool(enabled and self._current_variant.key != self._saved_variant_key))
        if self._current_variant is not None and self._current_variant.key == self._saved_variant_key:
            self.save_button.setText("Auswahl ist gespeichert")
        else:
            self.save_button.setText("Auswahl separat speichern")

    def _update_empty_state(self):
        self.variant_table.setRowCount(0)
        self.waveform.clear()
        self.failure_label.setText("")

    def _format_failures(self, failures):
        if not failures:
            return "Keine erfolgreichen Varianten und keine Fehlerdetails im Manifest."
        return "\n".join(
            f"{item.get('candidate_id', 'Candidate unbekannt')} · {item.get('renderer', 'Renderer unbekannt')}: "
            f"{item.get('message', item.get('error', 'Fehlerdetails nicht verfügbar'))}"
            for item in failures[:12]
        )


def _display_int(value):
    return "Nicht verfügbar" if value is None else str(value)


def _display_score(value):
    return "Nicht verfügbar" if value is None else f"{value:.4f}"


def _format_cutpoint(value):
    if not isinstance(value, dict) or not value:
        return "Nicht verfügbar"
    return (
        f"Takt {value.get('bar_index', '–')} · Beat {value.get('beat_index', '–')} · "
        f"Sample {value.get('sample', '–')}"
    )


def _format_boundaries(variant):
    if variant.transition_start_sample is None or variant.transition_end_sample is None:
        return "Nicht verfügbar (historisches Manifest ohne Rendergrenzen)"
    return f"{variant.transition_start_sample}–{variant.transition_end_sample} Samples"


def _format_value(value):
    if isinstance(value, float):
        return f"{value:.4f}"
    if value is None:
        return "Nicht verfügbar"
    return str(value)


def _format_time(milliseconds):
    seconds = max(0, int(milliseconds)) // 1000
    return f"{seconds // 60:02d}:{seconds % 60:02d}"
