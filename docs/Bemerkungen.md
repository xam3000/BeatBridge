# Beobachtungen, Entscheidungen und Gelerntes

## Offene Beobachtungen

- **Beobachtung (übernommen am 2026-07-17):** Die BPM-Ergebnisse von librosa und aufTAKT weichen für `HELP_LESS` voneinander ab (librosa: 161 BPM, aufTAKT: 157 BPM). Ursache und maßgebliches Grid sind noch nicht entschieden.
- **Beobachtung (übernommen am 2026-07-17):** Das erkannte Taktraster umfasst überwiegend vier Beats, musikalisch relevante Phrasen im Entwicklungsset häufig acht Beats. Kandidatengenerierung muss deshalb Beat, Takt und Phrase getrennt modellieren.

## Entscheidungen und Gelerntes

- **Entscheidung (2026-07-17):** Rendering arbeitet standardmäßig mit 44,1 kHz und kanalorientiertem Stereo-Audio. Grund: Das Entwicklungsset enthält sowohl 44,1-kHz- als auch 48-kHz-Dateien; ein gemeinsames Raster verhindert stilles Fehl-Timing.
- **Entscheidung (2026-07-17):** Der programmatische Rückgabevertrag startet mit `format_version = 1`; inkompatible Änderungen benötigen eine neue Version.
- **Entscheidung (2026-07-17):** Die Root-`README.md` bleibt eine kompakte Projekt- und Bedienungsübersicht; der veränderliche Arbeitsplan wird ausschließlich in `docs/STATUS.md` gepflegt. Grund: Doppelte Aktionspläne waren bereits auseinander gelaufen und enthielten erledigte Renderer weiterhin als offene Arbeit.
- **Gelernt (2026-07-17, 1. Versuch):** Fehlende Downbeat-Metadaten führten zuvor zu stillem Fallback auf beliebige Beats → Downbeat-Snapping bricht jetzt mit einer konkreten Fehlermeldung ab → kein vorgetäuschtes Bar-Alignment.
- **Gelernt (2026-07-17, 1. Versuch):** Eine Prüfung innerhalb der Codex-Dateisandbox meldete `ffmpeg` als nicht auffindbar, obwohl dessen WinGet-Verzeichnis im `PATH` stand → die Sandbox verweigerte Zugriff und Ausführung im Paketverzeichnis → externe Programme bei einem solchen Widerspruch durch einen tatsächlichen Prozessstart außerhalb der eingeschränkten Sandbox verifizieren. `ffmpeg 8.1` ist installiert und ausführbar.
