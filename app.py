'''
Code borrowed heavily from https://github.com/bokeh/bokeh/tree/master/examples
/embed/simple
'''
import flask
import os
import pandas as pd
import json
import requests

from math import pi

from bokeh.embed import components
from bokeh.plotting import figure
from bokeh.resources import INLINE
from bokeh.templates import RESOURCES
from bokeh.util.string import encode_utf8

app = flask.Flask(__name__)

def getitem(obj, item, default):
    if item not in obj:
        return default
    else:
        return obj[item]

@app.route("/")
def stock_plot():
	"""30-day price history for a user-provided stock ticker"""
	# Grab the inputs arguments from the URL
	# This is automated by the button
	args = flask.request.args

    # Set default for ticker
	ticker = getitem(args, 'ticker', 'TWTR')
	url = 'https://www.quandl.com/api/v1/datasets/WIKI/' + ticker + '.json'
	r = requests.get(url)
	if(type(r.json().get('error')) == unicode):
		# any returned error message means there's uh, an error
		return flask.render_template('error.html')
	else:
		# otherwise, we've got our stock
		ticker_data = r.json().get('data')
		
		# highly silly way to extract the full company name from the data
		ticker_company_name = r.json().get('name')
		ticker_company_name = \
			ticker_company_name[0:(ticker_company_name.find(')'))+1]
		# gather column names
		ticker_columns = r.json().get('column_names')
		# and chuck everything into a DataFrame
		temp_df = pd.DataFrame(ticker_data,columns=ticker_columns)
		# then pare down for the DataFrame we'll use
		df = temp_df[['Date','Open', 'Close', 'Low', 'High']]
		df.columns = ['date','open', 'close', 'low', 'high']
		df["date"] = pd.to_datetime(df["date"])
		df.index = df.date
		
		# various gyrations to grab the last month worth of data
		# find the last day in the data
		lastdate = df['date'][0]
		# set the first date to one month back from the last date
		firstdate = lastdate - pd.DateOffset(months=1)
		# then grab the last month worth of data
		df = df[lastdate:firstdate] 
		
		# calculations associated with generating candlesticks, taken from:
		# http://bokeh.pydata.org/en/latest/docs/gallery/candlestick.html
		mids = (df.open + df.close)/2
		spans = abs(df.close-df.open)
		inc = df.close > df.open
		dec = df.open > df.close
		# set candlestick duration (in ms)
		w = 24*60*60*1000 
		
		# configure plot
		TOOLS = "pan,wheel_zoom,box_zoom,reset,save"
		p = figure(title=ticker + " Daily Candles", x_axis_type="datetime", \
			tools=TOOLS, plot_width=1000, toolbar_location="left")
		p.segment(df.date, df.high, df.date, df.low, color="black")
		p.rect(df.date[inc], mids[inc], w, spans[inc], fill_color="#abdb8d", \
			line_color="black")
		p.rect(df.date[dec], mids[dec], w, spans[dec], fill_color="#F2583E", \
			line_color="black")
		p.title = ticker_company_name +' Daily Candles'
		p.xaxis.major_label_orientation = pi/4
		p.grid.grid_line_alpha=0.3
		p.xaxis.axis_label = 'Date'
		p.yaxis.axis_label = 'Price'

    	# Configure resources to include BokehJS inline in the document.
    	# For more details see:
    	# http://bokeh.pydata.org/en/latest/docs/reference/resources_embedding.html#module-bokeh.resources
		plot_resources = RESOURCES.render(
			js_raw=INLINE.js_raw,
			css_raw=INLINE.css_raw,
			js_files=INLINE.js_files,
			css_files=INLINE.css_files,
		)

   		# For more details see:
   		# http://bokeh.pydata.org/en/latest/docs/user_guide/embedding.html#components
		script, div = components(p, INLINE)
		html = flask.render_template(
			'embed.html',
			plot_script=script, plot_div=div, plot_resources=plot_resources,
			ticker=ticker
		)
		return encode_utf8(html)
    
if __name__ == "__main__":
	# taken verbatim from:
	# http://virantha.com/2013/11/14/starting-a-simple-flask-app-with-heroku/
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)