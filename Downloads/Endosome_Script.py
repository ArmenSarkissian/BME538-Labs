import numpy as np
import pandas as pd
import os
import matplotlib.pyplot as plt
import seaborn as sns
from collections import namedtuple, Counter
from numpy import linalg
from matplotlib import cm

from scipy.spatial import Voronoi, voronoi_plot_2d
from scipy.spatial import Delaunay, delaunay_plot_2d

# %% 2. Define Parameters:

PopStats = namedtuple("PopStats", ["mean", "stddev", "min_max_ratio", "disorder"])
PolyProps = namedtuple("PolyProps", ["area", "peri", "max_dist"])
TriProps = namedtuple("TriProps", ["sides", "area"])
DensityProps = namedtuple(
    "DensityProps", ["neighbors_in_distance", "distance_for_neighbors"]
)
Props = namedtuple("Props", ["voronoi", "delaunay", "mst_branches", "density"])

# %% 3. Define Functions Used:


def compute_global_cell_graph_features(
    centroids,
    neighbor_distances=None,
    neighbor_counts=(3, 5, 7),
):
    if neighbor_distances is None:
        neighbor_distances = 10.0 * np.arange(1, 6)
    return _flatten_to_dataframe(
        _compute_global_cell_graph_features(
            centroids,
            neighbor_distances,
            neighbor_counts,
        )
    )


def _compute_global_cell_graph_features(
    centroids,
    neighbor_distances,
    neighbor_counts,
):
    from scipy import sparse
    from scipy.sparse.csgraph import minimum_spanning_tree
    from scipy.spatial import Voronoi
    from scipy.spatial import cKDTree as KDTree
    from scipy.spatial.distance import pdist

    vor = Voronoi(centroids)
    centroids = vor.points
    vertices = vor.vertices

    regions = [r for r in vor.regions if r and -1 not in r]
    areas = np.array([_poly_area(vertices[r]) for r in regions])
    peris = np.array([_poly_peri(vertices[r]) for r in regions])
    max_dists = np.array([pdist(vertices[r]).max() for r in regions])
    poly_props = PolyProps._make(map(_pop_stats, (areas, peris, max_dists)))

    ridge_points = vor.ridge_points
    ridge_lengths = _dist(*np.swapaxes(centroids[ridge_points], 0, 1))
    sides = ridge_lengths

    tris = [[] for _ in vertices]
    for p, ri in enumerate(vor.point_region):
        for vi in vor.regions[ri]:
            if vi != -1:
                tris[vi].append(p)

    tris = [t for t in tris if len(t) == 3]
    tris = np.asarray(tris)

    areas = np.array([_poly_area(centroids[t]) for t in tris])
    tri_props = TriProps._make(map(_pop_stats, (sides, areas)))

    graph = sparse.coo_matrix(
        (ridge_lengths, np.sort(ridge_points).T), (len(centroids), len(centroids))
    )
    mst = minimum_spanning_tree(graph)

    mst_data = mst.data[mst.data != 0]
    mst_branches = _pop_stats(mst_data) if len(mst_data) > 0 else PopStats(0, 0, 0, 0)

    tree = KDTree(centroids)
    neighbors_in_distance = {
        r: _pop_stats(
            np.stack(np.array(list(map(len, tree.query_ball_tree(tree, r))))) - 1
        )
        for r in neighbor_distances
    }

    distance_for_neighbors = dict(
        zip(
            neighbor_counts,
            map(
                _pop_stats, tree.query(centroids, [c + 1 for c in neighbor_counts])[0].T
            ),
        )
    )
    density_props = DensityProps(neighbors_in_distance, distance_for_neighbors)

    return Props(poly_props, tri_props, mst_branches, density_props)


def _poly_area(vertices):
    return abs(_poly_signed_area(vertices))


def _poly_signed_area(vertices):
    return 0.5 * linalg.det(
        np.stack((vertices, np.roll(vertices, -1, axis=-2)), -1),
    ).sum(-1)


def _poly_peri(vertices):
    return _dist(vertices, np.roll(vertices, -1, axis=-2)).sum(-1)


def _dist(x, y):
    return (np.subtract(x, y) ** 2).sum(-1) ** 0.5


def _pop_stats(pop):
    while True:
        if len(pop) == 0:
            break
        mean = pop.mean()
        stddev = pop.std()
        mask = abs(pop - mean) <= 3 * stddev
        if mask.all():
            break
        pop = pop[mask]

    if len(pop) == 0:
        return PopStats(0, 0, 0, 0)

    minmaxr = pop.min() / pop.max() if pop.max() != 0 else 0.0
    disorder = stddev / (mean + stddev) if (mean + stddev) != 0 else 0.0

    return PopStats(mean, stddev, minmaxr, disorder)


