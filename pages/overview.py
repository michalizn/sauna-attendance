import dash
from dash import Input, Output, State
from dash import dcc, html
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
import numpy as np
import pandas as pd
import os
import re
import glob
from app import app
from plotly.subplots import make_subplots
from datetime import datetime
import requests
import xml.etree.ElementTree as ET

dash.register_page(__name__, path='/')

# Global variables to store data
data_cache = {}
prev_selected_file = None

# Get list of GPX files
gpx_folder = os.path.dirname(os.path.abspath(__file__)).replace('pages', 'data')
gpx_files = [f for f in os.listdir(gpx_folder) if f.endswith('.gpx')]

# App layout
layout = html.Div([
    dbc.Container([
        dbc.Row([
            dbc.Col([
                html.Div([], style={'textAlign': 'center'}),
            ]),
        ]),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        dcc.Store(id='screen-size', storage_type='session'),
                        html.Label('Select route and activity', className="desktop-visible", style={'fontSize': 30, 'textAlign': 'left'}),
                        html.Label('Select route and activity', className="mobile-visible", style={'fontSize': '5vw', 'textAlign': 'left'}),
                        html.Div([
                            html.Div([
                                dcc.Dropdown(
                                    id='gpx-dropdown',
                                    options=[
                                        {'label': f'{file_name}', 'value': file_path}
                                        for file_name, file_path in zip(
                                            [os.path.basename(file_path) for file_path in glob.glob(os.path.join(gpx_folder, '*.gpx'))],
                                            glob.glob(os.path.join(gpx_folder, '*.gpx'))
                                        )
                                    ],
                                    placeholder="Select a GPX file",
                                    clearable=True,
                                    searchable=True,
                                    persistence=True,
                                ),
                            ], className="desktop-visible", style={'width': '50%', 'margin-right': '10px'}),
                            html.Div([
                                dcc.Dropdown(
                                    id='activity-dropdown',
                                    options=['Running', 'Cycling', 'Walking'],
                                    placeholder="Select an activity",
                                    persistence=True,
                                ),
                            ], className="desktop-visible", style={'width': '50%', 'margin-right': '10px'}),
                            html.Div([
                                dcc.Dropdown(
                                    id='gpx-dropdown-mobile',
                                    options=[
                                        {'label': f'{file_name}', 'value': file_path}
                                        for file_name, file_path in zip(
                                            [os.path.basename(file_path) for file_path in glob.glob(os.path.join(gpx_folder, '*.gpx'))],
                                            glob.glob(os.path.join(gpx_folder, '*.gpx'))
                                        )
                                    ],
                                    placeholder="Select a GPX file",
                                    clearable=True,
                                    searchable=True,
                                    persistence=True,
                                ),
                                dcc.Dropdown(
                                    id='activity-dropdown-mobile',
                                    options=['Running', 'Cycling', 'Walking'],
                                    placeholder="Select an activity",
                                    persistence=True,
                                    style={'marginTop': '10px'},
                                ),
                            ], className="mobile-visible", style={'width': '100%', 'margin-bottom': '10px'}),
                        ], style={'display': 'flex', 'flexDirection': 'row', 'gap': '10px', 'flex': '1'}),
                    ]),
                ], style={'background': 'linear-gradient(to top, rgb(255, 255, 255) 0%, rgb(64, 64, 64) 100%)', 'border': '0px'}),
            ]),
        ]),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Trace details:", className="desktop-visible", style={'fontSize': 30, 'textAlign': 'left'}),
                    dbc.CardHeader("Trace details:", className="mobile-visible", style={'fontSize': '4vw', 'textAlign': 'left'}),
                    dbc.CardBody([
                        html.Div([
                            html.Div([
                                dcc.Graph(id='combined-graph', className="desktop-visible", style={'flex': '1', 'height': '200px'}),
                            ], style={'display': 'flex', 'flexDirection': 'column', 'gap': '10px', 'flex': '1'}),
                        ], style={'display': 'flex', 'flexDirection': 'row', 'gap': '10px', 'flex': '1'}),
                        html.Div([
                            html.Div([
                                dcc.Graph(id='combined-graph-mobile', className="mobile-visible", style={'flex': '1', 'height': '80vw'}),
                                ], className="mobile-visible", style={'display': 'flex', 'flexDirection': 'column', 'gap': '10px', 'flex': '1'}),
                        ], style={'display': 'flex', 'flexDirection': 'row', 'gap': '10px', 'flex': '1'}),
                    ]),
                ]),
            ]),
        ]),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Trace Information", className="desktop-visible", style={'fontSize': 30, 'textAlign': 'left', 'color': 'black'}),
                    dbc.CardHeader("Trace Information", className="mobile-visible", style={'fontSize': '4vw', 'textAlign': 'left', 'color': 'black'}),
                    dbc.CardBody([
                        html.Div(id='metrics-output', className="desktop-visible", style={'padding': '10px'}),
                        html.Div(id='metrics-output-mobile', className="mobile-visible", style={'padding': '10px'})
                    ]),
                ], style={'background': 'linear-gradient(to top, rgb(64, 64, 64) 0%, rgb(255, 255, 255) 100%)', 'border': '0px'}),
            ]),
        ]),
    ])
], style={'background': 'linear-gradient(to top, rgb(255, 255, 255) 0%, rgb(64, 64, 64) 100%)'})

