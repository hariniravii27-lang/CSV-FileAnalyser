import streamlit as st
import pandas as pd

st.set_page_config(layout="wide", page_title="CSV Data Checker", page_icon="📊")

# ---------------- CUSTOM STYLING ----------------
st.markdown("""
<style>
    .main { background-color: #ffffff; }
    h1 { color: #1f3c88; font-weight: 800; }
    h2 {
        color: #1f3c88; font-weight: 700; font-size: 22px;
        border-bottom: 2px solid #c9d6f5; padding-bottom: 6px; margin-top: 30px;
    }
    h3 { color: #2a4d9b; }
    .stButton>button {
        background-color: #2a4d9b; color: white; border-radius: 8px;
        border: none; padding: 6px 18px; font-weight: 600;
    }
    .stButton>button:hover { background-color: #1f3c88; color: #fff; }
    .stForm button {
        background-color: #2e9e6e !important; color: white !important;
        border-radius: 8px; font-weight: 600; border: none !important;
    }
    div[data-testid="stDataFrame"] { border: 1px solid #d8e0f0; border-radius: 10px; }
    .stAlert { border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

def green_tick(text):
    st.markdown(
        f"""<div style='display:inline-block; background-color:#d4edda; color:#155724;
        padding:4px 12px; border-radius:6px; margin:4px 0; font-size:14px; border-left:4px solid #2e9e6e;'>
        ✅ {text}</div>""",
        unsafe_allow_html=True
    )

def is_numeric_like(series):
    non_null = series.dropna()
    if len(non_null) == 0:
        return False
    converted = pd.to_numeric(non_null, errors="coerce")
    ratio = converted.notnull().sum() / len(non_null)
    return ratio > 0.5 or pd.api.types.is_numeric_dtype(series)

def apply_case(val, case):
    s = str(val)
    if case == "UPPER":
        return s.upper()
    elif case == "lower":
        return s.lower()
    else:
        return s.title()

CATEGORY_THRESHOLD = 15

FEMALE_SYNONYMS = {"female", "f", "woman", "girl"}
MALE_SYNONYMS = {"male", "m", "man", "boy"}

GENDER_FORMAT_OPTIONS = {
    "Female / Male": ("Female", "Male"),
    "F / M": ("F", "M"),
    "Woman / Man": ("Woman", "Man"),
}

def is_gender_column(uniq_vals):
    cleaned = {str(v).strip().lower() for v in uniq_vals}
    known = FEMALE_SYNONYMS | MALE_SYNONYMS
    return len(cleaned) > 0 and cleaned.issubset(known)

def classify_gender(val):
    v = str(val).strip().lower()
    if v in FEMALE_SYNONYMS:
        return "female"
    if v in MALE_SYNONYMS:
        return "male"
    return None

# ---------------- SESSION INIT ----------------
if "page" not in st.session_state:
    st.session_state.page = "config"
if "log" not in st.session_state:
    st.session_state.log = {}
if "history" not in st.session_state:
    st.session_state.history = []
if "col_config" not in st.session_state:
    st.session_state.col_config = {}

st.title("📊 CSV Data Checker & Fixer")
st.caption("Upload, configure, clean, and export your dataset.")

f = st.file_uploader("Upload your CSV", type="csv")

if f:
    if "df" not in st.session_state:
        st.session_state.df = pd.read_csv(f)

    df = st.session_state.df
    numeric_like_cols = [c for c in df.columns if is_numeric_like(df[c])]
    text_cols = [c for c in df.columns if c not in numeric_like_cols]

    # ================= PAGE 1: RANGE / FORMAT SETUP =================
    if st.session_state.page == "config":
        st.header("Set Range & Format")
        st.caption("Changing these settings later will not affect any data you have already fixed.")

        for col in df.columns:
            dtype = df[col].dtype
            st.markdown(f"### {col}  —  `{dtype}`")

            if col in numeric_like_cols:
                converted = pd.to_numeric(df[col], errors="coerce").dropna()
                data_min = float(converted.min()) if len(converted) else 0.0
                data_max = float(converted.max()) if len(converted) else 100.0

                existing = st.session_state.col_config.get(col, {})
                c1, c2 = st.columns(2)
                min_val = c1.number_input(
                    f"Minimum valid value for '{col}'",
                    value=float(existing.get("min", data_min)),
                    key=f"min_{col}"
                )
                max_val = c2.number_input(
                    f"Maximum valid value for '{col}'",
                    value=float(existing.get("max", data_max)),
                    key=f"max_{col}"
                )
                st.session_state.col_config[col] = {"kind": "numeric", "min": min_val, "max": max_val}

            else:
                existing = st.session_state.col_config.get(col, {})
                uniq_vals = df[col].dropna().unique().tolist()
                gender_like = is_gender_column(uniq_vals) and col not in ["Student_ID", "StudentID", "Name"]
                is_categorical = 0 < len(uniq_vals) <= CATEGORY_THRESHOLD and col not in ["Student_ID", "StudentID", "Name"]

                case_choice = st.selectbox(
                    f"Base style for '{col}'",
                    ["UPPER", "lower", "Title"],
                    index=["UPPER", "lower", "Title"].index(existing.get("case", "Title")),
                    key=f"case_{col}"
                )

                if gender_like:
                    st.caption(f"'{col}' looks like a Gender column. Choose the final format:")
                    fmt_choice = st.selectbox(
                        f"Gender format for '{col}'",
                        list(GENDER_FORMAT_OPTIONS.keys()),
                        index=list(GENDER_FORMAT_OPTIONS.keys()).index(existing.get("gender_format", "Female / Male")),
                        key=f"genderfmt_{col}"
                    )
                    st.session_state.col_config[col] = {
                        "kind": "text", "case": case_choice,
                        "categorical": True, "gender": True,
                        "gender_format": fmt_choice
                    }

                elif is_categorical:
                    st.caption(f"'{col}' has few unique values — set exactly what each should become:")
                    mapping = existing.get("mapping", {})
                    new_mapping = {}
                    for uv in uniq_vals:
                        default_val = mapping.get(uv, apply_case(uv, case_choice))
                        new_mapping[uv] = st.text_input(
                            f"'{uv}' →", value=default_val, key=f"map_{col}_{uv}"
                        )
                    st.session_state.col_config[col] = {
                        "kind": "text", "case": case_choice,
                        "categorical": True, "gender": False,
                        "mapping": new_mapping
                    }
                else:
                    st.session_state.col_config[col] = {
                        "kind": "text", "case": case_choice,
                        "categorical": False, "gender": False
                    }

            st.divider()

        if st.button("Finish — Apply Formats & Go to Analysis", type="primary"):
            for col, cfg in st.session_state.col_config.items():
                if cfg.get("kind") == "text":
                    if cfg.get("gender"):
                        female_word, male_word = GENDER_FORMAT_OPTIONS[cfg["gender_format"]]
                        def map_gender(v):
                            if pd.isnull(v):
                                return v
                            g = classify_gender(v)
                            if g == "female":
                                return female_word
                            elif g == "male":
                                return male_word
                            return v
                        df[col] = df[col].apply(map_gender)
                    elif cfg.get("categorical") and cfg.get("mapping"):
                        mapping = cfg["mapping"]
                        df[col] = df[col].apply(lambda v: mapping.get(v, v) if pd.notnull(v) else v)
                    else:
                        case = cfg.get("case", "Title")
                        df[col] = df[col].apply(lambda v: apply_case(v, case) if pd.notnull(v) else v)
            st.session_state.df = df
            st.session_state.page = "analysis"
            st.rerun()

    # ================= PAGE 2: ANALYSIS =================
    elif st.session_state.page == "analysis":
        if st.button("← Back to Range / Format Settings"):
            st.session_state.page = "config"
            st.rerun()

        df = st.session_state.df
        log = st.session_state.log
        col_config = st.session_state.col_config

        def id_of(idx):
            for c in ["Student_ID", "StudentID"]:
                if c in df.columns:
                    return df.loc[idx, c]
            return idx

        def show_row_with_red_cell(idx, col):
            row = df.loc[[idx]].copy()
            row = row.where(pd.notnull(row), "None")
            def highlight(s):
                return ['background-color:#ffe6e6; color:#c0392b; font-weight:bold; text-decoration:underline'
                        if s.name == col else '' for _ in s]
            styled = row.style.apply(highlight, axis=0)
            st.markdown(styled.to_html(), unsafe_allow_html=True)

        def record_history(section, col, idx, before, after):
            st.session_state.history.append({
                "Section": section, "Column": col, "Row": idx,
                "ID": id_of(idx), "Before": before, "After": after
            })

        def fix_row_ui(section, col, idx, is_num, expected_hint):
            key = f"{section}_{col}_{idx}"
            st.caption(f"Row {idx} — ID: {id_of(idx)}  |  Expected: {expected_hint}")
            show_row_with_red_cell(idx, col)

            current_val = df.loc[idx, col]
            current_display = "None" if pd.isnull(current_val) else current_val

            left, right = st.columns(2)
            with left:
                st.write(f"**Current value in '{col}':** {current_display}")
            with right:
                with st.form(key=f"form_{key}", clear_on_submit=True):
                    val_str = st.text_input(f"New value for '{col}'", key=f"in_{key}")
                    submitted = st.form_submit_button("Save")
                    if submitted:
                        if is_num:
                            try:
                                new_val = float(val_str)
                                ok = True
                            except ValueError:
                                ok = False
                                st.error(f"'{col}' expects a NUMBER.")
                        else:
                            new_val = val_str
                            ok = val_str.strip() != ""
                            if not ok:
                                st.error(f"'{col}' expects TEXT.")
                        if ok:
                            if df[col].dtype != "object":
                                df[col] = df[col].astype(object)
                            before = df.loc[idx, col]
                            df.loc[idx, col] = new_val
                            st.session_state.df = df
                            log[key] = True
                            record_history(section, col, idx, before, new_val)
                            st.rerun()
            if log.get(key):
                green_tick(f"Row {idx} — '{col}' fixed")
            st.divider()

        numeric_like_cols = [c for c in df.columns if is_numeric_like(df[c])]
        text_cols = [c for c in df.columns if c not in numeric_like_cols]

        # ---------------- 1. DATA ----------------
        st.header("1. Uploaded Data")
        st.write(f"**Rows:** {df.shape[0]}  |  **Columns:** {df.shape[1]}")
        st.dataframe(df, use_container_width=True)

        # ---------------- 2. MISSING VALUES ----------------
        st.header("2. Missing Values")
        missing_cols = df.columns[df.isnull().any()].tolist()
        if not missing_cols:
            green_tick("No missing values found.")
        else:
            for col in missing_cols:
                is_num = col in numeric_like_cols
                rows = df[df[col].isnull()]
                cfg = col_config.get(col, {})
                if is_num:
                    hint = f"Number between {cfg.get('min')} and {cfg.get('max')}"
                else:
                    hint = f"Text ({cfg.get('case')})"
                st.subheader(f"'{col}' — {len(rows)} missing")
                for idx in rows.index:
                    fix_row_ui("miss", col, idx, is_num, hint)

        # ---------------- 3. DUPLICATES ----------------
        st.header("3. Duplicate Rows")
        st.caption("A row is marked duplicate only when every column value matches another row exactly.")
        dup_count = df.duplicated().sum()
        if dup_count == 0:
            green_tick("No duplicate rows found.")
        else:
            st.warning(f"{dup_count} duplicate rows found.")
            st.dataframe(df[df.duplicated()], use_container_width=True)
            if st.button("Remove Duplicate Rows"):
                before_rows = df[df.duplicated()].copy()
                df.drop_duplicates(inplace=True)
                st.session_state.df = df
                log["dup"] = True
                for idx in before_rows.index:
                    record_history("duplicate", "ROW", idx, "duplicate row", "removed")
                st.rerun()
            if log.get("dup"):
                green_tick("Duplicates removed")

        # ---------------- 4. OUTLIERS ----------------
        st.header("4. Outlier Check")
        for col in numeric_like_cols:
            cfg = col_config.get(col, {})
            lo, hi = cfg.get("min"), cfg.get("max")
            if lo is None or hi is None:
                continue
            converted = pd.to_numeric(df[col], errors="coerce")
            out_idx = converted[(converted < lo) | (converted > hi)].index

            if len(out_idx) == 0:
                green_tick(f"{col}: No outliers found (valid range {lo} to {hi}).")
                continue

            st.subheader(f"'{col}' — {len(out_idx)} outlier(s)")
            for idx in out_idx:
                fix_row_ui("outlier", col, idx, True, f"Number between {lo} and {hi}")

        # ---------------- 5. DATA TYPE ERRORS ----------------
        st.header("5. Data Type Overview")
        cols_per_row = 4
        dtype_items = [(c, df[c].dtype) for c in df.columns]
        for i in range(0, len(dtype_items), cols_per_row):
            row_items = dtype_items[i:i + cols_per_row]
            cols = st.columns(cols_per_row)
            for j, (c, dt) in enumerate(row_items):
                cols[j].markdown(f"**{c}**  \n`{dt}`")

        st.subheader("Rows with text instead of number")
        found = False
        for col in numeric_like_cols:
            converted = pd.to_numeric(df[col], errors="coerce")
            bad_idx = df[(converted.isnull()) & (df[col].notnull())].index
            if len(bad_idx) > 0:
                found = True
                cfg = col_config.get(col, {})
                hint = f"Number between {cfg.get('min')} and {cfg.get('max')}"
                st.markdown(f"**'{col}'** — {len(bad_idx)} row(s)")
                for idx in bad_idx:
                    fix_row_ui("dtype", col, idx, True, hint)
        if not found:
            green_tick("No text-in-number errors found.")

        # ---------------- 6. TEXT FORMAT STATUS ----------------
        st.header("6. Text Format / Category Standardization")
        green_tick("All text columns have been standardized using your Page 1 settings.")
        for col in text_cols:
            cfg = col_config.get(col, {})
            if cfg.get("gender"):
                st.caption(f"**{col}**: Gender format — {cfg.get('gender_format')}")
            elif cfg.get("categorical"):
                st.caption(f"**{col}**: mapped — {cfg.get('mapping')}")
            else:
                st.caption(f"**{col}**: style — {cfg.get('case')}")

        # ---------------- 7. CHANGE HISTORY ----------------
        st.header("7. All Fixes So Far (Before vs After)")
        if len(st.session_state.history) == 0:
            st.info("No fixes made yet.")
        else:
            hist_df = pd.DataFrame(st.session_state.history)
            st.dataframe(hist_df, use_container_width=True)

        # ---------------- 8. SEARCH ----------------
        st.header("8. Search in Data")
        c1, c2, c3 = st.columns([1.5, 1.5, 1])
        search_col = c1.selectbox("Choose column", df.columns.tolist())
        is_num_col = search_col in numeric_like_cols
        if is_num_col:
            val = c2.text_input("Value", key="search_num")
            op = c3.selectbox("Condition", ["=", ">", "<", ">=", "<="])
            if st.button("Search"):
                try:
                    v = float(val)
                    converted = pd.to_numeric(df[search_col], errors="coerce")
                    ops = {"=": converted == v, ">": converted > v, "<": converted < v,
                           ">=": converted >= v, "<=": converted <= v}
                    result = df[ops[op]]
                    st.write(f"Found {len(result)} rows")
                    st.dataframe(result, use_container_width=True)
                except ValueError:
                    st.error("Enter a valid number.")
        else:
            val = c2.text_input("Value", key="search_text")
            c3.write("contains")
            if st.button("Search"):
                result = df[df[search_col].astype(str).str.contains(val, case=False, na=False)]
                st.write(f"Found {len(result)} rows")
                st.dataframe(result, use_container_width=True)

        # ---------------- 9. CURRENT DATA ----------------
        st.header("9. Current Modified Data (Live)")
        st.dataframe(df, use_container_width=True)

        # ---------------- 10. DOWNLOAD ----------------
        st.header("10. Download")
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("Download Current Data (CSV)", df.to_csv(index=False), "modified_data.csv")
        with c2:
            if len(st.session_state.history) > 0:
                hist_csv = pd.DataFrame(st.session_state.history).to_csv(index=False)
                st.download_button("Download Change History (CSV)", hist_csv, "change_history.csv")

        st.divider()
        if st.button("Reset to Original Upload"):
            del st.session_state.df
            st.session_state.log = {}
            st.session_state.history = []
            st.session_state.col_config = {}
            st.session_state.page = "config"
            st.rerun()