def _flatten_to_dataframe(nt):
    from pandas import DataFrame

    return DataFrame(_flatten_to_dict(nt), index=[0])


def _flatten_to_dict(nt, prefix=""):
    result = {}
    if isinstance(nt, tuple):
        d = nt._asdict()
    else:
        d = {str(i): kv[1] for i, kv in enumerate(sorted(nt.items()))}

    for k, v in d.items():
        if not isinstance(v, (tuple, dict)):
            result[prefix + k] = v
        else:
            result.update(_flatten_to_dict(v, prefix + k + "_"))
    return result


# %% 4. Directories and Input Files

# INPUT: the raw (unfiltered) per-cell spatial feature concat file built by
# build_concat_spatial_group_features.py. This must NOT be the same path as
# filtered_concat_groups_path below -- this step reads the unfiltered file
# and writes a separate, filtered file.
sheet_directory = r"C:\Users\armen\Downloads\003_Concat_Spatial_Group_Features.xlsx"

concat_groups = pd.ExcelFile(sheet_directory, engine="openpyxl")

# Auto-discover the group sheets directly from the workbook, rather than
# assuming a fixed "Control"/"Thermal" naming scheme. This means the
# script will work no matter what your Condition labels actually are
# (e.g. temperatures like "35", "37", "45"...), as long as each sheet in
# 003_Concat_Spatial_Group_Features.xlsx corresponds to one
# Condition/Time_h group -- whatever that sheet happens to be named.
sheet_names = list(concat_groups.sheet_names)
print(f"Found {len(sheet_names)} group sheet(s) in {os.path.basename(sheet_directory)}:")
print("  " + ", ".join(sheet_names))

# %% 5. Correlation Matrix (GLOBAL -- pooled across every group)

# IMPORTANT: this runs ONE correlation test on all groups pooled together,
# rather than a separate test per sheet. This guarantees every temperature/
# time sheet keeps the exact same set of feature columns, so groups can be
# compared apples-to-apples. (The previous per-sheet approach let a feature
# get dropped in one group but kept in another, and intersecting 20
# independent local tests turned out to be far too aggressive -- see the
# analysis that motivated this change.)
#
# Trade-off to keep in mind: pooling everything means a temperature-driven
# shift in a feature's average value can make two otherwise-independent
# features look correlated just because they both drift with temperature
# together, not because they're truly redundant within any one condition.

correlation_matrices_directory = r"C:\Users\armen\Downloads\Spatial_analysis_output\Matrix"
os.makedirs(correlation_matrices_directory, exist_ok=True)

threshold = 0.8

# Pool every sheet's feature rows together into one big table.
all_sheet_frames = [concat_groups.parse(sheet) for sheet in sheet_names]
pooled_df = pd.concat(all_sheet_frames, ignore_index=True)

metadata_cols = list(pooled_df.columns[:4])
feature_cols = list(pooled_df.columns[4:])
pooled_data = pooled_df[feature_cols]

correlated_features = set()
correlation_matrix = pooled_data.corr()

for i in range(len(correlation_matrix.columns)):
    for j in range(i):
        if abs(correlation_matrix.iloc[i, j]) > threshold:
            col_name = correlation_matrix.columns[i]
            correlated_features.add(col_name)

remaining_cols = [c for c in feature_cols if c not in correlated_features]
global_keep_columns = metadata_cols + remaining_cols

print(f"\nGlobal correlation filtering @ threshold {threshold}: "
      f"keeping {len(remaining_cols)} of {len(feature_cols)} feature(s) across all groups.")
dropped_cols = [c for c in feature_cols if c not in remaining_cols]
if dropped_cols:
    print("Dropped (correlated globally): " + ", ".join(dropped_cols))

# One global heatmap of the surviving (non-redundant) features
plt.figure(figsize=(12, 10))
sns.heatmap(pooled_data[remaining_cols].corr(), annot=True, cmap="coolwarm", fmt=".2f")
plt.title(f"Global correlation matrix (all groups pooled) @ {threshold}")
plt.tight_layout()
plt.savefig(os.path.join(correlation_matrices_directory, f"GLOBAL_{threshold}.png"))
plt.close()

# Same global feature set is also plotted per group, so you can still see
# how correlation structure differs by temperature/time even though the
# final kept-feature list is now identical everywhere.
for sheet, df in zip(sheet_names, all_sheet_frames):
    if len(remaining_cols) < 2:
        continue
    plt.figure(figsize=(12, 10))
    sns.heatmap(df[remaining_cols].corr(), annot=True, cmap="coolwarm", fmt=".2f")
    plt.title(f"{sheet} @ {threshold} (global feature set)")
    plt.tight_layout()
    plt.savefig(os.path.join(correlation_matrices_directory, f"{sheet}_{threshold}.png"))
    plt.close()