@app.callback(
    [Output('metrics-output', 'children'),
     Output('gpx-map', 'figure'),
     Output('combined-graph', 'figure')],
    [Input('gpx-dropdown', 'value'),
     Input('combined-graph', 'hoverData'),
     Input('activity-dropdown', 'value')],
    [State('store_weight', 'data'),
     State('store_height', 'data'),
     State('store_age', 'data'),
     State('store_sex', 'data'),]
)
def update_output(file_path, hoverData_plot, activity, weight, height, age, sex):
    global data_cache

    if not file_path:
        return [html.Div(), {}, {}]


    data = data_cache[file_path]
    
    # Format metrics
    metrics = data['metrics']
    times = data['times']
    formatted_times = [time.strftime('%Y-%m-%d %H:%M:%S %Z').replace(' Z', '') for time in times]  # Convert datetime to string
    # Combine speed and time for hover info
    hover_texts = [
        f"Speed: {speed:.2f} km/h<br>Time: {time}"
        for speed, time in zip(data['smoothed_speeds'], formatted_times)
    ]
    total_time_seconds = metrics['total_time_seconds']
    hours, minutes, seconds = int(total_time_seconds // 3600), int((total_time_seconds % 3600) // 60), int(total_time_seconds % 60)
    total_time_formatted = f"{hours:02}:{minutes:02}:{seconds:02}"
    
    map_fig = go.Figure(go.Scattermapbox(
        lat=data['latitudes'][1:],
        lon=data['longitudes'][1:],
        mode='markers+lines',
        marker=dict(size=7, color=data['speeds_normalized'], colorscale='turbo'),
        line=dict(width=2, color='blue'),
        text=hover_texts,
        hoverinfo='text'
    ))
    
    map_fig.update_layout(
        mapbox_style="open-street-map",
        mapbox=dict(
            center=go.layout.mapbox.Center(
                lat=data['latitudes'][len(data['latitudes']) // 2],
                lon=data['longitudes'][len(data['longitudes']) // 2]
            ),
            zoom=10
        ),
        margin={"r":0, "t":0, "l":0, "b":0}
    )

    # Create the combined figure with elevation and speed profiles
    elev_fig = go.Scatter(
        x=data['distances_kilometers'],
        y=data['elevations'],
        mode='lines+markers',
        line=dict(color='green'),
        marker=dict(size=5, color='green'),
        text=[f'Elevation: {ele:.2f} m' for ele in data['elevations']],
        hoverinfo='text'
    )

    speed_fig = go.Scatter(
        x=data['distances_kilometers'],
        y=data['smoothed_speeds'],
        mode='lines+markers',
        line=dict(color='red'),
        marker=dict(size=5, color='red'),
        text=[f'Speed: {speed:.2f} km/h' for speed in data['smoothed_speeds']],
        hoverinfo='text'
    )

    combined_fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1)
    combined_fig.add_trace(elev_fig, row=1, col=1)
    combined_fig.add_trace(speed_fig, row=2, col=1)
    combined_fig.update_layout(
        xaxis=dict(range=[min(data['distances_kilometers']), max(data['distances_kilometers'])]),
        xaxis_title='Distance (km)',
        yaxis1_title='Elevation (m)',
        yaxis2_title='Speed (km/h)',
        showlegend=False,
        margin={"r":0, "t":0, "l":0, "b":0}
    )

    ## TODO add to the calculation sex information and typical times for running, walking and biking based on Strava measurements
    if not activity or not weight or not height or not age or not sex:
        calories_burned = "Please select an activity and enter your personal information in setttings menu."
    else:
        total_time = float(total_time_seconds)
        average_speed = float(metrics["average_speed"])

        # MET values for different activities
        met_values = {
            'Running': 9.8,
            'Cycling': 7.5,
            'Walking': 3.8
        }

        met_value = met_values.get(activity, 1)
        
        # Adjust MET value based on elevation gain and average speed
        elevation_gain_value = metrics["top_elevation"] - metrics["lowest_elevation"]
        
        if elevation_gain_value > 500:
            met_value += 1  # Increase MET value for high elevation gain

        if average_speed > 20:
            met_value += 1  # Increase MET value for high speed

        calories_burned = met_value * weight * (total_time/3600)

        calories_burned = f'{calories_burned:.2f} kcal'

    metrics_output = html.Div([
        html.Div([
            dbc.Card([
                dbc.CardHeader("Total Distance:"),
                dbc.CardBody(html.P(f'{metrics["total_distance"]:.2f} km', style={'text-align': 'right', 'fontSize':20}))
            ], className="desktop-visible", style={'width': '25%', 'margin-right': '10px', 'color': 'white', 'border-color': 'white', 'background': 'radial-gradient(circle at 10% 20%, rgb(0, 0, 0) 0%, rgb(64, 64, 64) 90.2%)'}),
            dbc.Card([
                dbc.CardHeader("Highest Speed:"),
                dbc.CardBody(html.P(f'{metrics["highest_speed"]:.2f} km/h', style={'text-align': 'right', 'fontSize':20}))
            ], className="desktop-visible", style={'width': '25%', 'margin-right': '10px', 'color': 'white', 'border-color': 'white', 'background': 'radial-gradient(circle at 10% 20%, rgb(0, 0, 0) 0%, rgb(64, 64, 64) 90.2%)'}),
            dbc.Card([
                dbc.CardHeader("Lowest Speed:"),
                dbc.CardBody(html.P(f'{metrics["lowest_speed"]:.2f} km/h', style={'text-align': 'right', 'fontSize':20}))
            ], className="desktop-visible", style={'width': '25%', 'margin-right': '10px', 'color': 'white', 'border-color': 'white', 'background': 'radial-gradient(circle at 10% 20%, rgb(0, 0, 0) 0%, rgb(64, 64, 64) 90.2%)'}),
            dbc.Card([
                dbc.CardHeader("Average Speed:"),
                dbc.CardBody(html.P(f'{metrics["average_speed"]:.2f} km/h', style={'text-align': 'right', 'fontSize':20}))
            ], className="desktop-visible", style={'width': '25%', 'margin-right': '10px', 'color': 'white', 'border-color': 'white', 'background': 'radial-gradient(circle at 10% 20%, rgb(0, 0, 0) 0%, rgb(64, 64, 64) 90.2%)'}),
        ], style={'display': 'flex', 'flexDirection': 'row', 'gap': '10px', 'flex': '1'}),
        html.Div([
            dbc.Card([
                dbc.CardHeader("Total Time:"),
                dbc.CardBody(html.P(f'{total_time_formatted}', style={'text-align': 'right', 'fontSize':20}))
            ], className="desktop-visible", style={'width': '25%', 'margin-right': '10px', 'color': 'white', 'border-color': 'white', 'background': 'radial-gradient(circle at 10% 20%, rgb(0, 0, 0) 0%, rgb(64, 64, 64) 90.2%)'}),
            dbc.Card([
                dbc.CardHeader("Top Elevation:"),
                dbc.CardBody(html.P(f'{metrics["top_elevation"]:.2f} m', style={'text-align': 'right', 'fontSize':20}))
            ], className="desktop-visible", style={'width': '25%', 'margin-right': '10px', 'color': 'white', 'border-color': 'white', 'background': 'radial-gradient(circle at 10% 20%, rgb(0, 0, 0) 0%, rgb(64, 64, 64) 90.2%)'}),
            dbc.Card([
                dbc.CardHeader("Lowest Elevation:"),
                dbc.CardBody(html.P(f'{metrics["lowest_elevation"]:.2f} m', style={'text-align': 'right', 'fontSize':20}))
            ], className="desktop-visible", style={'width': '25%', 'margin-right': '10px', 'color': 'white', 'border-color': 'white', 'background': 'radial-gradient(circle at 10% 20%, rgb(0, 0, 0) 0%, rgb(64, 64, 64) 90.2%)'}),
            dbc.Card([
                dbc.CardHeader("Calories Burned: "),
                dbc.CardBody(html.P(calories_burned, style={'text-align': 'right', 'fontSize':20}))
            ], className="desktop-visible", style={'width': '25%', 'margin-right': '10px', 'color': 'white', 'border-color': 'white', 'background': 'radial-gradient(circle at 10% 20%, rgb(0, 0, 0) 0%, rgb(64, 64, 64) 90.2%)'}),
        ], style={'display': 'flex', 'flexDirection': 'row', 'gap': '10px', 'flex': '1'}),
    ], style={'display': 'flex', 'flexDirection': 'column', 'gap': '10px', 'flex': '1'})

    if hoverData_plot:
        point_index = hoverData_plot['points'][0]['pointIndex']
        lat = data['latitudes'][point_index + 1]
        lon = data['longitudes'][point_index + 1]

        # Update map figures
        map_fig.update_traces(
            marker=dict(size=[12 if i == point_index else 7 for i in range(len(data['latitudes']) - 1)])
        )
        map_fig.update_layout(
            mapbox=dict(
                center=go.layout.mapbox.Center(lat=lat, lon=lon),
                zoom=14
            )
        )

        # Update combined figures
        combined_fig.update_traces(
            marker=dict(size=[10 if i == point_index else 5 for i in range(len(data['smoothed_speeds']))])
        )

    return metrics_output, map_fig, combined_fig

@app.callback(
    [Output('metrics-output-mobile', 'children'),
     Output('gpx-map-mobile', 'figure'),
     Output('combined-graph-mobile', 'figure')],
    [Input('gpx-dropdown-mobile', 'value'),
     Input('combined-graph-mobile', 'hoverData'),
     Input('activity-dropdown-mobile', 'value')],
    [State('store_weight', 'data'),
     State('store_height', 'data'),
     State('store_age', 'data'),
     State('store_sex', 'data'),]
)
def update_output(file_path, hoverData_plot, activity, weight, height, age, sex):
    global data_cache

    if not file_path:
        return [html.Div(), {}, {}]

    data = data_cache[file_path]
    
    # Format metrics
    metrics = data['metrics']
    times = data['times']
    formatted_times = [time.strftime('%Y-%m-%d %H:%M:%S %Z').replace(' Z', '') for time in times]  # Convert datetime to string
    # Combine speed and time for hover info
    hover_texts = [
        f"Speed: {speed:.2f} km/h<br>Time: {time}"
        for speed, time in zip(data['smoothed_speeds'], formatted_times)
    ]
    total_time_seconds = metrics['total_time_seconds']
    hours, minutes, seconds = int(total_time_seconds // 3600), int((total_time_seconds % 3600) // 60), int(total_time_seconds % 60)
    total_time_formatted = f"{hours:02}:{minutes:02}:{seconds:02}"
    
    map_fig = go.Figure(go.Scattermapbox(
        lat=data['latitudes'][1:],
        lon=data['longitudes'][1:],
        mode='markers+lines',
        marker=dict(size=7, color=data['speeds_normalized'], colorscale='turbo'),
        line=dict(width=2, color='blue'),
        text=hover_texts,
        hoverinfo='text'
    ))
    
    map_fig.update_layout(
        mapbox_style="open-street-map",
        mapbox=dict(
            center=go.layout.mapbox.Center(
                lat=data['latitudes'][len(data['latitudes']) // 2],
                lon=data['longitudes'][len(data['longitudes']) // 2]
            ),
            zoom=10
        ),
        margin={"r":0, "t":0, "l":0, "b":0}
    )

    # Create the combined figure with elevation and speed profiles
    elev_fig = go.Scatter(
        x=data['distances_kilometers'],
        y=data['elevations'],
        mode='lines+markers',
        line=dict(color='green'),
        marker=dict(size=5, color='green'),
        text=[f'Elevation: {ele:.2f} m' for ele in data['elevations']],
        hoverinfo='text'
    )

    speed_fig = go.Scatter(
        x=data['distances_kilometers'],
        y=data['smoothed_speeds'],
        mode='lines+markers',
        line=dict(color='red'),
        marker=dict(size=5, color='red'),
        text=[f'Speed: {speed:.2f} km/h' for speed in data['smoothed_speeds']],
        hoverinfo='text'
    )

    combined_fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1)
    combined_fig.add_trace(elev_fig, row=1, col=1)
    combined_fig.add_trace(speed_fig, row=2, col=1)
    combined_fig.update_layout(
        xaxis=dict(range=[min(data['distances_kilometers']), max(data['distances_kilometers'])]),
        xaxis_title='Distance (km)',
        yaxis1_title='Elevation (m)',
        yaxis2_title='Speed (km/h)',
        showlegend=False,
        margin={"r":0, "t":0, "l":0, "b":0}
    )

    ## TODO add to the calculation sex information and typical times for running, walking and biking based on Strava measurements
    if not activity or not weight or not height or not age or not sex:
        calories_burned = "Please select an activity and enter your personal information in setttings menu."
    else:
        total_time = float(total_time_seconds)
        average_speed = float(metrics["average_speed"])

        # MET values for different activities
        met_values = {
            'Running': 9.8,
            'Cycling': 7.5,
            'Walking': 3.8
        }

        met_value = met_values.get(activity, 1)
        
        # Adjust MET value based on elevation gain and average speed
        elevation_gain_value = metrics["top_elevation"] - metrics["lowest_elevation"]
        
        if elevation_gain_value > 500:
            met_value += 1  # Increase MET value for high elevation gain

        if average_speed > 20:
            met_value += 1  # Increase MET value for high speed

        calories_burned = met_value * weight * (total_time/3600)

        calories_burned = f'{calories_burned:.2f} kcal'

    metrics_output = html.Div([
        html.Div([
            dbc.Card([
                dbc.CardHeader("Total Distance:"),
                dbc.CardBody(html.P(f'{metrics["total_distance"]:.2f} km', style={'text-align': 'right', 'fontSize': 20}))
            ], className="mobile-visible", style={'width': '100%', 'margin-bottom': '10px', 'color': 'white', 'border-color': 'white', 
                    'background': 'radial-gradient(circle at 10% 20%, rgb(0, 0, 0) 0%, rgb(64, 64, 64) 90.2%)'}),
            dbc.Card([
                dbc.CardHeader("Highest Speed:"),
                dbc.CardBody(html.P(f'{metrics["highest_speed"]:.2f} km/h', style={'text-align': 'right', 'fontSize': 20}))
            ], className="mobile-visible", style={'width': '100%', 'margin-bottom': '10px', 'color': 'white', 'border-color': 'white', 
                    'background': 'radial-gradient(circle at 10% 20%, rgb(0, 0, 0) 0%, rgb(64, 64, 64) 90.2%)'}),
            dbc.Card([
                dbc.CardHeader("Lowest Speed:"),
                dbc.CardBody(html.P(f'{metrics["lowest_speed"]:.2f} km/h', style={'text-align': 'right', 'fontSize': 20}))
            ], className="mobile-visible", style={'width': '100%', 'margin-bottom': '10px', 'color': 'white', 'border-color': 'white', 
                    'background': 'radial-gradient(circle at 10% 20%, rgb(0, 0, 0) 0%, rgb(64, 64, 64) 90.2%)'}),
            dbc.Card([
                dbc.CardHeader("Average Speed:"),
                dbc.CardBody(html.P(f'{metrics["average_speed"]:.2f} km/h', style={'text-align': 'right', 'fontSize': 20}))
            ], className="mobile-visible", style={'width': '100%', 'margin-bottom': '10px', 'color': 'white', 'border-color': 'white', 
                    'background': 'radial-gradient(circle at 10% 20%, rgb(0, 0, 0) 0%, rgb(64, 64, 64) 90.2%)'}),
            dbc.Card([
                dbc.CardHeader("Total Time:"),
                dbc.CardBody(html.P(f'{total_time_formatted}', style={'text-align': 'right', 'fontSize': 20}))
            ], className="mobile-visible", style={'width': '100%', 'margin-bottom': '10px', 'color': 'white', 'border-color': 'white', 
                    'background': 'radial-gradient(circle at 10% 20%, rgb(0, 0, 0) 0%, rgb(64, 64, 64) 90.2%)'}),
            dbc.Card([
                dbc.CardHeader("Top Elevation:"),
                dbc.CardBody(html.P(f'{metrics["top_elevation"]:.2f} m', style={'text-align': 'right', 'fontSize': 20}))
            ], className="mobile-visible", style={'width': '100%', 'margin-bottom': '10px', 'color': 'white', 'border-color': 'white', 
                    'background': 'radial-gradient(circle at 10% 20%, rgb(0, 0, 0) 0%, rgb(64, 64, 64) 90.2%)'}),
            dbc.Card([
                dbc.CardHeader("Lowest Elevation:"),
                dbc.CardBody(html.P(f'{metrics["lowest_elevation"]:.2f} m', style={'text-align': 'right', 'fontSize': 20}))
            ], className="mobile-visible", style={'width': '100%', 'margin-bottom': '10px', 'color': 'white', 'border-color': 'white', 
                    'background': 'radial-gradient(circle at 10% 20%, rgb(0, 0, 0) 0%, rgb(64, 64, 64) 90.2%)'}),
            dbc.Card([
                dbc.CardHeader("Calories Burned:"),
                dbc.CardBody(html.P(calories_burned, style={'text-align': 'right', 'fontSize': 20}))
            ], className="mobile-visible", style={'width': '100%', 'margin-bottom': '10px', 'color': 'white', 'border-color': 'white', 
                    'background': 'radial-gradient(circle at 10% 20%, rgb(0, 0, 0) 0%, rgb(64, 64, 64) 90.2%)'}),
        ], className="mobile-visible", style={'display': 'flex', 'flexDirection': 'column', 'gap': '10px'}),
    ], style={'display': 'flex', 'flexDirection': 'column', 'gap': '10px', 'flex': '1'})

    if hoverData_plot:
        point_index = hoverData_plot['points'][0]['pointIndex']
        lat = data['latitudes'][point_index + 1]
        lon = data['longitudes'][point_index + 1]

        # Update map figures
        map_fig.update_traces(
            marker=dict(size=[12 if i == point_index else 7 for i in range(len(data['latitudes']) - 1)])
        )
        map_fig.update_layout(
            mapbox=dict(
                center=go.layout.mapbox.Center(lat=lat, lon=lon),
                zoom=14
            )
        )

        # Update combined figures
        combined_fig.update_traces(
            marker=dict(size=[10 if i == point_index else 5 for i in range(len(data['smoothed_speeds']))])
        )

    return metrics_output, map_fig, combined_fig

# Define a callback to update the activity dropdown based on the average speed
@app.callback(
    Output('activity-dropdown', 'value'),
    Input('gpx-dropdown', 'value')
)
def update_activity_dropdown(file_path):
    if file_path:

        data = data_cache[file_path]
        metrics = data['metrics']
        average_speed = float(metrics["average_speed"])  # in km/h
        
        # Determine activity based on average speed
        if average_speed > 17:
            return 'Cycling'
        elif 7 <= average_speed <= 17:
            return 'Running'
        else:
            return 'Walking'
    
    return None  # Default value if no file is selected

# Define a callback to update the activity dropdown based on the average speed
@app.callback(
    Output('activity-dropdown-mobile', 'value'),
    Input('gpx-dropdown-mobile', 'value')
)
def update_activity_dropdown(file_path):
    if file_path:

        data = data_cache[file_path]
        metrics = data['metrics']
        average_speed = float(metrics["average_speed"])  # in km/h
        
        # Determine activity based on average speed
        if average_speed > 17:
            return 'Cycling'
        elif 7 <= average_speed <= 17:
            return 'Running'
        else:
            return 'Walking'
    
    return None  # Default value if no file is selected

@app.callback(
    Output('gpx-dropdown', 'options'),
    [Input('gpx-dropdown', 'value')]
)
def update_options(selected_value):
    updated_options = [
        {'label': f'{file_name}', 'value': file_path}
        for file_name, file_path in zip(
            [os.path.basename(file_path) for file_path in glob.glob(os.path.join(gpx_folder, '*.gpx'))],
            glob.glob(os.path.join(gpx_folder, '*.gpx'))
        )
    ]
    return updated_options

@app.callback(
    Output('gpx-dropdown-mobile', 'options'),
    [Input('gpx-dropdown-mobile', 'value')]
)
def update_options(selected_value):
    updated_options = [
        {'label': f'{file_name}', 'value': file_path}
        for file_name, file_path in zip(
            [os.path.basename(file_path) for file_path in glob.glob(os.path.join(gpx_folder, '*.gpx'))],
            glob.glob(os.path.join(gpx_folder, '*.gpx'))
        )
    ]
    return updated_options

if __name__ == '__main__':
    app.run_server(debug=True)