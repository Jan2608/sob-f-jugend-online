
from pathlib import Path
import calendar, json
from datetime import date, timedelta
import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "assets"
LOGO_PATH = ASSETS_DIR / "sob_logo.png"
SAISON_START = date(2025, 9, 1)
SAISON_END = date(2026, 7, 31)

def read_csv(name, cols):
    p = DATA_DIR / name
    if not p.exists():
        return pd.DataFrame(columns=cols)
    df = pd.read_csv(p, sep=";", encoding="utf-8-sig", dtype=str).fillna("")
    for c in cols:
        if c not in df.columns:
            df[c] = ""
    return df[cols]

def read_json(name, default):
    p = DATA_DIR / name
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default

def trainings():
    d = SAISON_START
    while d.weekday() != 2:
        d += timedelta(days=1)
    out = []
    while d <= SAISON_END:
        out.append(d)
        d += timedelta(days=7)
    return out

def gdate(v):
    if isinstance(v, date):
        return v.strftime("%d.%m.%Y")
    dt = pd.to_datetime(v, errors="coerce")
    return "—" if pd.isna(dt) else dt.strftime("%d.%m.%Y")

def count_att(name, att, dates):
    return sum(1 for d in dates if att.get(str(d), {}).get(name, False))

def pct_att(name, att, dates):
    return "0 %" if not dates else f"{round(count_att(name, att, dates) / len(dates) * 100)} %"

def icon(s):
    return {"none":"□","marco":"🔵","jan":"🔴","both":"🔵🔴"}.get(s,"□")

st.set_page_config(page_title="SOB F-Jugend Online", page_icon="⚽", layout="wide")
st.markdown("""
<style>
#MainMenu, footer, header {visibility:hidden!important;}
.block-container {padding:1rem; max-width:1450px;}
.stApp {background:linear-gradient(135deg,#F7FAFF,#EEF4FF);}
.card {background:white;border:1px solid rgba(0,51,204,.14);border-radius:16px;padding:12px;margin-bottom:12px;}
</style>
""", unsafe_allow_html=True)

player_cols=["id","name","jahrgang","status","geburtstag","fuss","position","weitere_position","staerken","notiz"]
event_cols=["id","datum","uhrzeit","typ","titel","ort","hinweis"]
train_cols=["id","titel","datum","kategorie","schwerpunkt","link","datei","notiz","vormerken"]

players=read_csv("spieler.csv", player_cols)
events=read_csv("spiele.csv", event_cols)
training=read_csv("training_library.csv", train_cols)
att=read_json("anwesenheit.json", {})
trainer=read_json("trainer_kalender.json", {})
tdates=trainings()

active=players[players["status"].str.lower().eq("aktiv")].copy() if not players.empty else players
if not active.empty:
    active["Training dabei"]=active["name"].apply(lambda n: count_att(n,att,tdates))
    active["Anwesenheit"]=active["name"].apply(lambda n: pct_att(n,att,tdates))
if not events.empty:
    events["_d"]=pd.to_datetime(events["datum"],errors="coerce")
    events=events.sort_values("_d")

h1, h2 = st.columns([0.15, 0.85])
with h1:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=90)
with h2:
    st.caption("Nur-Lesen-Ansicht")
    st.title("SOB F-Jugend")
    st.write("Online-Übersicht für den Sportplatz.")

items=[{"datum":d,"typ":"Training"} for d in tdates]
for _,r in events.iterrows():
    dt=pd.to_datetime(r.get("datum",""),errors="coerce")
    if not pd.isna(dt):
        items.append({"datum":dt.date(),"typ":r.get("typ","Termin")})
items=sorted(items,key=lambda x:x["datum"])[:3]
nextval=gdate(items[0]["datum"]) if items else "—"
nexthint=" · ".join([f"{gdate(i['datum'])} {i['typ']}" for i in items])

