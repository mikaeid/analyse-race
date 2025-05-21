import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm as cm
from datetime import datetime
from PIL import Image
import os
from streamlit_cropper import st_cropper
import numpy as np

st.title("Sailboat Performance & Trim Visualizer")

# Upload data file
data_file = st.file_uploader("Upload .tsv performance data", type="tsv")
if data_file:
    df = pd.read_csv(data_file, sep="\\t")

    # Combine date and time into a timestamp
    df["timestamp"] = pd.to_datetime(df["dd/mm/yy"] + " " + df["hhmmss"], format="%d/%m/%Y %H:%M:%S")

    # Drop NaNs for relevant columns
    df = df.dropna(subset=["Lat", "Lon", "Vs_perf%"])

    # Sidebar options
    st.sidebar.subheader("Performance Filter and Options")
    show_wind = st.sidebar.checkbox("Show TWA Arrows", value=False)
    vs_min = st.sidebar.slider("Minimum Vs_perf%", float(df["Vs_perf%"].min()), float(df["Vs_perf%"].max()), float(df["Vs_perf%"].min()))
    vs_max = st.sidebar.slider("Maximum Vs_perf%", float(df["Vs_perf%"].min()), float(df["Vs_perf%"].max()), float(df["Vs_perf%"].max()))
    df_filtered = df[(df["Vs_perf%"] >= vs_min) & (df["Vs_perf%"] <= vs_max)]

    # Plot course with Vs_perf% as color and a slider
    st.subheader("Boat Course Colored by Vs_perf% + Data Point Slider")

    if not df_filtered.empty:
        idx = st.slider("Select data point index", min_value=0, max_value=len(df_filtered) - 1, value=0, step=1)

        fig, ax = plt.subplots(figsize=(10, 6))

        # Custom colormap centered on 100% performance
        class MidpointNormalize(mcolors.Normalize):
            def __init__(self, vmin=None, vmax=None, midpoint=None, clip=False):
                self.midpoint = midpoint
                super().__init__(vmin, vmax, clip)

            def __call__(self, value, clip=None):
                result, is_scalar = self.process_value(value)
                vmin, vmax, midpoint = self.vmin, self.vmax, self.midpoint
                result = np.ma.masked_array((result - vmin) / (vmax - vmin))
                result = np.ma.masked_array(np.where(
                    result <= (midpoint - vmin) / (vmax - vmin),
                    0.5 * result / ((midpoint - vmin) / (vmax - vmin)),
                    0.5 + 0.5 * (result - (midpoint - vmin) / (vmax - vmin)) / ((vmax - midpoint) / (vmax - vmin))
                ))
                return result

        vmin = df["Vs_perf%"].min()
        vmax = df["Vs_perf%"].max()
        midpoint = 100
        cmap = cm.get_cmap("RdYlGn")
        norm = MidpointNormalize(vmin=vmin, vmax=vmax, midpoint=midpoint)

        sc = ax.scatter(df_filtered["Lon"], df_filtered["Lat"], c=df_filtered["Vs_perf%"], cmap=cmap, norm=norm, s=10, alpha=0.6)
        ax.plot(df_filtered["Lon"], df_filtered["Lat"], color="gray", alpha=0.2, linewidth=0.5)

        selected = df_filtered.iloc[idx]
        ax.scatter(selected["Lon"], selected["Lat"], color="blue", s=50, label=f"Index {idx}")
        ax.legend()

        cbar = fig.colorbar(sc, ax=ax, label="Vs_perf%")

        if show_wind:
            for _, row in df_filtered.iterrows():
                dx = 0.002 * np.cos(np.radians(row["TWA"]))
                dy = 0.002 * np.sin(np.radians(row["TWA"]))
                ax.arrow(row["Lon"], row["Lat"], dx, dy, head_width=0.0005, head_length=0.0005, fc='black', ec='black', alpha=0.4)

        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.set_title("Boat Track with Performance Color Map & Wind")
        st.pyplot(fig)

        # Show details of selected point
        st.markdown("### Selected Data Point")
        st.write(f"**Timestamp**: {selected['timestamp']}")
        st.write(f"**Boat Speed**: {selected['BSP']} kn")
        st.write(f"**Heel**: {selected['Heel']}°")
        st.write(f"**Wind Angle (TWA)**: {selected['TWA']}°")
        st.write(f"**Wind Speed (TWS)**: {selected['TWS']} kn")
        st.write(f"**Vs_perf%**: {selected['Vs_perf%']}%")

# Upload images
image_files = st.file_uploader("Upload trim images (filename format: trim_YYYY-MM-DD_HH-MM-SS.jpg)", 
                                type=["jpg", "jpeg", "png"], accept_multiple_files=True)

def extract_timestamp_from_filename(filename):
    try:
        base = os.path.splitext(filename)[0]
        dt_str = base.split("_")[-2] + "_" + base.split("_")[-1]
        return datetime.strptime(dt_str, "%Y-%m-%d_%H-%M-%S")
    except:
        return None

if data_file and image_files:
    st.subheader("Trim Images Matched to Closest Data Point + Cropping & Transforming")

    # Aspect ratio selector
    aspect_option = st.selectbox(
        "Select crop aspect ratio",
        options=["Free", "1:1", "4:3", "16:9"],
        index=0
    )

    aspect_ratio = None
    if aspect_option == "1:1":
        aspect_ratio = (1, 1)
    elif aspect_option == "4:3":
        aspect_ratio = (4, 3)
    elif aspect_option == "16:9":
        aspect_ratio = (16, 9)

    for img_file in image_files:
        timestamp = extract_timestamp_from_filename(img_file.name)
        if timestamp:
            idx = (df["timestamp"] - timestamp).abs().idxmin()
            row = df.loc[idx]

            st.markdown(f"#### Original Image: {img_file.name}")
            image = Image.open(img_file)
            cropped_image = st_cropper(image, box_color='blue', aspect_ratio=aspect_ratio)
            st.image(cropped_image, caption="Cropped Image")

            st.markdown("### Transform Cropped Image")
            rotate_degrees = st.slider("Rotate image (degrees)", -180, 180, 0)
            scale_x = st.slider("Scale X (width)", 0.1, 3.0, 1.0)
            scale_y = st.slider("Scale Y (height)", 0.1, 3.0, 1.0)

            transformed = cropped_image.rotate(rotate_degrees, expand=True)
            new_size = (int(transformed.width * scale_x), int(transformed.height * scale_y))
            transformed = transformed.resize(new_size, resample=Image.BICUBIC)
            st.image(transformed, caption="Transformed Image")

            st.write(f"**Trim @ {row['timestamp']}**")
            st.write(f"**Boat Speed**: {row['BSP']} kn")
            st.write(f"**Heel**: {row['Heel']}°")
            st.write(f"**Wind Angle (TWA)**: {row['TWA']}°")
            st.write(f"**Wind Speed (TWS)**: {row['TWS']} kn")
            st.write(f"**Vs_perf%**: {row['Vs_perf%']}%")
            st.markdown("---")
        else:
            st.warning(f"Couldn't extract timestamp from: {img_file.name}")
