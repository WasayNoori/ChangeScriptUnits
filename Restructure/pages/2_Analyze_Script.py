import json
import os
import re
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv, find_dotenv
import anthropic

load_dotenv(find_dotenv())
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

st.set_page_config(page_title="Script Analyzer", layout="wide")

# ── Styling (shared with Critique Viewer) ─────────────────────────────────────
st.markdown("""
<style>
.meta-box {
    background: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    padding: 1rem 1.25rem;
    margin-bottom: 1.25rem;
}
.meta-row { display: flex; flex-wrap: wrap; gap: 0.5rem 2rem; margin-top: 0.25rem; }
.meta-item { font-size: 0.9rem; color: #495057; }
.meta-item span { font-weight: 600; color: #212529; }

.block-card {
    border-radius: 8px;
    padding: 1rem 1.25rem;
    margin-bottom: 1rem;
    border-left: 5px solid;
}
.block-narrative  { background: #f0fdf4; border-color: #22c55e; }
.block-action     { background: #eff6ff; border-color: #3b82f6; }
.block-mixed      { background: #fff7ed; border-color: #f97316; }

.block-header { font-weight: 700; font-size: 0.95rem; margin-bottom: 0.5rem; }
.block-text   { font-size: 0.88rem; color: #374151; line-height: 1.6;
                white-space: pre-wrap; margin-bottom: 0.75rem; }

.badge {
    display: inline-block;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 0.15rem 0.55rem;
    border-radius: 999px;
    margin-right: 0.3rem;
    margin-bottom: 0.3rem;
}
.badge-mixed                    { background: #fed7aa; color: #9a3412; }
.badge-passive_action           { background: #fde68a; color: #92400e; }
.badge-vague                    { background: #fca5a5; color: #7f1d1d; }
.badge-observation_tangled      { background: #ddd6fe; color: #4c1d95; }
.badge-forward_reference        { background: #bfdbfe; color: #1e3a8a; }
.badge-indirect_action          { background: #d1fae5; color: #065f46; }
.badge-tense_person_inconsistency { background: #fce7f3; color: #9d174d; }
.badge-default                  { background: #e5e7eb; color: #374151; }

.issue-note {
    background: #fefce8;
    border: 1px solid #fde047;
    border-radius: 6px;
    padding: 0.5rem 0.75rem;
    font-size: 0.83rem;
    color: #713f12;
    margin-top: 0.5rem;
}

.quality-good  { color: #15803d; font-weight: 700; }
.quality-fair  { color: #b45309; font-weight: 700; }
.quality-poor  { color: #dc2626; font-weight: 700; }

.summary-box {
    background: #fff;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    padding: 1rem 1.25rem;
    margin-bottom: 1.5rem;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
BLOCK_TYPE_LABEL = {
    "narrative": ("Narrative", "narrative"),
    "action":    ("Action",    "action"),
    "mixed":     ("Mixed",     "mixed"),
}
QUALITY_CLASS = {"good": "quality-good", "fair": "quality-fair", "poor": "quality-poor"}

KNOWN_ISSUES = {
    "mixed", "passive_action", "vague", "observation_tangled",
    "forward_reference", "indirect_action", "tense_person_inconsistency",
}

def badge(issue: str) -> str:
    cls = f"badge-{issue}" if issue in KNOWN_ISSUES else "badge-default"
    return f'<span class="badge {cls}">{issue.replace("_", " ")}</span>'


def parse_filename(filename: str):
    """Extract lesson and topic numbers from filename like 24SWAdvSketch02_02.txt."""
    match = re.search(r'[A-Za-z]+(\d{2})_(\d{2})', filename)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None, None


def render_metadata(data: dict):
    quality = data.get("critique_summary", {}).get("overall_quality", "—")
    st.markdown(f"""
    <div class="meta-box">
      <div style="font-size:1.05rem; font-weight:700; margin-bottom:0.6rem;">
        Metadata — {data.get('filename', '—')}
      </div>
      <div class="meta-row">
        <div class="meta-item">Product <span>{data.get('product','—')}</span></div>
        <div class="meta-item">Course <span>{data.get('course') or '(not set)'}</span></div>
        <div class="meta-item">Lesson <span>{data.get('lesson','—')}</span></div>
        <div class="meta-item">Topic <span>{data.get('topic','—')}</span></div>
        <div class="meta-item">Language <span>{data.get('language','—').upper()}</span></div>
        <div class="meta-item">Word count <span>{data.get('word_count','—')}</span></div>
        <div class="meta-item">Version <span>{data.get('version','—')}</span></div>
      </div>
      <div style="margin-top:0.75rem; font-size:0.9rem;">
        <b>Topic:</b> {data.get('topic_summary','—')}
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_summary(cs: dict):
    quality = cs.get("overall_quality", "—")
    q_cls = QUALITY_CLASS.get(quality, "")
    issues = cs.get("issues_found", [])
    issues_html = "".join(badge(i) for i in issues) if issues else "<em>none</em>"
    mixed = cs.get("mixed_blocks",
        cs.get("total_blocks", 0) - cs.get("narrative_blocks", 0) - cs.get("action_blocks", 0))
    st.markdown(f"""
    <div class="summary-box">
      <div style="font-size:1.05rem; font-weight:700; margin-bottom:0.6rem;">Critique Summary</div>
      <div class="meta-row">
        <div class="meta-item">Total blocks <span>{cs.get('total_blocks','—')}</span></div>
        <div class="meta-item">Narrative <span>{cs.get('narrative_blocks','—')}</span></div>
        <div class="meta-item">Action <span>{cs.get('action_blocks','—')}</span></div>
        <div class="meta-item">Mixed <span>{mixed}</span></div>
        <div class="meta-item">Overall quality <span class="{q_cls}">{quality.upper()}</span></div>
      </div>
      <div style="margin-top:0.75rem; font-size:0.9rem;">
        <b>Issues found:</b> {issues_html}
      </div>
      {f'<div style="margin-top:0.6rem; font-size:0.88rem; color:#6b7280;">{cs["notes"]}</div>' if cs.get("notes") else ""}
    </div>
    """, unsafe_allow_html=True)


def render_block(block: dict):
    btype = block.get("type", "narrative")
    label, css_key = BLOCK_TYPE_LABEL.get(btype, (btype.capitalize(), "narrative"))
    issues = block.get("issues", [])
    note = block.get("issue_notes", "")
    badges_html = "".join(badge(i) for i in issues) if issues else ""
    note_html = f'<div class="issue-note"><b>Note:</b> {note}</div>' if note else ""
    st.markdown(f"""
    <div class="block-card block-{css_key}">
      <div class="block-header">Block {block.get('block_id','?')} &nbsp;·&nbsp; {label}</div>
      <div class="block-text">{block.get('text','')}</div>
      {f'<div style="margin-bottom:0.4rem;">{badges_html}</div>' if badges_html else ""}
      {note_html}
    </div>
    """, unsafe_allow_html=True)


def render_results(data: dict):
    render_metadata(data)
    render_summary(data.get("critique_summary", {}))

    blocks = data.get("blocks", [])
    if blocks:
        st.markdown(f"### Blocks ({len(blocks)})")

        col1, col2 = st.columns([2, 3])
        with col1:
            type_filter = st.multiselect(
                "Filter by type",
                options=["narrative", "action", "mixed"],
                default=["narrative", "action", "mixed"],
                key="type_filter",
            )
        with col2:
            issue_filter = st.multiselect(
                "Filter by issue",
                options=sorted(KNOWN_ISSUES),
                key="issue_filter",
            )

        visible = [
            b for b in blocks
            if b.get("type", "narrative") in type_filter
            and (not issue_filter or any(i in b.get("issues", []) for i in issue_filter))
        ]
        if visible:
            for block in visible:
                render_block(block)
        else:
            st.info("No blocks match the current filters. This script may have no blocks of the selected type — that itself is a finding.")
    else:
        st.info("No blocks found in the analysis result.")


# ── Analysis ──────────────────────────────────────────────────────────────────
RULES_FILE = Path(__file__).parent.parent / "ANALYSIS_RULES.md"


def load_prompt(text: str, filename: str, course: str) -> str:
    if not RULES_FILE.exists():
        st.error(f"Rules file not found: {RULES_FILE}")
        st.stop()

    raw = RULES_FILE.read_text(encoding="utf-8")

    # Strip comment lines (lines starting with #)
    lines = [l for l in raw.splitlines() if not l.startswith("#")]
    template = "\n".join(lines).strip()

    lesson, topic = parse_filename(filename)
    word_count = len(text.split())

    replacements = {
        "<<course>>":     course,
        "<<lesson>>":     str(lesson) if lesson is not None else "null",
        "<<topic>>":      str(topic) if topic is not None else "null",
        "<<filename>>":   filename,
        "<<word_count>>": str(word_count),
        "<<body>>":       text,
    }
    for placeholder, value in replacements.items():
        template = template.replace(placeholder, value)
    return template


# Maps likely Claude variations → canonical label
ISSUE_NORMALIZER = {
    "mixed content":               "mixed",
    "mixed_content":               "mixed",
    "passive or buried action":    "passive_action",
    "passive_or_buried_action":    "passive_action",
    "buried action":               "passive_action",
    "non specific verb":           "indirect_action",
    "non-specific verb":           "indirect_action",
    "nonspecific verb":            "indirect_action",
    "indirect action":             "indirect_action",
    "person voice inconsistency":  "tense_person_inconsistency",
    "tense inconsistency":         "tense_person_inconsistency",
    "voice inconsistency":         "tense_person_inconsistency",
    "person inconsistency":        "tense_person_inconsistency",
    "observation tangled":         "observation_tangled",
    "forward reference":           "forward_reference",
}

def normalize_issues(data: dict) -> dict:
    for block in data.get("blocks", []):
        block["issues"] = [
            ISSUE_NORMALIZER.get(i.lower(), ISSUE_NORMALIZER.get(i, i))
            for i in block.get("issues", [])
        ]
    return data


def call_claude(text: str, filename: str, course: str, api_key: str) -> dict:
    prompt = load_prompt(text, filename, course)

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8096,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()
    # Strip markdown code fences if Claude wrapped the JSON
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw.strip())
    return normalize_issues(json.loads(raw))


