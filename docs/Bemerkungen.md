BPM von librosa und auftakt unterschiedlich (HELP_LESS: librosa: 161, auftakt: 157)

beat raster ist immer 4 beats wir haben aber meisten frase mit 8 beats

## Entscheidungen und Gelerntes

- **Entscheidung (2026-07-17):** Rendering arbeitet standardmäßig mit 44,1 kHz und kanalorientiertem Stereo-Audio. Grund: Das Entwicklungsset enthält sowohl 44,1-kHz- als auch 48-kHz-Dateien; ein gemeinsames Raster verhindert stilles Fehl-Timing.
- **Entscheidung (2026-07-17):** Der programmatische Rückgabevertrag startet mit `format_version = 1`; inkompatible Änderungen benötigen eine neue Version.
- **Gelernt (2026-07-17, 1. Versuch):** Fehlende Downbeat-Metadaten führten zuvor zu stillem Fallback auf beliebige Beats → Downbeat-Snapping bricht jetzt mit einer konkreten Fehlermeldung ab → kein vorgetäuschtes Bar-Alignment.
