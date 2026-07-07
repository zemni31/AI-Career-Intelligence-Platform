"""
src/career_advisor/app.py
AI Career Intelligence Platform — Career Advisor
"""

import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

sys.path.append(str(Path(__file__).resolve().parent.parent))
from db.connection import get_connection

# ── Configuration ─────────────────────────────────────────────
st.set_page_config(
    page_title="AI Career Advisor",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CSS personnalisé ──────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0f1117; }
    .metric-card {
        background: linear-gradient(135deg, #1e3a5f, #2e86c1);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        color: white;
        margin: 5px;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #f0f0f0;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #aed6f1;
        margin-top: 5px;
    }
    .skill-tag {
        display: inline-block;
        background-color: #2e86c1;
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
    .section-title {
        font-size: 1.3rem;
        font-weight: bold;
        color: #2e86c1;
        border-left: 4px solid #2e86c1;
        padding-left: 10px;
        margin: 20px 0 10px 0;
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


# ── Sidebar — Navigation ──────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/artificial-intelligence.png",
             width=80)
    st.title("AI Career Advisor")
    st.markdown("---")

    page = st.radio(
        "Navigation",
        ["🏠 Accueil", "📝 Mon Profil", "📊 Résultats", "🗺️ Plan de carrière"],
        index=0
    )

    st.markdown("---")
    st.markdown("**Base de données**")
    st.metric("Offres analysées", f"{len(jobs_df):,}")
    st.metric("Compétences", f"{len(skills_df):,}")
    st.metric("Pays couverts", f"{len(countries_df):,}")


# ════════════════════════════════════════════════════════════
# PAGE 1 — ACCUEIL
# ════════════════════════════════════════════════════════════
if page == "🏠 Accueil":
    st.markdown("#  🤖 AI Career Intelligence Platform")
    st.markdown("### Prenez les meilleures décisions pour votre carrière Data & IA")
    st.markdown("---")

    # ── Dialogs (fenêtres modales) ────────────────────────────
@st.dialog("📋 Liste des offres", width="large")
def show_jobs():
    st.dataframe(
        jobs_df[["job_title", "country", "salary_avg", "experience_level"]]
        .rename(columns={
            "job_title": "Métier",
            "country": "Pays",
            "salary_avg": "Salaire (USD)",
            "experience_level": "Expérience"
        })
        .sort_values("Salaire (USD)", ascending=False)
        .reset_index(drop=True),
        use_container_width=True,
        height=500,
        column_config={
            "Salaire (USD)": st.column_config.NumberColumn(
                format="$%,.0f"
            )
        }
    )

@st.dialog("🛠️ Liste des compétences", width="large")
def show_skills():
    st.dataframe(
        skills_df[["name", "category"]]
        .rename(columns={"name": "Compétence", "category": "Catégorie"})
        .sort_values("Catégorie")
        .reset_index(drop=True),
        use_container_width=True,
        height=500
    )

@st.dialog("💼 Liste des métiers", width="large")
def show_metiers():
    metiers = (
        jobs_df.groupby("job_title")
        .agg(nb_offres=("id", "count"), salaire_moyen=("salary_avg", "mean"))
        .reset_index()
        .rename(columns={
            "job_title": "Métier",
            "nb_offres": "Nb offres",
            "salaire_moyen": "Salaire moyen (USD)"
        })
        .sort_values("Nb offres", ascending=False)
        .reset_index(drop=True)
    )
    metiers["Salaire moyen (USD)"] = metiers["Salaire moyen (USD)"].round(0)
    # Ajouter une colonne de pourcentage normalisée (0-100) pour la barre de progression
    if not metiers["Nb offres"].empty and metiers["Nb offres"].max() > 0:
        max_nb = metiers["Nb offres"].max()
        metiers["% Offres"] = (metiers["Nb offres"] / max_nb * 100).round(0).astype(float)
    else:
        metiers["% Offres"] = 0.0
    st.dataframe(
        metiers,
        use_container_width=True,
        height=500,
        column_config={
            "Salaire moyen (USD)": st.column_config.NumberColumn(format="$%,.0f"),
            "Nb offres": st.column_config.NumberColumn(format="%d"),
            "% Offres": st.column_config.ProgressColumn(min_value=0, max_value=100)
        }
    )

@st.dialog("🌍 Liste des pays", width="large")
def show_pays():
    pays = (
        jobs_df.groupby("country")
        .agg(nb_offres=("id", "count"), salaire_moyen=("salary_avg", "mean"))
        .reset_index()
        .rename(columns={
            "country": "Pays",
            "nb_offres": "Nb offres",
            "salaire_moyen": "Salaire moyen (USD)"
        })
        .sort_values("Nb offres", ascending=False)
        .reset_index(drop=True)
    )
    pays["Salaire moyen (USD)"] = pays["Salaire moyen (USD)"].round(0)
    # Normaliser en pourcentage pour la barre (0-100) et afficher aussi le nombre réel
    if not pays["Nb offres"].empty and pays["Nb offres"].max() > 0:
        max_nb_p = pays["Nb offres"].max()
        pays["% Offres"] = (pays["Nb offres"] / max_nb_p * 100).round(0).astype(float)
    else:
        pays["% Offres"] = 0.0

    st.dataframe(
        pays,
        use_container_width=True,
        height=500,
        column_config={
            "Salaire moyen (USD)": st.column_config.NumberColumn(format="$%,.0f"),
            "Nb offres": st.column_config.NumberColumn(format="%d"),
            "% Offres": st.column_config.ProgressColumn(min_value=0, max_value=100)
        }
    )

# ── Cards + boutons ───────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{len(jobs_df):,}</div>
        <div class="metric-label">Offres analysées</div>
    </div>""", unsafe_allow_html=True)
    if st.button("📋 Voir les offres", key="btn_jobs"):
        show_jobs()

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{len(skills_df):,}</div>
        <div class="metric-label">Compétences référencées</div>
    </div>""", unsafe_allow_html=True)
    if st.button("🛠️ Voir les compétences", key="btn_skills"):
        show_skills()

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{jobs_df['job_title'].nunique()}</div>
        <div class="metric-label">Métiers couverts</div>
    </div>""", unsafe_allow_html=True)
    if st.button("💼 Voir les métiers", key="btn_metiers"):
        show_metiers()

with col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{len(countries_df):,}</div>
        <div class="metric-label">Pays analysés</div>
    </div>""", unsafe_allow_html=True)
    if st.button("🌍 Voir les pays", key="btn_pays"):
        show_pays()
