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





<!doctype html>
<html lang="en">
	<head>
		<meta charset="UTF-8" />
		<meta
			name="viewport"
			content="width=device-width, initial-scale=1.0"
		/>
		<title>Cesium Time-Series Heatmap Visualization</title>
		<script src="https://cesium.com/downloads/cesiumjs/releases/1.95/Build/Cesium/Cesium.js"></script>
		<link
			href="https://cesium.com/downloads/cesiumjs/releases/1.95/Build/Cesium/Widgets/widgets.css"
			rel="stylesheet"
		/>
		<style>
			#cesiumContainer {
				width: 100%;
				height: 100%;
			}
		</style>
	</head>
	<body>
		<div id="cesiumContainer"></div>
		<script>
			// Your Cesium ion access token here
			Cesium.Ion.defaultAccessToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiIwZmNmYTQxMC1jYTY2LTQ4MmEtYWMyNy1mZmMzZDY5YWZhYjAiLCJpZCI6Mjk3NDgwLCJpYXQiOjE3NDU2OTMyNzF9.OoP-Pfhs89OyqRwc2IfW2aiWO-nDGjlKGAXgaE5VR5I'

			// Create the viewer
			const viewer = new Cesium.Viewer('cesiumContainer')

			function interpolateColor(color1, color2, factor) {
				const result = new Cesium.Color()
				result.red = color1.red + factor * (color2.red - color1.red)
				result.green =
					color1.green + factor * (color2.green - color1.green)
				result.blue = color1.blue + factor * (color2.blue - color1.blue)
				result.alpha = 'color' == 'size' ? 0.2 :
					color1.alpha + factor * (color2.alpha - color1.alpha)
				return result
			}

			function getColor(value, min, max) {
				const factor = (value - min) / (max - min)
				return interpolateColor(
					Cesium.Color.BLUE,
					Cesium.Color.RED,
					factor
				)
			}

			function getPixelSize(value, min, max) {
				const factor = (value - min) / (max - min)
				return 100 * (1 + factor)
			}

			function processTimeSeriesData(geoJsonData) {
				const timeSeriesMap = new Map()
				let minValue = Infinity
				let maxValue = -Infinity

				geoJsonData.features.forEach((feature) => {
					const id = feature.properties.id
					const time = Cesium.JulianDate.fromIso8601(
						feature.properties.time
					)
					const value = feature.properties.value
					const coordinates = feature.geometry.coordinates

					if (!timeSeriesMap.has(id)) {
						timeSeriesMap.set(id, [])
					}
					timeSeriesMap.get(id).push({ time, value, coordinates })

					minValue = Math.min(minValue, value)
					maxValue = Math.max(maxValue, value)
				})

				return { timeSeriesMap, minValue, maxValue }
			}

			function createTimeSeriesEntities(
				timeSeriesData,
				startTime,
				stopTime
			) {
				const dataSource = new Cesium.CustomDataSource(
					'AgentTorch Simulation'
				)

				for (const [id, timeSeries] of timeSeriesData.timeSeriesMap) {
					const entity = new Cesium.Entity({
						id: id,
						availability: new Cesium.TimeIntervalCollection([
							new Cesium.TimeInterval({
								start: startTime,
								stop: stopTime,
							}),
						]),
						position: new Cesium.SampledPositionProperty(),
						point: {
							pixelSize: 'color' == 'size' ? new Cesium.SampledProperty(Number) : 10,
							color: new Cesium.SampledProperty(Cesium.Color),
						},
						properties: {
							value: new Cesium.SampledProperty(Number),
						},
					})

					timeSeries.forEach(({ time, value, coordinates }) => {
						const position = Cesium.Cartesian3.fromDegrees(
							coordinates[0],
							coordinates[1]
						)
						entity.position.addSample(time, position)
						entity.properties.value.addSample(time, value)
						entity.point.color.addSample(
							time,
							getColor(
								value,
								timeSeriesData.minValue,
								timeSeriesData.maxValue
							)
						)

						if ('color' == 'size') {
						  entity.point.pixelSize.addSample(
  							time,
  							getPixelSize(
  								value,
  								timeSeriesData.minValue,
  								timeSeriesData.maxValue
  							)
  						)
						}
					})

					dataSource.entities.add(entity)
				}

				return dataSource
			}

			// Example time-series GeoJSON data
			const geoJsons = []

			const start = Cesium.JulianDate.fromIso8601('2025-04-26T19:01:57.794146+00:00')
			const stop = Cesium.JulianDate.fromIso8601('2025-04-26T19:01:57.794146+00:00')

			viewer.clock.startTime = start.clone()
			viewer.clock.stopTime = stop.clone()
			viewer.clock.currentTime = start.clone()
			viewer.clock.clockRange = Cesium.ClockRange.LOOP_STOP
			viewer.clock.multiplier = 3600 // 1 hour per second

			viewer.timeline.zoomTo(start, stop)

			for (const geoJsonData of geoJsons) {
				const timeSeriesData = processTimeSeriesData(geoJsonData)
				const dataSource = createTimeSeriesEntities(
					timeSeriesData,
					start,
					stop
				)
				viewer.dataSources.add(dataSource)
				viewer.zoomTo(dataSource)
			}
		</script>
	</body>
</html>



the token will be stored in the environmental variable, that is .env file which will be called in my index.HTML that will help to create the 3D model

It contains estimated timeline of the project, and the deliverables and it approches