"""Generate editable thesis SVGs; render/check them without running BeatBridge.

Run with the repository venv. Qt is used for installed-font measurements and
headless SVG previews only. All figure content is explicit, not inferred from
audio or model weights. See README.md for source contracts and captions.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QRectF
from PySide6.QtGui import QFont, QFontDatabase, QFontMetricsF, QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)
ROOT = Path(__file__).resolve().parent
PALETTE = {
    "analysis": ("#E6F1FA", "#286998"),
    "data": ("#E1F1EF", "#28756F"),
    "control": ("#FFF0D7", "#9C641B"),
    "render": ("#EEE8F7", "#6F5591"),
    "evaluation": ("#E6F2E4", "#4F7643"),
    "neutral": ("#F1F3F5", "#697783"),
    "reject": ("#FBEAE6", "#A65A4B"),
}
INK = "#1B2630"
LINE = "#48535E"


def el(parent, tag, **attrs):
    return ET.SubElement(parent, f"{{{NS}}}{tag}", {k.replace("_", "-"): str(v) for k, v in attrs.items()})


def metrics(size, bold=False):
    font = QFont("Arial")
    font.setPixelSize(size)
    font.setBold(bold)
    return QFontMetricsF(font)


def wrap(text, width, size, bold=False):
    result = []
    fm = metrics(size, bold)
    for paragraph in text.split("\n"):
        current = ""
        for word in paragraph.split():
            candidate = f"{current} {word}".strip()
            if current and fm.horizontalAdvance(candidate) > width:
                result.append(current)
                current = word
            else:
                current = candidate
        result.append(current)
    return result


class Figure:
    def __init__(self, name, title, height, description):
        self.name, self.height = name, height
        self.root = ET.Element(f"{{{NS}}}svg", {
            "version": "1.1", "width": "160mm", "height": f"{height * .16:.2f}mm",
            "viewBox": f"0 0 1000 {height}", "role": "img",
            "aria-labelledby": "figure-title figure-description",
        })
        el(self.root, "title", id="figure-title").text = title
        el(self.root, "desc", id="figure-description").text = description
        el(self.root, "metadata").text = "BeatBridge; evidence baseline 2026-10-27; artwork 2026-10-28; see README.md."
        defs = el(self.root, "defs")
        marker = el(defs, "marker", id="arrow", viewBox="0 0 10 8", refX="9", refY="4", markerWidth="10", markerHeight="8", markerUnits="userSpaceOnUse", orient="auto")
        el(marker, "path", d="M 0 0 L 10 4 L 0 8 Z", fill=LINE)
        el(self.root, "rect", x=0, y=0, width=1000, height=height, fill="#FFFFFF")
        self.edges = el(self.root, "g", id="connections", fill="none", stroke=LINE, stroke_width="2", stroke_linejoin="round")
        self.nodes_layer = el(self.root, "g", id="nodes")
        self.labels_layer = el(self.root, "g", id="edge-labels")
        self.nodes, self.text_boxes, self.routes = {}, [], []

    def text(self, layer, x, y, value, size=20, bold=False, anchor="middle"):
        fm = metrics(size, bold)
        missing = sorted({c for c in value if not fm.inFontUcs4(ord(c))})
        assert not missing, (self.name, "missing font glyphs", missing, value)
        width = fm.horizontalAdvance(value)
        left = x - width / 2 if anchor == "middle" else x
        bounds = (left, y - fm.ascent(), width, fm.height())
        self.text_boxes.append(bounds)
        element = el(layer, "text", x=x, y=y, fill=INK, font_family="Arial, Helvetica, sans-serif", font_size=size, font_weight="700" if bold else "400", text_anchor=anchor)
        element.text = value
        return bounds

    def node(self, key, x, y, w, h, title, body="", category="neutral", kind="process", dashed=False):
        assert key not in self.nodes
        self.nodes[key] = (x, y, w, h, kind)
        fill, stroke = PALETTE[category]
        group = el(self.nodes_layer, "g", id=key, **{"data-category": category})
        attrs = dict(fill=fill, stroke=stroke, stroke_width="1.5")
        if dashed:
            attrs["stroke_dasharray"] = "8 5"
        if kind == "decision":
            el(group, "polygon", points=f"{x+w/2},{y} {x+w},{y+h/2} {x+w/2},{y+h} {x},{y+h/2}", **attrs)
            text_width, max_height = w * .64, h * .61
        else:
            el(group, "rect", x=x, y=y, width=w, height=h, rx=18 if kind == "data" else 5, **attrs)
            text_width, max_height = w - 34, h - 18
        lines = [(line, 22, True) for line in wrap(title, text_width, 22, True)]
        if body:
            lines += [(line, 20, False) for line in wrap(body, text_width, 20)]
        line_height = 27
        total = len(lines) * line_height
        assert total <= max_height, (self.name, key, "text too tall", total, max_height, lines)
        first = y + h/2 - total/2 + 21
        for i, (line, size, bold) in enumerate(lines):
            assert metrics(size, bold).horizontalAdvance(line) <= text_width, (key, line)
            self.text(group, x+w/2, first+i*line_height, line, size, bold)

    def port(self, node, side):
        x,y,w,h,_ = self.nodes[node]
        return {"t": (x+w/2,y), "b": (x+w/2,y+h), "l": (x,y+h/2), "r": (x+w,y+h/2)}[side]

    def edge(self, source, target, sp="b", tp="t", via=(), label=None, lp=None, dashed=False):
        points = [self.port(source, sp), *via, self.port(target, tp)]
        attrs = {"d": "M " + " L ".join(f"{x:g},{y:g}" for x,y in points), "marker-end": "url(#arrow)"}
        if dashed:
            attrs["stroke-dasharray"] = "8 5"
        el(self.edges, "path", **attrs)
        self.routes.append((source, target, points))
        if label:
            assert lp is not None
            x,y=lp
            width=metrics(18).horizontalAdvance(label)
            el(self.labels_layer, "rect", x=x-width/2-7, y=y-19, width=width+14, height=26, fill="#FFFFFF")
            self.text(self.labels_layer, x, y, label, 18)

    def note(self, text, y, x=500, size=19, bold=False):
        self.text(self.labels_layer, x, y, text, size, bold)

    def save(self, preview_root):
        problems=[]
        items=list(self.nodes.items())
        for i,(a,(x,y,w,h,_)) in enumerate(items):
            assert x >= 0 and y >= 0 and x+w <=1000 and y+h<=self.height, (self.name,a,"outside viewBox")
            for b,(xx,yy,ww,hh,_) in items[i+1:]:
                if min(x+w,xx+ww)>max(x,xx) and min(y+h,yy+hh)>max(y,yy):
                    problems.append(("overlapping nodes",a,b))
        for x,y,w,h in self.text_boxes:
            if x<0 or y<0 or x+w>1000 or y+h>self.height:
                problems.append(("text outside viewBox",x,y,w,h))
        for source,target,points in self.routes:
            for (x1,y1),(x2,y2) in zip(points,points[1:]):
                assert x1==x2 or y1==y2, (self.name,source,target,"non-orthogonal edge")
                for key,(x,y,w,h,_) in items:
                    if key in (source,target):
                        continue
                    hit=(x1==x2 and x<x1<x+w and max(min(y1,y2),y)<min(max(y1,y2),y+h)) or (y1==y2 and y<y1<y+h and max(min(x1,x2),x)<min(max(x1,x2),x+w))
                    if hit:
                        problems.append(("edge through unrelated node",source,target,key))
        assert not problems, (self.name,problems)
        path=ROOT/f"{self.name}.svg"
        ET.indent(self.root, space="  ")
        ET.ElementTree(self.root).write(path,encoding="utf-8",xml_declaration=True)
        renderer=QSvgRenderer(str(path))
        assert renderer.isValid(), (path,"invalid Qt SVG")
        image=QImage(1500,round(self.height*1.5),QImage.Format.Format_ARGB32)
        image.fill(0xFFFFFFFF)
        painter=QPainter(image)
        renderer.render(painter,QRectF(0,0,image.width(),image.height()))
        painter.end()
        assert image.save(str(preview_root/f"{self.name}.png"))
        return {"file":path.name,"nodes":len(self.nodes),"edges":len(self.routes),"viewBox":f"0 0 1000 {self.height}","qt_svg_valid":True,"layout_checks":"passed"}


def figures():
    result=[]
    f=Figure("01-overall-pipeline","BeatBridge overall pipeline",1160,"Transition generation with separate controller training and evaluation workflows.")
    for key,y,title,body,cat in [
        ("input",30,"Import audio","Original recordings", "neutral"),
        ("analysis",190,"Analyse tracks","Tempo, beats and bar-grid provenance", "analysis"),
        ("selection",350,"Select songs and cue points","Automatic ranking or manual GUI selection", "analysis"),
        ("prepare",510,"Prepare transition inputs","Feature windows and aligned audio", "data"),
        ("render",710,"Render transition","Baseline or learned controls", "render"),
        ("export",870,"Preview and export","Transition WAV and provenance", "neutral"),
        ("evaluate",1030,"Evaluate variants","Technical metrics and separate listening studies", "evaluation"),
    ]:
        f.node(key,40,y,530,100,title,body,cat)
    for a,b in zip(["input","analysis","selection","prepare","render","export"],["analysis","selection","prepare","render","export","evaluate"]): f.edge(a,b)
    f.note("Separate training workflow",470,815,20,True)
    f.node("dataset",675,510,285,100,"Build datasets","Track splits and caches","data")
    f.node("train",675,710,285,100,"Train controller","Renderer + fixed objective","control")
    f.node("checkpoint",675,910,285,100,"Best checkpoint","For learned inference","control",kind="data")
    f.edge("prepare","dataset","r","l")
    f.edge("dataset","train")
    f.edge("train","checkpoint")
    f.edge("checkpoint","render","l","r",via=[(620,960),(620,760)])
    result.append(f)

    f=Figure("02-audio-analysis","Beat and bar-grid analysis",1030,"Separate beat and bar-position detectors are merged; failed detection remains explicit as a fallback.")
    f.node("audio",350,30,300,90,"Audio track",kind="data")
    f.node("librosa",40,200,400,100,"librosa","Tempo and beat positions","analysis")
    f.node("auftakt",560,200,400,100,"aufTAKT","Bar positions and meter","analysis")
    f.node("merge",300,380,400,100,"Merge detections","Versioned matching algorithm","analysis")
    f.node("valid",300,530,400,160,"Merge criteria","satisfied?","analysis",kind="decision")
    f.node("detected",40,760,400,100,"Detected grid","Matched beat/bar metadata","data")
    f.node("fallback",560,760,400,100,"Explicit fallback","Approximate or unknown grid","reject")
    f.node("cache",300,930,400,80,"Analysis cache + provenance",category="data",kind="data")
    f.edge("audio","librosa",via=[(500,150),(240,150)])
    f.edge("audio","auftakt",via=[(500,150),(760,150)])
    f.edge("librosa","merge",via=[(240,340),(500,340)])
    f.edge("auftakt","merge",via=[(760,340),(500,340)])
    f.edge("merge","valid")
    f.edge("valid","detected","l","t",via=[(240,610)],label="yes",lp=(250,582))
    f.edge("valid","fallback","r","t",via=[(760,610)],label="no",lp=(750,582))
    f.edge("detected","cache",via=[(240,900),(500,900)])
    f.edge("fallback","cache",via=[(760,900),(500,900)])
    result.append(f)

    f=Figure("03-candidate-selection","Automatic transition-candidate selection",1080,"Candidate generation, strict feasibility filters, feature ranking and top-k selection; manual cues form a separate workflow.")
    f.node("pair",180,25,580,100,"Rank compatible song targets","song_compatibility_v1","analysis")
    f.node("boundaries",180,195,580,115,"Generate cue-pair candidates","Bar boundaries for each requested length","analysis")
    f.node("filters",235,380,470,170,"Feasible windows?","Grid, meter and tempo","analysis",kind="decision")
    f.node("reject",795,410,180,110,"Reject","Record reason","reject")
    f.node("accepted",180,620,580,90,"Accepted candidates",category="data",kind="data")
    f.node("rank",180,790,580,110,"Rank cue combinations","High power, non-overlap, harmony, energy, timbre, tempo","analysis")
    f.node("top",180,970,580,85,"Select top-k candidates",category="data",kind="data")
    f.edge("pair","boundaries")
    f.edge("boundaries","filters")
    f.edge("filters","reject","r","l",label="no",lp=(750,444))
    f.edge("filters","accepted",label="yes",lp=(505,595))
    f.edge("accepted","rank")
    f.edge("rank","top")
    result.append(f)

    f=Figure("04-feature-extraction","Beat-synchronous feature extraction",1010,"Reusable full-track features are cropped at cues, combined with global pair features and passed to the controller; waveform caches are separate.")
    f.node("audio",40,30,400,100,"Track audio + detected grid",category="neutral",kind="data")
    f.node("align",40,210,400,100,"Align track B to source tempo",category="analysis")
    f.node("vocals",560,210,400,110,"Vocal analysis","BS-RoFormer by default","analysis")
    f.node("features",40,410,400,135,"Full-track feature cache","Timing, energy, spectrum, harmony, vocals and masks","data")
    f.node("windows",40,630,400,110,"Extract cue windows","A postroll and B preroll","data")
    f.node("globals",560,630,400,110,"Global pair features","Tempo, tonal and context information","data")
    f.node("inputs",240,850,520,130,"Controller inputs","A/B: T × 54; globals: 16\nProtocol 2 also supplies L/8","data",kind="data")
    f.edge("audio","align")
    f.edge("audio","vocals","r","t",via=[(760,80)])
    f.edge("align","features")
    f.edge("vocals","features","b","r",via=[(760,365),(500,365),(500,477.5)])
    f.edge("features","windows")
    f.edge("windows","globals","r","l")
    f.edge("windows","inputs",via=[(240,800),(500,800)])
    f.edge("globals","inputs",via=[(760,800),(500,800)])
    result.append(f)

    f=Figure("05-dataset-construction","Dataset construction and split isolation",960,"Track-hash splits and training-only normalisation precede immutable, versioned dataset export. Test export depends on the corpus protocol.")
    f.node("records",230,30,540,105,"Selected records + feature artifacts",category="data",kind="data")
    f.node("split",230,220,540,100,"Apply track-level split authority","Reject cross-split pairs","data")
    f.node("train",30,410,270,100,"Training split",category="data",kind="data")
    f.node("val",365,410,270,100,"Validation split",category="data",kind="data")
    f.node("test",700,410,270,100,"Test split","When exported","neutral",kind="data",dashed=True)
    f.node("stats",30,610,400,130,"Fit normalisation statistics","Training artifacts only","data")
    f.node("dataset",280,820,440,115,"Normalise and export dataset","Features, metadata and hashes","data",kind="data")
    for target,x in [("train",165),("val",500),("test",835)]: f.edge("split",target,via=[(500,365),(x,365)])
    f.edge("records","split")
    f.edge("train","stats",via=[(165,560),(230,560)])
    f.edge("train","dataset","l","l",via=[(10,460),(10,877.5)])
    f.edge("stats","dataset",via=[(230,780),(500,780)])
    f.edge("val","dataset",via=[(500,780)])
    f.edge("test","dataset",via=[(835,780),(500,780)],dashed=True)
    result.append(f)

    f=Figure("06-self-supervised-training","Self-supervised controller training",1050,"The fixed proxy objective supplies gradients through a differentiable renderer; validation selects checkpoints without updating weights.")
    f.node("features",80,40,400,100,"Training features",category="data",kind="data")
    f.node("model",80,240,400,100,"Feature-to-control model","Predict mixing curves","control")
    f.node("renderer",80,440,400,100,"Differentiable renderer","Apply predicted controls","render")
    f.node("objective",80,640,400,110,"Fixed proxy objective","Audio and feature-based terms","evaluation")
    f.node("optimiser",80,870,400,100,"AdamW update","Controller parameters only","control")
    f.node("waveforms",620,440,340,115,"Training waveform cache","Mixes and required vocal stems","data",kind="data")
    f.node("validation",620,240,340,115,"Validation pass","Same renderer and objective; no weight update","evaluation")
    f.node("checkpoints",620,40,340,110,"Select best checkpoint","Save history and resume state","control",kind="data")
    f.edge("features","model")
    f.edge("model","renderer")
    f.edge("renderer","objective")
    f.edge("objective","optimiser",label="backpropagation",lp=(390,820),dashed=True)
    f.edge("optimiser","model","l","l",via=[(30,920),(30,290)],dashed=True)
    f.edge("waveforms","renderer","l","r",via=[(550,497.5),(550,490)])
    f.edge("model","validation","r","l",via=[(550,290),(550,297.5)],label="model selection",lp=(550,210))
    f.edge("validation","checkpoints","t","b")
    f.note("No target control curves or human quality labels are required.",1020)
    result.append(f)

    f=Figure("07-fixed-tcn-bilstm","Fixed four-bar TCN/BiLSTM architecture",1050,"Shared temporal encoders, pair fusion, projected global context, a bidirectional LSTM and a constrained ten-channel control head.")
    f.node("a",30,30,400,90,"Features A","32 × 54","data",kind="data")
    f.node("b",570,30,400,90,"Features B","32 × 54","data",kind="data")
    f.node("encoder_a",30,205,400,100,"Shared TCN encoder","Same weights for A and B","control")
    f.node("encoder_b",570,205,400,100,"Shared TCN encoder","Same weights for A and B","control")
    f.node("fusion",300,390,400,125,"Pair fusion","Concat(A, B, A - B, A * B)\nLinear: 512 → 256","control")
    f.node("global",30,590,285,130,"Global features","16 values → 256\nLinear projection","data")
    f.node("add",400,590,400,100,"Add global context","Broadcast over time","control")
    f.node("lstm",400,770,400,100,"Two-layer BiLSTM","128 hidden units per direction","control")
    f.node("head",400,940,400,90,"Constrained control head","32 × 10 temporal controls","control")
    f.edge("a","encoder_a")
    f.edge("b","encoder_b")
    f.edge("encoder_a","fusion",via=[(230,350),(500,350)])
    f.edge("encoder_b","fusion",via=[(770,350),(500,350)])
    f.edge("fusion","add",via=[(500,555),(600,555)])
    f.edge("global","add","r","l",via=[(360,655),(360,640)])
    f.edge("add","lstm")
    f.edge("lstm","head")
    result.append(f)

    f=Figure("08-controller-renderer-contracts","Controller, renderer and objective contracts",845,"The four trained controller families use different rendering and objective contracts. The variable TCN uses a stem-aware renderer, not the fixed TCN's three-band renderer.")
    for x,txt in [(165,"Controller"),(520,"Training renderer"),(870,"Proxy objective")]: f.note(txt,30,x,20,True)
    rows=[
        (70,"Time-shared MLP","Four bars","Two-band renderer","Mix + low-end handover","Objective v4",""),
        (260,"Vocal-aware MLP","Four bars","Stem-aware renderer","Accompaniment + vocals","Objective v5",""),
        (450,"Fixed TCN/BiLSTM","Four bars","Three-band renderer","Low / mid / high + ducking","Objective v4",""),
        (640,"Variable TCN/BiLSTM","2 / 4 / 6 / 8 bars","Stem-aware renderer","Accompaniment + vocals","Objective v5","Time-normalised"),
    ]
    for i,(y,title,body,rt,rb,ot,ob) in enumerate(rows):
        f.node(f"model_{i}",20,y,290,130,title,body,"control")
        f.node(f"renderer_{i}",365,y,310,130,rt,rb,"render")
        f.node(f"objective_{i}",740,y,245,130,ot,ob,"evaluation")
        f.edge(f"model_{i}",f"renderer_{i}","r","l")
        f.edge(f"renderer_{i}",f"objective_{i}","r","l")
    f.note("The generic fixed-TCN training path uses mid-band ducking as a vocal proxy.",820,500,18)
    result.append(f)

    f=Figure("09-variable-bridge-alignment","Local-grid alignment and bridge construction",1060,"The source postroll sets the local bridge duration. Target preroll and target vocal stem receive the same pitch-preserving stretch before rendering.")
    f.node("source",40,30,400,100,"Source A + cue A","Detected local grid","data",kind="data")
    f.node("target",560,30,400,100,"Target B + cue B","Detected local grid","data",kind="data")
    f.node("postroll",40,220,400,130,"Extract A postroll","After cue A; mix + vocal\nLocal duration authority","data")
    f.node("preroll",560,220,400,130,"Extract B preroll","Before cue B\nMix and vocal stem","data")
    f.node("stretch",560,430,400,110,"Stretch target to source duration","Rubber Band; pitch preserved","analysis")
    f.node("aligned",260,640,480,110,"Aligned waveform windows","Same sample count for mixes and stems","data",kind="data")
    f.node("render",260,820,480,90,"Apply mixing controls",category="render")
    f.node("output",190,970,620,70,"A context → rendered bridge → B context",category="neutral",kind="data")
    f.edge("source","postroll")
    f.edge("target","preroll")
    f.edge("preroll","stretch")
    f.edge("postroll","stretch","r","l",via=[(500,285),(500,485)],label="source duration",lp=(500,395))
    f.edge("postroll","aligned",via=[(240,590),(500,590)])
    f.edge("stretch","aligned",via=[(760,590),(500,590)])
    f.edge("aligned","render")
    f.edge("render","output")
    result.append(f)

    f=Figure("10-transition-evaluation","Technical and perceptual transition evaluation",1070,"Technical audio metrics and blinded listening ratings are distinct branches. Listening variants are decoded only after all required ratings are complete.")
    f.node("variants",280,25,440,90,"Rendered transition variants",category="neutral",kind="data")
    f.node("metric",40,220,400,130,"Technical render metric","Energy, boundaries, harmony and rhythm","evaluation")
    f.node("report",40,450,400,110,"Scores and diagnostics","Technical baseline only","evaluation",kind="data")
    f.node("blind",560,220,400,130,"Export blinded listening set","Matched context and shared peak gain; separate answer key","evaluation")
    f.node("ratings",560,450,400,110,"Collect human ratings","Preferences and criteria","evaluation")
    f.node("complete",560,640,400,160,"All required ratings","complete?","evaluation",kind="decision")
    f.node("decode",560,860,400,80,"Unblind methods",category="evaluation")
    f.node("results",560,980,400,70,"Analyse listening results",category="evaluation",kind="data")
    f.edge("variants","metric",via=[(500,165),(240,165)])
    f.edge("variants","blind",via=[(500,165),(760,165)])
    f.edge("metric","report")
    f.edge("blind","ratings")
    f.edge("ratings","complete")
    f.edge("complete","decode",label="yes",lp=(795,835))
    f.edge("complete","ratings","r","r",via=[(985,720),(985,505)],label="no",lp=(975,610),dashed=True)
    f.edge("decode","results")
    result.append(f)

    f=Figure("11-experimental-cue-ranker","Experimental learned cue-ranker pipeline",890,"Implemented extension with synthetic verification only. No real-data ranker training or independent musical quality result is established.")
    f.note("Experimental extension · synthetic verification only",35,500,22,True)
    f.node("index",40,110,400,110,"Verified pair index","Train and validation only","data")
    f.node("universe",40,310,400,110,"Candidate-v2 universe","All accepted cue candidates","data")
    f.node("teacher",40,510,400,125,"Frozen teacher release","Variable TCN + renderer\n+ Objective v5","control")
    f.node("labels",40,730,400,115,"Teacher labels","Utility, guard rejections and provenance","data")
    f.node("dataset",560,730,400,115,"Format-3 grouped dataset","Train-only normalisation","data")
    f.node("training",560,510,400,125,"Train temporal cue ranker","Grouped listwise ranking loss","control")
    f.node("checkpoint",560,310,400,110,"Verified ranker checkpoint","Bound to dataset and teacher","control",kind="data")
    f.node("inference",560,110,400,110,"Optional cue ranking","Select candidate IDs for rendering","analysis",dashed=True)
    f.edge("index","universe")
    f.edge("universe","teacher")
    f.edge("teacher","labels")
    f.edge("labels","dataset","r","l")
    f.edge("dataset","training","t","b")
    f.edge("training","checkpoint","t","b")
    f.edge("checkpoint","inference","t","b",dashed=True)
    result.append(f)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview-dir",type=Path,required=True)
    args=parser.parse_args()
    app=QGuiApplication.instance() or QGuiApplication([])
    # Qt's offscreen platform does not enumerate Windows system fonts.
    for font_file in ("arial.ttf", "arialbd.ttf"):
        assert QFontDatabase.addApplicationFont(f"C:/Windows/Fonts/{font_file}") >= 0
    args.preview_dir.mkdir(parents=True,exist_ok=True)
    reports=[figure.save(args.preview_dir) for figure in figures()]
    (args.preview_dir/"verification.json").write_text(json.dumps(reports,indent=2)+"\n",encoding="utf-8")
    from PIL import Image, ImageOps, ImageDraw, ImageFont
    thumbs=[]
    font=ImageFont.truetype("C:/Windows/Fonts/arial.ttf",22)
    for report in reports:
        src=Image.open(args.preview_dir/Path(report["file"]).with_suffix(".png"))
        thumb=ImageOps.contain(src,(470,565))
        tile=Image.new("RGB",(500,620),"#e9ecef")
        tile.paste(thumb,((500-thumb.width)//2,45))
        ImageDraw.Draw(tile).text((15,12),report["file"].removesuffix(".svg"),font=font,fill="#1b2630")
        thumbs.append(tile)
    sheet=Image.new("RGB",(1500,620*((len(thumbs)+2)//3)),"white")
    for i,tile in enumerate(thumbs): sheet.paste(tile,((i%3)*500,(i//3)*620))
    sheet.save(args.preview_dir/"contact-sheet.png")
    print(json.dumps({"result":"PASS","figures":len(reports),"nodes":sum(r["nodes"] for r in reports),"all_svg_valid":True,"layout_checks":"passed","preview_dir":str(args.preview_dir.resolve())}))


if __name__=="__main__":
    main()
