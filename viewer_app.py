
from pathlib import Path
import base64
import calendar
import html
import json
from datetime import date, timedelta

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "assets"
LOGO_PATH = ASSETS_DIR / "sob_logo.png"
TRAINING_UPLOAD_DIR = DATA_DIR / "training_uploads"

SAISON_START = date(2026, 9, 16)
SAISON_END = date(2027, 7, 31)
SAISON_LABEL = "2026/2027"

# Offizielle Schulferien Baden-Württemberg für das Schuljahr 2026/2027.
# Bewegliche Ferientage sind lokal je Schule und deshalb hier nicht automatisch enthalten.
SCHOOL_HOLIDAYS_BW = [
    ("Sommerferien 2026", date(2026, 7, 30), date(2026, 9, 12)),
    ("Herbstferien 2026", date(2026, 10, 26), date(2026, 10, 30)),
    ("Weihnachtsferien 2026/2027", date(2026, 12, 23), date(2027, 1, 9)),
    ("Osterferien 2027", date(2027, 3, 30), date(2027, 4, 3)),
    ("Pfingstferien 2027", date(2027, 5, 18), date(2027, 5, 29)),
    ("Sommerferien 2027", date(2027, 7, 29), date(2027, 9, 11)),
]
SCHOOL_FREE_DAYS_BW = {
    date(2026, 10, 31): "Reformationsfest schulfrei",
    date(2027, 3, 25): "Gründonnerstag schulfrei",
}


def school_holiday_name(day):
    for name, start, end in SCHOOL_HOLIDAYS_BW:
        if start <= day <= end:
            return name
    return SCHOOL_FREE_DAYS_BW.get(day, "")


def is_school_holiday(day):
    return bool(school_holiday_name(day))

PLAYER_COLUMNS = ["id", "name", "jahrgang", "status", "geburtstag", "fuss", "position", "weitere_position", "staerken", "notiz", "eltern1_name", "eltern1_telefon", "eltern1_email", "eltern2_name", "eltern2_telefon", "eltern2_email", "notfallnummer", "private_info", "mitgliedsantrag", "spielgenehmigungsantrag", "kontaktdaten", "aufsichtspflicht"]
EVENT_COLUMNS = ["id", "datum", "uhrzeit", "typ", "titel", "ort", "hinweis"]
TRAINING_COLUMNS = ["id", "titel", "datum", "kategorie", "schwerpunkt", "link", "datei", "dateiname", "notiz", "vormerken"]

