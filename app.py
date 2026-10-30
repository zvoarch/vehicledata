"""Car Data Dashboard: a Streamlit app exploring EPA fuel economy data (1984 to today)."""

import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="Car Data",
    page_icon=":material/directions_car:",
    layout="wide"
)


COLUMNS = ["make", "model", "year", "cylinders", "fuelType1", "atvType", "comb08", "fuelCost08"]

# Readable names for column titles and chart labels
LABELS = {
    "make": "Make",
    "model": "Model",
    "year": "Year",
    "cylinders": "Cylinders",
    "fuelType1": "Fuel Type",
    "atvType": "Technology",
    "comb08": "Combined MPG",
    "fuelCost08": "Yearly Fuel Cost ($)",
}


@st.cache_data
def load_data():
    """Load the EPA Vehicle Data and remove rows
    with no usable fuel cost."""
    df = pd.read_csv("data/raw/vehicles.csv", usecols=COLUMNS)
    df = df[df["fuelType1"].notna() & (df["fuelType1"] != "Hydrogen")]
    return df


def cylinders_chart(df, col, choice):
    """Bar chart of the average of col (MPG or fuel cost) per cylinder count."""
    # EVs have no cylinders, so they drop out of the groupby
    by_cyl = df.groupby("cylinders", as_index=False)[col].mean()
    by_cyl["cylinders"] = by_cyl["cylinders"].astype(int).astype(str)

    fig = px.bar(
        by_cyl,
        x="cylinders",
        y=col,
        color="cylinders",
        title=f"Average {choice} by Number of Cylinders",
        labels={**LABELS, col: f"Average {choice}"},
    )
    fig.update_xaxes(type="category")
    return fig


def trend_chart(df, makes):
    """Line chart of average MPG per model year.
    One line for all vehicles, or one line per make if makes are picked."""
    if makes:
        df = df[df["make"].isin(makes)]
        by_year = df.groupby(["year", "make"], as_index=False)["comb08"].mean()
    else:
        by_year = df.groupby("year", as_index=False)["comb08"].mean()
        by_year["make"] = "All vehicles"  # so the single line still gets a legend

    return px.line(
        by_year,
        x="year",
        y="comb08",
        color="make",
        markers=True,
        title="Average Combined MPG by Model Year",
        labels={**LABELS, "comb08": "Average Combined MPG"},
    )


def rankings_chart(df, most):
    """Horizontal bar chart of the 10 most (or least) efficient vehicles."""
    # Sort by MPG, then keep each make + model once (its best or worst year)
    ranked = df.sort_values("comb08", ascending=not most)
    ranked = ranked.drop_duplicates(subset=["make", "model"]).head(10)
    ranked["vehicle"] = ranked["year"].astype(str) + " " + ranked["make"] + " " + ranked["model"]

    title = "Most" if most else "Least"
    fig = px.bar(
        ranked,
        x="comb08",
        y="vehicle",
        color="fuelType1",
        orientation="h",
        title=f"Top 10 {title} Efficient Vehicles",
        labels={**LABELS, "vehicle": "Vehicle"},
    )
    # Keep the #1 vehicle at the top
    fig.update_yaxes(categoryorder="array", categoryarray=ranked["vehicle"].tolist()[::-1])
    return fig


df = load_data()


st.title("Car Data Dashboard")
st.caption("U.S. fuel economy data from the EPA, 1984 to today")
st.markdown("Explore how engines, brands and time affect fuel economy. Each tab below has one chart with its own control. "
            "Hover over a chart for exact values, drag to zoom, and click legend items to hide or show them.")
col1, col2, col3 = st.columns(3)
col1.metric("Vehicles", f"{len(df):,}")
col2.metric("Avg MPG (incl. EVs)", round(df["comb08"].mean(), 1))
col3.metric("Avg Yearly Fuel Cost", f"${df['fuelCost08'].mean():,.0f}")

st.divider()

engine_fuel, trends, rankings, insights, data = st.tabs(["Engine & Fuel", "Trends", "Rankings", "Insights", "Data"])


# Engine & Fuel tab: average MPG or fuel cost by cylinders
with engine_fuel:
    st.subheader("Engine & Fuel Types")
    st.markdown("Engines have a big effect on efficiency and costs. This chart shows how much.")

    choice = st.radio("Show", ["Combined MPG", "Yearly Fuel Cost"], horizontal=True, key="ef_choice")

    if choice == "Combined MPG":
        col = "comb08"
    else:
        col = "fuelCost08"

    st.plotly_chart(cylinders_chart(df, col, choice))
    st.caption("Electric vehicles are not shown because they have no cylinders.")


# Trends tab: average MPG over the years, optionally per make
with trends:
    st.subheader("Fuel economy over time")
    st.markdown("How has average MPG changed since 1984? Pick makes to compare them.")

    makes = st.multiselect("Makes", sorted(df["make"].unique()), key="trend_makes")

    st.plotly_chart(trend_chart(df, makes))
    st.caption("Includes electric vehicles (MPGe). As more EVs appear from about 2022 on, they pull the average up sharply. "
               "The latest model year is still incomplete.")


# Rankings tab: top 10 most or least efficient vehicles
with rankings:
    st.subheader("Most & least efficient vehicles")

    order = st.radio("Show", ["Most efficient", "Least efficient"], horizontal=True, key="rank_order")
    most = order == "Most efficient"

    st.plotly_chart(rankings_chart(df, most))
    st.caption("Each model appears once. Electric vehicle efficiency is in MPGe.")


# Insights tab: key findings calculated from the data, plus limitations
with insights:
    st.subheader("Key findings")

    gas = df[df["fuelType1"] != "Electricity"]
    ev = df[df["fuelType1"] == "Electricity"]
    four_cyl = df.loc[df["cylinders"] == 4, "comb08"].mean()
    eight_cyl = df.loc[df["cylinders"] == 8, "comb08"].mean()

    st.markdown(
        f"- **Fewer cylinders, better MPG.** 4-cylinder cars average {four_cyl:.1f} MPG, "
        f"8-cylinder cars only {eight_cyl:.1f}.\n"
        f"- **Gas cars vary a lot.** Non-electric vehicles range from {gas['comb08'].min()} "
        f"to {gas['comb08'].max()} MPG.\n"
        f"- **EVs are in another league.** Electric vehicles average {ev['comb08'].mean():.0f} MPGe, "
        f"compared to {gas['comb08'].mean():.1f} MPG for everything else."
    )

    st.markdown("#### Limitations")
    st.markdown(
        "- Fuel cost uses today's fuel prices and 15,000 miles/year, even for older cars.\n"
        "- EV efficiency is MPGe, which is not directly comparable to MPG.\n"
        "- Averages count every model equally, not by how many were sold.\n"
        "- Hydrogen vehicles were removed because the EPA lists no fuel cost for them."
    )


# Data tab: the full table, filterable by fuel type
with data:
    st.subheader("Browse the dataset")

    fuels = st.multiselect("Fuel type", sorted(df["fuelType1"].unique()), key="data_fuels")
    table = df[df["fuelType1"].isin(fuels)] if fuels else df

    st.caption(f"Showing {len(table):,} of {len(df):,} vehicles")

    # Readable column titles for display only
    st.dataframe(table.rename(columns=LABELS), hide_index=True)

    st.caption("Fuel cost is the EPA’s estimate at current fuel prices and 15,000 miles/year.")
