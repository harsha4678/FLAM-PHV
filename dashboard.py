# dashboard.py
from flask import Flask, jsonify, render_template_string, request
from db import all_metrics, list_jobs_by_state

TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Queue Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <meta http-equiv="refresh" content="5">
</head>
<body class="bg-gray-50">
    <nav class="bg-white shadow-sm">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between h-16">
                <div class="flex items-center">
                    <h1 class="text-2xl font-bold text-gray-900">Queue Dashboard</h1>
                </div>
            </div>
        </div>
    </nav>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <!-- Metrics Cards -->
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5 mb-8">
            {% for state in ['pending', 'processing', 'completed', 'failed', 'dead'] %}
            <div class="bg-white overflow-hidden shadow rounded-lg">
                <div class="px-4 py-5 sm:p-6">
                    <dt class="text-sm font-medium text-gray-500 truncate">{{ state|title }}</dt>
                    <dd class="mt-1 text-3xl font-semibold text-gray-900">{{ metrics.get(state, 0) }}</dd>
                </div>
            </div>
            {% endfor %}
        </div>

        <!-- Performance Stats -->
        <div class="bg-white shadow rounded-lg mb-8">
            <div class="px-4 py-5 sm:p-6">
                <h3 class="text-lg font-medium text-gray-900 mb-4">Performance Metrics</h3>
                <dl class="grid grid-cols-1 gap-5 sm:grid-cols-3">
                    <div class="bg-gray-50 px-4 py-5 shadow rounded-lg sm:p-6">
                        <dt class="text-sm font-medium text-gray-500">Average Time</dt>
                        <dd class="mt-1 text-3xl font-semibold text-gray-900">
                            {{ "%.2f"|format(metrics.get('avg_time', 0)) }}s
                        </dd>
                    </div>
                    <div class="bg-gray-50 px-4 py-5 shadow rounded-lg sm:p-6">
                        <dt class="text-sm font-medium text-gray-500">Min Time</dt>
                        <dd class="mt-1 text-3xl font-semibold text-gray-900">
                            {{ "%.2f"|format(metrics.get('min_time', 0)) }}s
                        </dd>
                    </div>
                    <div class="bg-gray-50 px-4 py-5 shadow rounded-lg sm:p-6">
                        <dt class="text-sm font-medium text-gray-500">Max Time</dt>
                        <dd class="mt-1 text-3xl font-semibold text-gray-900">
                            {{ "%.2f"|format(metrics.get('max_time', 0)) }}s
                        </dd>
                    </div>
                </dl>
            </div>
        </div>

        <!-- Jobs Table -->
        <div class="bg-white shadow rounded-lg overflow-hidden">
            <div class="px-4 py-5 border-b border-gray-200 sm:px-6">
                <h3 class="text-lg font-medium text-gray-900">Recent Jobs</h3>
            </div>
            <div class="overflow-x-auto">
                <table class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50">
                        <tr>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">State</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Priority</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Attempts</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Timeout</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Time</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Command</th>
                        </tr>
                    </thead>
                    <tbody class="bg-white divide-y divide-gray-200">
                        {% for j in jobs %}
                        <tr class="hover:bg-gray-50">
                            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{{ j.id[:8] }}...</td>
                            <td class="px-6 py-4 whitespace-nowrap">
                                <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full
                                    {% if j.state == 'completed' %}bg-green-100 text-green-800
                                    {% elif j.state == 'failed' %}bg-red-100 text-red-800
                                    {% elif j.state == 'processing' %}bg-blue-100 text-blue-800
                                    {% elif j.state == 'dead' %}bg-gray-100 text-gray-800
                                    {% else %}bg-yellow-100 text-yellow-800{% endif %}">
                                    {{ j.state }}
                                </span>
                            </td>
                            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                {% if j.get('priority', 0) > 5 %}
                                <span class="text-red-600 font-medium">{{ j.get('priority', 0) }}</span>
                                {% else %}
                                {{ j.get('priority', 0) }}
                                {% endif %}
                            </td>
                            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ j.attempts }}/{{ j.max_retries }}</td>
                            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ j.get('timeout_seconds', '-') }}</td>
                            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                {% if j.get('execution_time') %}{{ "%.2f"|format(j.execution_time) }}s{% else %}-{% endif %}
                            </td>
                            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                <code class="bg-gray-100 px-2 py-1 rounded">{{ j.command }}</code>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
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