# %% 6. Save Filtered Data

# OUTPUT of this step. Deliberately a different file from sheet_directory
# above (003_...) so this step never reads its own output as input.
filtered_concat_groups_path = (
    r"C:\Users\armen\Downloads\004_Concat_Spatial_Group_Features_Filtered.xlsx"
)

if not remaining_cols:
    raise RuntimeError(
        "The global correlation filter dropped every feature column -- there is "
        "nothing left to save. Double check the 'Global correlation filtering' "
        "line printed above; this usually means the threshold is too aggressive "
        "for how many features you have, or something upstream produced constant/"
        "duplicate columns."
    )

with pd.ExcelWriter(filtered_concat_groups_path, engine="openpyxl") as writer:
    for sheet, df in zip(sheet_names, all_sheet_frames):
        filtered_df = df[global_keep_columns]
        filtered_df.to_excel(writer, sheet_name=sheet, index=False)

print(f"Filtered file saved to: {filtered_concat_groups_path}")
print(f"Every sheet now has the same {len(global_keep_columns)} columns: "
      + ", ".join(global_keep_columns))

# %% 7-9 Setup remaining paths

file_path_2 = r"C:\Users\armen\Downloads\Master_Rescaled_Intensity_Data.xlsx"

output_folder = r"C:\Users\armen\Downloads\Spatial_analysis_output\Delaunay"
os.makedirs(output_folder, exist_ok=True)

# %% 10. Generate and Save Voronoi/Delaunay Plots

if os.path.exists(file_path_2):
    print("Intensity file found. Loading 'Rescaled_Intensity_Data' for plotting...")
    # Load specific sheet from your intensity file
    raw_df = pd.read_excel(file_path_2, sheet_name="Rescaled_Intensity_Data")

    # Cleaning column names of hidden whitespace
    raw_df.columns = [str(c).strip() for c in raw_df.columns]
    cols = raw_df.columns.tolist()

    # Normalize legacy "Control" condition label to its actual temperature
    # (37 C). "Control"/"Thermal" were old-experiment labels; every
    # condition is now tracked by temperature in Celsius, and Control
    # corresponds to 37C.
    if "Condition" in cols:
        is_control = raw_df["Condition"].astype(str).str.strip().str.lower() == "control"
        if is_control.any():
            print(f"Normalizing {is_control.sum()} 'Control' row(s) to Condition '37'.")
            raw_df.loc[is_control, "Condition"] = "37"

    # Coordinates found in your file
    x_col = "Pos_X_um"
    y_col = "Pos_Y_um"

    # Build the grouping label (e.g., 'Control' + '_' + '0.5' + 'h')
    # This ensures the raw data grouping matches your sheet_names exactly.
    #
    # IMPORTANT: Condition may come back from Excel as a float (e.g. 35.0)
    # rather than the string "35" -- Excel sometimes auto-detects
    # numeric-looking text and stores it as a number. str(35.0) == "35.0",
    # which would never match a sheet named "35_0h". So Condition gets the
    # same "strip trailing .0" treatment as Time_h before being combined.
    def _format_label(x):
        s = str(x).strip()
        if s.endswith(".0"):
            s = s[:-2]
        return s

    raw_df["Condition_Time"] = (
        raw_df["Condition"].apply(_format_label)
        + "_"
        + raw_df["Time_h"].apply(_format_label)
        + "h"
    )

    if x_col in cols and y_col in cols:
        print(f"Plotting using columns: {x_col}, {y_col}")
        for group in sheet_names:
            group_data = raw_df[raw_df["Condition_Time"] == group]

            if not group_data.empty:
                # Drop rows with empty coordinates for spatial math
                points = group_data[[x_col, y_col]].dropna().values

                # Spatial analysis requires at least 4 points
                if len(points) > 3:
                    # 1. Voronoi Plot
                    vor = Voronoi(points)
                    fig_vor = voronoi_plot_2d(
                        vor, show_vertices=False, line_colors="orange", point_size=1
                    )
                    plt.title(f"Voronoi: {group}")
                    plt.savefig(
                        os.path.join(output_folder, f"Voronoi_{group}.png"), dpi=300
                    )
                    plt.close()

                    # 2. Delaunay Plot
                    tri = Delaunay(points)
                    fig_tri = delaunay_plot_2d(tri)
                    plt.title(f"Delaunay: {group}")
                    plt.savefig(
                        os.path.join(output_folder, f"Delaunay_{group}.png"), dpi=300
                    )
                    plt.close()
                    print(f"Successfully saved Voronoi and Delaunay for: {group}")
                else:
                    print(f"Skipping {group}: Insufficient data points ({len(points)})")
            else:
                print(f"Notice: No raw data found matching the group label '{group}'")

        print(f"\nSUCCESS: Plots generated in {output_folder}")
    else:
        print(f"ERROR: Could not find columns {x_col} or {y_col} in the file.")
        print(f"Available columns: {cols}")
