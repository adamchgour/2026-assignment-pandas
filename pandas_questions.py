from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd


def find_data_file(filename):
    """Find a data file relative to this script."""
    root = Path(__file__).resolve().parent
    matches = sorted(root.rglob(filename))

    if not matches:
        raise FileNotFoundError(
            f"Fichier {filename!r} introuvable dans {root}."
        )
    if len(matches) > 1:
        raise ValueError(
            f"Plusieurs fichiers {filename!r} trouvés : {matches}"
        )

    return matches[0]


def normalize_codes(series):
    """Normalize codes while preserving Corsican department codes."""
    return (
        series.astype("string")
        .str.strip()
        .str.upper()
        .str.zfill(2)
    )


def load_data():
    """Load referendum, regions, and departments CSV files."""
    referendum = pd.read_csv(
        find_data_file("referendum.csv"),
        sep=";",
        dtype={"Department code": str, "Town code": str},
    )
    regions = pd.read_csv(
        find_data_file("regions.csv"),
        dtype={"code": str},
    )
    departments = pd.read_csv(
        find_data_file("departments.csv"),
        dtype={"region_code": str, "code": str},
    )

    return referendum, regions, departments


def merge_regions_and_departments(regions, departments):
    """Merge regions and departments into one DataFrame."""
    regions = regions.rename(
        columns={"code": "code_reg", "name": "name_reg"}
    ).copy()

    departments = departments.rename(
        columns={
            "region_code": "code_reg",
            "code": "code_dep",
            "name": "name_dep",
        }
    ).copy()

    regions["code_reg"] = normalize_codes(regions["code_reg"])
    departments["code_reg"] = normalize_codes(departments["code_reg"])
    departments["code_dep"] = normalize_codes(departments["code_dep"])

    return regions[["code_reg", "name_reg"]].merge(
        departments[["code_reg", "code_dep", "name_dep"]],
        on="code_reg",
        validate="one_to_many",
    )


def merge_referendum_and_areas(referendum, regions_and_departments):
    """Merge referendum results with departments and regions."""
    referendum = referendum.copy()
    areas = regions_and_departments.copy()

    # Keep the original column, as required by the tests.
    referendum["Department code"] = normalize_codes(
        referendum["Department code"]
    )
    areas["code_dep"] = normalize_codes(areas["code_dep"])

    referendum = referendum.loc[
        ~referendum["Department code"].str.contains("Z", na=False)
    ].copy()

    return referendum.merge(
        areas,
        left_on="Department code",
        right_on="code_dep",
        validate="many_to_one",
    )


def compute_referendum_result_by_regions(referendum_and_areas):
    """Return absolute counts for each region, indexed by code_reg."""
    counts = [
        "Registered",
        "Abstentions",
        "Null",
        "Choice A",
        "Choice B",
    ]

    grouped = referendum_and_areas.groupby("code_reg")
    names = grouped["name_reg"].first()
    totals = grouped[counts].sum()

    return names.to_frame().join(totals)


def plot_referendum_map(referendum_result_by_regions):
    """Plot Choice A as a proportion of expressed ballots."""
    regions = gpd.read_file(find_data_file("regions.geojson"))
    regions = regions.rename(columns={"code": "code_reg"})
    regions["code_reg"] = normalize_codes(regions["code_reg"])

    results = referendum_result_by_regions.copy()
    results.index = normalize_codes(results.index.to_series()).array
    results.index.name = "code_reg"

    results = regions.merge(
        results,
        left_on="code_reg",
        right_index=True,
        how="inner",
        validate="one_to_one",
    )

    expressed = results["Choice A"] + results["Choice B"]
    results["ratio"] = (
        results["Choice A"] / expressed.where(expressed != 0)
    )

    ax = results.plot(
        column="ratio",
        cmap="RdYlGn",
        vmin=0,
        vmax=1,
        legend=True,
        edgecolor="white",
        linewidth=0.6,
        figsize=(10, 10),
        legend_kwds={"label": "Choice A / expressed ballots"},
        missing_kwds={"color": "lightgrey"},
    )
    ax.set_title("Referendum results by region")
    ax.set_axis_off()

    return results


if __name__ == "__main__":
    referendum, df_reg, df_dep = load_data()

    regions_and_departments = merge_regions_and_departments(
        df_reg, df_dep
    )
    referendum_and_areas = merge_referendum_and_areas(
        referendum, regions_and_departments
    )
    referendum_results = compute_referendum_result_by_regions(
        referendum_and_areas
    )

    print(referendum_results)
    plot_referendum_map(referendum_results)
    plt.show()
