import streamlit as st
import pandas as pd

EXCEL_FILE = "data.xlsx"

CHIP_COL = "Číslo čipu"
DATE_COL = "Dátum zvozu"
KG_COL = "Počet kg odpadu"

def normalize_chip(x) -> str:
    if x is None:
        return ""
    s = str(x).strip()
    return s.replace(" ", "").replace("-", "")

def parse_kg(x):
    if x is None:
        return None
    s = str(x).strip().lower()
    s = s.replace("kg", "").strip()
    s = s.replace("\u00a0", " ")
    s = s.replace(" ", "")
    s = s.replace(",", ".")
    try:
        return float(s)
    except:
        return None

@st.cache_data(show_spinner=False)
def load_data():
    df = pd.read_excel(EXCEL_FILE, engine="openpyxl")

    missing = [c for c in [CHIP_COL, DATE_COL, KG_COL] if c not in df.columns]
    if missing:
        raise ValueError(
            "V Exceli chýbajú stĺpce: " + ", ".join(missing) +
            f" | Očakávané: '{CHIP_COL}', '{DATE_COL}', '{KG_COL}'."
        )

    df[CHIP_COL] = df[CHIP_COL].astype(str).apply(normalize_chip)
    df[KG_COL] = df[KG_COL].apply(parse_kg)
    df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors="coerce")
    df = df.dropna(subset=[DATE_COL])
    return df

st.set_page_config(page_title="Kg odpadu podľa čipu", layout="centered")
st.title("Kg odpadu podľa čipu")
st.caption("Zadaj číslo čipu a vyber obdobie. Výsledok sa spočíta aj pri opakovaných zvozoch.")

if st.button("Obnoviť dáta (keď je nový Excel)"):
    st.cache_data.clear()

try:
    df = load_data()
except Exception as e:
    st.error(f"Chyba pri načítaní dát: {e}")
    st.stop()

chip_in = st.text_input("Číslo čipu", placeholder="napr. 000123456")

if chip_in:
    chip = normalize_chip(chip_in)
    hits = df[df[CHIP_COL] == chip].copy()

    if hits.empty:
        st.warning("Tento čip sa nenašiel.")
        st.stop()

    min_d = hits[DATE_COL].min().date()
    max_d = hits[DATE_COL].max().date()

    st.subheader("Obdobie")
    date_from = st.date_input("Od", value=min_d, min_value=min_d, max_value=max_d)
    date_to = st.date_input("Do", value=max_d, min_value=min_d, max_value=max_d)

    if date_from > date_to:
        st.error("Dátum 'Od' nemôže byť neskôr ako 'Do'.")
        st.stop()

    hits_f = hits[(hits[DATE_COL].dt.date >= date_from) & (hits[DATE_COL].dt.date <= date_to)].copy()

    if hits_f.empty:
        st.warning("Pre zadaný dátumový rozsah neboli nájdené žiadne záznamy.")
        st.stop()

    total = hits_f[KG_COL].dropna().sum()
    st.success(f"Spolu: {total:.2f} kg")

    view = hits_f[[DATE_COL, KG_COL]].sort_values(by=DATE_COL, ascending=False).copy()
    view.columns = ["Dátum zvozu", "Počet kg odpadu"]
    st.dataframe(view, use_container_width=True)
