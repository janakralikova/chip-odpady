import streamlit as st
import pandas as pd

# ----- Nastavenia -----
EXCEL_FILE = "data.xlsx"

CHIP_COL = "Číslo čipu"
DATE_COL = "Dátum zvozu"
KG_COL = "Počet kg odpadu"

PRICE_PER_KG = 0.25  # € / kg (podľa VZN)
# ----------------------


def normalize_chip(x) -> str:
    """Odstráni medzery a pomlčky, aby vyhľadávanie fungovalo aj pri rôznom zápise."""
    if x is None:
        return ""
    s = str(x).strip()
    return s.replace(" ", "").replace("-", "")


def parse_kg(x):
    """Zvládne čísla aj text typu '12,5' alebo '12,5 kg'."""
    if x is None:
        return None
    s = str(x).strip().lower()
    s = s.replace("kg", "").strip()
    s = s.replace("\u00a0", " ")  # non-breaking space
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
            "V Exceli chýbajú stĺpce: " + ", ".join(missing)
            + f" | Očakávané: '{CHIP_COL}', '{DATE_COL}', '{KG_COL}'."
        )

    df[CHIP_COL] = df[CHIP_COL].astype(str).apply(normalize_chip)
    df[KG_COL] = df[KG_COL].apply(parse_kg)
    df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors="coerce")
    df = df.dropna(subset=[DATE_COL])  # dátum je nutný pre filter
    return df


st.set_page_config(page_title="Kg odpadu podľa čipu", layout="centered")
st.title("Kg odpadu podľa čipu")
st.caption("Zadaj číslo čipu a vyber obdobie. Výsledok sa spočíta aj pri opakovaných zvozoch.")

# --- Skrytý ADMIN režim (len cez tajný link) ---
# Admin link: https://tvoja-app.streamlit.app/?admin=HODNOTA_ZO_SECRETS
ADMIN_KEY = st.secrets.get("ADMIN_KEY", "")
is_admin = (ADMIN_KEY != "") and (st.query_params.get("admin", "") == ADMIN_KEY)

if is_admin:
    st.warning("Admin režim")
    if st.button("Obnoviť dáta"):
        st.cache_data.clear()
        st.success("Dáta obnovené (cache vyčistená).")
# ------------------------------------------------

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
        st.warning("Tento čip sa v dátach nenašiel.")
        st.stop()

    min_d = hits[DATE_COL].min().date()
    max_d = hits[DATE_COL].max().date()

    st.subheader("Obdobie")
    date_from = st.date_input("Od", value=min_d, min_value=min_d, max_value=max_d)
    date_to = st.date_input("Do", value=max_d, min_value=min_d, max_value=max_d)

    if date_from > date_to:
        st.error("Dátum 'Od' nemôže byť neskôr ako 'Do'.")
        st.stop()

    hits_f = hits[
        (hits[DATE_COL].dt.date >= date_from)
        & (hits[DATE_COL].dt.date <= date_to)
    ].copy()

    if hits_f.empty:
        st.warning("Pre zadaný dátumový rozsah neboli nájdené žiadne záznamy.")
        st.stop()

    total_kg = hits_f[KG_COL].dropna().sum()
    count_pickups = len(hits_f)
    est_amount = total_kg * PRICE_PER_KG

    st.success(f"Spolu: {total_kg:.2f} kg")
    st.info(f"Počet zvozov v období: {count_pickups}")

    st.subheader("Predbežná suma podľa VZN")
    st.write(f"Sadzba: **{PRICE_PER_KG:.2f} € / kg**")
    st.write(f"Predbežná suma: **{est_amount:.2f} €**")

    view = hits_f[[DATE_COL, KG_COL]].sort_values(by=DATE_COL, ascending=False).copy()
    view.columns = ["Dátum zvozu", "Počet kg odpadu"]
    st.caption("Detailné záznamy:")
    st.dataframe(view, width="stretch")