st.set_page_config(
    page_title="SOB F-Jugend · Online-Ansicht",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def esc(value):
    return html.escape(str(value)) if value is not None else ""


def is_checked(value):
    value = str(value).strip().lower()
    return value in ["1", "true", "wahr", "ja", "yes", "y", "x", "✓", "ok"]


def checkbox_value(value):
    return "ja" if value else ""


def check_icon(value):
    return "✅" if is_checked(value) else "⬜"


def antraege_count(row):
    fields = ["mitgliedsantrag", "spielgenehmigungsantrag", "kontaktdaten", "aufsichtspflicht"]
    return sum(1 for field in fields if is_checked(row.get(field, "")))


def antraege_status(row):
    count = antraege_count(row)
    return f"{count}/4" if count < 4 else "✅ 4/4"


def antraege_detail_html(row):
    return f"""
      <div class=\"info-section-title\">Anträge / Unterlagen</div>
      <div class=\"check-grid\">
        <div><span>{check_icon(row.get('mitgliedsantrag',''))}</span><b>Mitgliedsantrag</b></div>
        <div><span>{check_icon(row.get('spielgenehmigungsantrag',''))}</span><b>Spielgenehmigungsantrag</b></div>
        <div><span>{check_icon(row.get('kontaktdaten',''))}</span><b>Kontaktdaten</b></div>
        <div><span>{check_icon(row.get('aufsichtspflicht',''))}</span><b>Aufsichtspflicht</b></div>
      </div>
    """


def qp_get_value(key, default=""):
    try:
        val = st.query_params.get(key, default)
        if isinstance(val, list):
            return val[0] if val else default
        return val
    except Exception:
        return default


def player_info_html(row):
    def val(col):
        value = str(row.get(col, "")).strip()
        return esc(value) if value else "—"
    return f"""
    <div class="info-card">
      <div class="info-title">Spielerinfo · {val('name')}</div>
      {antraege_detail_html(row)}
      <div class="info-grid">
        <div><span>Elternteil 1</span><b>{val('eltern1_name')}</b></div>
        <div><span>Telefon Elternteil 1</span><b>{val('eltern1_telefon')}</b></div>
        <div><span>E-Mail Elternteil 1</span><b>{val('eltern1_email')}</b></div>
        <div><span>Elternteil 2</span><b>{val('eltern2_name')}</b></div>
        <div><span>Telefon Elternteil 2</span><b>{val('eltern2_telefon')}</b></div>
        <div><span>E-Mail Elternteil 2</span><b>{val('eltern2_email')}</b></div>
        <div><span>Notfallnummer</span><b>{val('notfallnummer')}</b></div>
        <div><span>Private Hinweise</span><b>{val('private_info')}</b></div>
      </div>
    </div>
    """


def logo_b64():
    if not LOGO_PATH.exists():
        return ""
    return base64.b64encode(LOGO_PATH.read_bytes()).decode("utf-8")


def load_table(path: Path, columns):
    if not path.exists():
        return pd.DataFrame(columns=columns)
    df = pd.read_csv(path, sep=";", encoding="utf-8-sig", dtype=str).fillna("")
    for col in columns:
        if col not in df.columns:
            df[col] = ""
    return df[columns]


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def make_training_dates():
    current = SAISON_START
    while current.weekday() != 2:
        current += timedelta(days=1)
    dates = []
    while current <= SAISON_END:
        dates.append(current)
        current += timedelta(days=7)
    return dates


def german_date(value):
    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")
    dt = pd.to_datetime(value, errors="coerce")
    if pd.isna(dt):
        return "—"
    return dt.strftime("%d.%m.%Y")


def relevant_training_dates_for_stats(dates, attendance=None):
    """Nur Trainingstage zählen, die für die Quote wirklich relevant sind.

    Normalfall: bis einschließlich heute.
    Falls das Saisonjahr in der Zukunft/Vergangenheit zum Testen nicht passt, werden alternativ
    die Trainingstage genommen, zu denen bereits Anwesenheiten gepflegt wurden. So ergeben 3/3
    besuchte Trainings 100 % und nicht 3 von allen Saisontrainings.
    """
    today = date.today()
    dates = list(dates)
    past_dates = [d for d in dates if d <= today]
    attendance = attendance or {}
    touched_dates = []
    for d in dates:
        day_data = attendance.get(str(d), {})
        if isinstance(day_data, dict) and any(bool(v) for v in day_data.values()):
            touched_dates.append(d)

    if past_dates and today <= SAISON_END:
        return past_dates
    if touched_dates:
        return touched_dates
    return past_dates


def attendance_count(name, attendance, dates):
    return sum(1 for d in dates if attendance.get(str(d), {}).get(name, False))


def attendance_percent(name, attendance, dates):
    relevant_dates = relevant_training_dates_for_stats(dates, attendance)
    if not relevant_dates:
        return "0 %"
    return f"{round(attendance_count(name, attendance, relevant_dates) / len(relevant_dates) * 100)} %"


def trainer_icon(status):
    return {"none": "□", "marco": "🔵", "jan": "🔴", "both": "🔵🔴"}.get(status, "□")


def trainer_label(status):
    return {"none": "kein Trainer", "marco": "Marco", "jan": "Jan", "both": "Marco & Jan"}.get(status, "kein Trainer")


def file_mime(path):
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "application/pdf"
    if suffix in [".png"]:
        return "image/png"
    if suffix in [".jpg", ".jpeg"]:
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    return "application/octet-stream"


def render_training_file(abs_file, display_name="", key_prefix="file"):
    """Zeigt hochgeladene Trainingsdateien sinnvoll an.

    Bilder werden direkt angezeigt.
    PDFs bekommen eine Vorschau und einen Öffnen/Download-Button.
    Andere Dateien bekommen einen Download-Button.
    """
    if not abs_file or not abs_file.exists():
        st.write("⚽")
        return

    suffix = abs_file.suffix.lower()
    display_name = str(display_name or abs_file.name).strip() or abs_file.name

    if suffix in [".png", ".jpg", ".jpeg", ".webp"]:
        st.image(str(abs_file), use_container_width=True)
        st.caption(display_name)
        return

    data = abs_file.read_bytes()

    if suffix == ".pdf":
        st.markdown(f"📄 **{esc(display_name)}**")
        st.download_button(
            "PDF öffnen / herunterladen",
            data=data,
            file_name=display_name if display_name.lower().endswith(".pdf") else abs_file.name,
            mime="application/pdf",
            key=f"download_pdf_{key_prefix}",
            use_container_width=True,
        )
        with st.expander("PDF-Vorschau anzeigen"):
            pdf_b64 = base64.b64encode(data).decode("utf-8")
            st.markdown(
                f'<iframe src="data:application/pdf;base64,{pdf_b64}" '
                f'width="100%" height="520" style="border:1px solid rgba(0,51,204,.18);border-radius:12px;"></iframe>',
                unsafe_allow_html=True,
            )
        return

    st.markdown(f"📎 **{esc(display_name)}**")
    st.download_button(
        "Datei öffnen / herunterladen",
        data=data,
        file_name=display_name,
        mime=file_mime(abs_file),
        key=f"download_file_{key_prefix}",
        use_container_width=True,
    )


def build_player_table_html(df):
    headers = ["Name", "Jahrgang", "Training", "Anw.", "Position", "Kann auch", "Fuß", "Stärken", "Geburtstag", "Notiz", "Anträge", "Info"]
    out = '<table class="compact-table"><thead><tr>'
    for h in headers:
        out += f"<th>{esc(h)}</th>"
    out += "</tr></thead><tbody>"
    for _, r in df.iterrows():
        out += "<tr>"
        out += f"<td><b>{esc(r.get('name',''))}</b></td>"
        out += f"<td>{esc(r.get('jahrgang',''))}</td>"
        out += f"<td>{esc(r.get('Training dabei','0'))}</td>"
        out += f"<td>{esc(r.get('Anwesenheit','0 %'))}</td>"
        out += f"<td>{esc(r.get('position',''))}</td>"
        out += f"<td>{esc(r.get('weitere_position',''))}</td>"
        out += f"<td>{esc(r.get('fuss',''))}</td>"
        out += f"<td>{esc(r.get('staerken',''))}</td>"
        out += f"<td>{esc(r.get('geburtstag',''))}</td>"
        out += f"<td>{esc(r.get('notiz',''))}</td>"
        out += f"<td><b>{esc(antraege_status(r))}</b></td>"
        out += f"<td><a class='action-link' href='?info_player={esc(r.get('id',''))}' target='_self'>i</a></td>"
        out += "</tr>"
    out += "</tbody></table>"
    return out


def build_event_table_html(df):
    headers = ["Datum", "Uhrzeit", "Typ", "Titel", "Ort", "Hinweis"]
    out = '<table class="compact-table"><thead><tr>'
    for h in headers:
        out += f"<th>{esc(h)}</th>"
    out += "</tr></thead><tbody>"
    for _, r in df.iterrows():
        out += "<tr>"
        out += f"<td><b>{esc(german_date(r.get('datum','')))}</b></td>"
        out += f"<td>{esc(r.get('uhrzeit',''))}</td>"
        out += f"<td>{esc(r.get('typ',''))}</td>"
        out += f"<td><b>{esc(r.get('titel',''))}</b></td>"
        out += f"<td>{esc(r.get('ort',''))}</td>"
        out += f"<td>{esc(r.get('hinweis',''))}</td>"
        out += "</tr>"
    out += "</tbody></table>"
    return out


st.markdown("""
<style>
[data-testid="stSidebar"], [data-testid="collapsedControl"] {display:none!important;}
#MainMenu, footer, header {visibility:hidden!important;}
.block-container {padding:1rem 2rem 2.2rem 2rem; max-width:1620px;}
.stApp {
    background:
        radial-gradient(circle at 10% 0%, rgba(0,51,204,.18), transparent 27%),
        linear-gradient(135deg, #F7FAFF 0%, #EEF4FF 52%, #F7FAFF 100%);
    color:#0B1736;
}
.sob-hero {
    display:grid; grid-template-columns:110px 1fr 185px; gap:22px; align-items:center;
    border-radius:24px; padding:20px 26px; background:rgba(255,255,255,.96);
    border:1px solid rgba(0,51,204,.14); box-shadow:0 16px 38px rgba(11,23,54,.08); margin-bottom:16px;
}
.sob-logo {width:88px;height:88px;border-radius:22px;background:#fff;display:flex;align-items:center;justify-content:center;}
.sob-logo img {width:76px;height:76px;object-fit:contain;}
.sob-kicker {font-size:12px;letter-spacing:.18em;font-weight:900;color:#0033CC;text-transform:uppercase;margin-bottom:9px;}
.sob-title {font-size:40px;line-height:1;font-weight:950;color:#0B1736;margin-bottom:9px;}
.sob-subtitle {font-size:14px;color:#60708D;}
.season-card {background:#07142F;color:#fff;border-radius:20px;padding:16px;text-align:center;}
.season-label {color:#9CC2FF;letter-spacing:.18em;font-size:11px;font-weight:900;text-transform:uppercase;}
.season-value {font-size:24px;font-weight:950;margin-top:7px;}
.metric-grid {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:16px;}
.metric-card {background:rgba(255,255,255,.96);border:1px solid rgba(0,51,204,.14);border-radius:18px;padding:14px 16px;min-height:92px;}
.metric-label {color:#60708D;font-size:11px;font-weight:900;letter-spacing:.10em;text-transform:uppercase;}
.metric-value {color:#0B1736;font-size:21px;font-weight:950;margin-top:7px;}
.metric-hint {color:#60708D;font-size:12px;margin-top:5px;line-height:1.25;}
.section-title {font-size:22px;font-weight:950;color:#0B1736;margin:16px 0 9px 0;}
.empty-box {background:rgba(255,255,255,.96);border:1px dashed rgba(0,51,204,.2);border-radius:16px;padding:14px;color:#60708D;margin-bottom:16px;}
.calendar-panel {background:rgba(255,255,255,.96);border:1px solid rgba(0,51,204,.14);border-radius:20px;padding:16px;margin-bottom:16px;}
.legend {display:flex;gap:16px;align-items:center;flex-wrap:wrap;margin-bottom:10px;color:#60708D;font-size:13px;}
.dot {width:12px;height:12px;border-radius:50%;display:inline-block;margin-right:6px;}
.blue {background:#0033CC} .red{background:#D62828} .empty{background:#E7ECF5;border:1px solid #C9D3E6}
.compact-table {
    width:100%;
    border-collapse:collapse;
    background:rgba(255,255,255,.96);
    border:1px solid rgba(0,51,204,.14);
    border-radius:14px;
    overflow:hidden;
    font-size:13px;
    color:#0B1736;
    margin-bottom:18px;
}
.compact-table th {
    text-align:left;
    padding:7px 9px;
    color:#60708D;
    font-size:10px;
    text-transform:uppercase;
    letter-spacing:.06em;
    border-bottom:1px solid rgba(0,51,204,.14);
    white-space:nowrap;
}
.compact-table td {
    padding:6px 9px;
    border-bottom:1px solid rgba(0,51,204,.14);
    color:#0B1736;
    line-height:1.1;
    vertical-align:middle;
}
.compact-table tr:last-child td {border-bottom:none;}
.training-card {
    background:rgba(255,255,255,.96);
    border:1px solid rgba(0,51,204,.14);
    border-radius:16px;
    padding:12px;
    margin-bottom:12px;
}
.training-card h3 {margin:0 0 5px 0;font-size:20px;}
.training-meta {color:#60708D;font-size:13px;margin-bottom:8px;}
.training-note {font-size:14px;line-height:1.35;}
.mobile-hint {display:none;color:#60708D;font-size:12px;margin-top:-5px;margin-bottom:10px;}
@media (max-width:900px){
    .block-container {padding:0.75rem 0.75rem 2rem 0.75rem;}
    .sob-hero{grid-template-columns:84px 1fr; gap:12px; padding:15px;}
    .season-card{display:none;}
    .sob-logo{width:76px;height:76px;border-radius:18px;}
    .sob-logo img{width:66px;height:66px;}
    .sob-title{font-size:30px;}
    .sob-subtitle{font-size:13px;}
    .metric-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:9px;}
    .metric-card{padding:11px 12px;min-height:80px;}
    .metric-value{font-size:18px;}
    .compact-table{display:block;overflow-x:auto;white-space:nowrap;font-size:12px;}
    .mobile-hint{display:block;}
}
@media (max-width:560px){
    .metric-grid{grid-template-columns:1fr;}
    .section-title{font-size:20px;}
}

.info-card {
    background:var(--panel, rgba(255,255,255,.98));
    border:1px solid rgba(0,51,204,.16);
    border-radius:18px;
    padding:16px;
    margin:10px 0 18px 0;
    box-shadow:0 12px 28px rgba(11,23,54,.07);
}
.info-title {font-size:20px;font-weight:950;color:var(--text, #0B1736);margin-bottom:12px;}
.info-grid {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;}
.info-grid div {background:rgba(0,51,204,.055);border:1px solid rgba(0,51,204,.10);border-radius:12px;padding:10px;}
.info-grid span {display:block;font-size:11px;color:var(--muted, #60708D);text-transform:uppercase;font-weight:900;letter-spacing:.06em;margin-bottom:4px;}
.info-grid b {font-size:14px;color:var(--text, #0B1736);font-weight:800;word-break:break-word;}
.action-link {font-weight:950;text-decoration:none;color:#0033CC;margin-left:8px;}
@media (max-width:700px){.info-grid{grid-template-columns:1fr;}}


.calendar-panel-full {background:rgba(255,255,255,.96);border:1px solid rgba(0,51,204,.14);border-radius:20px;padding:16px;margin-bottom:16px;}
.calendar-month-card {margin-bottom:14px;}
.calendar-grid {display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:4px;}
.cal-head {text-align:center;color:#60708D;font-size:11px;font-weight:900;padding:3px 0;}
.empty-day {min-height:34px;}
.cal-day {display:block;text-align:center;text-decoration:none;background:rgba(0,51,204,.055);border:1px solid rgba(0,51,204,.14);border-radius:9px;padding:7px 2px;min-height:34px;color:#0B1736;font-size:12px;font-weight:800;line-height:1.15;}
.cal-day-disabled {cursor:default;}
.holiday-day {background:#FFE66D!important;border-color:#D6AA00!important;color:#2B2400!important;box-shadow:inset 0 0 0 1px rgba(214,170,0,.35);}
.holiday-badge {display:inline-block;width:12px;height:12px;border-radius:4px;background:#FFE66D;border:1px solid #D6AA00;margin-right:6px;vertical-align:-2px;}
.cal-note {color:#60708D;font-size:12px;margin-top:10px;}
.calendar-help {color:#60708D;font-size:13px;margin-bottom:10px;}
.week-head {color:#60708D;font-size:11px;font-weight:800;text-align:center;}
.month-name {font-weight:950;color:#0B1736;font-size:15px;margin:5px 0 7px 0;}
@media (max-width:900px){.calendar-panel-full>div[style*="grid-template-columns"]{grid-template-columns:1fr!important}.calendar-grid{gap:3px}.cal-day{font-size:11px;padding:6px 1px;min-height:31px}}


.info-section-title {font-size:15px;font-weight:950;color:var(--text, #0B1736);margin:14px 0 8px 0;}
.check-grid {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin-bottom:8px;}
.check-grid div {background:rgba(0,51,204,.055);border:1px solid rgba(0,51,204,.10);border-radius:12px;padding:10px;display:flex;gap:8px;align-items:center;}
.check-grid span {font-size:18px;line-height:1;}
.check-grid b {font-size:13px;color:var(--text, #0B1736);font-weight:850;word-break:break-word;}
@media (max-width:900px){.check-grid{grid-template-columns:repeat(2,minmax(0,1fr));}}
@media (max-width:520px){.check-grid{grid-template-columns:1fr;}}

</style>
""", unsafe_allow_html=True)


players = load_table(DATA_DIR / "spieler.csv", PLAYER_COLUMNS)
events = load_table(DATA_DIR / "spiele.csv", EVENT_COLUMNS)
training = load_table(DATA_DIR / "training_library.csv", TRAINING_COLUMNS)
attendance = load_json(DATA_DIR / "anwesenheit.json", {})
trainer_calendar = load_json(DATA_DIR / "trainer_kalender.json", {})
training_dates = make_training_dates()

if not events.empty:
    events["_datum"] = pd.to_datetime(events["datum"], errors="coerce")
    events = events.sort_values("_datum")

active = players[players["status"].str.lower().eq("aktiv")].copy() if not players.empty else players.copy()
if not active.empty:
    active["Training dabei"] = active["name"].apply(lambda n: attendance_count(n, attendance, training_dates))
    active["Anwesenheit"] = active["name"].apply(lambda n: attendance_percent(n, attendance, training_dates))
    active["Anträge"] = active.apply(antraege_status, axis=1)

st.markdown(f"""
<div class="sob-hero">
  <div class="sob-logo"><img src="data:image/png;base64,{logo_b64()}" alt="SOB Logo"></div>
  <div>
    <div class="sob-kicker">Nur-Lesen-Ansicht</div>
    <div class="sob-title">SOB F-Jugend</div>
    <div class="sob-subtitle">Online-Übersicht für Spieler, Termine, Kalender und Trainingsplanung.</div>
  </div>
  <div class="season-card"><div class="season-label">Saison</div><div class="season-value">{SAISON_LABEL}</div></div>
</div>
""", unsafe_allow_html=True)

items = [{"datum": d, "typ": "Training"} for d in training_dates]
for _, r in events.iterrows():
    dt = pd.to_datetime(r.get("datum", ""), errors="coerce")
    if not pd.isna(dt):
        items.append({"datum": dt.date(), "typ": r.get("typ", "Termin")})
items = sorted(items, key=lambda x: x["datum"])[:3]
next_hint = " · ".join([f"{german_date(i['datum'])} {i['typ']}" for i in items])
next_value = german_date(items[0]["datum"]) if items else "—"

metric_html = '<div class="metric-grid">'
for label, value, hint in [
    ("Aktive Spieler", len(active), "aktuell im Kader"),
    ("Nächste Termine", next_value, next_hint),
    ("Spiele & Termine", len(events), "nur ansehen"),
    ("Trainings", len(training_dates), "mittwochs 17:30 bis 19:00"),
]:
    metric_html += f'<div class="metric-card"><div class="metric-label">{esc(label)}</div><div class="metric-value">{esc(value)}</div><div class="metric-hint">{esc(hint)}</div></div>'
metric_html += '</div>'
st.markdown(metric_html, unsafe_allow_html=True)

st.markdown('<div class="section-title">Spielerübersicht</div>', unsafe_allow_html=True)
st.markdown('<div class="mobile-hint">Auf dem Handy kannst du Tabellen seitlich wischen.</div>', unsafe_allow_html=True)
if active.empty:
    st.markdown('<div class="empty-box">Noch keine Spieler eingetragen.</div>', unsafe_allow_html=True)
else:
    st.markdown(build_player_table_html(active), unsafe_allow_html=True)


info_player_id = qp_get_value("info_player", "")
if info_player_id and not players.empty:
    info_rows = players[players["id"].astype(str).eq(str(info_player_id))]
    if not info_rows.empty:
        st.markdown(player_info_html(info_rows.iloc[0]), unsafe_allow_html=True)

st.markdown('<div class="section-title">Spiele & Termine</div>', unsafe_allow_html=True)
if events.empty:
    st.markdown('<div class="empty-box">Noch keine Spiele oder Termine eingetragen.</div>', unsafe_allow_html=True)
else:
    st.markdown(build_event_table_html(events), unsafe_allow_html=True)

st.markdown('<div class="section-title">Trainer- & Saisonkalender</div>', unsafe_allow_html=True)
month_names = ["", "Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
months = []
current = date(SAISON_START.year, SAISON_START.month, 1)
while current <= SAISON_END:
    months.append((current.year, current.month))
    current = date(current.year + 1, 1, 1) if current.month == 12 else date(current.year, current.month + 1, 1)
training_set = set(training_dates)
game_dates = set(pd.to_datetime(events["datum"], errors="coerce").dt.date.dropna().tolist()) if not events.empty else set()
cal_html = '<div class="calendar-panel-full">'
cal_html += '<div class="legend"><span><span class="dot blue"></span>Marco</span><span><span class="dot red"></span>Jan</span><span>🔵🔴 Marco & Jan</span><span><span class="dot empty"></span>kein Trainer</span><span><span class="holiday-badge"></span>Schulferien BW / schulfrei</span></div>'
cal_html += '<div class="calendar-help">T = Training, S = Spiel/Termin. Gelb = Schulferien Baden-Württemberg oder offizieller schulfrei-Tag.</div>'
cal_html += '<div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;">'
for year, month in months:
    cal_html += '<div class="calendar-month-card">'
    cal_html += f'<div class="month-name">{month_names[month]} {year}</div>'
    cal_html += '<div class="calendar-grid">'
    for lab in ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]:
        cal_html += f'<div class="cal-head">{lab}</div>'
    for week in calendar.monthcalendar(year, month):
        for day in week:
            if day == 0:
                cal_html += '<div class="empty-day"></div>'
                continue
            d = date(year, month, day)
            prefix = "T" if d in training_set else "S" if d in game_dates else ""
            holiday = school_holiday_name(d)
            cls = "cal-day holiday-day" if holiday else "cal-day"
            title = f"{german_date(d)} · {trainer_label(trainer_calendar.get(str(d), 'none'))}" + (f" · {holiday}" if holiday else "")
            label = f"{day}{prefix}<br>{trainer_icon(trainer_calendar.get(str(d),'none'))}"
            cal_html += f'<span class="{cls} cal-day-disabled" title="{esc(title)}">{label}</span>'
    cal_html += '</div></div>'
cal_html += '</div>'
cal_html += '<div class="cal-note">Hinweis: Bewegliche Ferientage sind je Schule unterschiedlich und nicht automatisch enthalten.</div>'
cal_html += '</div>'
st.markdown(cal_html, unsafe_allow_html=True)

st.markdown('<div class="section-title">Geplante Trainingsübungen</div>', unsafe_allow_html=True)
if training.empty:
    st.markdown('<div class="empty-box">Noch keine Trainingsideen gespeichert.</div>', unsafe_allow_html=True)
else:
    training = training.copy()
    training["datum"] = training["datum"].fillna("").astype(str)
    planned = training[training["datum"].str.strip().ne("")].copy()
    collection = training[training["datum"].str.strip().eq("")].copy()

    if planned.empty:
        st.markdown('<div class="empty-box">Noch keine Übung ist fest eingeplant.</div>', unsafe_allow_html=True)
    else:
        planned["_date"] = pd.to_datetime(planned["datum"], errors="coerce")
        planned = planned.sort_values("_date").drop(columns=["_date"])
        current_date = None
        for _, r in planned.iterrows():
            date_label = german_date(r.get("datum", ""))
            if date_label != current_date:
                current_date = date_label
                st.markdown(f'<div class="section-title" style="font-size:17px;margin-top:14px;">{esc(date_label)}</div>', unsafe_allow_html=True)

            with st.container():
                st.markdown('<div class="training-card">', unsafe_allow_html=True)
                c1, c2 = st.columns([.28, .72], vertical_alignment="top")
                file_ref = str(r.get("datei", ""))
                abs_file = DATA_DIR / file_ref if file_ref else None
                with c1:
                    render_training_file(abs_file, r.get("dateiname", "") or (abs_file.name if abs_file else ""), key_prefix=f"{r.get('id','')}_planned")
                with c2:
                    badge = " ⭐ vorgemerkt" if str(r.get("vormerken", "")).lower() == "ja" else ""
                    st.markdown(f"### {esc(r.get('titel',''))}{badge}")
                    st.markdown(f'<div class="training-meta">{esc(r.get("kategorie",""))} · {esc(r.get("schwerpunkt",""))}</div>', unsafe_allow_html=True)
                    if r.get("notiz", ""):
                        st.markdown(f'<div class="training-note">{esc(r.get("notiz",""))}</div>', unsafe_allow_html=True)
                    if r.get("link", ""):
                        st.markdown(f"[Link öffnen]({r.get('link','')})")
                st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<hr style="border:0;border-top:1px solid rgba(120,140,180,.35);margin:24px 0 14px 0;">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Sammlung</div>', unsafe_allow_html=True)
    if collection.empty:
        st.markdown('<div class="empty-box">Keine offenen Übungen in der Sammlung.</div>', unsafe_allow_html=True)
    else:
        collection = collection.sort_values("titel")
        for _, r in collection.iterrows():
            with st.container():
                st.markdown('<div class="training-card">', unsafe_allow_html=True)
                c1, c2 = st.columns([.28, .72], vertical_alignment="top")
                file_ref = str(r.get("datei", ""))
                abs_file = DATA_DIR / file_ref if file_ref else None
                with c1:
                    render_training_file(abs_file, r.get("dateiname", "") or (abs_file.name if abs_file else ""), key_prefix=f"{r.get('id','')}_collection")
                with c2:
                    st.markdown(f"### {esc(r.get('titel',''))}")
                    st.markdown(f'<div class="training-meta">{esc(r.get("kategorie",""))} · {esc(r.get("schwerpunkt",""))}</div>', unsafe_allow_html=True)
                    if r.get("notiz", ""):
                        st.markdown(f'<div class="training-note">{esc(r.get("notiz",""))}</div>', unsafe_allow_html=True)
                    if r.get("link", ""):
                        st.markdown(f"[Link öffnen]({r.get('link','')})")
                st.markdown('</div>', unsafe_allow_html=True)
