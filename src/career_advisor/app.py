"""
src/career_advisor/app.py
AI Career Intelligence Platform — Career Advisor V2
"""

import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

sys.path.append(str(Path(__file__).resolve().parent.parent))
from db.connection import get_connection

# ── Configuration ─────────────────────────────────────────────
st.set_page_config(
    page_title="AI Career Advisor",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1e3a5f, #2e86c1);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        color: white;
        margin: 5px;
    }
    .metric-value { font-size: 2rem; font-weight: bold; color: #f0f0f0; }
    .metric-label { font-size: 0.85rem; color: #aed6f1; margin-top: 5px; }
    .skill-tag {
        display: inline-block;
        background-color: #27AE60;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        margin: 3px;
        font-size: 0.85rem;
    }
    .missing-tag {
        display: inline-block;
        background-color: #e74c3c;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        margin: 3px;
        font-size: 0.85rem;
    }
    .badge-excellent {
        background-color: #27AE60;
        color: white;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: bold;
    }
    .badge-bon {
        background-color: #F39C12;
        color: white;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: bold;
    }
    .badge-moyen {
        background-color: #E74C3C;
        color: white;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: bold;
    }
    .section-title {
        font-size: 1.2rem;
        font-weight: bold;
        color: #2e86c1;
        border-left: 4px solid #2e86c1;
        padding-left: 10px;
        margin: 20px 0 10px 0;
    }
    .job-card {
        background: #f8f9fa;
        border-left: 4px solid #2e86c1;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 8px 0;
    }
</style>
""", unsafe_allow_html=True)


# ── Chargement des données ────────────────────────────────────
@st.cache_data
def load_data():
    conn = get_connection()

    skills_df = pd.read_sql(
        "SELECT id, name, category FROM skills ORDER BY name;", conn)

    jobs_df = pd.read_sql("""
        SELECT j.id, j.job_title, j.job_category,
               j.experience_level, j.salary_avg,
               j.company_size, j.is_remote_friendly,
               c.name as country
        FROM jobs j
        LEFT JOIN countries c ON j.country_id = c.id
        WHERE j.source = 'kaggle_ai_jobs'
          AND j.salary_avg IS NOT NULL;
    """, conn)

    job_skills_df = pd.read_sql("""
        SELECT j.id as job_id, j.job_title,
               j.experience_level, j.salary_avg,
               c.name as country, s.name as skill_name
        FROM jobs j
        JOIN job_skills js ON j.id = js.job_id
        JOIN skills s ON js.skill_id = s.id
        LEFT JOIN countries c ON j.country_id = c.id
        WHERE j.source = 'kaggle_ai_jobs';
    """, conn)

    countries_df = pd.read_sql(
        "SELECT DISTINCT name FROM countries ORDER BY name;", conn)

    conn.close()
    return skills_df, jobs_df, job_skills_df, countries_df

skills_df, jobs_df, job_skills_df, countries_df = load_data()


# ── Dialogs ───────────────────────────────────────────────────
@st.dialog("📋 Offres d'emploi", width="large")
def show_jobs():
    df = (jobs_df[["job_title", "country", "salary_avg", "experience_level"]]
          .rename(columns={"job_title": "Métier", "country": "Pays",
                           "salary_avg": "Salaire (USD)",
                           "experience_level": "Expérience"})
          .sort_values("Salaire (USD)", ascending=False)
          .drop_duplicates().reset_index(drop=True))
    st.dataframe(df, use_container_width=True, height=500,
                 column_config={"Salaire (USD)": st.column_config.NumberColumn(format="$%,.0f")})

@st.dialog("🛠️ Compétences référencées", width="large")
def show_skills():
    df = (skills_df[["name", "category"]]
          .rename(columns={"name": "Compétence", "category": "Catégorie"})
          .fillna("Non catégorisée")
          .sort_values(["Catégorie", "Compétence"])
          .drop_duplicates().reset_index(drop=True))
    st.dataframe(df, use_container_width=True, height=500)

@st.dialog("💼 Métiers couverts", width="large")
def show_metiers():
    df = (jobs_df.groupby("job_title")
          .agg(nb_offres=("id", "count"), salaire_moyen=("salary_avg", "mean"))
          .reset_index()
          .rename(columns={"job_title": "Métier", "nb_offres": "Nb offres",
                           "salaire_moyen": "Salaire moyen (USD)"})
          .sort_values("Nb offres", ascending=False)
          .reset_index(drop=True))
    df["Salaire moyen (USD)"] = df["Salaire moyen (USD)"].round(0)
    max_nb = int(df["Nb offres"].max())
    st.dataframe(df, use_container_width=True, height=500,
                 column_config={
                     "Salaire moyen (USD)": st.column_config.NumberColumn(format="$%,.0f"),
                     "Nb offres": st.column_config.ProgressColumn(
                         min_value=0, max_value=max_nb, format="%d")
                 })

@st.dialog("🌍 Pays analysés", width="large")
def show_pays():
    df = (jobs_df.groupby("country")
          .agg(nb_offres=("id", "count"), salaire_moyen=("salary_avg", "mean"))
          .reset_index()
          .rename(columns={"country": "Pays", "nb_offres": "Nb offres",
                           "salaire_moyen": "Salaire moyen (USD)"})
          .sort_values("Nb offres", ascending=False)
          .reset_index(drop=True))
    df["Salaire moyen (USD)"] = df["Salaire moyen (USD)"].round(0)
    max_nb = int(df["Nb offres"].max())
    st.dataframe(df, use_container_width=True, height=500,
                 column_config={
                     "Salaire moyen (USD)": st.column_config.NumberColumn(format="$%,.0f"),
                     "Nb offres": st.column_config.ProgressColumn(
                         min_value=0, max_value=max_nb, format="%d")
                 })


# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/artificial-intelligence.png", width=80)
    st.title("AI Career Advisor")
    st.markdown("---")
    page = st.radio("Navigation", [
        "🏠 Accueil", "📝 Mon Profil",
        "📊 Résultats", "🗺️ Plan de carrière"
    ])
    st.markdown("---")
    st.markdown("**Base de données**")
    st.metric("Offres analysées", f"{len(jobs_df):,}")
    st.metric("Compétences", f"{len(skills_df):,}")
    st.metric("Pays couverts", f"{len(countries_df):,}")


# ════════════════════════════════════════════════════════════
# PAGE 1 — ACCUEIL
# ════════════════════════════════════════════════════════════
if page == "🏠 Accueil":
    st.markdown("# 🤖 AI Career Intelligence Platform")
    st.markdown("### Prenez les meilleures décisions pour votre carrière Data & IA")
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-value">{len(jobs_df):,}</div>
            <div class="metric-label">Offres analysées</div>
        </div>""", unsafe_allow_html=True)
        if st.button("📋 Voir les offres", key="btn_jobs", use_container_width=True):
            show_jobs()

    with col2:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-value">{len(skills_df):,}</div>
            <div class="metric-label">Compétences référencées</div>
        </div>""", unsafe_allow_html=True)
        if st.button("🛠️ Voir les compétences", key="btn_skills", use_container_width=True):
            show_skills()

    with col3:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-value">{jobs_df['job_title'].nunique()}</div>
            <div class="metric-label">Métiers couverts</div>
        </div>""", unsafe_allow_html=True)
        if st.button("💼 Voir les métiers", key="btn_metiers", use_container_width=True):
            show_metiers()

    with col4:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-value">{len(countries_df):,}</div>
            <div class="metric-label">Pays analysés</div>
        </div>""", unsafe_allow_html=True)
        if st.button("🌍 Voir les pays", key="btn_pays", use_container_width=True):
            show_pays()

    st.markdown("---")
    st.markdown("### Comment utiliser le Career Advisor ?")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.info("**Étape 1 — Mon Profil**\n\nSaisissez vos compétences, votre niveau d'expérience et votre pays cible.")
    with c2:
        st.success("**Étape 2 — Résultats**\n\nDécouvrez vos métiers compatibles avec score, badges et compétences manquantes.")
    with c3:
        st.warning("**Étape 3 — Plan de carrière**\n\nIdentifiez les compétences prioritaires et les pays qui recrutent pour votre profil.")


# ════════════════════════════════════════════════════════════
# PAGE 2 — MON PROFIL
# ════════════════════════════════════════════════════════════
elif page == "📝 Mon Profil":
    st.markdown("# 📝 Mon Profil")
    st.markdown("Renseignez votre profil pour obtenir des recommandations personnalisées.")
    st.markdown("---")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown('<div class="section-title">Mes compétences actuelles</div>',
                    unsafe_allow_html=True)
        user_skills = st.multiselect(
            "Recherchez et sélectionnez vos compétences :",
            options=sorted(skills_df["name"].dropna().unique().tolist()),
            placeholder="Ex: Python, SQL, AWS...",
        )
        if user_skills:
            st.markdown("**Compétences sélectionnées :**")
            tags_html = "".join([f'<span class="skill-tag">{s}</span>'
                                 for s in user_skills])
            st.markdown(tags_html, unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="section-title">Mon profil</div>',
                    unsafe_allow_html=True)
        experience = st.selectbox(
            "Niveau d'expérience :",
            ["Entry (0-2 ans)", "Mid (2-5 ans)",
             "Senior (5-10 ans)", "Lead (10+ ans)"]
        )
        target_country = st.selectbox(
            "Pays cible :",
            ["Tous les pays"] + countries_df["name"].dropna().tolist()
        )
        salary_expectation = st.slider(
            "Salaire minimum souhaité (USD/an) :",
            min_value=30000, max_value=300000,
            value=80000, step=5000, format="$%d"
        )

    st.markdown("---")
    if st.button("🔍 Analyser mon profil", type="primary", use_container_width=True):
        if not user_skills:
            st.error("⚠️ Veuillez sélectionner au moins une compétence.")
        else:
            st.session_state["user_skills"]        = user_skills
            st.session_state["experience"]         = experience
            st.session_state["target_country"]     = target_country
            st.session_state["salary_expectation"] = salary_expectation
            st.success("✅ Profil analysé ! Allez dans **Résultats** pour voir vos recommandations.")


# ════════════════════════════════════════════════════════════
# PAGE 3 — RÉSULTATS
# ════════════════════════════════════════════════════════════
elif page == "📊 Résultats":
    st.markdown("# 📊 Résultats de l'analyse")

    if "user_skills" not in st.session_state:
        st.warning("⚠️ Veuillez d'abord renseigner votre profil dans **Mon Profil**.")
        st.stop()

    user_skills    = st.session_state["user_skills"]
    target_country = st.session_state["target_country"]

    st.markdown(f"**Profil analysé :** {', '.join(user_skills)}")
    st.markdown("---")

    # Filtrer par pays
    filtered_df = job_skills_df.copy()
    if target_country != "Tous les pays":
        filtered_df = filtered_df[filtered_df["country"] == target_country]

    # Calcul des scores — Dice coefficient
    job_scores    = {}
    job_skills_map = {}
    job_salaries  = {}
    user_set      = set(user_skills)

    for job_title, group in filtered_df.groupby("job_title"):
        required = set(group["skill_name"].dropna().tolist())
        match    = user_set & required
        score    = round(2 * len(match) / (len(user_set) + len(required)) * 100, 1) \
                   if (len(user_set) + len(required)) > 0 else 0
        job_scores[job_title]     = score
        job_skills_map[job_title] = required
        job_salaries[job_title]   = group["salary_avg"].dropna().mean()

    sorted_jobs = sorted(job_scores.items(), key=lambda x: x[1], reverse=True)
    top_10      = [(j, s) for j, s in sorted_jobs if s > 0][:10]

    if not top_10:
        st.error("Aucun métier compatible. Essayez d'ajouter plus de compétences.")
        st.stop()

    best_job    = top_10[0][0]
    best_score  = top_10[0][1]
    best_salary = job_salaries.get(best_job, 0)

    # ── KPI ──────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    col1.metric("🏆 Meilleur métier", best_job)
    col2.metric("🎯 Score de compatibilité", f"{best_score}%")
    col3.metric("💰 Salaire moyen estimé",
                f"${best_salary:,.0f}" if best_salary and best_salary > 0 else "N/A")

    st.markdown("---")

    col_left, col_right = st.columns(2)

    # ── Graphique scores avec badges ─────────────────────────
    with col_left:
        st.markdown('<div class="section-title">Top 10 métiers compatibles</div>',
                    unsafe_allow_html=True)

        jobs_chart   = [j for j, _ in top_10]
        scores_chart = [s for _, s in top_10]
        colors = ["#27AE60" if s >= 50 else "#F39C12" if s >= 25 else "#E74C3C"
                  for s in scores_chart]

        fig = go.Figure(go.Bar(
            x=scores_chart,
            y=jobs_chart,
            orientation="h",
            marker_color=colors,
            text=[f"{s}%" for s in scores_chart],
            textposition="outside",
            textfont=dict(size=12)
        ))
        fig.update_layout(
            xaxis=dict(range=[0, 120], title="Score (%)"),
            height=400,
            margin=dict(l=0, r=60, t=10, b=0),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Badges sous le graphique
        st.markdown("**Légende :**")
        st.markdown(
            '<span class="badge-excellent">🟢 Excellent ≥ 50%</span> &nbsp;'
            '<span class="badge-bon">🟡 Bon ≥ 25%</span> &nbsp;'
            '<span class="badge-moyen">🔴 Moyen < 25%</span>',
            unsafe_allow_html=True
        )

    # ── Compétences manquantes ────────────────────────────────
    with col_right:
        st.markdown('<div class="section-title">Analyse des compétences</div>',
                    unsafe_allow_html=True)

        selected_job = st.selectbox("Choisir un métier cible :", [j for j, _ in top_10])
        score_sel    = job_scores.get(selected_job, 0)
        required     = job_skills_map.get(selected_job, set())
        matched      = sorted(required & user_set)
        missing      = sorted(required - user_set)

        # Jauge de compatibilité
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score_sel,
            number={"suffix": "%"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": "#27AE60" if score_sel >= 50
                        else "#F39C12" if score_sel >= 25 else "#E74C3C"},
                "steps": [
                    {"range": [0, 25],  "color": "#FADBD8"},
                    {"range": [25, 50], "color": "#FDEBD0"},
                    {"range": [50, 100],"color": "#D5F5E3"},
                ],
            },
            title={"text": f"Compatibilité — {selected_job}"}
        ))
        fig_gauge.update_layout(height=220, margin=dict(l=20, r=20, t=40, b=10),
                                paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_gauge, use_container_width=True)

        if matched:
            st.markdown("✅ **Compétences acquises :**")
            st.markdown("".join([f'<span class="skill-tag">{s}</span>'
                                 for s in matched]), unsafe_allow_html=True)
        if missing:
            st.markdown("❌ **Compétences à acquérir :**")
            st.markdown("".join([f'<span class="missing-tag">{s}</span>'
                                 for s in missing]), unsafe_allow_html=True)
        else:
            st.success("🎉 Vous avez toutes les compétences requises !")

    st.markdown("---")
    st.markdown('<div class="section-title">📊 Compétences matchées vs manquantes — Top 5 métiers</div>',
                unsafe_allow_html=True)

    top5_jobs = [j for j, _ in top_10[:5]]
    chart_data = []
    for job in top5_jobs:
        req     = job_skills_map.get(job, set())
        matched = len(req & user_set)
        missing = len(req - user_set)
        chart_data.append({
            "Métier": job,
            "✅ Compétences acquises": matched,
            "❌ Compétences manquantes": missing
        })

    chart_df = pd.DataFrame(chart_data)
    fig_comp = px.bar(
        chart_df.melt(id_vars="Métier",
                      value_vars=["✅ Compétences acquises", "❌ Compétences manquantes"],
                      var_name="Type", value_name="Nombre"),
        x="Métier", y="Nombre", color="Type",
        color_discrete_map={
            "✅ Compétences acquises": "#27AE60",
            "❌ Compétences manquantes": "#E74C3C"
        },
        barmode="group",
        labels={"Nombre": "Nombre de compétences", "Métier": ""}
    )
    fig_comp.update_layout(
        height=350,
        margin=dict(l=0, r=0, t=10, b=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=-0.4)
    )
    st.plotly_chart(fig_comp, use_container_width=True)

    st.markdown("---")
    st.markdown('<div class="section-title">📄 Télécharger mon rapport PDF</div>',
                unsafe_allow_html=True)

    def generate_pdf(user_skills, top_10, job_scores, job_skills_map, job_salaries, target_country):
        from fpdf import FPDF

        pdf = FPDF()
        pdf.add_page()

        # Titre
        pdf.set_font("Helvetica", "B", 20)
        pdf.set_text_color(30, 58, 95)
        pdf.cell(0, 12, "AI Career Advisor", ln=True, align="C")

        pdf.set_font("Helvetica", "", 12)
        pdf.set_text_color(100, 100, 100)
        pdf.cell(0, 8, "Rapport d'analyse de carrière", ln=True, align="C")
        pdf.ln(5)

        # Ligne séparatrice
        pdf.set_draw_color(46, 134, 193)
        pdf.set_line_width(0.8)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(6)

        # Profil
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(30, 58, 95)
        pdf.cell(0, 8, "Mon profil", ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(50, 50, 50)
        pdf.multi_cell(0, 7, f"Compétences : {', '.join(user_skills)}")
        pdf.cell(0, 7, f"Pays cible : {target_country}", ln=True)
        pdf.ln(4)

        # Top métiers
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(30, 58, 95)
        pdf.cell(0, 8, "Top 10 métiers compatibles", ln=True)
        pdf.ln(2)

        for i, (job, score) in enumerate(top_10):
            badge  = "EXCELLENT" if score >= 50 else "BON" if score >= 25 else "MOYEN"
            color  = (39, 174, 96) if score >= 50 else (243, 156, 18) if score >= 25 else (231, 76, 60)
            sal    = job_salaries.get(job, 0)
            sal_str = f"${sal:,.0f}" if sal and sal > 0 else "N/A"

            pdf.set_fill_color(245, 248, 252)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(30, 58, 95)
            pdf.cell(0, 7, f"{i+1}. {job}", ln=True, fill=True)

            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(*color)
            pdf.cell(60, 6, f"Score : {score}%  [{badge}]")
            pdf.set_text_color(80, 80, 80)
            pdf.cell(0, 6, f"Salaire moyen : {sal_str}", ln=True)
            pdf.ln(1)

        # Analyse détaillée du meilleur métier
        best_job = top_10[0][0]
        pdf.ln(4)
        pdf.set_line_width(0.5)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(4)

        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(30, 58, 95)
        pdf.cell(0, 8, f"Analyse detaillee : {best_job}", ln=True)

        matched = sorted(job_skills_map.get(best_job, set()) & set(user_skills))
        missing = sorted(job_skills_map.get(best_job, set()) - set(user_skills))

        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(39, 174, 96)
        pdf.cell(0, 7, "Competences acquises :", ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(50, 50, 50)
        pdf.multi_cell(0, 6, ", ".join(matched) if matched else "Aucune")

        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(231, 76, 60)
        pdf.cell(0, 7, "Competences a acquerir :", ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(50, 50, 50)
        pdf.multi_cell(0, 6, ", ".join(missing) if missing else "Aucune — profil complet !")

        # Footer
        pdf.ln(10)
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 6, "Genere par AI Career Intelligence Platform", ln=True, align="C")

        return bytes(pdf.output())

    pdf_bytes = generate_pdf(
        user_skills, top_10, job_scores,
        job_skills_map, job_salaries, target_country
    )

    st.download_button(
        label="⬇️ Télécharger mon rapport (.pdf)",
        data=pdf_bytes,
        file_name="career_advisor_rapport.pdf",
        mime="application/pdf",
        use_container_width=True
    )


# ════════════════════════════════════════════════════════════
# PAGE 4 — PLAN DE CARRIÈRE
# ════════════════════════════════════════════════════════════
elif page == "🗺️ Plan de carrière":
    st.markdown("# 🗺️ Plan de carrière")

    if "user_skills" not in st.session_state:
        st.warning("⚠️ Veuillez d'abord renseigner votre profil dans **Mon Profil**.")
        st.stop()

    user_skills = st.session_state["user_skills"]
    st.markdown("---")

    # Compétences manquantes les plus demandées
    all_required   = job_skills_df.groupby("skill_name").size().reset_index(name="nb_offres")
    missing_skills = (all_required[~all_required["skill_name"].isin(user_skills)]
                      .sort_values("nb_offres", ascending=False)
                      .head(15))

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="section-title">🎯 Compétences à acquérir en priorité</div>',
                    unsafe_allow_html=True)
        st.caption("Compétences les plus demandées que vous n'avez pas encore")
        fig = px.bar(missing_skills, x="nb_offres", y="skill_name",
                     orientation="h", color="nb_offres",
                     color_continuous_scale="Blues",
                     labels={"nb_offres": "Nombre d'offres", "skill_name": "Compétence"})
        fig.update_layout(height=450, margin=dict(l=0, r=0, t=10, b=0),
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                          coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<div class="section-title">🌍 Pays qui recrutent pour votre profil</div>',
                    unsafe_allow_html=True)
        st.caption("Pays avec le plus d'offres correspondant à vos compétences")
        matching      = job_skills_df[job_skills_df["skill_name"].isin(user_skills)]
        country_counts = (matching.groupby("country")["job_id"].nunique()
                          .reset_index(name="nb_offres")
                          .dropna(subset=["country"])
                          .sort_values("nb_offres", ascending=False).head(10))
        fig2 = px.bar(country_counts, x="country", y="nb_offres",
                      color="nb_offres", color_continuous_scale="Teal",
                      labels={"nb_offres": "Nombre d'offres", "country": "Pays"})
        fig2.update_layout(height=450, margin=dict(l=0, r=0, t=10, b=0),
                           plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                           coloraxis_showscale=False)
        st.plotly_chart(fig2, use_container_width=True)

    # Impact sur le salaire
    st.markdown("---")
    st.markdown('<div class="section-title">💰 Impact des compétences sur le salaire</div>',
                unsafe_allow_html=True)
    st.caption("Salaire moyen des offres demandant chaque compétence manquante — "
               "plus la barre est verte, plus la compétence est lucrative")

    skill_salary = []
    for skill in missing_skills["skill_name"].head(10):
        job_ids = job_skills_df[job_skills_df["skill_name"] == skill]["job_id"].unique()
        avg_sal = jobs_df[jobs_df["id"].isin(job_ids)]["salary_avg"].mean()
        if pd.notna(avg_sal) and avg_sal > 0:
            skill_salary.append({"Compétence": skill, "Salaire moyen (USD)": round(avg_sal, 0)})

    if skill_salary:
        sal_df = pd.DataFrame(skill_salary).sort_values("Salaire moyen (USD)", ascending=False)
        fig3 = px.bar(sal_df, x="Compétence", y="Salaire moyen (USD)",
                      color="Salaire moyen (USD)", color_continuous_scale="RdYlGn",
                      text_auto=True)
        fig3.update_layout(height=350, margin=dict(l=0, r=0, t=10, b=0),
                           plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                           coloraxis_showscale=False)
        fig3.update_traces(texttemplate="$%{y:,.0f}", textposition="outside")
        st.plotly_chart(fig3, use_container_width=True)