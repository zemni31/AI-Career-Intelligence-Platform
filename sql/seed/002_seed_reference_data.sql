-- ============================================================
-- Seed: countries
-- Pays couverts par les sources de données (Adzuna + Kaggle).
-- À exécuter une seule fois après la création des tables.
-- ============================================================

INSERT INTO countries (code, name, continent) VALUES
    ('FR', 'France',          'Europe'),
    ('GB', 'United Kingdom',  'Europe'),
    ('US', 'United States',   'North America'),
    ('DE', 'Germany',         'Europe'),
    ('NL', 'Netherlands',     'Europe'),
    ('CA', 'Canada',          'North America'),
    ('IN', 'India',           'Asia'),
    ('AU', 'Australia',       'Oceania'),
    ('ES', 'Spain',           'Europe'),
    ('IT', 'Italy',           'Europe'),
    ('PL', 'Poland',          'Europe'),
    ('SG', 'Singapore',       'Asia'),
    ('JP', 'Japan',           'Asia'),
    ('BR', 'Brazil',          'South America')
ON CONFLICT (code) DO NOTHING;

-- ============================================================
-- Seed: skills (compétences les plus courantes en Data/IA)
-- Liste de départ ; l'ETL pourra en ajouter automatiquement
-- d'autres au fil des offres traitées.
-- ============================================================

INSERT INTO skills (name, category) VALUES
    ('Python',          'Langage'),
    ('SQL',              'Langage'),
    ('R',                 'Langage'),
    ('Java',               'Langage'),
    ('Scala',                'Langage'),
    ('AWS',                    'Cloud'),
    ('Azure',                   'Cloud'),
    ('GCP',                       'Cloud'),
    ('Docker',                      'DevOps'),
    ('Kubernetes',                    'DevOps'),
    ('Power BI',                        'BI Tool'),
    ('Tableau',                           'BI Tool'),
    ('Excel',                               'BI Tool'),
    ('TensorFlow',                            'ML Framework'),
    ('PyTorch',                                 'ML Framework'),
    ('Scikit-learn',                              'ML Framework'),
    ('Pandas',                                      'Librairie'),
    ('NumPy',                                         'Librairie'),
    ('Spark',                                           'Big Data'),
    ('Hadoop',                                            'Big Data'),
    ('NLP',                                                 'Domaine ML'),
    ('Computer Vision',                                        'Domaine ML'),
    ('LLM',                                                      'Domaine ML'),
    ('LangChain',                                                  'ML Framework'),
    ('Hugging Face',                                                 'ML Framework'),
    ('Git',                                                            'Outil'),
    ('Airflow',                                                          'Outil')
ON CONFLICT (name) DO NOTHING;