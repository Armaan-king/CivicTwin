"""Generate the 2.5-minute demo script as a Word document.

    python scripts/make_demo_script.py

Timed for roughly 150 words a minute, which is an unhurried presenting pace. Every number
in it was read off the running application rather than remembered, and the two places where
the honest answer differs from the impressive one are marked so they are not stumbled into.
"""
from __future__ import annotations

import pathlib

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor, Inches

OUT = pathlib.Path(__file__).resolve().parent.parent / "CivicTwin-demo-script.docx"

NAVY = RGBColor(0x14, 0x2B, 0x45)
RED = RGBColor(0xC2, 0x2A, 0x33)
GREY = RGBColor(0x6B, 0x7B, 0x8C)

#: (cumulative start, page, on-screen cue, what to say)
BEATS = [
    ("0:00", "0:15", "Landing page", "Test the impact. Improve the plan.", [
        ("say", "Close two bus stops and the average journey across a town gets faster. "
                "That number is true, and it is the number the plan gets approved on."),
        ("say", "CivicTwin finds the people that average hides."),
    ]),
    ("0:15", "0:32", "Policy", "Click POLICY", [
        ("do", "Point at the left panel, then the right."),
        ("say", "A planner writes the proposal in plain English. CivicTwin reads it into a "
                "structured change and shows that reading back before anything runs."),
        ("say", "Anything it assumed rather than was told is marked assumed. You check the "
                "interpretation before you trust the output."),
    ]),
    ("0:32", "0:52", "Simulate", "Click RUN SIMULATION, let all four stages play", [
        ("do", "Wait for the counters to settle — they animate for about a second and a half."),
        ("say", "Four stages: the corridor as it runs today, the stops closing, residents "
                "adjusting, and the full picture."),
        ("say", "Twenty-one essential trips lost. Seventeen people walking further. "
                "And four family carers — who appear only in the last stage, because they "
                "were never near the closure."),
    ]),
    ("0:52", "1:17", "Impact", "Click IMPACT", [
        ("say", "Twenty-two residents severely harmed. Four through someone else's "
                "dependency."),
        ("do", "Point at the two bars on the right."),
        ("say", "Carers are five times more likely to be severely harmed — and not one of "
                "them lost access themselves. They are driving a parent to the clinic and "
                "missing their own shift."),
        ("say", "That finding does not exist without the dependency graph."),
    ]),
    ("1:17", "1:47", "Voices", "Click VOICES — residents arrive one at a time", [
        ("do", "Let three or four load, then read one aloud."),
        ("say", "Every resident reasons in their own words, using only the facts we gave "
                "them about their own life."),
        ("say", "Mister Ang: the policy closes the stop I use for trips to the hospital. "
                "Now I walk 360 metres instead of 135."),
        ("say", "His support falls from zero point six to zero point one five. Every claim "
                "cites the facts it rests on, and anything citing something we never told "
                "them is rejected — the count is in the header."),
    ]),
    ("1:47", "2:05", "Options", "Click OPTIONS", [
        ("do", "Point at the highlighted row of the comparison table."),
        ("say", "Five interventions, each re-simulated over the same residents with the "
                "same seeds."),
        ("say", "Assisted transport looks cheapest — and it moves the harm rather than "
                "removing it, creating two newly harmed riders on a corridor the original "
                "policy never touched. A single score would have hidden that."),
    ]),
    ("2:05", "2:30", "Learn", "Click LEARN", [
        ("say", "We asked residents. The model was three points off overall — and fourteen "
                "points off on one road."),
        ("do", "Point at the amber panel."),
        ("say", "The covered walkway ends partway and there is a slope. The model costed "
                "the distance, not the walk. It found that in residents' own free text."),
        ("say", "It proposes a correction sized from the error, and a human decides. It "
                "never applies itself."),
    ]),
]

CLOSING = ("If you have ten seconds spare, close on: “A policy that looks fine on average, "
           "and the four people it quietly breaks. That is the whole product.”")

