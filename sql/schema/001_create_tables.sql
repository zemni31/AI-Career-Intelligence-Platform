-- ============================================================
-- AI Career Intelligence Platform
-- Schéma PostgreSQL — Version 1
-- ============================================================
-- Ce schéma unifie deux sources de données :
--   1. Adzuna API   -> offres individuelles réelles, mises à jour hebdomadaire
--   2. Kaggle        -> données de marché agrégées (tendances, scores, salaires)
--
-- Beaucoup de colonnes sont nullable car chaque source ne remplit
-- pas les mêmes champs (ex: Adzuna a "company", Kaggle ne l'a pas).
-- ============================================================

-- ------------------------------------------------------------
-- Table: countries
-- Référence des pays. Remplie une fois via sql/seed/.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS countries (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(5)  UNIQUE,        -- ex: 'FR', 'GB', 'US'
    name            VARCHAR(100) NOT NULL,
    continent       VARCHAR(50)
);

-- ------------------------------------------------------------
-- Table: companies
-- Alimentée uniquement par Adzuna (le dataset Kaggle ne fournit
-- pas de noms d'entreprises individuels).
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS companies (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    size            VARCHAR(20),                -- 'S', 'M', 'L' (peut être NULL si inconnu)
    country_id      INTEGER REFERENCES countries(id),
    created_at      TIMESTAMP DEFAULT NOW(),

    UNIQUE (name, country_id)
);

-- ------------------------------------------------------------
-- Table: skills
-- Référence des compétences. Remplie via seed initial (ex:
-- Python, SQL, AWS...) puis enrichie dynamiquement par l'ETL
-- quand de nouvelles compétences apparaissent dans les offres.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS skills (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(100) UNIQUE NOT NULL,
    category        VARCHAR(50)                 -- ex: 'Langage', 'Cloud', 'BI Tool', 'ML Framework'
);

-- ------------------------------------------------------------
-- Table: jobs
-- Table centrale. Une ligne = une offre d'emploi (Adzuna) ou
-- un enregistrement de marché (Kaggle). Le champ `source`
-- permet de distinguer l'origine et donc les champs attendus.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS jobs (
    id                      SERIAL PRIMARY KEY,

    -- Identifiants externes
    external_id             VARCHAR(100),        -- id Adzuna ou job_id Kaggle
    source                  VARCHAR(30) NOT NULL, -- 'adzuna' | 'kaggle_ai_jobs' | 'kaggle_ds_salaries'

    -- Informations générales
    job_title               VARCHAR(255) NOT NULL,
    job_category             VARCHAR(100),        -- ex: 'AI Engineering' (Kaggle uniquement)
    company_id               INTEGER REFERENCES companies(id),  -- NULL pour Kaggle

    -- Localisation
    country_id               INTEGER REFERENCES countries(id),
    city                      VARCHAR(150),
    latitude                  NUMERIC(9,6),
    longitude                 NUMERIC(9,6),

    -- Salaire
    salary_min                NUMERIC(12,2),
    salary_max                NUMERIC(12,2),
    salary_avg                NUMERIC(12,2),       -- calculé ou fourni directement (annual_salary_usd)
    salary_currency           VARCHAR(10) DEFAULT 'USD',
    salary_is_predicted       BOOLEAN DEFAULT FALSE,

    -- Profil du poste
    experience_level          VARCHAR(50),         -- 'EN','MI','SE','EX' ou équivalent texte
    years_of_experience        INTEGER,
    education_required          VARCHAR(50),
    employment_type             VARCHAR(20),         -- 'FT','PT','CT','FL'
    contract_time                VARCHAR(20),         -- 'full_time','part_time' (Adzuna)

    -- Travail à distance
    remote_ratio                 INTEGER,             -- 0 / 50 / 100 (style ds_salaries)
    is_remote_friendly             BOOLEAN,

    -- Entreprise / secteur
    company_size                   VARCHAR(20),
    industry                        VARCHAR(100),

    -- Indicateurs de marché (Kaggle ai_jobs uniquement)
    demand_score                     INTEGER,
    demand_growth_yoy_pct             NUMERIC(6,2),
    ai_salary_premium_pct              NUMERIC(6,2),
    benefits_score_10                   NUMERIC(4,2),
    is_llm_role                          BOOLEAN,
    salary_tier                           VARCHAR(50),

    -- Contenu brut
    description                            TEXT,
    required_skills_raw                     TEXT,    -- texte brut avant parsing dans job_skills

    -- Dates
    posted_date                              DATE,
    posting_year                              INTEGER,
    posting_month                             INTEGER,

    -- Métadonnées techniques
    created_at                                 TIMESTAMP DEFAULT NOW(),
    updated_at                                 TIMESTAMP DEFAULT NOW(),

    UNIQUE (external_id, source)
);

-- ------------------------------------------------------------
-- Table: job_skills
-- Table de relation N:N entre jobs et skills.
-- Remplie par l'ETL après extraction des compétences depuis
-- `required_skills_raw` (Kaggle) ou `description` (Adzuna, NLP léger).
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS job_skills (
    job_id          INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
    skill_id        INTEGER REFERENCES skills(id) ON DELETE CASCADE,

    PRIMARY KEY (job_id, skill_id)
);

-- ------------------------------------------------------------
-- Index utiles pour les requêtes analytiques fréquentes
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_jobs_country       ON jobs(country_id);
CREATE INDEX IF NOT EXISTS idx_jobs_source         ON jobs(source);
CREATE INDEX IF NOT EXISTS idx_jobs_posted_date     ON jobs(posted_date);
CREATE INDEX IF NOT EXISTS idx_jobs_job_title        ON jobs(job_title);
CREATE INDEX IF NOT EXISTS idx_job_skills_skill        ON job_skills(skill_id);