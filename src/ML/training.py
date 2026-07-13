"""
Entraînement du modèle de prédiction de salaire - Random Forest
Career Advisor Platform
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.model_selection import train_test_split, RandomizedSearchCV
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor


# ============================================================
# 1. EXTRACTION DES DONNÉES DEPUIS POSTGRESQL
# ============================================================

load_dotenv()

engine = create_engine(
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}",
    connect_args={"client_encoding": "latin1"}
)

query = """
SELECT 
    j.id,
    j.job_title,
    j.salary_avg,
    j.experience_level,
    j.years_of_experience,
    j.is_remote_friendly,
    j.job_category,
    j.employment_type,
    j.company_size,
    j.industry,
    c.name AS country,
    STRING_AGG(s.name, ',') AS skills
FROM jobs j
JOIN countries c ON j.country_id = c.id
LEFT JOIN job_skills js ON j.id = js.job_id
LEFT JOIN skills s ON js.skill_id = s.id
WHERE j.salary_avg IS NOT NULL AND j.salary_avg > 0
GROUP BY j.id, j.job_title, j.salary_avg, j.experience_level, 
         j.years_of_experience, j.is_remote_friendly, j.job_category,
         j.employment_type, j.company_size, j.industry, c.name
"""

df = pd.read_sql(query, engine)
print(f"Données extraites : {df.shape}")


# ============================================================
# 2. NETTOYAGE
# ============================================================

df = df.dropna(subset=['salary_avg'])
df = df[(df['salary_avg'] > 5000) & (df['salary_avg'] < 500000)]

# Regrouper les titres rares
title_counts = df['job_title'].value_counts()
rare_titles = title_counts[title_counts < 10].index
df['job_title'] = df['job_title'].apply(lambda x: 'Other' if x in rare_titles else x)

print(f"Données après nettoyage : {df.shape}")


# ============================================================
# 3. FEATURE ENGINEERING
# ============================================================

# Colonnes catégorielles utilisées pour l'encodage
CATEGORICAL_COLS = [
    'job_title', 'country', 'experience_level',
    'is_remote_friendly', 'job_category', 'employment_type',
    'company_size', 'industry'
]

# Skills : one-hot encoding multi-label
df['skills'] = df['skills'].fillna('')
df['skills_list'] = df['skills'].apply(lambda x: [s.strip() for s in x.split(',') if s.strip()])

mlb = MultiLabelBinarizer()
skills_encoded = pd.DataFrame(
    mlb.fit_transform(df['skills_list']),
    columns=[f"skill_{c}" for c in mlb.classes_],
    index=df.index
)

# Variables catégorielles
df_encoded = pd.get_dummies(df[CATEGORICAL_COLS], drop_first=False)

# Variable numérique
numeric_features = df[['years_of_experience']]

# Fusion finale
X = pd.concat([df_encoded, numeric_features, skills_encoded], axis=1)
y = np.log1p(df['salary_avg'])

print(f"Nombre de features : {X.shape[1]}")


# ============================================================
# 4. SPLIT TRAIN/TEST
# ============================================================

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)


# ============================================================
# 5. OPTIMISATION DES HYPERPARAMÈTRES
# ============================================================

param_grid = {
    'n_estimators': [200, 300, 500],
    'max_depth': [10, 15, 20, None],
    'min_samples_split': [2, 5, 10],
    'min_samples_leaf': [1, 2, 4],
    'max_features': ['sqrt', 'log2']
}

search = RandomizedSearchCV(
    RandomForestRegressor(random_state=42, n_jobs=-1),
    param_distributions=param_grid,
    n_iter=20,
    cv=5,
    scoring='neg_mean_absolute_error',
    random_state=42,
    n_jobs=-1,
    verbose=1
)

search.fit(X_train, y_train)
print(f"\nMeilleurs paramètres : {search.best_params_}")

model = search.best_estimator_


# ============================================================
# 6. ÉVALUATION
# ============================================================

y_pred = np.expm1(model.predict(X_test))
y_test_orig = np.expm1(y_test)

mae = mean_absolute_error(y_test_orig, y_pred)
rmse = np.sqrt(mean_squared_error(y_test_orig, y_pred))
r2 = r2_score(y_test_orig, y_pred)

print(f"\n--- Performance du modèle ---")
print(f"MAE  : {mae:.2f}")
print(f"RMSE : {rmse:.2f}")
print(f"R²   : {r2:.3f}")

# ============================================================
# 6bis. COMPARAISON AVEC UNE BASELINE (RÉGRESSION LINÉAIRE)
# ============================================================

from sklearn.linear_model import LinearRegression

baseline = LinearRegression()
baseline.fit(X_train, y_train)
baseline_pred = np.expm1(baseline.predict(X_test))

baseline_mae = mean_absolute_error(y_test_orig, baseline_pred)
baseline_r2 = r2_score(y_test_orig, baseline_pred)

print(f"\n--- Baseline (Régression Linéaire) ---")
print(f"MAE  : {baseline_mae:.2f}")
print(f"R²   : {baseline_r2:.3f}")

xgb_param_grid = {
    'n_estimators': [200, 300, 500],
    'max_depth': [4, 6, 8],
    'learning_rate': [0.01, 0.05, 0.1],
    'subsample': [0.7, 0.8, 0.9],
    'colsample_bytree': [0.7, 0.8, 1.0],
    'min_child_weight': [1, 3, 5]
}

xgb_search = RandomizedSearchCV(
    XGBRegressor(random_state=42, n_jobs=-1, objective='reg:squarederror'),
    param_distributions=xgb_param_grid,
    n_iter=20,
    cv=5,
    scoring='neg_mean_absolute_error',
    random_state=42,
    n_jobs=-1,
    verbose=1
)

xgb_search.fit(X_train, y_train)
best_xgb = xgb_search.best_estimator_

xgb_pred = best_xgb.predict(X_test)
xgb_pred_real = np.expm1(xgb_pred)
y_test_real = np.expm1(y_test)

print(f"\n--- XGBoost Optimisé ---")
print(f"Meilleurs paramètres : {xgb_search.best_params_}")
print(f"MAE réel  : {mean_absolute_error(y_test_real, xgb_pred_real):.2f}")
print(f"R² log    : {r2_score(y_test, xgb_pred):.3f}")
print(f"RMSE réel : {np.sqrt(mean_squared_error(y_test_real, xgb_pred_real)):.2f}")
print(f"R² réel   : {r2_score(y_test_real, xgb_pred_real):.3f}")
# ============================================================
# 7. IMPORTANCE DES FEATURES
# ============================================================

importances = pd.Series(model.feature_importances_, index=X.columns)
top20 = importances.sort_values(ascending=False).head(20)

top20.plot(kind='barh', figsize=(8, 8))
plt.gca().invert_yaxis()
plt.title("Top 20 features les plus importantes")
plt.tight_layout()
plt.savefig('feature_importance.png')
plt.show()

# Garder seulement les 30 features les plus importantes
top_features = importances.sort_values(ascending=False).head(30).index.tolist()
X_reduced = X[top_features]

X_train_r, X_test_r, y_train_r, y_test_r = train_test_split(
    X_reduced, y, test_size=0.2, random_state=42
)

model_reduced = RandomForestRegressor(
    **search.best_params_, random_state=42, n_jobs=-1
)
model_reduced.fit(X_train_r, y_train_r)
y_pred_r = np.expm1(model_reduced.predict(X_test_r))
y_test_r_orig = np.expm1(y_test_r)

print(f"\n--- Modèle réduit (30 features) ---")
print(f"MAE  : {mean_absolute_error(y_test_r_orig, y_pred_r):.2f}")
print(f"R²   : {r2_score(y_test_r_orig, y_pred_r):.3f}")


# ============================================================
# 8. SAUVEGARDE DU MODÈLE
# ============================================================

joblib.dump(best_xgb, 'salary_model.pkl')
joblib.dump(X.columns.tolist(), 'model_columns.pkl')
joblib.dump(mlb, 'skills_encoder.pkl')

print("\nModèle XGBoost optimisé sauvegardé : salary_model.pkl, model_columns.pkl, skills_encoder.pkl")


# ============================================================
# 9. FONCTION DE PRÉDICTION RÉUTILISABLE
# ============================================================

def predict_salary(job_title, country, experience_level, years_of_experience,
                    is_remote_friendly, job_category, employment_type,
                    company_size, industry, skills_list):
    model = joblib.load('salary_model.pkl')
    columns = joblib.load('model_columns.pkl')
    mlb = joblib.load('skills_encoder.pkl')

    # Filtrer les skills inconnues avant la transformation
    known_skills = [s for s in skills_list if s in mlb.classes_]
    if not known_skills:
        known_skills = []
    skills_encoded = pd.DataFrame(
        mlb.transform([known_skills]),
        columns=[f"skill_{c}" for c in mlb.classes_]
    )

    input_row = pd.DataFrame(columns=columns)
    input_row.loc[0] = 0

    categorical_values = {
        'job_title': job_title,
        'country': country,
        'experience_level': experience_level,
        'is_remote_friendly': is_remote_friendly,
        'job_category': job_category,
        'employment_type': employment_type,
        'company_size': company_size,
        'industry': industry,
    }

    for col, val in categorical_values.items():
        col_name = f"{col}_{val}"
        if col_name in input_row.columns:
            input_row[col_name] = 1

    if 'years_of_experience' in input_row.columns:
        input_row['years_of_experience'] = years_of_experience

    for col in skills_encoded.columns:
        if col in input_row.columns:
            input_row[col] = skills_encoded[col].values[0]

    input_row = input_row.fillna(0)
    prediction = np.expm1(model.predict(input_row)[0])
    return round(prediction, 2)


# ============================================================
# 10. TEST DE LA FONCTION
# ============================================================

if __name__ == "__main__":
    salary = predict_salary(
        job_title="Data Scientist",
        country="France",
        experience_level="Senior",
        years_of_experience=5,
        is_remote_friendly=True,
        job_category="Data Science",
        employment_type="Full-time",
        company_size="Large",
        industry="Finance",
        skills_list=["Python", "SQL", "AWS"]
    )
    print(f"\nSalaire estimé : {salary} €")