else:
    print(f"ERROR: Raw intensity file not found at {file_path_2}")
    
    
    #%% 8. Box Plots for Features

# Path to the filtered Excel file
filtered_concat_groups = r"C:\Users\armen\Downloads\004_Concat_Spatial_Group_Features_Filtered.xlsx"
excel_data = pd.read_excel(filtered_concat_groups, sheet_name=None)  # Read all sheets into a dictionary

# Directory to save the box plot images
box_plots_folder = r"C:\Users\armen\Downloads\Spatial_analysis_output\Boxplots"

# Create the folder if it doesn't exist
os.makedirs(box_plots_folder, exist_ok=True)

# Define the feature names
feature_names = [
    'voronoi_area_mean',
    'voronoi_area_min_max_ratio',
    'delaunay_sides_min_max_ratio',
    'delaunay_area_min_max_ratio',
    'delaunay_sides_mean',
    'delaunay_area_disorder',
    'delaunay_sides_disorder'
]

# Initialize a dictionary to hold the data for each feature across all sheets
feature_data = {feature: [] for feature in feature_names}
# Track which sheet actually contributed each entry in feature_data, so the
# x-tick labels always match the number of boxes plotted -- some sheets may
# be missing a given feature (e.g. it was dropped as constant/correlated
# for that particular temperature/time group), so this list can be shorter
# than the full set of sheet names.
feature_labels = {feature: [] for feature in feature_names}

# Iterate over each sheet and extract the data for each feature
for sheet_name, df in excel_data.items():
    print(f"Processing sheet: {sheet_name}")
    
    try:
        # Drop the first four columns (indexing starts from 0)
        df_filtered = df.drop(columns=df.columns[:4])

        # Ensure the DataFrame is not empty after dropping the columns
        if df_filtered.empty:
            print(f"Warning: Sheet {sheet_name} is empty after dropping the first four columns.")
            continue
        
        # For each feature, collect the data across all sheets
        for feature in feature_names:
            if feature in df_filtered.columns:
                feature_data[feature].append(df_filtered[feature].dropna())
                feature_labels[feature].append(sheet_name)
            else:
                print(f"  Note: '{feature}' not present in sheet {sheet_name} -- skipping it for this feature's box plot.")

    except Exception as e:
        print(f"Error processing sheet {sheet_name}: {e}")

# Now create a separate box plot for each feature
for feature, data in feature_data.items():
    if not data:
        print(f"Skipping box plot for {feature} -- no sheet had this column.")
        continue

    plt.figure(figsize=(10, 6))

    # Create a viridis colormap instance
    cmap = cm.viridis

    # Create box plots for each sheet (each item in 'data' corresponds to one sheet)
    box = plt.boxplot(data, patch_artist=True)
    
    # Assign colors from the viridis colormap to the boxes
    for patch, color in zip(box['boxes'], cmap(np.linspace(0, 1, len(data)))):
        patch.set_facecolor(color)  # Set color for each box plot

    plt.title(f'Box Plot of {feature}')
    # Use only the sheet names that actually contributed data for THIS
    # feature (feature_labels[feature]), not the full excel_data.keys() --
    # those can differ in count if some sheets were missing this column.
    plt.xticks(range(1, len(data) + 1), feature_labels[feature], rotation=45)
    plt.ylabel('Value')

    # Comment out for linear
    if feature == 'voronoi_area_mean':
        plt.yscale('log')  # Set logarithmic scale for the y-axis
    if feature == 'voronoi_area_min_max_ratio':
        plt.yscale('log')  # Set logarithmic scale for the y-axis
    if feature == 'delaunay_sides_min_max_ratio':
        plt.yscale('log')  # Set logarithmic scale for the y-axis
    if feature == 'delaunay_area_min_max_ratio':
        plt.yscale('log')  # Set logarithmic scale for the y-axis
    # if feature == 'delaunay_sides_mean':
    #     plt.yscale('log')  # Set logarithmic scale for the y-axis
    if feature == 'delaunay_area_disorder':
        plt.yscale('log')  # Set logarithmic scale for the y-axis
    if feature == 'delaunay_sides_disorder':
        plt.yscale('log')  # Set logarithmic scale for the y-axis

    
    # Save the plot as a PNG file
    box_plot_path = os.path.join(box_plots_folder, f'{feature}_boxplot.png')
    plt.savefig(box_plot_path)
    plt.close()
    print(f"Box plot saved for {feature} at {box_plot_path}")

print("All box plots saved successfully.")