HONESTY = [
    ("If asked “is this real data?”",
     "The bus network is real — Singapore LTA DataMall, under the open data licence. "
     "The 2,000 residents are synthetic and labelled as such on every screen. The "
     "consultation responses are seeded for the demo; the header says so."),
    ("If asked “what happens when you click Apply?”",
     "It records the decision. A human approving a model change is the boundary we "
     "enforce — the correction feeds the next run, and nothing is ever self-applied. "
     "(It is set to record-only for this demo, so a click cannot rebuild the screens "
     "mid-presentation.)"),
    ("If asked “did the model make these people up?”",
     "Each resident is given a numbered list of facts about their own life and may cite "
     "only those. A conclusion citing anything else is rejected and counted — the count "
     "is on the Voices header. Distances and routes are computed in code; the resident "
     "only judges what they mean."),
    ("If asked about coverage",
     "109 residents were evaluated of 2,000. The rest were never asked, and the product "
     "reports them as unknown rather than unaffected — that distinction is the point."),
]


def _para(doc, text, *, size=11, bold=False, color=None, space_after=6, italic=False,
          align=None):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color is not None:
        run.font.color.rgb = color
    p.paragraph_format.space_after = Pt(space_after)
    if align is not None:
        p.alignment = align
    return p


def build() -> pathlib.Path:
    doc = Document()
    for section in doc.sections:
        section.top_margin = Inches(0.7)
        section.bottom_margin = Inches(0.7)
        section.left_margin = Inches(0.85)
        section.right_margin = Inches(0.85)

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    _para(doc, "CivicTwin", size=24, bold=True, color=NAVY, space_after=0)
    _para(doc, "Two-and-a-half minute demo script", size=13, color=GREY, space_after=2)
    _para(doc, "Timed at an unhurried 150 words a minute. Every figure below was read off "
               "the running application.", size=9, color=GREY, italic=True, space_after=14)

    for start, end, page, cue, lines in BEATS:
        head = doc.add_paragraph()
        r = head.add_run(f"{start} – {end}   {page}")
        r.bold = True
        r.font.size = Pt(13)
        r.font.color.rgb = NAVY
        head.paragraph_format.space_before = Pt(10)
        head.paragraph_format.space_after = Pt(1)

        _para(doc, cue, size=9.5, color=RED, bold=True, space_after=5)

        for kind, text in lines:
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.22)
            p.paragraph_format.space_after = Pt(4)
            if kind == "do":
                run = p.add_run("[ " + text + " ]")
                run.italic = True
                run.font.size = Pt(9.5)
                run.font.color.rgb = GREY
            else:
                run = p.add_run(text)
                run.font.size = Pt(11)

    doc.add_page_break()

    _para(doc, "If you have a moment spare", size=14, bold=True, color=NAVY, space_after=4)
    _para(doc, CLOSING, size=11, space_after=16)

    _para(doc, "Questions you should expect", size=14, bold=True, color=NAVY, space_after=6)
    _para(doc, "Answer these plainly. Every one of them has a good honest answer, and the "
               "honest answer is more impressive than a hedge.",
          size=9.5, color=GREY, italic=True, space_after=10)

    for question, answer in HONESTY:
        _para(doc, question, size=11, bold=True, color=NAVY, space_after=2)
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.22)
        p.paragraph_format.space_after = Pt(10)
        p.add_run(answer).font.size = Pt(10.5)

    _para(doc, "Before you start", size=14, bold=True, color=NAVY, space_after=6)
    for item in [
        "Backend on port 8000, frontend on 5173. Hard-refresh the browser.",
        "Click through every page once to warm it — Voices takes about twenty seconds "
        "the first time after a backend restart, then it is instant.",
        "Do not restart the backend right before presenting.",
        "On Simulate, let the counters finish animating before you read them.",
    ]:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.space_after = Pt(3)
        p.add_run(item).font.size = Pt(10.5)

    doc.save(OUT)
    return OUT


if __name__ == "__main__":
    path = build()
    print(f"wrote {path} ({path.stat().st_size // 1024} KB)")
