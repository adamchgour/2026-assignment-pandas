"""Plotting referendum results in pandas.

In short, we want to make beautiful map to report results of a referendum. In
some way, we would like to depict results with something similar to the maps
that you can find here:
https://github.com/x-datascience-datacamp/datacamp-assignment-pandas/blob/main/example_map.png

To do that, you will load the data as pandas.DataFrame, merge the info and
aggregate them by regions and finally plot them on a map using `geopandas`.
"""
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt


def load_data():
    """Load data from the CSV files referundum/regions/departments."""
    referendum = pd.read_csv(
        "referendum.csv",
        sep=";",
        dtype={"department code": str, "Town code": str},
    )
    regions = pd.read_csv(
        "regions.csv",
        dtype={"code": str},
    )
    departments = pd.read_csv(
        "departments.csv",
        dtype={"region_code": str, "code": str},
    )

    return referendum, regions, departments


def merge_regions_and_departments(regions, departments):
    """Merge regions and departments into one DataFrame."""
    regions = regions.rename(
        columns={"code": "code_reg", "name": "name_reg"}
    )
    departments = departments.rename(
        columns={
            "region_code": "code_reg",
            "code": "code_dep",
            "name": "name_dep",
        }
    )

    return regions[["code_reg", "name_reg"]].merge(
        departments[["code_reg", "code_dep", "name_dep"]],
        on="code_reg",
        validate="one_to_many",
    )


def merge_referendum_and_areas(referendum, regions_and_departments):
    """Merge referendum results with their departments and regions."""
    referendum = referendum.rename(
        columns={"department code": "code_dep"}
    )
    referendum = referendum.loc[
        ~referendum["code_dep"].str.contains("Z", na=False)
    ].copy()

    return referendum.merge(
        regions_and_departments,
        on="code_dep",
        validate="many_to_one",
    )


def compute_referendum_result_by_regions(referendum_and_areas):
    """Return absolute counts for each region."""
    counts = ["Registered", "Abstentions", "Null", "Choice A", "Choice B"]

    grouped = referendum_and_areas.groupby("code_reg")
    names = grouped["name_reg"].first()
    totals = grouped[counts].sum()

    return names.to_frame().join(totals)


def plot_referendum_map(referendum_result_by_regions):
    """Plot Choice A as a proportion of expressed ballots."""
    regions = gpd.read_file("regions.geojson")
    regions = regions.rename(columns={"code": "code_reg"})

    results = regions.merge(
        referendum_result_by_regions,
        left_on="code_reg",
        right_index=True,
        how="inner",
        validate="one_to_one",
    )

    expressed = results["Choice A"] + results["Choice B"]
    results["ratio"] = results["Choice A"] / expressed.where(expressed != 0)

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
