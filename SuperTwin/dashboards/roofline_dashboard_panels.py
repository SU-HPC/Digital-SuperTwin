def two_templates_one(data, layout, datasource):
    
    template = {
        "id": 41,
        "gridPos": {
            "h": 16,
            "w": 16,
            "x": 0,
            "y": 0
        },
        "type": "ae3e-plotly-panel",
        "title": "Cache Aware Roofline Model",
        "datasource": {
            "type": "influxdb",
            "uid": datasource
        },
        "options": {
            "script": "console.log(data)\n\n\nreturn {};",
            "onclick": "console.log(data)\nwindow.updateVariables({query:{'var-project':'test'}, partial: true})",
            "config": {
                "displayModeBar": True,
                "locale": "en"
            },
            "data": data,
            "layout": layout
        },
        "targets": [
            {
                "alias": "",
                "bucketAggs": [
                    {
                        "field": "@timestamp",
                        "id": "2",
                        "settings": {
                            "interval": "auto"
                        },
                        "type": "date_histogram"
                    }
                ],
                "datasource": {
                    "type": "influxdb",
                    "uid": datasource
                },
                "metrics": [
                    {
                        "id": "1",
                        "type": "count"
                    }
                ],
                "payload": "",
                "query": "",
                "refId": "A",
                "target": "system_ip",
                "timeField": "@timestamp"
            }
        ],
        "transparent": True
    }

    return template

def two_templates_two(data, layout, datasource):
    
    template = {
        "id": 42,
        "gridPos": {
            "h": 27,
            "w": 8,
            "x": 16,
            "y": 0
        },
        "type": "ae3e-plotly-panel",
        "title": "System Hardware Info",
        "datasource": {
            "type": "influxdb",
            "uid": datasource
        },
        "options": {
            "script": "console.log(data)\n\n\nreturn {};",
            "onclick": "console.log(data)\nwindow.updateVariables({query:{'var-project':'test'}, partial: true})",
            "config": {
                "displayModeBar": False,
                "locale": "en"
            },
            "data": data,
            "layout": layout
        },
        "targets": [
            {
                "alias": "",
                "bucketAggs": [
                    {
                        "field": "@timestamp",
                        "id": "2",
                        "settings": {
                            "interval": "auto"
                        },
                        "type": "date_histogram"
                    }
                ],
                "datasource": {
                    "type": "influxdb",
                    "uid": datasource
                },
                "metrics": [
                    {
                        "id": "1",
                        "type": "count"
                    }
                ],
                "payload": "",
                "query": "",
                "refId": "A",
                "target": "system_ip",
                "timeField": "@timestamp"
            }
        ],
        "transparent": True
    }

    return template

def two_templates_three(data, layout, h, w, x, y, datasource, title, id):
    
    template = {
        "id": id,
        "gridPos": {
            "h": h,
            "w": w,
            "x": x,
            "y": y
        },
        "type": "ae3e-plotly-panel",
        "title": title,
        "datasource": {
            "type": "influxdb",
            "uid": datasource
        },
        "options": {
            "script": "console.log(data)\n\n\nreturn {};",
            "onclick": "console.log(data)\nwindow.updateVariables({query:{'var-project':'test'}, partial: true})",
            "config": {
                "displayModeBar": False,
                "locale": "en"
            },
            "data": data,
            "layout": layout
        },
        "targets": [
            {
                "alias": "",
                "bucketAggs": [
                    {
                        "field": "@timestamp",
                        "id": "2",
                        "settings": {
                            "interval": "auto"
                        },
                        "type": "date_histogram"
                    }
                ],
                "datasource": {
                    "type": "influxdb",
                    "uid": datasource
                },
                "metrics": [
                    {
                        "id": "1",
                        "type": "count"
                    }
                ],
                "payload": "",
                "query": "",
                "refId": "A",
                "target": "system_ip",
                "timeField": "@timestamp"
            }
        ],
        "transparent": True
    }

    return template

def grafana_layout(fig):

    fig.update_layout({
        #"legend": {
        #    "orientation": "h",
        #    "x": 0,
        #    "y": 1.3
        #},
        "margin": {
            "b": 0,
            "l": 0,
            "r": 50,
            "t": 10
        },
        "modebar": {
            "orientation": "v"
        },
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "xaxis": {
            "autorange": False,
            "dtick": 0.30102999566,
            "nticks": 32,
            "rangemode": "tozero",
            "showspikes": False,
            "title": {
                "text": "Arithmetic Intensity"
            },
            "type": "log",
            "range": [
                -1.5194309088656293,
                3.1052677216436475
            ]
        },
        "yaxis": {
            "autorange": False,
            "dtick": 0.30102999566,
            "rangemode": "tozero",
            "showspikes": False,
            "title": {
                "text": "Performance [GFlop/s]"
            },
            "type": "log",
            "range": [
                -1.040179707535978,
                3.717236972979037
            ]
        }
    })

    return fig

def grafana_layout_2(fig):

    fig.update_layout({
        #"legend": {
        #    "orientation": "h",
        #    "x": 0,
        #    "y": 1.3
        #},
        "margin": {
            "b": 0,
            "l": 0,
            "r": 0,
            "t": 0
        },
        "modebar": {
            "orientation": "v"
        },
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "xaxis": {
            "autorange": False,
            "dtick": 0.30102999566,
            "nticks": 32,
            "rangemode": "tozero",
            "showspikes": False,
            "title": {
                "text": "Arithmetic Intensity"
            },
            "type": "log",
            "range": [
                -1.8194309088656293,
                3.1052677216436475
            ]
        },
        "yaxis": {
            "autorange": False,
            "dtick": 0.30102999566,
            "rangemode": "tozero",
            "showspikes": False,
            "title": {
                "text": "Performance [GFlop/s]"
            },
            "type": "log",
            "range": [
                -1.2040179707535978,
                3.717236972979037
            ]
        }
    })

    return fig

def grafana_layout_3(fig, xtickvals, ytitle):

    fig.update_layout({
        #"legend": {
        #    "orientation": "h",
        #    "x": 0,
        #    "y": 1.3
        #},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "xaxis": {"title": "Number of Threads",
                  "tickvals": xtickvals,
                  "nticks": len(xtickvals),
                  "type": "category"},
        "yaxis": {"title": ytitle,
                  "rangemode": "tozero"},
        "margin": {"l": 50, "r": 35, "t": 10, "b": 40},
        "legend": {"orientation": "h",
                   "y": 1.1}
        })

    return fig
