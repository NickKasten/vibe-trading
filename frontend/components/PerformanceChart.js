import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import ApiClient from '../utils/api';

export default function PerformanceChart() {
  const [performance, setPerformance] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedPeriod, setSelectedPeriod] = useState(30);

  useEffect(() => {
    fetchPerformance();
  }, [selectedPeriod]);

  const fetchPerformance = async () => {
    try {
      setLoading(true);
      const data = await ApiClient.getPerformance(selectedPeriod);
      setPerformance(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatChartData = (portfolioData, benchmarkData) => {
    const merged = new Map();

    const appendSeries = (series, key) => {
      if (!Array.isArray(series)) return;

      series.forEach((point) => {
        if (!point?.timestamp) return;
        const timestamp = point.timestamp;
        const dateLabel = new Date(timestamp).toLocaleDateString();
        const existing = merged.get(timestamp) || { timestamp, date: dateLabel };
        if (typeof point.equity === 'number' || point.equity) {
          existing[key] = parseFloat(point.equity);
        }
        merged.set(timestamp, existing);
      });
    };

    appendSeries(portfolioData, 'portfolioEquity');
    appendSeries(benchmarkData, 'benchmarkEquity');

    return Array.from(merged.values()).sort(
      (a, b) => new Date(a.timestamp) - new Date(b.timestamp)
    );
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(value);
  };

  const periods = [
    { value: 7, label: '7D' },
    { value: 30, label: '30D' },
    { value: 90, label: '90D' },
    { value: 365, label: '1Y' }
  ];

  if (loading) {
    return (
      <div className="bg-white overflow-hidden shadow rounded-lg">
        <div className="p-6">
          <div className="animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-1/3 mb-4"></div>
            <div className="h-64 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white overflow-hidden shadow rounded-lg">
        <div className="p-6 text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100 text-red-600">
            <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v3m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900">Unable to load performance data</h3>
          <p className="mt-2 text-sm text-gray-600">
            We couldn’t retrieve the equity curve. Ensure the backend has `equity` records and that the service is
            reachable from this deployment.
          </p>
          <div className="mt-4 flex justify-center space-x-3 text-xs text-gray-500">
            <span>• Confirm Supabase credentials</span>
            <span>• Check Render API logs</span>
          </div>
          <button
            onClick={fetchPerformance}
            className="mt-6 inline-flex items-center rounded-md border border-transparent bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700"
          >
            Try again
          </button>
          <p className="mt-3 overflow-hidden text-ellipsis whitespace-pre-line break-all rounded bg-red-50 px-3 py-2 text-left text-xs text-red-600">
            {error}
          </p>
        </div>
      </div>
    );
  }

  const chartData = formatChartData(
    performance?.equity_curve || [],
    performance?.benchmark_curve || []
  );
  const hasBenchmark = chartData.some((point) => typeof point.benchmarkEquity === 'number');
  const metricsGridClass = hasBenchmark ? 'md:grid-cols-5' : 'md:grid-cols-4';

  return (
    <div className="bg-white overflow-hidden shadow rounded-lg">
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg leading-6 font-medium text-gray-900">Performance Chart</h3>
          <div className="flex space-x-2">
            {periods.map(period => (
              <button
                key={period.value}
                onClick={() => setSelectedPeriod(period.value)}
                className={`px-3 py-1 text-sm rounded ${
                  selectedPeriod === period.value
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {period.label}
              </button>
            ))}
          </div>
        </div>

        {performance?.metrics && (
          <div className={`grid grid-cols-1 ${metricsGridClass} gap-4 mb-6`}>
            <div className="text-center">
              <dt className="text-sm font-medium text-gray-500">Initial Equity</dt>
              <dd className="mt-1 text-lg font-semibold text-gray-900">
                {formatCurrency(performance.metrics.initial_equity)}
              </dd>
            </div>
            <div className="text-center">
              <dt className="text-sm font-medium text-gray-500">Final Equity</dt>
              <dd className="mt-1 text-lg font-semibold text-gray-900">
                {formatCurrency(performance.metrics.final_equity)}
              </dd>
            </div>
            <div className="text-center">
              <dt className="text-sm font-medium text-gray-500">Total Return</dt>
              <dd className={`mt-1 text-lg font-semibold ${
                performance.metrics.total_return_percent >= 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                {performance.metrics.total_return_percent >= 0 ? '+' : ''}
                {performance.metrics.total_return_percent.toFixed(2)}%
              </dd>
            </div>
            <div className="text-center">
              <dt className="text-sm font-medium text-gray-500">Period</dt>
              <dd className="mt-1 text-lg font-semibold text-gray-900">
                {performance.metrics.period_days} days
              </dd>
            </div>
            {performance?.benchmark_metrics && (
              <div className="text-center">
                <dt className="text-sm font-medium text-gray-500">
                  {`Benchmark (${performance?.benchmark_symbol || 'SPY'})`}
                </dt>
                <dd className={`mt-1 text-lg font-semibold ${
                  performance.benchmark_metrics.total_return_percent >= 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {performance.benchmark_metrics.total_return_percent >= 0 ? '+' : ''}
                  {performance.benchmark_metrics.total_return_percent.toFixed(2)}%
                </dd>
              </div>
            )}
          </div>
        )}

        <div className="h-64">
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="date" 
                  tick={{ fontSize: 12 }}
                  interval="preserveStartEnd"
                />
                <YAxis 
                  tick={{ fontSize: 12 }}
                  tickFormatter={(value) => `$${(value / 1000).toFixed(0)}K`}
                />
                <Tooltip 
                  formatter={(value, name) => [
                    formatCurrency(value),
                    name === 'portfolioEquity' ? 'Portfolio Equity' : 'S&P 500 (normalized)'
                  ]}
                  labelFormatter={(label) => `Date: ${label}`}
                />
                <Legend />
                <Line 
                  type="monotone" 
                  dataKey="portfolioEquity" 
                  stroke="#2563eb" 
                  strokeWidth={2}
                  name="Portfolio Equity"
                  dot={false}
                />
                {hasBenchmark && (
                  <Line
                    type="monotone"
                    dataKey="benchmarkEquity"
                    stroke="#16a34a"
                    strokeWidth={2}
                    name="S&P 500 (Normalized)"
                    dot={false}
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500">
              No performance data available for the selected period
            </div>
          )}
        </div>

        <div className="mt-4 text-xs text-gray-400 text-center">
          Data delayed {performance?.data_delay_minutes ?? 15} minutes
          {performance?.benchmark_metrics ? ' • Benchmark normalized to starting equity' : ''}
        </div>
      </div>
    </div>
  );
}
