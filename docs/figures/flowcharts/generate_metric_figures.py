"""Render metric-mechanism SVGs from explicit, code-audited definitions.

The first eleven pipeline figures are not rewritten. Numeric illustrations
are synthetic and labelled; no corpus audio, ratings or weights are loaded.
"""
from __future__ import annotations

import argparse
from io import StringIO
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import generate_flowcharts as base
from generate_flowcharts import Figure, el, QGuiApplication, QFontDatabase


class MetricFigure(Figure):
    def __init__(self, name, title, height, description):
        super().__init__(name, title, height, description)
        self.root.find(f"{{{base.NS}}}metadata").text = (
            "BeatBridge; metric definitions audited 2026-10-29; "
            "code defaults, not run-specific weights; see METRICS_README.md."
        )


def bank(name, title, input_text, rows, output_title, output_body, lower=False):
    out_y = 220 + 150 * len(rows)
    f = MetricFigure(name, title, out_y+160, title)
    f.node("inputs",120,30,760,90,input_text,category="data",kind="data")
    for i,(heading,formula,category) in enumerate(rows):
        y=180+150*i
        f.node(f"component_{i}",120,y,760,120,heading,formula,category)
    f.node("output",120,out_y,760,100,output_title,output_body,"evaluation",kind="data")
    for i in range(len(rows)):
        y=240+150*i
        f.edge("inputs",f"component_{i}","l","l",via=[(50,75),(50,y)])
        f.edge(f"component_{i}","output","r","r",via=[(950,y),(950,out_y+50)])
    f.note("Code defaults shown; each run's saved configuration is authoritative.",out_y+140,500,19)
    return f


def energy_plot(f):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({"font.family":"Arial","font.size":15,"svg.fonttype":"none","svg.hashsalt":"beatbridge-metric-20261029"})
    t=np.linspace(0,1,32)
    target=np.where(t<=.5,-6+(-12+6)*t*2,-12+(-3+12)*(t-.5)*2)
    rendered=target+1.6*np.sin(np.pi*t)
    fig,ax=plt.subplots(figsize=(9,3.1))
    ax.plot(t,target,color="#286998",ls="--",lw=2,label="Target frame RMS")
    ax.plot(t,rendered,color="#6F5591",lw=2,label="Illustrative rendered RMS")
    ax.set(xlim=(0,1),ylim=(-14,0),xlabel="Normalised transition position",ylabel="RMS (dBFS)")
    ax.set_xticks([0,.5,1]);ax.set_yticks([-12,-6,0])
    ax.legend(loc="upper center",bbox_to_anchor=(.5,1.25),ncol=2,frameon=False,fontsize=13)
    ax.spines[['top','right']].set_visible(False)
    ax.grid(axis="y",color="#DFE4E8",lw=.6)
    fig.tight_layout(pad=.7)
    buf=StringIO();fig.savefig(buf,format="svg",metadata={"Date":None});plt.close(fig)
    nested=ET.fromstring(buf.getvalue())
    # Flatten the SVG viewport: QtSvg does not render this nested <svg>
    # consistently, while ordinary SVG groups retain the same vector plot.
    _,_,width,height=map(float,nested.attrib['viewBox'].split())
    scale=min(910/width,320/height)
    plot=el(f.nodes_layer,"g",id="energy-plot",transform=f"translate(45 {55+(320-height*scale)/2}) scale({scale})")
    for child in nested:
        plot.append(child)