c1,c2,c3,c4=st.columns(4)
c1.metric("Aktive Spieler", len(active))
c2.metric("Nächster Termin", nextval)
c2.caption(nexthint)
c3.metric("Spiele & Termine", len(events))
c4.metric("Trainings", len(tdates))

st.subheader("Spielerübersicht")
if active.empty:
    st.info("Noch keine Spieler.")
else:
    show=active[["name","jahrgang","Training dabei","Anwesenheit","position","weitere_position","fuss","staerken","geburtstag","notiz"]].rename(columns={"name":"Name","jahrgang":"Jahrgang","position":"Position","weitere_position":"Kann auch","fuss":"Fuß","staerken":"Stärken","geburtstag":"Geburtstag","notiz":"Notiz"})
    st.dataframe(show, hide_index=True, use_container_width=True)

st.subheader("Spiele & Termine")
if events.empty:
    st.info("Noch keine Termine.")
else:
    ev=events.copy()
    ev["Datum"]=ev["datum"].apply(gdate)
    ev=ev[["Datum","uhrzeit","typ","titel","ort","hinweis"]].rename(columns={"uhrzeit":"Uhrzeit","typ":"Typ","titel":"Titel","ort":"Ort","hinweis":"Hinweis"})
    st.dataframe(ev, hide_index=True, use_container_width=True)

st.subheader("Trainer- & Saisonkalender")
months=[]; cur=date(2025,9,1)
while cur<=SAISON_END:
    months.append((cur.year,cur.month))
    cur=date(cur.year+1,1,1) if cur.month==12 else date(cur.year,cur.month+1,1)
names=["","Januar","Februar","März","April","Mai","Juni","Juli","August","September","Oktober","November","Dezember"]
training_set=set(tdates)
game_dates=set(pd.to_datetime(events["datum"],errors="coerce").dt.date.dropna().tolist()) if not events.empty else set()
for i in range(0,len(months),3):
    cols=st.columns(3)
    for col,(y,m) in zip(cols,months[i:i+3]):
        with col:
            st.markdown(f"**{names[m]} {y}**")
            for week in calendar.monthcalendar(y,m):
                row=[]
                for day in week:
                    if day==0:
                        row.append(" ")
                    else:
                        d=date(y,m,day)
                        pref="T" if d in training_set else "S" if d in game_dates else ""
                        row.append(f"{day}{pref}{icon(trainer.get(str(d),'none'))}")
                st.caption(" · ".join(row))

st.subheader("Geplante Trainingsübungen")
if training.empty:
    st.info("Noch keine Trainingsideen.")
else:
    training["datum"]=training["datum"].fillna("").astype(str)
    planned=training[training["datum"].str.strip().ne("")].copy()
    coll=training[training["datum"].str.strip().eq("")].copy()
    if planned.empty:
        st.info("Noch keine Übung fest eingeplant.")
    else:
        planned["_d"]=pd.to_datetime(planned["datum"],errors="coerce")
        planned=planned.sort_values("_d")
        for _,r in planned.iterrows():
            st.markdown(f"### {gdate(r.get('datum',''))} · {r.get('titel','')}")
            tc1,tc2=st.columns([0.25,0.75])
            f=DATA_DIR/str(r.get("datei","")) if r.get("datei","") else None
            if f and f.exists() and f.suffix.lower() in [".png",".jpg",".jpeg",".webp"]:
                tc1.image(str(f), use_container_width=True)
            tc2.write(f"{r.get('kategorie','')} · {r.get('schwerpunkt','')}")
            if r.get("notiz",""):
                tc2.write(r.get("notiz",""))
            if r.get("link",""):
                tc2.markdown(f"[Link öffnen]({r.get('link','')})")
    st.subheader("Sammlung")
    if coll.empty:
        st.info("Keine offenen Übungen.")
    else:
        for _,r in coll.sort_values("titel").iterrows():
            st.markdown(f"**{r.get('titel','')}** — {r.get('kategorie','')} · {r.get('schwerpunkt','')}")