st.markdown("---")
st.markdown("### Comment utiliser le Career Advisor ?")

c1, c2, c3 = st.columns(3)
with c1:
    st.info("**Étape 1 — Mon Profil**\n\nSaisissez vos compétences actuelles, votre niveau d'expérience et votre pays cible.")
with c2:
    st.success("**Étape 2 — Résultats**\n\nDécouvrez les métiers compatibles avec votre profil et votre score de compatibilité.")
with c3:
    st.warning("**Étape 3 — Plan de carrière**\n\nIdentifiez les compétences à acquérir en priorité pour maximiser votre salaire.")


# ════════════════════════════════════════════════════════════
# PAGE 2 — MON PROFIL
# ════════════════════════════════════════════════════════════
if page == "📝 Mon Profil":
    st.markdown("# 📝 Mon Profil")
    st.markdown("Renseignez votre profil pour obtenir des recommandations personnalisées.")
    st.markdown("---")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown('<div class="section-title">Mes compétences actuelles</div>',
                    unsafe_allow_html=True)

        # Grouper les compétences par catégorie
        categories = skills_df["category"].dropna().unique().tolist()
        categories.sort()

        user_skills = st.multiselect(
            "Recherchez et sélectionnez vos compétences :",
            options=skills_df["name"].tolist(),
            placeholder="Ex: Python, SQL, AWS...",
            help="Vous pouvez sélectionner autant de compétences que vous voulez"
        )

        if user_skills:
            st.markdown("**Compétences sélectionnées :**")
            tags_html = "".join(
                [f'<span class="skill-tag">{s}</span>' for s in user_skills])
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
            ["Tous les pays"] + countries_df["name"].tolist()
        )

        salary_expectation = st.slider(
            "Salaire minimum souhaité (USD/an) :",
            min_value=30000,
            max_value=300000,
            value=80000,
            step=5000,
            format="$%d"
        )

    st.markdown("---")

    if st.button("🔍 Analyser mon profil", key="btn_analyze"):
        if not user_skills:
            st.error("⚠️ Veuillez sélectionner au moins une compétence.")
        else:
            st.session_state["user_skills"]        = user_skills
            st.session_state["experience"]         = experience
            st.session_state["target_country"]     = target_country
            st.session_state["salary_expectation"] = salary_expectation
            st.success("✅ Profil analysé ! Rendez-vous dans **Résultats** pour voir vos recommandations.")


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
    salary_exp     = st.session_state["salary_expectation"]

    st.markdown(f"**Profil analysé :** {', '.join(user_skills)}")
    st.markdown("---")

    # Filtrer par pays si nécessaire
    filtered_df = job_skills_df.copy()
    if target_country != "Tous les pays":
        filtered_df = filtered_df[filtered_df["country"] == target_country]

    # Calcul des scores de compatibilité
    job_scores   = {}
    job_skills_map = {}
    job_salaries = {}

    for job_title, group in filtered_df.groupby("job_title"):
        required  = set(group["skill_name"].tolist())
        user_set  = set(user_skills)
        match     = user_set & required
        # Dice coefficient — plus équilibré entre tes compétences et celles requises
        score = round(
            2 * len(match) / (len(user_set) + len(required)) * 100, 1
        ) if required else 0
        avg_sal   = group["salary_avg"].mean()

        job_scores[job_title]    = score
        job_skills_map[job_title] = required
        job_salaries[job_title]  = avg_sal

    # Trier par score
    sorted_jobs = sorted(job_scores.items(), key=lambda x: x[1], reverse=True)
    top_10      = [(j, s) for j, s in sorted_jobs if s > 0][:10]

    if not top_10:
        st.error("Aucun métier compatible trouvé. Essayez d'ajouter plus de compétences.")
        st.stop()

    # KPI
    best_job   = top_10[0][0]
    best_score = top_10[0][1]
    best_salary = job_salaries.get(best_job, 0)

    col1, col2, col3 = st.columns(3)
    col1.metric("🏆 Meilleur métier", best_job)
    col2.metric("🎯 Score de compatibilité", f"{best_score}%")
    col3.metric("💰 Salaire moyen", f"${best_salary:,.0f}" if best_salary else "N/A")

    st.markdown("---")

    # Graphique scores
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown('<div class="section-title">Top 10 métiers compatibles</div>',
                    unsafe_allow_html=True)

        jobs_chart = [j for j, _ in top_10]
        scores_chart = [s for _, s in top_10]
        colors = ["#27AE60" if s >= 50 else "#F39C12" if s >= 25 else "#E74C3C"
                  for s in scores_chart]

        fig = go.Figure(go.Bar(
            x=scores_chart,
            y=jobs_chart,
            orientation="h",
            marker_color=colors,
            text=[f"{s}%" for s in scores_chart],
            textposition="auto",
            textfont=dict(color="white", size=12)
        ))
        fig.update_layout(
            xaxis_title="Score de compatibilité (%)",
            xaxis=dict(range=[0, 120]),
            height=400,
            margin=dict(l=0, r=50, t=10, b=0),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white")
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.markdown('<div class="section-title">Compétences manquantes</div>',
                    unsafe_allow_html=True)

        selected_job = st.selectbox(
            "Choisir un métier cible :",
            [j for j, _ in top_10]
        )

        required = job_skills_map.get(selected_job, set())
        missing  = sorted(required - set(user_skills))
        matched  = sorted(required & set(user_skills))

        if matched:
            st.markdown("✅ **Compétences que vous avez déjà :**")
            tags = "".join(
                [f'<span class="skill-tag">{s}</span>' for s in matched])
            st.markdown(tags, unsafe_allow_html=True)

        if missing:
            st.markdown("❌ **Compétences à acquérir :**")
            tags = "".join(
                [f'<span class="missing-tag">{s}</span>' for s in missing])
            st.markdown(tags, unsafe_allow_html=True)
        else:
            st.success("🎉 Vous avez toutes les compétences requises !")


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

    # Compétences les plus demandées que l'utilisateur n'a pas encore
    all_required = job_skills_df.groupby("skill_name").size().reset_index(
        name="nb_offres")
    missing_skills = all_required[
        ~all_required["skill_name"].isin(user_skills)
    ].sort_values("nb_offres", ascending=False).head(15)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="section-title">Compétences à acquérir en priorité</div>',
                    unsafe_allow_html=True)
        st.caption("Compétences les plus demandées par les offres que vous n'avez pas encore")

        fig = px.bar(
            missing_skills,
            x="nb_offres",
            y="skill_name",
            orientation="h",
            color="nb_offres",
            color_continuous_scale="Blues",
            labels={"nb_offres": "Nombre d'offres", "skill_name": "Compétence"}
        )
        fig.update_layout(
            height=450,
            margin=dict(l=0, r=0, t=10, b=0),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            showlegend=False,
            coloraxis_showscale=False
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<div class="section-title">Pays qui recrutent pour votre profil</div>',
                    unsafe_allow_html=True)
        st.caption("Pays avec le plus d'offres correspondant à vos compétences")

        # Offres qui matchent au moins une compétence de l'utilisateur
        matching = job_skills_df[
            job_skills_df["skill_name"].isin(user_skills)
        ]
        country_counts = matching.groupby("country")["job_id"].nunique().reset_index(
            name="nb_offres"
        ).sort_values("nb_offres", ascending=False).head(10)
        country_counts = country_counts[country_counts["country"].notna()]

        fig2 = px.bar(
            country_counts,
            x="country",
            y="nb_offres",
            color="nb_offres",
            color_continuous_scale="Teal",
            labels={"nb_offres": "Nombre d'offres", "country": "Pays"}
        )
        fig2.update_layout(
            height=450,
            margin=dict(l=0, r=0, t=10, b=0),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            showlegend=False,
            coloraxis_showscale=False
        )
        st.plotly_chart(fig2, use_container_width=True)

    # Impact sur le salaire
    st.markdown("---")
    st.markdown('<div class="section-title">Impact des compétences sur le salaire</div>',
                unsafe_allow_html=True)
    st.caption("Salaire moyen des offres qui demandent chaque compétence manquante")

    skill_salary = []
    for skill in missing_skills["skill_name"].head(10):
        jobs_with_skill = job_skills_df[
            job_skills_df["skill_name"] == skill
        ]["job_id"].unique()
        avg_sal = jobs_df[jobs_df["id"].isin(jobs_with_skill)]["salary_avg"].mean()
        if avg_sal > 0:
            skill_salary.append({"skill": skill, "salaire_moyen": round(avg_sal, 0)})

    if skill_salary:
        sal_df = pd.DataFrame(skill_salary).sort_values(
            "salaire_moyen", ascending=False)

        fig3 = px.bar(
            sal_df,
            x="skill",
            y="salaire_moyen",
            color="salaire_moyen",
            color_continuous_scale="RdYlGn",
            labels={"salaire_moyen": "Salaire moyen (USD)", "skill": "Compétence"},
            text_auto=True
        )
        fig3.update_layout(
            height=350,
            margin=dict(l=0, r=0, t=10, b=0),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            coloraxis_showscale=False
        )
        st.plotly_chart(fig3, use_container_width=True)