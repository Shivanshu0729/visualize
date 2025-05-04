"""
geoplot.py
----------

This visualization renders a 3-D plot of the data given the state
trajectory of a simulation, and the path of the property to render.

It generates an HTML file that contains code to render the plot
using Cesium Ion, and the GeoJSON file of data provided to the plot.

An example of its usage is as follows:

```py
from agent_torch.visualize import GeoPlot

# create a simulation
# ...

# create a visualizer
engine = GeoPlot(config, {
  cesium_token: "...",
  step_time: 3600,
  coordinates = "agents/consumers/coordinates",
  feature = "agents/consumers/money_spent",
})

# visualize in the runner-loop
for i in range(0, num_episodes):
  runner.step(num_steps_per_episode)
  engine.render(runner.state_trajectory)
```
"""
import re 
import json 
import pandas as pd
import numpy as np 
from string import Template  


def get_by_path(root, items): 
    '''Navigates a nested dictionary or list structure using a sequence of keys. '''
    ''' Imagine you have a dictionary inside another dictionary, inside another... This function helps dig into that structure using a list of keys.'''
    """Access a nested object in root by item sequence."""
    for item in items:
        root = root[item]
    return root


def read_var(state, var):
    return get_by_path(state, re.split("/", var))  
''' If you give it something like "agents/consumers/coordinates" and a big dictionary, it splits the string and fetches the value inside the dictionary step by step.'''


class GeoPlot: 
    '''When you create an instance of this class, it takes some configuration info (config) and some extra options (options).'''
    def __init__(self, config, options):
        self.config = config
        (
            self.cesium_token, 
            self.step_time,  
            self.entity_position,  
            self.entity_property,  
            self.visualization_type,
        ) = (
            options["cesium_token"],
            options["step_time"],
            options["coordinates"],
            options["feature"],
            options["visualization_type"],
        )

    def render(self, state_trajectory):  
        '''This function takes the simulation's state history (all the positions and values over time) and prepares it for visualization.'''
        coords, values = [], []
        name = self.config["simulation_metadata"]["name"]  
        geodata_path, geoplot_path = f"{name}.geojson", f"{name}.html"

        for i in range(0, len(state_trajectory) - 1): 
            ''' We go through each episode in the simulation. For each one, we take the final state (the last step in that episode).'''
            final_state = state_trajectory[i][-1]

            coords = np.array(read_var(final_state, self.entity_position)).tolist()
            values.append(
                np.array(read_var(final_state, self.entity_property)).flatten().tolist()
            )
            '''From the final state, we get: '''
            '''1- the coordinates of each agent'''
            '''2- the values of the feature we're interested in.'''
            '''3- We convert these into lists so we can use them easily later.'''


        start_time = pd.Timestamp.utcnow()
        timestamps = [
            start_time + pd.Timedelta(seconds=i * self.step_time)
            for i in range(
                self.config["simulation_metadata"]["num_episodes"]
                * self.config["simulation_metadata"]["num_steps_per_episode"]
            )
        ]  
        '''  We generate time values for each step. For example, if the step time is 1 hour, and we have 10 steps, we make a list like: [start_time, start_time + 1hr, start_time + 2hr, ...]'''
        
        geojsons = []
        for i, coord in enumerate(coords):
            features = []
            for time, value_list in zip(timestamps, values):
                '''we loop through each agent's coordinates and each timestamp to create "features" for the map.'''
                features.append(
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [coord[1], coord[0]],
                        },
                        "properties": {
                            "value": value_list[i],
                            "time": time.isoformat(),
                        },
                    }
                )
            geojsons.append({"type": "FeatureCollection", "features": features})
            '''Each feature contains:'''
            '''where the agent was (latitude and longitude),'''
            '''what their value was at that time (like money spent),'''
            '''and the exact time.'''
            '''We wrap up the features and collect them into a GeoJSON format.'''


        with open(geodata_path, "w", encoding="utf-8") as f:
            json.dump(geojsons, f, ensure_ascii=False, indent=2)  
            '''We save everything into a .geojson file, which stores all positions and properties.'''
            

        tmpl = Template(geoplot_template)
        with open(geoplot_path, "w", encoding="utf-8") as f:
            f.write(
                tmpl.substitute(
                    {
                        "accessToken": self.cesium_token,
                        "startTime": timestamps[0].isoformat(),
                        "stopTime": timestamps[-1].isoformat(),
                        "data": json.dumps(geojsons),
                        "visualType": self.visualization_type,
                    }
                )
            ) 
            ''' we take an HTML template fill in the values like:'''
            ''' - The Cesium token, '''
            ''' - Start and end times,'''
            ''' - GeoJSON data,'''
            ''' - Visualization type,'''
            ''' and then write it to a .html file. Now you can open this in a browser and see a 3D animated map!'''
