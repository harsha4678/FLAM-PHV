# dashboard.py
from flask import Flask, jsonify, render_template_string, request
from db import all_metrics, list_jobs_by_state

TEMPLATE = """
<!doctype html>
<html>
  <head>
    <title>queuectl dashboard</title>
    <style>
      body { font-family: Arial, sans-serif; padding: 20px; }
      .counts { display:flex; gap:20px; margin-bottom:20px; }
      .card { padding:10px 15px; border-radius:8px; background:#f2f2f2; }
      table { width:100%; border-collapse: collapse;}
      th, td { padding:8px 6px; border:1px solid #ddd; text-align:left; }
      th { background:#eee; }
    </style>
  </head>
  <body>
    <h1>queuectl dashboard</h1>
    <div class="counts">
      {% for k, v in metrics.items() %}
        <div class="card"><strong>{{k}}</strong><br><span style="font-size:20px">{{v}}</span></div>
      {% endfor %}
    </div>

    <h2>Recent jobs (all states)</h2>
    <table>
      <thead><tr><th>id</th><th>state</th><th>attempts</th><th>max_retries</th><th>priority</th><th>timeout</th><th>cmd</th></tr></thead>
      <tbody>
      {% for j in jobs %}
        <tr>
          <td>{{j['id']}}</td>
          <td>{{j['state']}}</td>
          <td>{{j['attempts']}}</td>
          <td>{{j['max_retries']}}</td>
          <td>{{j.get('priority',0)}}</td>
          <td>{{j.get('timeout_seconds') or '-'}}</td>
          <td><code>{{j['command']}}</code></td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
  </body>
</html>
"""

def create_app():
    app = Flask(__name__)

    @app.route("/")
    def index():
        metrics = all_metrics()
        # show latest 200 jobs
        jobs = list_jobs_by_state(None, limit=200)
        return render_template_string(TEMPLATE, metrics=metrics, jobs=jobs)

    @app.route("/metrics")
    def metrics():
        return jsonify(all_metrics())

    return app
