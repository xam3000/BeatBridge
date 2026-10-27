"""Native waveform display with asynchronous WAV decoding."""

from __future__ import annotations

import numpy as np
import soundfile as sf

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class _WaveformSignals(QObject):
    loaded = Signal(int, object, object, int, int, str)


class _WaveformTask(QRunnable):
    def __init__(self, token: int, path: str, bins: int):
        super().__init__()
        self.token = token
        self.path = path
        self.bins = bins
        self.signals = _WaveformSignals()

    def run(self):
        try:
            info = sf.info(self.path)
            if info.frames <= 0:
                raise ValueError("Die WAV-Datei enthält keine Audiodaten.")
            bin_count = max(1, min(int(self.bins), int(info.frames)))
            minima = np.full(bin_count, np.inf, dtype=np.float32)
            maxima = np.full(bin_count, -np.inf, dtype=np.float32)
            offset = 0
            with sf.SoundFile(self.path) as audio_file:
                while True:
                    block = audio_file.read(131072, dtype="float32", always_2d=True)
                    if block.shape[0] == 0:
                        break
                    frame_minimums = np.min(block, axis=1)
                    frame_maximums = np.max(block, axis=1)
                    bucket_ids = np.minimum(
                        ((np.arange(offset, offset + len(frame_minimums), dtype=np.int64) * bin_count)
                         // info.frames),
                        bin_count - 1,
                    )
                    np.minimum.at(minima, bucket_ids, frame_minimums)
                    np.maximum.at(maxima, bucket_ids, frame_maximums)
                    offset += len(frame_minimums)
            minima[~np.isfinite(minima)] = 0.0
            maxima[~np.isfinite(maxima)] = 0.0
            self.signals.loaded.emit(
                self.token, minima, maxima, int(info.frames), int(info.samplerate), ""
            )
        except Exception as error:  # propagate file/codec problems to the view
            self.signals.loaded.emit(self.token, [], [], 0, 0, str(error))


class WaveformWidget(QWidget):
    cue_changed = Signal(float)
    duration_loaded = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150)
        self.setMaximumHeight(210)
        self.setAutoFillBackground(False)
        self._token = 0
        self._minimums: np.ndarray | list[float] = []
        self._maximums: np.ndarray | list[float] = []
        self._frame_count = 0
        self._sample_rate = 0
        self._position_ms = 0
        self._duration_ms = 0
        self._cue_seconds: float | None = None
        self._accent_color = "#37cde6"
        self._beat_seconds: list[float] = []
        self._cue_selectable = False
        self._transition_start: int | None = None
        self._transition_end: int | None = None
        self._error = ""
        self._loading = False
        self._view_start = 0.0
        self._view_span = 1.0
        self._pan_x: float | None = None
        self._pool = QThreadPool.globalInstance()
        self.setToolTip("Mausrad: Zoom · Shift+Mausrad oder mittlere Maustaste: verschieben · Doppelklick: Gesamtansicht")

    def set_variant(self, variant):
        self._cue_selectable = False
        self.set_audio_path(
            variant.audio_path if variant.status == "rendered" else None,
            transition_start=variant.transition_start_sample,
            transition_end=variant.transition_end_sample,
        )

    def set_audio_path(self, path, *, transition_start=None, transition_end=None):
        self._token += 1
        self._minimums = []
        self._maximums = []
        self._frame_count = 0
        self._sample_rate = 0
        self._transition_start = transition_start
        self._transition_end = transition_end
        self._view_start = 0.0
        self._view_span = 1.0
        self._pan_x = None
        self._position_ms = 0
        self._duration_ms = 0
        self._cue_seconds = None
        self._beat_seconds = []
        self._error = ""
        self._loading = path is not None and path.is_file()
        if self._loading:
            bins = max(48000, min(160000, self.width() * 80))
            task = _WaveformTask(self._token, str(path), bins)
            task.signals.loaded.connect(self._on_loaded)
            self._pool.start(task)
        else:
            self._error = "Audiodatei nicht verfügbar" if path is None else "Datei fehlt"
        self.update()

    def set_cue_selection_enabled(self, enabled: bool):
        self._cue_selectable = bool(enabled)
        self.setCursor(Qt.CursorShape.CrossCursor if enabled else Qt.CursorShape.ArrowCursor)

    def set_accent_color(self, color: str):
        self._accent_color = str(color)
        self.update()

    def set_cue_seconds(self, seconds: float | None):
        self._cue_seconds = None if seconds is None else max(0.0, float(seconds))
        self.update()

    def set_beat_times(self, seconds):
        self._beat_seconds = [float(value) for value in seconds if float(value) >= 0.0]
        self.update()

    def clear(self, message="Öffne ein Batchmanifest, um Varianten zu laden."):
        self._token += 1
        self._minimums = []
        self._maximums = []
        self._frame_count = 0
        self._sample_rate = 0
        self._duration_ms = 0
        self._position_ms = 0
        self._cue_seconds = None
        self._beat_seconds = []
        self._cue_selectable = False
        self._transition_start = None
        self._transition_end = None
        self._view_start = 0.0
        self._view_span = 1.0
        self._pan_x = None
        self._error = message
        self._loading = False
        self.update()

    def _on_loaded(self, token, minimums, maximums, frames, sample_rate, error):
        if token != self._token:
            return
        self._minimums = minimums
        self._maximums = maximums
        self._frame_count = frames or self._frame_count
        self._sample_rate = sample_rate
        if sample_rate and frames:
            self._duration_ms = int(round(frames * 1000 / sample_rate))
            self.duration_loaded.emit(self._duration_ms / 1000.0)
        self._error = error
        self._loading = False
        self.update()

    def set_position(self, position_ms: int):
        self._position_ms = max(0, int(position_ms))
        self.update()

    def set_duration(self, duration_ms: int):
        self._duration_ms = max(0, int(duration_ms))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.fillRect(rect, QColor("#0b151c"))
        painter.setPen(QPen(QColor("#263943"), 1))
        painter.drawRect(rect)
        center_y = rect.center().y()
        painter.setPen(QPen(QColor("#283c47"), 1))
        painter.drawLine(rect.left() + 8, center_y, rect.right() - 8, center_y)

        if len(self._minimums) > 0:
            plot_left = rect.left() + 10
            plot_width = max(1, rect.width() - 20)
            amplitude = max(1.0, rect.height() * 0.42)
            last_index = max(1, len(self._minimums) - 1)
            first_bin = max(0, int(self._view_start * last_index))
            last_bin = min(last_index, int((self._view_start + self._view_span) * last_index) + 1)
            visible_bins = max(1, last_bin - first_bin + 1)
            draw_step = max(1, (visible_bins + plot_width * 3 - 1) // (plot_width * 3))
            upper_path = QPainterPath()
            lower_path = QPainterPath()
            polygon_path = QPainterPath()
            for index in range(first_bin, last_bin + 1, draw_step):
                group_end = min(last_bin + 1, index + draw_step)
                low = float(np.min(self._minimums[index:group_end]))
                high = float(np.max(self._maximums[index:group_end]))
                group_center = (index + group_end - 1) / 2.0
                fraction = (group_center / last_index - self._view_start) / self._view_span
                x = plot_left + round(fraction * (plot_width - 1))
                y_top = center_y - round(high * amplitude)
                y_bottom = center_y - round(low * amplitude)
                if upper_path.elementCount() == 0:
                    upper_path.moveTo(x, y_top)
                    lower_path.moveTo(x, y_bottom)
                    polygon_path.moveTo(x, y_top)
                else:
                    upper_path.lineTo(x, y_top)
                    lower_path.lineTo(x, y_bottom)
                    polygon_path.lineTo(x, y_top)
            if upper_path.elementCount():
                for element_index in range(lower_path.elementCount() - 1, -1, -1):
                    element = lower_path.elementAt(element_index)
                    polygon_path.lineTo(element.x, element.y)
                polygon_path.closeSubpath()
                fill = QColor(self._accent_color)
                fill.setAlpha(48)
                painter.fillPath(polygon_path, fill)
                painter.setPen(QPen(QColor(self._accent_color), 1))
                painter.drawPath(upper_path)
                painter.drawPath(lower_path)

            if self._cue_selectable and self._duration_ms > 0:
                painter.setPen(QPen(QColor("#f7bd55"), 1))
                for beat_seconds in self._beat_seconds:
                    fraction = (beat_seconds * 1000 / self._duration_ms - self._view_start) / self._view_span
                    if 0.0 <= fraction <= 1.0:
                        x = plot_left + int(plot_width * fraction)
                        painter.drawLine(x, rect.top() + 20, x, rect.bottom() - 1)

            if self._transition_start is not None and self._transition_end is not None and self._frame_count:
                transition_start = self._transition_start / self._frame_count
                transition_end = self._transition_end / self._frame_count
                x1_fraction = (transition_start - self._view_start) / self._view_span
                x2_fraction = (transition_end - self._view_start) / self._view_span
                if x2_fraction > 0.0 and x1_fraction < 1.0:
                    x1 = plot_left + int(plot_width * max(0.0, x1_fraction))
                    x2 = plot_left + int(plot_width * min(1.0, x2_fraction))
                    painter.fillRect(x1, rect.top() + 1, max(1, x2 - x1), rect.height() - 2, QColor(154, 120, 255, 38))

            if self._duration_ms > 0:
                position_fraction = (self._position_ms / self._duration_ms - self._view_start) / self._view_span
                if 0.0 <= position_fraction <= 1.0:
                    x = plot_left + int(plot_width * position_fraction)
                    painter.setPen(QPen(QColor("#ffffff"), 2))
                    painter.drawLine(x, rect.top() + 1, x, rect.bottom() - 1)

                if self._cue_seconds is not None:
                    cue_fraction = (self._cue_seconds * 1000 / self._duration_ms - self._view_start) / self._view_span
                    if 0.0 <= cue_fraction <= 1.0:
                        cue_x = plot_left + int(plot_width * cue_fraction)
                        painter.setPen(QPen(QColor("#f7bd55"), 2))
                        painter.drawLine(cue_x, rect.top() + 1, cue_x, rect.bottom() - 1)

            note = ""
        else:
            painter.setPen(QColor("#9aabb4"))
            note = "Wellenform wird geladen …" if self._loading else (self._error or "Keine Audiodatei ausgewählt.")

        if note:
            painter.setPen(QColor("#9aabb4"))
            painter.drawText(rect.adjusted(10, 8, -10, -6), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, note)
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton or (
            event.button() == Qt.MouseButton.LeftButton
            and event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            self._pan_x = event.position().x()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        if self._cue_selectable and event.button() == Qt.MouseButton.LeftButton and self._duration_ms > 0:
            margin = 11
            fraction = (event.position().x() - margin) / max(1, self.width() - margin * 2)
            position = self._view_start + min(1.0, max(0.0, fraction)) * self._view_span
            seconds = min(1.0, max(0.0, position)) * self._duration_ms / 1000.0
            self.set_cue_seconds(seconds)
            self.cue_changed.emit(seconds)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._pan_x is not None:
            delta = event.position().x() - self._pan_x
            self._pan_x = event.position().x()
            self._set_view(self._view_start - delta / max(1, self.width() - 20) * self._view_span, self._view_span)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._pan_x is not None:
            self._pan_x = None
            self.setCursor(Qt.CursorShape.CrossCursor if self._cue_selectable else Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        self._set_view(0.0, 1.0)
        event.accept()

    def wheelEvent(self, event):
        if len(self._minimums) == 0:
            event.ignore()
            return
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            steps = event.angleDelta().y() / 120.0
            self._set_view(self._view_start - steps * self._view_span * 0.15, self._view_span)
            event.accept()
            return
        plot_left = 10.0
        relative_x = min(1.0, max(0.0, (event.position().x() - plot_left) / max(1.0, self.width() - 20.0)))
        anchor = self._view_start + relative_x * self._view_span
        factor = 0.8 if event.angleDelta().y() > 0 else 1.25
        new_span = min(1.0, max(1.0 / 40.0, self._view_span * factor))
        new_start = anchor - relative_x * new_span
        self._set_view(new_start, new_span)
        event.accept()

    def _set_view(self, start, span):
        span = min(1.0, max(1.0 / 40.0, float(span)))
        start = min(1.0 - span, max(0.0, float(start)))
        self._view_start = start
        self._view_span = span
        self.update()
