# dashboard.py
from flask import Flask, jsonify, render_template_string, request
from db import all_metrics, list_jobs_by_state

TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>FLAM PHV — Queue Dashboard</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <meta http-equiv="refresh" content="5">
  <style>
    /* small custom tweaks */
    .card-shadow { box-shadow: 0 6px 18px rgba(15,23,42,0.08); }
    .badge { font-weight: 600; padding: 0.25rem 0.5rem; border-radius: 9999px; font-size: 0.75rem; }
    .cmd { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, "Roboto Mono", "Segoe UI Mono", monospace; font-size:0.9rem; }
    .priority-indicator { width: 8px; height: 100%; border-radius: 6px; }
    .table-head { background: linear-gradient(90deg, rgba(248,250,252,1), rgba(241,245,249,1)); }
    .small-muted { font-size: 0.85rem; color: #6b7280; }
  </style>
</head>
<body class="bg-slate-50 text-slate-800">
  <header class="bg-gradient-to-r from-indigo-600 via-cyan-500 to-teal-400 text-white">
    <div class="max-w-7xl mx-auto px-6 py-6 flex items-center justify-between">
      <div class="flex items-center gap-4">
        <div class="rounded-lg bg-white/10 p-2">
          <svg class="w-8 h-8" viewBox="0 0 24 24" fill="none" stroke="currentColor"><path d="M3 12h18M12 3v18" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </div>
        <div>
          <h1 class="text-xl font-semibold">FLAM PHV</h1>
          <p class="text-sm opacity-90">Job Queue — Priority, Timeouts & Metrics</p>
        </div>
      </div>
      <div class="text-right small-muted">
        <div>Auto-refresh every 5s</div>
        <div class="mt-1 text-xs">Access: <span class="font-medium">/</span></div>
      </div>
    </div>
  </header>

  <main class="max-w-7xl mx-auto px-6 py-8">
    <!-- Top metrics -->
    <section class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
      <div class="bg-white rounded-lg p-4 card-shadow">
        <div class="flex items-center justify-between">
          <div>
            <div class="text-sm text-slate-500">Pending</div>
            <div class="text-2xl font-bold">{{ metrics.get('pending', 0) }}</div>
          </div>
          <div class="bg-amber-50 text-amber-600 rounded-full px-3 py-1 text-sm font-semibold">⏳</div>
        </div>
      </div>

      <div class="bg-white rounded-lg p-4 card-shadow">
        <div class="flex items-center justify-between">
          <div>
            <div class="text-sm text-slate-500">Processing</div>
            <div class="text-2xl font-bold">{{ metrics.get('processing', 0) }}</div>
          </div>
          <div class="bg-sky-50 text-sky-600 rounded-full px-3 py-1 text-sm font-semibold">⚙️</div>
        </div>
      </div>

      <div class="bg-white rounded-lg p-4 card-shadow">
        <div class="flex items-center justify-between">
          <div>
            <div class="text-sm text-slate-500">Completed</div>
            <div class="text-2xl font-bold text-emerald-600">{{ metrics.get('completed', 0) }}</div>
          </div>
          <div class="bg-emerald-50 text-emerald-600 rounded-full px-3 py-1 text-sm font-semibold">✅</div>
        </div>
      </div>

      <div class="bg-white rounded-lg p-4 card-shadow">
        <div class="flex items-center justify-between">
          <div>
            <div class="text-sm text-slate-500">Failed</div>
            <div class="text-2xl font-bold text-rose-600">{{ metrics.get('failed', 0) }}</div>
          </div>
          <div class="bg-rose-50 text-rose-600 rounded-full px-3 py-1 text-sm font-semibold">❌</div>
        </div>
      </div>

      <div class="bg-white rounded-lg p-4 card-shadow">
        <div class="flex items-center justify-between">
          <div>
            <div class="text-sm text-slate-500">Dead (DLQ)</div>
            <div class="text-2xl font-bold text-gray-700">{{ metrics.get('dead', 0) }}</div>
          </div>
          <div class="bg-gray-50 text-gray-700 rounded-full px-3 py-1 text-sm font-semibold">🗄️</div>
        </div>
      </div>
    </section>

    <!-- Performance -->
    <section class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
      <div class="bg-white rounded-lg p-5 card-shadow">
        <div class="text-sm text-slate-500">Average Exec Time</div>
        <div class="mt-2 text-3xl font-semibold">{{ "%.2f"|format(metrics.get('avg_time', 0)) }}s</div>
        <div class="small-muted mt-1">Aggregated over completed jobs</div>
      </div>
      <div class="bg-white rounded-lg p-5 card-shadow">
        <div class="text-sm text-slate-500">Min Exec Time</div>
        <div class="mt-2 text-3xl font-semibold">{{ "%.2f"|format(metrics.get('min_time', 0)) }}s</div>
        <div class="small-muted mt-1">Fastest completed job</div>
      </div>
      <div class="bg-white rounded-lg p-5 card-shadow">
        <div class="text-sm text-slate-500">Max Exec Time</div>
        <div class="mt-2 text-3xl font-semibold">{{ "%.2f"|format(metrics.get('max_time', 0)) }}s</div>
        <div class="small-muted mt-1">Slowest completed job</div>
      </div>
    </section>

    <!-- Jobs table -->
    <section class="bg-white rounded-lg card-shadow overflow-hidden">
      <div class="px-6 py-4 border-b">
        <div class="flex items-center justify-between">
          <h2 class="text-lg font-semibold">Recent Jobs</h2>
          <div class="small-muted">Showing latest 200</div>
        </div>
      </div>

      <div class="overflow-x-auto">
        <table class="min-w-full bg-white">
          <thead class="table-head">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-slate-600 uppercase tracking-wider">ID</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-slate-600 uppercase tracking-wider">State</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-slate-600 uppercase tracking-wider">Priority</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-slate-600 uppercase tracking-wider">Attempts</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-slate-600 uppercase tracking-wider">Timeout</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-slate-600 uppercase tracking-wider">Time</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-slate-600 uppercase tracking-wider">Command</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            {% for j in jobs %}
            <tr class="hover:bg-slate-50">
              <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-800">{{ j.id[:8] }}...</td>
              <td class="px-6 py-4 whitespace-nowrap">
                {% set s = j.state %}
                <span class="badge
                  {% if s == 'completed' %} bg-emerald-100 text-emerald-800
                  {% elif s == 'failed' %} bg-rose-100 text-rose-800
                  {% elif s == 'processing' %} bg-sky-100 text-sky-800
                  {% elif s == 'pending' %} bg-amber-100 text-amber-800
                  {% else %} bg-gray-100 text-gray-800 {% endif %}">
                  {{ s }}
                </span>
              </td>

              <td class="px-6 py-4 whitespace-nowrap">
                {% set p = j.get('priority', 0) %}
                <div class="flex items-center gap-3">
                  <div style="min-width:120px" class="flex items-center gap-3">
                    <div class="priority-indicator"
                         style="background:
                          {% if p >= 8 %}#ef4444
                          {% elif p >=5 %}#f59e0b
                          {% elif p > 0 %}#10b981
                          {% else %}#94a3b8{% endif %};"></div>
                    <div class="text-sm font-medium">
                      <span class="{% if p >= 8 %}text-rose-600{% elif p >=5 %}text-amber-600{% elif p>0 %}text-emerald-600{% else %}text-slate-500{% endif %}">{{ p }}</span>
                    </div>
                  </div>
                </div>
              </td>

              <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-600">{{ j.attempts }}/{{ j.max_retries }}</td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-600">{{ j.get('timeout_seconds', '-') }}</td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-600">
                {% if j.get('execution_time') %}{{ "%.2f"|format(j.execution_time) }}s{% else %}-{% endif %}
              </td>
              <td class="px-6 py-4 whitespace-nowrap cmd text-slate-700"><code class="px-2 py-1 bg-slate-100 rounded">{{ j.command }}</code></td>
            </tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </section>

    <footer class="mt-8 text-center small-muted">
      FLAM PHV • Job Queue Dashboard — lightweight monitoring for local development
    </footer>
  </main>
</body>
</html>
"""

def create_app():
    app = Flask(__name__)

    @app.route("/")
    def index():
        try:
            metrics = all_metrics()
            jobs = list_jobs_by_state(state=None, limit=200)  # Get last 200 jobs
            return render_template_string(TEMPLATE, metrics=metrics, jobs=jobs)
        except Exception as e:
            app.logger.error(f"Error loading dashboard: {str(e)}")
            return f"Error loading dashboard: {str(e)}", 500

    @app.route("/metrics")
    def metrics():
        return jsonify(all_metrics())

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