def figures():
    result=[]
    f=MetricFigure("12-metric-roles","Distinct roles of BeatBridge metrics",1050,"Song and cue scores, rendered-audio metrics, training losses and human ratings are separate quantities.")
    rows=[
        ("Whole songs A and B","Before cue generation","Song compatibility","Score [0,1] · higher is better","analysis"),
        ("Candidate cue windows","Before rendering","Feature cue ranking","Score [0,1] · higher is better","analysis"),
        ("Rendered transition audio","After rendering","Render-audio metric","Score [0,1] · higher is better","render"),
        ("Audio + controls + features","During controller training","Fixed proxy objective","Loss · lower is better","control"),
        ("Blinded listening variants","Separate human study","Ratings and preferences","Criterion summaries; wins / ties","evaluation"),
    ]
    for i,(it,ib,ot,ob,c) in enumerate(rows):
        y=30+i*200
        f.node(f"input_{i}",40,y,400,120,it,ib,"data",kind="data")
        f.node(f"metric_{i}",560,y,400,120,ot,ob,c)
        f.edge(f"input_{i}",f"metric_{i}","r","l")
    f.note("A high technical score or a low training loss is not a human quality probability.",1030,500,18)
    result.append(f)

    result.append(bank("13-song-compatibility-metric","Song-compatibility metric", "Whole-track summaries of songs A and B", [
        ("Harmonic similarity · weight 0.35","Cosine similarity of mean 12-bin chroma profiles","analysis"),
        ("Tempo similarity · weight 0.25","d = |BPM_A - BPM_B| / max(BPM_A, BPM_B)\nscore = max(0, 1 - d / 0.15)","analysis"),
        ("Timbre similarity · weight 0.15","d = |log2((centroid_A + 20) / (centroid_B + 20))|\nscore = exp(-d)","analysis"),
        ("Energy similarity · weight 0.15","score = max(0, 1 - |RMS_A_dB - RMS_B_dB| / 24)","analysis"),
        ("Rhythm-profile similarity · weight 0.10","Cosine similarity of 32-point onset-strength profiles","analysis"),
    ],"Weighted sum → song ranking","Score in [0,1] · higher is better; no cue-specific quality guarantee"))

    result.append(bank("14-cue-ranking-metric","Feature-based cue ranking", "Four raw windows around source and target cues", [
        ("High power · weight 0.30","Minimum of the two drop-window energy percentiles","analysis"),
        ("Non-overlap · weight 0.30","Combine quiet transition windows with energy fall and rise\nSee Figure 15 for the component calculation","analysis"),
        ("Harmonic similarity · weight 0.18","Cosine similarity of the two drop-window chroma profiles","analysis"),
        ("Energy similarity · weight 0.10","max(0, 1 - |drop_A_dB - drop_B_dB| / 24)","analysis"),
        ("Timbre similarity · weight 0.05","exp(-|log2((centroid_A + 20) / (centroid_B + 20))|)","analysis"),
        ("Tempo similarity · weight 0.07","max(0, 1 - relative_BPM_difference / 0.15)","analysis"),
    ],"Weighted sum → cue ranking","Score in [0,1] · higher is better; renderer has not run yet"))

    f=MetricFigure("15-cue-energy-and-non-overlap","Cue-window high power and non-overlap",1030,"Four unrendered cue windows provide track-relative energy percentiles and local energy contrasts.")
    windows=[("apre",30,"A before cue","Drop window","control"),("apost",270,"A after cue","Source postroll","analysis"),("bpre",510,"B before cue","Target preroll","analysis"),("bpost",750,"B after cue","Drop window","control")]
    for k,x,t,b,c in windows: f.node(k,x,35,220,115,t,b,c,kind="data")
    f.node("extract",120,250,760,110,"Measure window RMS and track energy percentiles","Each window is compared with its own track's RMS distribution","data")
    f.node("hp",30,460,420,130,"High-power score","HP = min(p_A_before, p_B_after)","analysis")
    f.node("contrast",550,460,420,140,"Boundary contrast","d_A = clip(fall_A_dB / 6, 0, 1)\nd_B = clip(rise_B_dB / 6, 0, 1)","analysis")
    f.node("quiet",550,660,420,120,"Transition quietness","q = 1 - max(p_A_after, p_B_before)","analysis")
    f.node("no",550,870,420,110,"Non-overlap score","NO = sqrt(q * min(d_A, d_B))","analysis")
    f.node("contribution",30,870,420,110,"Contribution to cue score","0.30 * HP + 0.30 * NO\n+ four other components","evaluation",kind="data")
    for k,x,_,_,_ in windows: f.edge(k,"extract",via=[(x+110,205),(500,205)])
    f.edge("extract","hp",via=[(500,410),(240,410)])
    f.edge("extract","contrast",via=[(500,410),(760,410)])
    f.edge("extract","quiet","r","r",via=[(990,305),(990,720)])
    f.edge("contrast","no","l","t",via=[(510,530),(510,820),(760,820)])
    f.edge("quiet","no")
    f.edge("hp","contribution")
    f.edge("no","contribution","l","r")
    f.note("p denotes an empirical percentile, not an absolute loudness threshold.",1015,500,18)
    result.append(f)

    result.append(bank("16-render-audio-metric","Rendered-transition baseline metric","Rendered audio + exact bridge boundaries + expected BPM",[
        ("Energy shape · weight 0.30","sqrt(clip(fall_dB / 6, 0, 1) * clip(rise_dB / 6, 0, 1))\nCompare pre-context, whole bridge and post-context RMS","render"),
        ("Boundary smoothness · weight 0.30","Average sqrt(RMS_score * click_score) over actual boundaries\nLocal loudness jumps and sample discontinuities","render"),
        ("Harmonic continuity · weight 0.20","Average chroma cosine similarity:\npre → first bridge half; second bridge half → post","render"),
        ("Rhythmic stability · weight 0.20","Mean-centred onset correlation at the expected beat lag\nscore = (correlation + 1) / 2","render"),
    ],"Weighted sum → rendered-variant ranking","Score in [0,1] · higher is better; separate from the training loss"))

    f=MetricFigure("17-boundary-and-rhythm-mechanisms","Boundary and rhythm score mechanisms",800,"Two separate components of the rendered-audio score: local discontinuity checks and beat-lag onset correlation.")
    f.node("boundary",40,30,400,100,"Actual render boundary b","Start/end of bridge, or hard cut","data",kind="data")
    f.node("context",560,30,400,100,"Local rendered context","Expected BPM and sample rate","data",kind="data")
    f.node("jumps",40,235,400,220,"Measure RMS and sample jump","R = exp(-|RMS_left_dB - RMS_right_dB| / 12)\nJ = boundary jump / local p99(|Δsample|)\nC = exp(-max(0, J - 1))","render")
    f.node("corr",560,235,400,220,"Measure beat-lag correlation","Compute onset envelope and subtract its mean\nlag = max(1, round(60 * sr / (BPM * 512)))\nrho = cosine(envelope[:-lag], envelope[lag:])","render")
    f.node("bs",40,565,400,120,"Boundary score","sqrt(R * C)\nThen average across boundaries","evaluation",kind="data")
    f.node("rs",560,565,400,120,"Rhythm score","clip((rho + 1) / 2, 0, 1)","evaluation",kind="data")
    f.edge("boundary","jumps");f.edge("jumps","bs")
    f.edge("context","corr");f.edge("corr","rs")
    f.note("Silent / insufficient onset evidence returns a neutral rhythm score of 0.5.",760,500,19)
    result.append(f)

    f=MetricFigure("18-objective-energy-and-boundaries","Training objective: energy and boundary losses",970,"An illustrative target in frame RMS decibels and the two corresponding normalised mean-squared-error losses. Not measured experiment data.")
    energy_plot(f)
    f.note("Illustrative levels only · no experiment measurements",425,500,20,True)
    f.node("target",70,485,860,110,"Construct frame-level energy target","Start = first source-frame RMS; end = last target-frame RMS\nV-shaped valley = min(start, end) - 6 dB","data")
    f.node("energy",40,690,440,160,"Energy-shape loss · weight 1.0","mean(((rendered_dB - target_dB) / 12)^2)","evaluation")
    f.node("boundary",520,690,440,160,"Boundary loss · weight 0.5","Squared endpoint RMS differences:\nstart vs source start; end vs target end\nNormalise by 6 dB, then average","evaluation")
    f.edge("target","energy",via=[(500,635),(260,635)])
    f.edge("target","boundary",via=[(500,635),(740,635)])
    f.note("Lower is better · endpoint RMS matching is not the render-metric click detector.",920,500,18)
    result.append(f)

    result.append(bank("19-control-and-clipping-losses","Training objective: control and clipping terms","Mix position m, low-end position l, rendered samples y",[
        ("Uniform-step regularisation · weight 0.02","u = 1 / (T - 1)\nmean(((Δm - u) / u)^2 + ((Δl - u) / u)^2)","control"),
        ("Control curvature · weight 0.05","Penalise changes between successive control increments\nmean((Δ²m / u)^2 + (Δ²l / u)^2)","control"),
        ("Monotonicity · weight 0.10","Penalise backward handovers\nmean(relu(-Δm)^2 + relu(-Δl)^2)","control"),
        ("Clipping · weight 2.0","Penalise samples exceeding full scale\nmean(relu(|y| - 1)^2)","render"),
    ],"Add weighted penalties to the training objective","Lower is better · these losses are not normalised quality scores",True))

    result.append(bank("20-objective-v4-conditioned-terms","Objective v4: feature-conditioned terms","Valid features + mix/low-end controls; framewise vocal strengths s_A/s_B",[
        ("Vocal overlap · weight 1.0","mean(s_A * s_B * (gain_A * gain_B)^2)\nMix-position equal-power gains; joint vocal-validity mask","control"),
        ("Vocal boundary cost · weight 0.30","Handover rate × source cut cost and target entry cost\nOffset, onset and phrase-progress features condition the cost","control"),
        ("Transient artifact proxy · weight 0.08","Onset / spectral-flux importance × (mix rate + 0.5 * low rate)\nJoint audio-validity mask; average over control intervals","control"),
    ],"Add to Objective v4","Missing conditioning on both sides → exact zero conditioned terms",True))

    result.append(bank("21-objective-v5-vocal-losses","Objective v5: stem-aware vocal losses","Vocal gains g_A/g_B and stem-weighted strengths s_A/s_B",[
        ("Stem overlap · weight 1.0","mean(s_A * s_B * (g_A * g_B)^2)\nPenalise two strong vocal stems being audible together","control"),
        ("Vocal audibility · weight 0.5","mean(s_A * (1 - 0.75*s_B) * (1 - g_A)^2 + symmetric B term)\nAvoid suppressing an active vocal without sufficient reason","control"),
        ("Mid-phrase gain change · weight 0.2","mean(mid(s_A*(1-offset_A)) * (Δg_A)^2\n+ mid(s_B*(1-onset_B)) * (Δg_B)^2)","control"),
    ],"Add vocal terms to the configured base objective","Default v5 disables v4 feature-vocal overlap/boundary weights",True))

    f=MetricFigure("22-experimental-ranker-metrics","Experimental cue-ranker evaluation metrics",1170,"Synthetic demonstration of top-1 and top-k agreement, teacher-ordinal NDCG and score correlation. No measured ranker quality result.")
    f.note("Experimental ranker · agreement with a frozen teacher",30,500,22,True)
    f.node("teacher",40,90,420,130,"Teacher order","A → B → C → D\nOrdinal gains: 4, 3, 2, 1","data",kind="data")
    f.node("ranker",540,90,420,130,"Illustrative ranker order","B → A → D → C\nk = 2; synthetic ordering only","control",kind="data")
    f.node("compare",250,290,500,100,"Frozen candidate group","Compare the same candidate IDs","data")
    f.node("top1",40,480,420,130,"Top-1 agreement","Does the selected candidate equal the teacher's first choice?\nHere: 0","evaluation")
    f.node("topk",540,480,420,130,"Top-k agreement","|ranker top-k ∩ teacher top-k| / k\nHere: 1.0 despite a different first choice","evaluation")
    f.node("ndcg",40,740,420,170,"NDCG at k","DCG = sum(gain_i / log2(i + 1))\nNDCG = DCG / ideal_DCG\nHere: NDCG@2 = 0.937 (rounded)","evaluation")
    f.node("corr",540,740,420,170,"Score correlation and utility","Pearson(ranker score, teacher utility)\nAlso report selected top-1 teacher utility","evaluation")
    for source in ("teacher","ranker"):
        x=f.port(source,"b")[0]
        f.edge(source,"compare",via=[(x,260),(500,260)])
    f.edge("compare","top1",via=[(500,435),(250,435)])
    f.edge("compare","topk",via=[(500,435),(750,435)])
    f.edge("compare","ndcg","l","l",via=[(20,340),(20,825)])
    f.edge("compare","corr","r","r",via=[(980,340),(980,825)])
    f.note("Report global and per-length summaries; agreement is not listening quality.",1010,500,19)
    f.note("No real-data cue-ranker quality result is established by this illustration.",1080,500,19)
    result.append(f)

    f=MetricFigure("23-human-rating-summary","Human listening-rating summaries",910,"Completed blind ratings are remapped to methods, then preference rates and criterion summaries are reported separately.")
    f.node("blind",250,30,500,100,"Completed blind ratings","Preference A/B/tie + criterion scores 1–5","data",kind="data")
    f.node("map",250,215,500,100,"Apply hidden answer key","Map public A/B labels to method identities","analysis")
    f.node("preferences",40,420,420,180,"Preference summary","Count wins and ties separately\nWin rate = method wins / non-ties\nAll ties → no decisive win rate","evaluation")
    f.node("criteria",540,420,420,180,"Criterion summaries","Per-method mean, minimum and maximum\nPaired difference = candidate - reference\nOverall pools the criterion scores","evaluation")
    f.node("limits",120,725,760,120,"Report study scope and limits","Repeated cues are not independent track tests\nDescriptive summaries do not establish population-level superiority","neutral",kind="data")
    f.edge("blind","map")
    f.edge("map","preferences",via=[(500,365),(250,365)])
    f.edge("map","criteria",via=[(500,365),(750,365)])
    f.edge("preferences","limits",via=[(250,660),(500,660)])
    f.edge("criteria","limits",via=[(750,660),(500,660)])
    result.append(f)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview-dir",type=Path,required=True)
    args=parser.parse_args()
    app=QGuiApplication.instance() or QGuiApplication([])
    for filename in ("arial.ttf","arialbd.ttf"):
        assert QFontDatabase.addApplicationFont(f"C:/Windows/Fonts/{filename}")>=0
    args.preview_dir.mkdir(parents=True,exist_ok=True)
    reports=[f.save(args.preview_dir) for f in figures()]
    (args.preview_dir/"verification.json").write_text(json.dumps(reports,indent=2)+"\n",encoding="utf-8")
    from PIL import Image,ImageOps,ImageDraw,ImageFont
    sheet=Image.new("RGB",(1500,620*math.ceil(len(reports)/3)),"white")
    font=ImageFont.truetype("C:/Windows/Fonts/arial.ttf",20)
    for i,report in enumerate(reports):
        image=Image.open(args.preview_dir/Path(report['file']).with_suffix('.png'))
        thumb=ImageOps.contain(image,(470,565))
        tile=Image.new("RGB",(500,620),"#e9ecef")
        tile.paste(thumb,((500-thumb.width)//2,45))
        ImageDraw.Draw(tile).text((12,12),Path(report['file']).stem,font=font,fill=base.INK)
        sheet.paste(tile,((i%3)*500,(i//3)*620))
    sheet.save(args.preview_dir/"contact-sheet.png")
    print(json.dumps({"result":"PASS","metric_figures":len(reports),"nodes":sum(r['nodes'] for r in reports),"all_svg_valid":True,"layout_checks":"passed"}))


if __name__=="__main__":
    main()
