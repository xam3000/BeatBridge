window.BeatBridgeMockData = {
  project: {
    id: "mock-project-v1",
    name: "Performance Set 01",
    formatVersion: 1
  },
  tracks: [
    { id: "track-help", title: "HELP LESS", artist: "TSHA", bpm: 161.0, key: "F♯m", duration: "05:28", color: "cyan", seed: 11, status: "analysiert" },
    { id: "track-breath", title: "BREATH LESS", artist: "Chris Stussy", bpm: 160.0, key: "Em", duration: "06:12", color: "coral", seed: 23, status: "analysiert" },
    { id: "track-higher", title: "HIGHER GROUND", artist: "Jamie Jones", bpm: 162.2, key: "Am", duration: "07:01", color: "violet", seed: 37, status: "analysiert" },
    { id: "track-momentum", title: "MOMENTUM", artist: "Will Clarke", bpm: 159.6, key: "Gm", duration: "06:38", color: "amber", seed: 41, status: "analysiert" },
    { id: "track-lost", title: "LOST IN MOTION", artist: "Ben Böhmer", bpm: 122.0, key: "Dm", duration: "06:21", color: "blue", seed: 53, status: "Warnung" },
    { id: "track-silence", title: "SILENCE TALKS", artist: "Klangkuenstler", bpm: 135.0, key: "Fm", duration: "05:49", color: "green", seed: 67, status: "analysiert" }
  ],
  sections: [
    { id: "section-help-drop", trackId: "track-help", label: "Build-up + Drop", range: "01:08–01:46" },
    { id: "section-breath-intro", trackId: "track-breath", label: "Intro + Drop", range: "01:14–01:55" },
    { id: "section-higher-break", trackId: "track-higher", label: "Break + Refrain", range: "02:06–02:51" },
    { id: "section-momentum-outro", trackId: "track-momentum", label: "Peak + Outro", range: "03:12–03:58" }
  ],
  edges: [
    {
      id: "edge-help-breath", fromSectionId: "section-help-drop", toSectionId: "section-breath-intro", status: "ready",
      config: { bars: 4, targetBpm: 161.5, renderer: "Equal Power", maxStretch: 8, energyPriority: 75, avoidVocals: true },
      cueA: "Takt 61 · 01:32.8", cueB: "Takt 65 · 01:38.7", candidateId: "candidate-33640deded712342",
      variants: [
        { id: "v-hb-01", rank: 1, score: 88, method: "Equal Power", bars: 4, bpm: 161.5, status: "rendered" },
        { id: "v-hb-02", rank: 2, score: 82, method: "ML Control", bars: 4, bpm: 161.5, status: "rendered" },
        { id: "v-hb-03", rank: 3, score: 76, method: "Equal Power", bars: 8, bpm: 160.0, status: "rendered" }
      ], selectedVariantId: "v-hb-01"
    },
    {
      id: "edge-breath-higher", fromSectionId: "section-breath-intro", toSectionId: "section-higher-break", status: "editing",
      config: { bars: 4, targetBpm: 161.0, renderer: "ML Control", maxStretch: 8, energyPriority: 75, avoidVocals: true },
      cueA: "Takt 88 · 02:11.4", cueB: "Takt 49 · 01:12.3", candidateId: "candidate-a39b3732c9444fb6",
      variants: [
        { id: "v-bh-01", rank: 1, score: 91, method: "ML Control", bars: 4, bpm: 161.0, status: "rendered" },
        { id: "v-bh-02", rank: 2, score: 86, method: "Equal Power", bars: 4, bpm: 161.0, status: "rendered" },
        { id: "v-bh-03", rank: 3, score: 79, method: "ML Control", bars: 6, bpm: 160.8, status: "rendered" }
      ], selectedVariantId: "v-bh-01"
    },
    {
      id: "edge-higher-momentum", fromSectionId: "section-higher-break", toSectionId: "section-momentum-outro", status: "open",
      config: { bars: 4, targetBpm: 160.9, renderer: "Equal Power", maxStretch: 8, energyPriority: 75, avoidVocals: true },
      cueA: "Takt 104 · 02:34.1", cueB: "Takt 76 · 01:54.2", candidateId: "candidate-966e75d1a240fc27",
      variants: [
        { id: "v-hm-01", rank: 1, score: 84, method: "Equal Power", bars: 4, bpm: 160.9, status: "rendered" },
        { id: "v-hm-02", rank: 2, score: 80, method: "ML Control", bars: 4, bpm: 160.9, status: "rendered" },
        { id: "v-hm-03", rank: 3, score: 72, method: "Equal Power", bars: 2, bpm: 160.4, status: "rendered" }
      ], selectedVariantId: "v-hm-01"
    }
  ],
  scoreProfiles: {
    baseline: [
      { label: "Energieform", value: 81 },
      { label: "Grenzglätte", value: 90 },
      { label: "Harmonie", value: 78 },
      { label: "Rhythmus", value: 92 }
    ],
    model: [
      { label: "Rhythmus", value: 92 },
      { label: "Harmonie", value: 78 },
      { label: "Energie", value: 85 },
      { label: "Vocal", value: 88 },
      { label: "Stretch", value: 96 }
    ]
  }
};
