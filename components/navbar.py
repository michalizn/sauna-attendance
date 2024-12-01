from dash import html
import dash_bootstrap_components as dbc

def Navbar():

    layout = html.Div([
        dbc.NavbarSimple(
            children=[
                dbc.NavItem(dbc.NavLink("Overview", href="/overview")),
                dbc.NavItem(dbc.NavLink("Analysis", href="/analysis")),
                dbc.NavItem(dbc.NavLink("About", href="/about")),
            ],
            brand="Sauna Data Dashboard",
            brand_href="/overview",
            color="rgb(32, 32, 32)",
            dark=True
        ), 
    ])

    return layout