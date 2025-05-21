import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm as cm
from datetime import datetime
from PIL import Image
import os
from streamlit_cropper import st_cropper

st.title("Sailboat Performance & Trim Visualizer")

st.sidebar.subheader("Performance Filter and Options")
show_wind = st.sidebar.checkbox("Show TWA Arrows", value=False)
vs_min = st.sidebar.slider("Minimum Vs_perf%", float(df["Vs_perf%"].min()), float(df["Vs_perf%"].max()), float(df["Vs_perf%"].min()))
vs_max = st.sidebar.slider("Maximum Vs_perf%", float(df["Vs_perf%"].min()), float(df["Vs_perf%"].max()), float(df["Vs_perf%"].max()))
df_filtered = df[(df["Vs_perf%"] >= vs_min) & (df["Vs_perf%"] <= vs_max)]


# Upload data file
data_file = st.file_uploader("Upload .tsv performance data", type="tsv")
if data_file:
    df = pd.read_csv(data_file, sep="\\t")

    # Combine date and time into a timestamp
    df["timestamp"] = pd.to_datetime(df["dd/mm/yy"] + " " + df["hhmmss"], format="%d/%m/%Y %H:%M:%S")

    # Drop NaNs for relevant columns
    df = df.dropna(subset=["Lat", "Lon", "Vs_perf%"])

    # Plot course with Vs_perf% as color and a slider
    st.subheader("Boat Course Colored by Vs_perf% + Data Point Slider")

    if not df.empty:
        idx = st.slider("Select data point index", min_value=0, max_value=len(df) - 1, value=0, step=1)

        fig, ax = plt.subplots(figsize=(10, 6))
        norm = mcolors.Normalize(vmin=df["Vs_perf%"].min(), vmax=df["Vs_perf%"].max())
        cmap = cm.viridis

        sc = ax.scatter(df["Lon"], df["Lat"], c=df["Vs_perf%"], cmap=cmap, norm=norm, s=10, alpha=0.6)
        ax.plot(df["Lon"], df["Lat"], color="gray", alpha=0.2, linewidth=0.5)

        selected = df.iloc[idx]
        ax.scatter(selected["Lon"], selected["Lat"], color="red", s=50, label=f"Index {idx}")
        ax.legend()

        cbar = fig.colorbar(sc, ax=ax, label="Vs_perf%")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.set_title("Boat Track")

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

            # Rotate and stretch/squash
            st.markdown("### Transform Cropped Image")

            rotate_degrees = st.slider("Rotate image (degrees)", min_value=-180, max_value=180, value=0, step=1)
            scale_x = st.slider("Scale X (width)", min_value=0.1, max_value=3.0, value=1.0, step=0.1)
            scale_y = st.slider("Scale Y (height)", min_value=0.1, max_value=3.0, value=1.0, step=0.1)

            # Apply transformations
            transformed = cropped_image.rotate(rotate_degrees, expand=True)
            width, height = transformed.size
            new_width = int(width * scale_x)
            new_height = int(height * scale_y)
            transformed = transformed.resize((new_width, new_height), resample=Image.BICUBIC)

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