# ── Main UI ───────────────────────────────────────────────────────────────────
st.title("Script Analyzer")
st.caption("Upload a raw .txt script file to generate a critique report using AI.")

# API key — use env var or let user paste it in the sidebar
with st.sidebar:
    st.header("Settings")
    api_key_input = st.text_input(
        "Anthropic API Key",
        value=ANTHROPIC_API_KEY,
        type="password",
        help="Set ANTHROPIC_API_KEY in your .env file, or paste it here.",
    )
    course_input = st.text_input(
        "Course name",
        placeholder="e.g. 24SWAdvSketch",
        help="Applied to the 'course' field in the output JSON.",
    )

uploaded = st.file_uploader("Drop a .txt script file here", type="txt")

if uploaded:
    raw_text = uploaded.read().decode("utf-8", errors="replace")

    col_left, col_right = st.columns([3, 1])
    with col_left:
        st.markdown(f"**{uploaded.name}** — {len(raw_text.split())} words")
    with col_right:
        analyze_btn = st.button("Analyze", type="primary", use_container_width=True)

    with st.expander("Preview raw text"):
        st.text(raw_text[:2000] + ("…" if len(raw_text) > 2000 else ""))

    if analyze_btn:
        if not api_key_input:
            st.error("No Anthropic API key found. Add it in the sidebar or set ANTHROPIC_API_KEY in your .env file.")
            st.stop()

        with st.spinner("Analyzing script..."):
            try:
                result = call_claude(raw_text, uploaded.name, course_input, api_key_input)
            except json.JSONDecodeError as e:
                st.error(f"Claude returned invalid JSON: {e}")
                st.stop()
            except Exception as e:
                st.error(f"Analysis failed: {e}")
                st.stop()

        st.session_state["last_result"] = result
        st.session_state["last_filename"] = uploaded.name

if "last_result" in st.session_state:
    result = st.session_state["last_result"]
    st.divider()

    dl_col, _ = st.columns([1, 3])
    with dl_col:
        stem = os.path.splitext(st.session_state.get("last_filename", "script"))[0]
        st.download_button(
            label="Download JSON",
            data=json.dumps(result, indent=2),
            file_name=f"{stem}_critique.json",
            mime="application/json",
            use_container_width=True,
        )

    render_results(result)
else:
    st.info("Upload a .txt file and click Analyze to generate a critique report.")
