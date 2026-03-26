import json
import streamlit as st

st.set_page_config(page_title="Script Critique Viewer", layout="wide")

# ── Styling ──────────────────────────────────────────────────────────────────
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
.badge-mixed           { background: #fed7aa; color: #9a3412; }
.badge-passive_action  { background: #fde68a; color: #92400e; }
.badge-vague           { background: #fca5a5; color: #7f1d1d; }
.badge-observation_tangled { background: #ddd6fe; color: #4c1d95; }
.badge-forward_reference   { background: #bfdbfe; color: #1e3a8a; }
.badge-default         { background: #e5e7eb; color: #374151; }

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

def badge(issue: str) -> str:
    cls = (f"badge-{issue}" if issue in {
        "mixed", "passive_action", "vague",
        "observation_tangled", "forward_reference"
    } else "badge-default")
    return f'<span class="badge {cls}">{issue.replace("_", " ")}</span>'


def render_metadata(data: dict):
    cs = data.get("critique_summary", {})
    quality = cs.get("overall_quality", "—")
    q_cls = QUALITY_CLASS.get(quality, "")

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

    st.markdown(f"""
    <div class="summary-box">
      <div style="font-size:1.05rem; font-weight:700; margin-bottom:0.6rem;">Critique Summary</div>
      <div class="meta-row">
        <div class="meta-item">Total blocks <span>{cs.get('total_blocks','—')}</span></div>
        <div class="meta-item">Narrative <span>{cs.get('narrative_blocks','—')}</span></div>
        <div class="meta-item">Action <span>{cs.get('action_blocks','—')}</span></div>
        <div class="meta-item">Mixed <span>{cs.get('mixed_blocks', cs.get('total_blocks',0) - cs.get('narrative_blocks',0) - cs.get('action_blocks',0))}</span></div>
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


# ── Main ──────────────────────────────────────────────────────────────────────
st.title("Script Critique Viewer")
st.caption("Upload a JSON critique report to inspect metadata, block structure, and issues.")

uploaded = st.file_uploader("Drop a critique JSON file here", type="json")

if uploaded:
    try:
        data = json.load(uploaded)
    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON: {e}")
        st.stop()

    render_metadata(data)
    render_summary(data.get("critique_summary", {}))

    blocks = data.get("blocks", [])
    if blocks:
        st.markdown(f"### Blocks ({len(blocks)})")

        # Filter controls
        col1, col2 = st.columns([2, 3])
        with col1:
            type_filter = st.multiselect(
                "Filter by type",
                options=["narrative", "action", "mixed"],
                default=["narrative", "action", "mixed"],
            )
        with col2:
            issue_filter = st.multiselect(
                "Filter by issue",
                options=sorted({i for b in blocks for i in b.get("issues", [])}),
            )

        for block in blocks:
            btype = block.get("type", "narrative")
            bids = block.get("issues", [])
            if btype not in type_filter:
                continue
            if issue_filter and not any(i in bids for i in issue_filter):
                continue
            render_block(block)
    else:
        st.info("No blocks found in this critique report.")
else:
    st.info("Upload a JSON critique file to get started.")
