import sqlite3
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"
OUTPUT_DIR = PROJECT_ROOT / "output"
REPORTS_DIR = PROJECT_ROOT / "reports"

CLUSTER_NAMES_MAP = {
    0: "High-Quality Compounders",
    1: "Defensive Dividend Payers",
    2: "Value Cyclicals",
    3: "Distressed or Turnaround",
    4: "Emerging Growth",
}


def run_clustering_and_analytics():
    """Runs KMeans clustering (k=5), generates elbow plot, cluster labels,

    correlation heatmap, outlier detection, and portfolio percentile stats.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH))

    # Fetch 92 unique companies with sector info and latest financial ratios
    query = """
        SELECT fr.company_id, c.company_name, s.broad_sector, s.sub_sector,
               fr.return_on_equity_pct, fr.debt_to_equity, fr.revenue_cagr_5yr,
               fr.pat_cagr_5yr, fr.operating_profit_margin_pct, fr.net_profit_margin_pct,
               fr.return_on_capital_employed_pct, fr.interest_coverage, fr.asset_turnover,
               fr.free_cash_flow_cr, fr.pe_ratio, fr.pb_ratio, fr.composite_quality_score
        FROM financial_ratios fr
        JOIN companies c ON fr.company_id = c.id
        LEFT JOIN sectors s ON c.id = s.company_id
        WHERE fr.year = (SELECT MAX(year) FROM financial_ratios)
        ORDER BY c.company_name ASC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    # Drop duplicate company_ids if any to guarantee 92 companies
    df = df.drop_duplicates(subset=["company_id"]).reset_index(drop=True)

    # 5 Key Features for KMeans
    feature_cols = [
        "return_on_equity_pct",
        "debt_to_equity",
        "revenue_cagr_5yr",
        "pat_cagr_5yr",  # proxy for FCF/PAT growth
        "operating_profit_margin_pct",
    ]

    # Impute missing values with sector median (or global median fallback)
    features_df = df[feature_cols].copy()
    for col in feature_cols:
        features_df[col] = df.groupby("broad_sector")[col].transform(
            lambda x: x.fillna(x.median())
        )
        features_df[col] = features_df[col].fillna(df[col].median()).fillna(0.0)

    # 1. Generate Elbow Plot (k = 2 to 10)
    inertias = []
    k_range = range(2, 11)
    for k in k_range:
        scaler_temp = StandardScaler()
        scaled_temp = scaler_temp.fit_transform(features_df)
        km_temp = KMeans(n_clusters=k, random_state=42, n_init=10)
        km_temp.fit(scaled_temp)
        inertias.append(km_temp.inertia_)

    elbow_path = REPORTS_DIR / "elbow_plot.png"
    plt.figure(figsize=(7, 4), dpi=150)
    plt.plot(k_range, inertias, "bo-", linewidth=2, markersize=7)
    plt.xlabel("Number of Clusters (k)", fontsize=10)
    plt.ylabel("Inertia / Within-Cluster Sum of Squares", fontsize=10)
    plt.title("KMeans Elbow Plot for Nifty 100 Financial Clustering", fontsize=12)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.savefig(elbow_path)
    plt.close()
    print(f"✅ Generated Elbow Plot: {elbow_path.name}")

    # 2. KMeans Clustering with k=5
    scaler = StandardScaler()
    scaled_matrix = scaler.fit_transform(features_df)

    kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(scaled_matrix)
    centroids = kmeans.cluster_centers_

    # Calculate Euclidean distance from centroid
    distances = np.linalg.norm(scaled_matrix - centroids[cluster_labels], axis=1)

    # Assign descriptive cluster names based on cluster profiles
    cluster_profiles = {}
    for cid in range(5):
        mask = cluster_labels == cid
        mean_roe = features_df.loc[mask, "return_on_equity_pct"].mean()
        mean_de = features_df.loc[mask, "debt_to_equity"].mean()
        mean_growth = features_df.loc[mask, "revenue_cagr_5yr"].mean()
        cluster_profiles[cid] = (mean_roe, mean_de, mean_growth)

    # Sort cluster IDs by ROE / quality to assign descriptive names predictably
    sorted_clusters = sorted(
        cluster_profiles.keys(), key=lambda c: cluster_profiles[c][0], reverse=True
    )
    name_assignment = {
        sorted_clusters[0]: "High-Quality Compounders",
        sorted_clusters[1]: "Emerging Growth",
        sorted_clusters[2]: "Defensive Dividend Payers",
        sorted_clusters[3]: "Value Cyclicals",
        sorted_clusters[4]: "Distressed or Turnaround",
    }

    df["cluster_id"] = cluster_labels
    df["cluster_name"] = df["cluster_id"].map(name_assignment)
    df["distance_from_centroid"] = np.round(distances, 4)

    # Export output/cluster_labels.csv
    cluster_csv = OUTPUT_DIR / "cluster_labels.csv"
    cluster_out = df[
        [
            "company_id",
            "company_name",
            "broad_sector",
            "cluster_id",
            "cluster_name",
            "distance_from_centroid",
        ]
    ]
    cluster_out.to_csv(cluster_csv, index=False)
    print(f"✅ Exported {len(cluster_out)} companies to {cluster_csv.name}")

    # 3. Pearson Correlation Heatmap of 10 KPIs
    kpi_cols = [
        "return_on_equity_pct",
        "return_on_capital_employed_pct",
        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "debt_to_equity",
        "revenue_cagr_5yr",
        "pat_cagr_5yr",
        "interest_coverage",
        "asset_turnover",
        "free_cash_flow_cr",
    ]
    kpi_labels = [
        "ROE",
        "ROCE",
        "NPM",
        "OPM",
        "D/E",
        "Rev CAGR 5y",
        "PAT CAGR 5y",
        "ICR",
        "Asset Turn",
        "FCF",
    ]

    corr_df = df[kpi_cols].apply(pd.to_numeric, errors="coerce").corr()
    corr_df.columns = kpi_labels
    corr_df.index = kpi_labels

    heatmap_path = REPORTS_DIR / "correlation_heatmap.png"
    plt.figure(figsize=(9, 7), dpi=150)
    sns.heatmap(
        corr_df,
        annot=True,
        fmt=".2f",
        cmap="coolwarm",
        square=True,
        cbar_kws={"shrink": 0.8},
        linewidths=0.5,
    )
    plt.title("Nifty 100 Pearson Correlation Matrix (10 Core KPIs)", fontsize=12)
    plt.tight_layout()
    plt.savefig(heatmap_path)
    plt.close()
    print(f"✅ Generated Correlation Heatmap: {heatmap_path.name}")

    # 4. Outlier Detection: Z-Score per metric per broad_sector (|Z| > 3)
    outliers = []
    for col in kpi_cols:
        for sector_name, group in df.groupby("broad_sector"):
            vals = group[col].dropna()
            if len(vals) >= 3 and vals.std() > 0:
                z_scores = (vals - vals.mean()) / vals.std()
                for idx, z in z_scores.items():
                    if abs(z) > 3.0:
                        outliers.append(
                            {
                                "company_id": df.loc[idx, "company_id"],
                                "company_name": df.loc[idx, "company_name"],
                                "broad_sector": sector_name,
                                "metric": col,
                                "metric_value": round(df.loc[idx, col], 2),
                                "sector_mean": round(vals.mean(), 2),
                                "sector_std": round(vals.std(), 2),
                                "z_score": round(z, 2),
                            }
                        )

    outlier_df = pd.DataFrame(outliers)
    outlier_csv = OUTPUT_DIR / "outlier_report.csv"
    outlier_df.to_csv(outlier_csv, index=False)
    print(f"✅ Exported {len(outlier_df)} metric outliers to {outlier_csv.name}")

    # 5. Generate output/portfolio_stats.csv (P10, P25, P50, P75, P90, Mean, Std)
    stats = []
    for c_idx, col in enumerate(kpi_cols):
        s = df[col].dropna()
        if not s.empty:
            stats.append(
                {
                    "metric": kpi_labels[c_idx],
                    "raw_column": col,
                    "count": len(s),
                    "mean": round(s.mean(), 2),
                    "std": round(s.std(), 2),
                    "P10": round(s.quantile(0.10), 2),
                    "P25": round(s.quantile(0.25), 2),
                    "P50_median": round(s.quantile(0.50), 2),
                    "P75": round(s.quantile(0.75), 2),
                    "P90": round(s.quantile(0.90), 2),
                }
            )

    stats_df = pd.DataFrame(stats)
    stats_csv = OUTPUT_DIR / "portfolio_stats.csv"
    stats_df.to_csv(stats_csv, index=False)
    print(f"✅ Exported Portfolio Percentile Stats to {stats_csv.name}")

    return cluster_out, outlier_df, stats_df


if __name__ == "__main__":
    run_clustering_and_analytics()
