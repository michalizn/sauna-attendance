import dash
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
from dash import dcc
from dash import html
from app import app
from dash import Input, Output, State
import dash
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.express as px
import os
import plotly.graph_objects as go

dash.register_page(__name__, path='/')
data_dir = "/Users/baranekm/Documents/Python/sauna-attendance/data"

# Combine all CSV files in the data directory into one DataFrame
def load_combined_data(data_dir):
    all_files = [os.path.join(data_dir, file) for file in os.listdir(data_dir) if file.endswith(".csv")]
    if not all_files:
        return pd.DataFrame(columns=["timestamp", "persons_sauna"])  # Return an empty DataFrame if no files exist
    combined_data = pd.concat((pd.read_csv(file) for file in all_files), ignore_index=True)
    combined_data['timestamp'] = pd.to_datetime(combined_data['timestamp'])  # Ensure timestamp is in datetime format
    
    # Convert 'persons_sauna' to numeric, coercing errors to NaN
    combined_data['persons_sauna'] = pd.to_numeric(combined_data['persons_sauna'], errors='coerce')
    
    # Drop rows where 'persons_sauna' is NaN
    combined_data = combined_data.dropna(subset=['persons_sauna'])

    # Replace isolated zeros (not at the start or end) with the mean of previous and next valid samples
    combined_data['persons_sauna'] = combined_data['persons_sauna'].mask(
        (combined_data['persons_sauna'] == 0) & 
        (combined_data['persons_sauna'].shift() != 0) & 
        (combined_data['persons_sauna'].shift(-1) != 0),
        (combined_data['persons_sauna'].shift() + combined_data['persons_sauna'].shift(-1)) / 2
    )
    
    return combined_data

# Initial data load to populate dropdown
combined_data = load_combined_data(data_dir)
available_dates = [
    {'label': f"{date} ({pd.Timestamp(date).day_name()}, Week {pd.Timestamp(date).week})", 'value': str(date)}
    for date in combined_data['timestamp'].dt.date.unique()
] if not combined_data.empty else []

# Layout
layout = html.Div([
    dbc.Container([
        html.H1("Sauna Attendance Dashboard", style={'textAlign': 'center'}),
        dcc.Dropdown(
            id='date-picker',
            options=available_dates,
            multi=True,
            placeholder="Select dates",
        ),
        dcc.Checklist(
            id='show-average',
            options=[{'label': 'Show Average Line', 'value': 'show_avg'}],
            value=[],  # Default is unchecked
            style={'marginTop': '20px'}
        ),
        dcc.Graph(id='time-series-graph'),
        dcc.Slider(
            id='smoothing-slider',
            min=1,
            max=12,  # Default max for 1 hour of smoothing (12 x 5 minutes)
            step=1,
            value=3,  # Default to 15 minutes (3 x 5 minutes)
            marks={i: f"{i*5} min" for i in range(1, 13)},
            #tooltip={"placement": "bottom", "always_visible": True},
        ),
        html.Div(id='stats-summary', style={'marginTop': '20px', 'textAlign': 'center', 'fontSize': '18px'}),
    ], fluid=True),
])

# Callback to update the graph and statistics based on selected dates and smoothing window
@app.callback(
    [Output('time-series-graph', 'figure'), Output('stats-summary', 'children')],
    [Input('date-picker', 'value'), Input('smoothing-slider', 'value'), Input('show-average', 'value')]
)
def update_analysis(selected_dates, smoothing_window, show_average):
    # Reload data from the directory
    combined_data = load_combined_data(data_dir)

    if not selected_dates or combined_data.empty:
        return {}, "Please select valid dates."

    # Prepare figure and statistics
    figure = go.Figure()
    stats = []

    # Extract the time component for alignment
    combined_data['time'] = combined_data['timestamp'].dt.time

    # Container for aggregated data
    all_filtered_data = pd.DataFrame()

    for date in selected_dates:
        filtered_data = combined_data[
            combined_data['timestamp'].dt.date == pd.to_datetime(date).date()
        ]

        if filtered_data.empty:
            stats.append(f"No data available for {date}.")
            continue

        # Apply moving average for smoothing
        window_size = smoothing_window  # Use slider value directly as the number of rows for rolling
        filtered_data = filtered_data.set_index('time') # Align data by time
        filtered_data['smoothed'] = filtered_data['persons_sauna'].rolling(window=window_size).mean()

        # Add the filtered data for averaging
        all_filtered_data = pd.concat([all_filtered_data, filtered_data[['persons_sauna']]], axis=1)

        # Add traces for raw and smoothed data
        figure.add_trace(go.Scatter(
            x=filtered_data.index,  # Use time for x-axis
            y=filtered_data['persons_sauna'],
            mode='lines+markers',
            line=dict(dash='dot'),
            name=f'Raw Data ({date})',
            hoverinfo='x+y'
        ))
        figure.add_trace(go.Scatter(
            x=filtered_data.index,  # Use time for x-axis
            y=filtered_data['smoothed'],
            mode='lines',
            line=dict(width=2),
            name=f'Smoothed Data ({date})',
            hoverinfo='x+y'
        ))

        # Summary statistics for the date
        avg_usage = filtered_data['persons_sauna'].mean()
        peak_usage = filtered_data['persons_sauna'].max()
        stats.append(f"{date} - Average: {avg_usage:.2f}, Peak: {peak_usage}")

    # Calculate and add the average line if the checkbox is selected
    if 'show_avg' in show_average and not all_filtered_data.empty:
        all_filtered_data['average'] = all_filtered_data.mean(axis=1)
        figure.add_trace(go.Scatter(
            x=all_filtered_data.index,  # Use time for x-axis
            y=all_filtered_data['average'],
            mode='lines',
            line=dict(color='black', width=2, dash='dash'),
            name='Average Line',
            hoverinfo='x+y'
        ))

    # Update figure layout
    figure.update_layout(
        title="Sauna Usage (Aligned by Time of Day)",
        xaxis_title="Time of Day",
        yaxis_title="Persons in Sauna",
        xaxis=dict(
            type='category',  # Treat time as categorical for proper alignment
            categoryorder='category ascending'
        ),
        template="plotly_white"
    )

    return figure, " | ".join(stats)

if __name__ == '__main__':
    app.run_server(debug=True)